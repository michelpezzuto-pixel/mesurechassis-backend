"""Dépendances FastAPI : auth, RBAC, abonnement, Expo Push.

Toutes les fonctions partagées par plusieurs routeurs vivent ici.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from passlib.context import CryptContext

from db import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGO,
    JWT_SECRET,
    TRIAL_DAYS,
    db,
    logger,
)
from models import UserPublic

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Password hashing ----------------------------------------------------
def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --- JWT -----------------------------------------------------------------
def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": user_id, "role": role, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )


def user_to_public(doc: dict) -> UserPublic:
    return UserPublic(
        id=doc["id"],
        name=doc["name"],
        email=doc["email"],
        role=doc["role"],
        company_id=doc.get("company_id", "default"),
    )


# --- Company helper ------------------------------------------------------
async def ensure_company(company_id: str) -> dict:
    """Idempotent : charge ou crée la société (essai 90 jours)."""
    doc = await db.companies.find_one(
        {"company_id": company_id}, {"_id": 0}
    )
    if doc:
        update: dict = {}
        if "subscription_status" not in doc:
            update["subscription_status"] = "trial"
        if "subscription_expires_at" not in doc:
            update["subscription_expires_at"] = (
                datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
            ).isoformat()
        if "plan" not in doc:
            # Préserve l'expérience existante : les comptes pré-Freemium
            # restent en "trial" (accès Pro 90j). Les nouveaux comptes
            # peuvent être placés en "free" via /platform.
            update["plan"] = "trial"
        if "chantiers_lifetime_count" not in doc:
            update["chantiers_lifetime_count"] = await db.chantiers.count_documents(
                {"company_id": company_id}
            )
        if "cancel_at_period_end" not in doc:
            update["cancel_at_period_end"] = False
        if update:
            await db.companies.update_one(
                {"company_id": company_id}, {"$set": update}
            )
            doc.update(update)
        return doc
    new_doc = {
        "company_id": company_id,
        "name": company_id,
        "artisan_mode": False,
        "subscription_status": "trial",
        "subscription_expires_at": (
            datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
        ).isoformat(),
        "plan": "trial",
        "chantiers_lifetime_count": 0,
        "cancel_at_period_end": False,
        "cancelled_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.companies.insert_one(new_doc)
    new_doc.pop("_id", None)
    return new_doc


# --- Auth dependencies ---------------------------------------------------
async def auth_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    company_id = user.get("company_id", "default")
    company_doc = await ensure_company(company_id)
    user["artisan_mode"] = bool(company_doc.get("artisan_mode"))
    user["subscription_status"] = company_doc.get(
        "subscription_status", "trial"
    )
    user["subscription_expires_at"] = company_doc.get(
        "subscription_expires_at"
    )
    user["plan"] = company_doc.get("plan", "trial")
    user["chantiers_lifetime_count"] = int(
        company_doc.get("chantiers_lifetime_count", 0)
    )
    user["cancel_at_period_end"] = bool(
        company_doc.get("cancel_at_period_end", False)
    )
    user["cancelled_at"] = company_doc.get("cancelled_at")
    return user


def is_subscription_blocked(user: dict) -> bool:
    status = user.get("subscription_status") or "trial"
    if status == "suspended":
        return True
    expires_at = user.get("subscription_expires_at")
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(timezone.utc) > dt


async def require_active_subscription(
    user: dict = Depends(auth_user),
) -> dict:
    if is_subscription_blocked(user):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "subscription_expired",
                "message": (
                    "Votre accès a expiré. Veuillez régulariser votre abonnement."
                ),
                "subscription_status": user.get("subscription_status"),
                "subscription_expires_at": user.get("subscription_expires_at"),
            },
        )
    return user


def require_admin(
    user: dict = Depends(require_active_subscription),
) -> dict:
    if user["role"] != "admin" and not user.get("artisan_mode"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def require_roles(roles: List[str]):
    def _dep(user: dict = Depends(require_active_subscription)) -> dict:
        # Mode Artisan Unique : bypass total des restrictions RBAC
        if user.get("artisan_mode"):
            return user
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Réservé aux rôles : {', '.join(roles)}",
            )
        return user
    return _dep


# --- Expo Push -----------------------------------------------------------
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_to_user(
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """Best-effort push : ne lève jamais. Skip si pas de token."""
    u = await db.users.find_one(
        {"id": user_id}, {"_id": 0, "push_token": 1}
    )
    if not u or not u.get("push_token"):
        return
    payload = {
        "to": u["push_token"],
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.post(
                EXPO_PUSH_URL,
                json=payload,
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    "Accept": "application/json",
                },
            )
            if r.status_code >= 400:
                logger.warning(
                    "Push failed [%s]: %s", r.status_code, r.text[:200]
                )
    except Exception as exc:
        logger.warning("Push send error: %s", exc)
