"""Routes d'authentification + gestion utilisateurs + double opt-in."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

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
from email_service import (
    build_verification_link,
    send_verification_email,
)
from models import (
    LoginRequest,
    PushTokenIn,
    RegisterMasterAdmin,
    RegisterResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserPublic,
    VerifyEmailRequest,
)

router = APIRouter()


VERIFICATION_TTL_DAYS = 7


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def _create_verification(
    *, user_id: str, email: str, kind: str = "verify"
) -> str:
    token = _new_token()
    await db.email_verifications.insert_one(
        {
            "token": token,
            "user_id": user_id,
            "email": email.lower(),
            "kind": kind,  # verify | invite
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(days=VERIFICATION_TTL_DAYS)
            ).isoformat(),
            "used": False,
        }
    )
    return token


# --- Master Admin self-signup (création d'une nouvelle société) ---------
@router.post("/auth/register")
async def register(payload: dict):
    """Inscription — Dual-mode :

    * **Master Admin (nouveau flux)** : payload `{name, email, password, company_name?}`
      → crée un compte `admin` en `status="pending_verification"`,
      envoie un email de vérification (MOCKÉ : lien retourné dans la réponse).

    * **Legacy/internal (tests + tooling)** : payload `{name, email, password,
      role, company_id?}` → crée un utilisateur ACTIF avec le rôle demandé,
      retourne un JWT directement (pas de double opt-in). Réservé aux tests
      et à l'usage interne. La frontale principale n'utilise PAS ce mode.
    """
    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")
    if not (name and email and password):
        raise HTTPException(400, "Champs requis : name, email, password")
    email_lower = str(email).lower()

    existing = await db.users.find_one({"email": email_lower})
    if existing:
        raise HTTPException(400, "Email déjà enregistré")

    # ---- Legacy mode ----------------------------------------------------
    if "role" in payload:
        role = payload["role"]
        if role not in VALID_ROLES:
            raise HTTPException(400, "Invalid role")
        company_id = payload.get("company_id", "default")
        user_doc = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email_lower,
            "role": role,
            "company_id": company_id,
            "hashed_password": hash_password(password),
            "status": "active",
            "email_verified_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)
        token = create_access_token(user_doc["id"], user_doc["role"])
        return {"access_token": token, "token_type": "bearer",
                "user": user_to_public(user_doc).model_dump()}

    # ---- Master Admin mode (nouveau flux, double opt-in) ----------------
    company_name = payload.get("company_name") or name
    base_slug = company_name.strip().lower()
    safe_slug = "".join(c if c.isalnum() else "-" for c in base_slug).strip("-")
    company_id = f"{safe_slug or 'co'}-{uuid.uuid4().hex[:6]}"

    user_doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email_lower,
        "role": "admin",
        "company_id": company_id,
        "hashed_password": hash_password(password),
        "status": "pending_verification",
        "email_verified_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)
    await db.companies.insert_one(
        {
            "company_id": company_id,
            "name": company_name,
            "artisan_mode": False,
            "subscription_status": "trial",
            "plan": "trial",
            "chantiers_lifetime_count": 0,
            "cancel_at_period_end": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    token = await _create_verification(
        user_id=user_doc["id"], email=email_lower, kind="verify"
    )
    link = build_verification_link(token)
    send_verification_email(to=email_lower, name=name, link=link)

    return {
        "user": user_to_public(user_doc).model_dump(),
        "verification_link": link,
        "message": (
            "Compte créé. Un email de vérification a été envoyé. "
            "Cliquez sur le lien pour activer votre compte."
        ),
    }


# --- Verify email -------------------------------------------------------
@router.post("/auth/verify", response_model=TokenResponse)
async def verify_email(payload: VerifyEmailRequest):
    rec = await db.email_verifications.find_one({"token": payload.token})
    if not rec:
        raise HTTPException(400, "Lien de vérification invalide")
    if rec.get("used"):
        raise HTTPException(400, "Lien déjà utilisé")
    try:
        expires = datetime.fromisoformat(
            str(rec["expires_at"]).replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(400, "Lien expiré (>7 jours)")
    except ValueError:
        raise HTTPException(400, "Lien malformé")

    if rec.get("kind") != "verify":
        raise HTTPException(
            400,
            "Ce lien est une invitation. Utilisez /auth/invite/accept.",
        )

    user = await db.users.find_one({"id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "status": "active",
                "email_verified_at": now_iso,
            }
        },
    )
    await db.email_verifications.update_one(
        {"token": payload.token},
        {"$set": {"used": True, "used_at": now_iso}},
    )
    user["status"] = "active"
    user["email_verified_at"] = now_iso

    # Génère un token JWT pour login automatique après vérification.
    jwt_token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=jwt_token, user=user_to_public(user))


@router.post("/auth/resend-verification")
async def resend_verification(payload: ResendVerificationRequest):
    """Renvoie un nouvel email de vérification."""
    email_lower = payload.email.lower()
    user = await db.users.find_one({"email": email_lower})
    # Ne révèle pas si l'email existe (anti-énumération)
    if not user or (user.get("status") or "active") != "pending_verification":
        return {
            "ok": True,
            "message": "Si ce compte est en attente, un nouvel email a été envoyé.",
        }
    token = await _create_verification(
        user_id=user["id"], email=email_lower, kind="verify"
    )
    link = build_verification_link(token)
    send_verification_email(to=email_lower, name=user["name"], link=link)
    return {"ok": True, "verification_link": link}


# --- Login --------------------------------------------------------------
@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not user.get("hashed_password") or not verify_password(
        payload.password, user["hashed_password"]
    ):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    status = user.get("status") or "active"
    if status == "pending_verification":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": (
                    "Votre adresse email n'a pas encore été vérifiée. "
                    "Cliquez sur le lien envoyé par email pour activer votre compte."
                ),
                "email": user["email"],
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
    payload: PushTokenIn, user=Depends(auth_user)
):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"push_token": payload.push_token}},
    )
    return {"ok": True}
