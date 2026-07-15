"""Dépendances FastAPI : auth, RBAC, abonnement, Expo Push.

Toutes les fonctions partagées par plusieurs routeurs vivent ici.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from passlib.context import CryptContext

from db import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    BETA_MODE,
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
        status=doc.get("status") or "active",
        email_verified_at=doc.get("email_verified_at"),
    )


# --- Company helper ------------------------------------------------------
async def ensure_company(company_id: str) -> dict:
    """Idempotent : charge ou crée la société.

    🚧 BETA GRATUITE (`BETA_MODE=True` dans db.py) : tous les comptes
    sont forcés en `plan=pro` + `subscription_status=active` + `expires_at`
    long terme. Aucun lockout n'est appliqué. À désactiver quand Stripe
    sera prêt.
    """
    # Date d'expiration "loin dans le futur" pour la beta : 10 ans.
    beta_expires_at = (
        datetime.now(timezone.utc) + timedelta(days=365 * 10)
    ).isoformat()

    doc = await db.companies.find_one(
        {"company_id": company_id}, {"_id": 0}
    )
    if doc:
        update: dict = {}
        # 🍎 Exception ciblée : le compte apple-review-expired doit RESTER
        # expiré pour qu'Apple puisse tester le paywall iOS (Guideline 2.1).
        # Aucun forçage BETA_MODE pour cette company_id précise.
        is_apple_expired_demo = company_id == "apple-review-expired"

        if BETA_MODE and not is_apple_expired_demo:
            # Force tout le monde en plan Pro actif pendant la phase beta.
            if doc.get("plan") != "pro":
                update["plan"] = "pro"
            if doc.get("subscription_status") != "active":
                update["subscription_status"] = "active"
            # Renouvelle l'expiration si elle est dans moins d'1 an.
            try:
                exp_iso = doc.get("subscription_expires_at")
                needs_renew = True
                if exp_iso:
                    exp_dt = datetime.fromisoformat(
                        str(exp_iso).replace("Z", "+00:00")
                    )
                    if exp_dt > datetime.now(timezone.utc) + timedelta(days=365):
                        needs_renew = False
                if needs_renew:
                    update["subscription_expires_at"] = beta_expires_at
            except ValueError:
                update["subscription_expires_at"] = beta_expires_at
        else:
            # --- Logique historique (Trial/Free) — réactivable à la fin de la beta.
            if "subscription_status" not in doc:
                update["subscription_status"] = "trial"
            if "subscription_expires_at" not in doc:
                update["subscription_expires_at"] = (
                    datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)
                ).isoformat()
            if "plan" not in doc:
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

    # Création d'une nouvelle société
    if BETA_MODE:
        new_doc = {
            "company_id": company_id,
            "name": company_id,
            "artisan_mode": False,
            "subscription_status": "active",
            "subscription_expires_at": beta_expires_at,
            "plan": "pro",
            "chantiers_lifetime_count": 0,
            "cancel_at_period_end": False,
            "cancelled_at": None,
            "beta_account": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
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
    # Double opt-in : refus immédiat des comptes non vérifiés / suspendus.
    status = user.get("status") or "active"
    # 🛡️ RGPD soft-delete : invalidation immédiate des JWT zombies.
    # Si un attaquant détient un token volé d'un user supprimé, on lui
    # refuse l'accès sans révéler la raison exacte (sécurité).
    if status == "deleted":
        raise HTTPException(status_code=401, detail="Compte supprimé.")
    if status == "pending_verification":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": (
                    "Votre adresse email n'a pas encore été vérifiée. "
                    "Cliquez sur le lien envoyé par email pour activer votre compte."
                ),
            },
        )
    if status == "suspended":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "user_suspended",
                "message": "Votre compte a été suspendu.",
            },
        )
    user["status"] = status
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
    # 🍎 Exception ciblée : le compte applereview-expired doit TOUJOURS être
    # bloqué (paywall) pour qu'Apple puisse tester le flux d'expiration
    # sur iOS (Guideline 2.1). Aucun bypass BETA_MODE.
    if user.get("company_id") == "apple-review-expired":
        return True
    # 🚧 BETA GRATUITE : jamais de blocage tant que BETA_MODE=True.
    if BETA_MODE:
        return False
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


# 🔐 Outils internes plateforme (campagne emailing, LinkedIn, testeurs) :
# réservés au propriétaire de MesureChâssis — PAS aux admins clients.
# Configurable via env PLATFORM_OWNER_EMAILS (liste séparée par virgules).
PLATFORM_OWNER_EMAILS = {
    e.strip().lower()
    for e in os.environ.get(
        "PLATFORM_OWNER_EMAILS",
        "info@mesurechassis.com,artisan@mesurechassis.fr,michelpezzuto@hotmail.com,michelpezzuto@gmail.com",
    ).split(",")
    if e.strip()
}


def require_platform_owner(
    user: dict = Depends(require_active_subscription),
) -> dict:
    email = (user.get("email") or "").lower()
    if user["role"] != "admin" or email not in PLATFORM_OWNER_EMAILS:
        raise HTTPException(
            status_code=403,
            detail="Réservé au propriétaire de la plateforme",
        )
    return user


# 🔒 Build 12 (juin 2026) — Emails techniques exemptés du verrou TVA
# (CompleteVatScreen frontend). Réservé aux comptes plateforme + Apple
# Review + super admin, qui n'ont pas vocation à émettre des factures
# clients. Tout le monde d'autre voit l'écran tant que la TVA n'est pas
# renseignée (Apple 3.1.3(c) + Stripe UE).
VAT_CHECK_EXEMPT_EMAILS = PLATFORM_OWNER_EMAILS | {
    "applereview@mesurechassis.com",
    "admin@mesurechassis.fr",
}


def user_needs_vat_completion(user_doc: dict, company_doc: Optional[dict]) -> bool:
    """Retourne True si l'utilisateur doit compléter sa TVA avant d'accéder
    à l'app. Le calcul est fait à la volée dans /auth/me et
    /auth/google/session — jamais stocké en DB.

    Règles d'exemption :
      - Email dans VAT_CHECK_EXEMPT_EMAILS (owners plateforme + apple review
        + super admin technique).
      - Company avec `vat_number` déjà renseigné.
    """
    email = (user_doc.get("email") or "").lower()
    if email in VAT_CHECK_EXEMPT_EMAILS:
        return False
    if not company_doc:
        return True
    return not bool(company_doc.get("vat_number"))


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
