"""Routes d'authentification + gestion utilisateurs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from db import VALID_ROLES, db
from deps import (
    auth_user,
    create_access_token,
    hash_password,
    require_active_subscription,
    user_to_public,
    verify_password,
)
from models import (
    LoginRequest,
    PushTokenIn,
    TokenResponse,
    UserCreate,
    UserPublic,
)

router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
async def register(payload: UserCreate):
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, "Invalid role")
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    user_doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email.lower(),
        "role": payload.role,
        "company_id": payload.company_id,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    token = create_access_token(user_doc["id"], user_doc["role"])
    return TokenResponse(access_token=token, user=user_to_public(user_doc))


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=token, user=user_to_public(user))


@router.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(auth_user)):
    return user_to_public(user)


@router.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(require_active_subscription)):
    docs = await db.users.find(
        {"company_id": user.get("company_id", "default")},
        {"_id": 0, "hashed_password": 0},
    ).to_list(500)
    return [user_to_public(d) for d in docs]


@router.post("/auth/push-token")
async def set_push_token(
    payload: PushTokenIn, user=Depends(require_active_subscription)
):
    await db.users.update_one(
        {"id": user["id"]}, {"$set": {"push_token": payload.push_token}}
    )
    return {"ok": True}
