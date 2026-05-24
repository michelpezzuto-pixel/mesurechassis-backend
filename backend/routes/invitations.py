"""Routes Invitations — Master Admin invite Commercial/Technicien."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import (
    auth_user,
    create_access_token,
    hash_password,
    require_admin,
    user_to_public,
)
from email_service import build_invitation_link, send_invitation_email
from models import (
    InvitationAccept,
    InvitationCreate,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter()


VALID_INVITE_ROLES = {"commercial", "technician"}
INVITE_TTL_DAYS = 7


def _new_token() -> str:
    return secrets.token_urlsafe(32)


@router.post("/admin/invitations", response_model=RegisterResponse)
async def create_invitation(
    payload: InvitationCreate,
    user=Depends(require_admin),
):
    """Le Master Admin invite un nouveau membre (Commercial ou Technicien).

    Crée l'utilisateur en `status="pending_verification"` sans mot de passe.
    L'invité définit son mot de passe via `POST /admin/invitations/{token}/accept`
    qui valide aussi l'email simultanément.
    """
    if payload.role not in VALID_INVITE_ROLES:
        raise HTTPException(
            400,
            f"Rôle invalide. Autorisés : {sorted(VALID_INVITE_ROLES)}",
        )

    # 🚫 Compte Artisan : pas d'équipe possible. Les Artisans paient un
    # abonnement solo (24,99 €/mois), ils ne peuvent inviter personne.
    company_id = user.get("company_id", "default")
    company_doc = await db.companies.find_one(
        {"company_id": company_id}, {"_id": 0, "account_type": 1}
    ) or {}
    if (company_doc.get("account_type") or "entreprise") == "artisan":
        raise HTTPException(
            403,
            "Les comptes Artisan sont limités à un seul utilisateur. "
            "Pour inviter des collaborateurs, passez à un compte Entreprise.",
        )

    email_lower = payload.email.lower()
    existing = await db.users.find_one({"email": email_lower})
    if existing:
        raise HTTPException(400, "Cet email est déjà enregistré.")

    user_doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": email_lower,
        "role": payload.role,
        "company_id": company_id,
        # Pas de hashed_password : sera défini lors de l'acceptation.
        "hashed_password": None,
        "status": "pending_verification",
        "email_verified_at": None,
        "invited_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)

    token = _new_token()
    await db.email_verifications.insert_one(
        {
            "token": token,
            "user_id": user_doc["id"],
            "email": email_lower,
            "kind": "invite",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)
            ).isoformat(),
            "used": False,
        }
    )
    link = build_invitation_link(token)

    # Nom commercial de la société pour personnaliser l'email
    company = await db.companies.find_one(
        {"company_id": company_id}, {"_id": 0, "name": 1}
    )
    company_name = (company or {}).get("name", company_id)

    send_invitation_email(
        to=email_lower,
        name=payload.name,
        role=payload.role,
        company_name=company_name,
        link=link,
    )

    return RegisterResponse(
        user=user_to_public(user_doc),
        verification_link=link,  # MOCK MVP : exposé pour démo
        message=(
            f"Invitation envoyée à {email_lower}. "
            f"Le lien expire dans {INVITE_TTL_DAYS} jours."
        ),
    )


@router.get("/admin/invitations/{token}")
async def get_invitation(token: str):
    """Récupère les infos de l'invitation pour afficher la page d'acceptation."""
    rec = await db.email_verifications.find_one({"token": token}, {"_id": 0})
    if not rec or rec.get("kind") != "invite":
        raise HTTPException(404, "Invitation introuvable")
    if rec.get("used"):
        raise HTTPException(400, "Cette invitation a déjà été utilisée")
    try:
        expires = datetime.fromisoformat(
            str(rec["expires_at"]).replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(400, "Invitation expirée")
    except ValueError:
        raise HTTPException(400, "Invitation malformée")
    user = await db.users.find_one(
        {"id": rec["user_id"]}, {"_id": 0, "hashed_password": 0}
    )
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    company = await db.companies.find_one(
        {"company_id": user.get("company_id", "default")},
        {"_id": 0, "name": 1},
    )
    return {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "company_name": (company or {}).get("name"),
        "expires_at": rec["expires_at"],
    }


@router.post(
    "/admin/invitations/{token}/accept", response_model=TokenResponse
)
async def accept_invitation(token: str, payload: InvitationAccept):
    """Acceptation d'invitation : définit le mot de passe + valide l'email."""
    rec = await db.email_verifications.find_one({"token": token})
    if not rec or rec.get("kind") != "invite":
        raise HTTPException(404, "Invitation introuvable")
    if rec.get("used"):
        raise HTTPException(400, "Invitation déjà utilisée")
    try:
        expires = datetime.fromisoformat(
            str(rec["expires_at"]).replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(400, "Invitation expirée")
    except ValueError:
        raise HTTPException(400, "Invitation malformée")

    if not payload.password or len(payload.password) < 6:
        raise HTTPException(
            400, "Le mot de passe doit faire au moins 6 caractères"
        )

    user = await db.users.find_one({"id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")

    now_iso = datetime.now(timezone.utc).isoformat()
    updates = {
        "hashed_password": hash_password(payload.password),
        "status": "active",
        "email_verified_at": now_iso,
    }
    if payload.name and payload.name.strip():
        updates["name"] = payload.name.strip()

    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    await db.email_verifications.update_one(
        {"token": token},
        {"$set": {"used": True, "used_at": now_iso}},
    )
    user.update(updates)

    jwt_token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=jwt_token, user=user_to_public(user))
