"""JWT, bcrypt, time helpers and RBAC dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import JWT_ALGO, JWT_EXPIRES_HOURS, JWT_SECRET
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
    return user


def require_roles(*roles: str):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé (rôles autorisés: {', '.join(roles)})",
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
