"""JWT, bcrypt, time helpers and RBAC dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import JWT_ALGO, JWT_EXPIRES_HOURS, JWT_SECRET, TRIAL_DAYS
from .db import db

security = HTTPBearer(auto_error=False)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": now_utc() + timedelta(hours=JWT_EXPIRES_HOURS),
        "iat": now_utc(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not creds:
        raise HTTPException(status_code=401, detail="Token manquant")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    user.setdefault("solo_mode", False)
    # Compute trial / subscription state for downstream code & API responses
    user.update(compute_access_state(user))
    return user


def compute_access_state(user: dict) -> dict:
    """Returns trial / subscription fields ready to attach to a user dict."""
    trial_start = user.get("trial_start_date") or user.get("created_at") or now_utc()
    # Ensure tz-aware
    if trial_start.tzinfo is None:
        trial_start = trial_start.replace(tzinfo=timezone.utc)
    elapsed = (now_utc() - trial_start).days
    trial_days_remaining = max(0, TRIAL_DAYS - elapsed)
    is_trial_active = trial_days_remaining > 0
    subscription_active = bool(user.get("subscription_active"))
    is_locked = (not is_trial_active) and (not subscription_active)
    return {
        "trial_start_date": trial_start,
        "trial_days_remaining": trial_days_remaining,
        "is_trial_active": is_trial_active,
        "subscription_active": subscription_active,
        "is_locked": is_locked,
    }


async def require_active_access(user=Depends(get_current_user)):
    """Use this dependency on routes that must be blocked by the paywall."""
    if user.get("is_locked"):
        raise HTTPException(
            status_code=402,
            detail="Période d'essai terminée. Un abonnement actif est requis.",
        )
    return user


def require_roles(*roles: str):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé (rôles autorisés: {', '.join(roles)})",
            )
        # Roles also enforce paywall (admin/technicien are paid features)
        if user.get("is_locked"):
            raise HTTPException(
                status_code=402,
                detail="Période d'essai terminée. Un abonnement actif est requis.",
            )
        return user
    return checker


def has_admin_powers(user) -> bool:
    """Admin always has admin powers."""
    return user["role"] == "admin"


def has_technician_powers(user) -> bool:
    """Technicien always; admin only if solo_mode is enabled."""
    return user["role"] == "technicien" or (user["role"] == "admin" and user.get("solo_mode"))


def project_visible_to(user) -> dict:
    """MongoDB filter restricting projects to the user's scope.

    - Admin: sees everything.
    - Technicien: sees assigned + unassigned projects.
    """
    if user["role"] == "admin":
        return {}
    if user["role"] == "technicien":
        return {"$or": [{"technicien_id": user["id"]}, {"technicien_id": None}]}
    return {"_never_match": True}
