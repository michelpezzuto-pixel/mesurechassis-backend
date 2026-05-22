"""Authentication + Users (Admin invites Technicien)."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import (
    get_current_user, hash_password, make_token, now_utc,
    require_roles, verify_password,
)
from models.schemas import (
    AuthResponse, InviteUserRequest, LoginRequest, ProfileUpdate,
    RegisterRequest, UserPublic,
)

router = APIRouter()


@router.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": req.email.lower(),
        "full_name": req.full_name,
        "company_name": req.company_name or req.full_name,
        "role": "admin",
        "solo_mode": False,
        "password_hash": hash_password(req.password),
        "created_at": now_utc(),
    }
    await db.users.insert_one(user_doc)
    token = make_token(user_id, "admin")
    user_doc.pop("password_hash")
    user_doc.pop("_id", None)
    return AuthResponse(token=token, user=UserPublic(**user_doc))


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    token = make_token(user["id"], user["role"])
    user.pop("password_hash", None)
    user.pop("_id", None)
    user.setdefault("solo_mode", False)
    return AuthResponse(token=token, user=UserPublic(**user))


@router.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return UserPublic(**user)


@router.put("/auth/me", response_model=UserPublic)
async def update_me(payload: ProfileUpdate, user=Depends(get_current_user)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "solo_mode" in update and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Le mode artisan unique est réservé aux Admin")
    if update:
        await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    fresh.setdefault("solo_mode", False)
    return UserPublic(**fresh)


@router.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(require_roles("admin"))):
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for r in rows:
        r.setdefault("solo_mode", False)
    return [UserPublic(**r) for r in rows]


@router.post("/users", response_model=UserPublic)
async def invite_user(req: InviteUserRequest, user=Depends(require_roles("admin"))):
    if await db.users.find_one({"email": req.email.lower()}):
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": req.email.lower(),
        "full_name": req.full_name,
        "company_name": user.get("company_name"),
        "role": req.role,
        "solo_mode": False,
        "password_hash": hash_password(req.password),
        "created_at": now_utc(),
    }
    await db.users.insert_one(doc)
    doc.pop("password_hash")
    doc.pop("_id", None)
    return UserPublic(**doc)


@router.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(require_roles("admin"))):
    if uid == user["id"]:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas vous supprimer vous-même")
    res = await db.users.delete_one({"id": uid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {"ok": True}
