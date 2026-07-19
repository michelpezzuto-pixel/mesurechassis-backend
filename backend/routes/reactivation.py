"""
Routes de réactivation de compte ("Seconde Chance").

Flux 100 % automatisé :
1. User supprimé tente une nouvelle inscription avec la même adresse email
   → l'endpoint /auth/register détecte le match via `original_email_hash`
     et renvoie 409 avec un code métier explicite :
       - ACCOUNT_DELETED_CAN_REACTIVATE  (reactivation_count < 1)
       - ACCOUNT_DELETED_QUOTA_EXHAUSTED (reactivation_count >= 1)
2. L'app affiche un modal "Vous avez déjà eu un compte..."
   avec un bouton "Réactiver mon compte" qui appelle
     POST /auth/reactivation/request { email }
3. Le backend :
   - Vérifie le compteur < 1
   - Génère un token JWT (24 h)
   - Incrémente le compteur → 1
   - Envoie un email de confirmation à l'utilisateur (Resend)
4. L'utilisateur clique le lien magique → GET/POST /auth/reactivation/confirm
   → le compte est restauré (status=active, mdp reset, email restauré)

Sécurité :
- Le hash `original_email_hash` (SHA-256) est utilisé pour la recherche RGPD-friendly
- Le token est signé JWT + stocké en DB (single-use)
- Le compteur est incrémenté de façon atomique ($inc MongoDB)
- Admin override disponible via POST /admin/reactivation/override

Auteur : MesureChâssis, juillet 2026.
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from db import db
from deps import (
    auth_user,
    create_access_token,
    hash_password,
    require_platform_owner,
)
from email_service import send_email, _build_link

load_dotenv()
logger = logging.getLogger("mesurechassis.reactivation")

router = APIRouter()


# ────────────────────────────────────────────────────────────────────────────
# Constantes
# ────────────────────────────────────────────────────────────────────────────

REACTIVATION_TOKEN_TTL_HOURS = 24
REACTIVATION_QUOTA_MAX = 1  # Maximum 1 réactivation par email

# Codes d'erreur métier exposés au frontend (à partager dans l'app)
CODE_CAN_REACTIVATE = "ACCOUNT_DELETED_CAN_REACTIVATE"
CODE_QUOTA_EXHAUSTED = "ACCOUNT_DELETED_QUOTA_EXHAUSTED"


# ────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ────────────────────────────────────────────────────────────────────────────


def hash_email(email: str) -> str:
    """Hash SHA-256 (stable + irréversible) d'un email normalisé.
    Utilisé pour rechercher un utilisateur supprimé sans exposer son email en
    clair (RGPD-friendly).
    """
    normalized = (email or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _find_deleted_user_by_email(email: str) -> Optional[dict]:
    """Retourne le user (status='deleted') dont l'email d'origine correspond,
    ou None si aucun match."""
    h = hash_email(email)
    return await db.users.find_one(
        {
            "status": "deleted",
            "original_email_hash": h,
        }
    )


# ────────────────────────────────────────────────────────────────────────────
# Modèles de requête
# ────────────────────────────────────────────────────────────────────────────


class ReactivationRequestIn(BaseModel):
    email: EmailStr


class ReactivationConfirmIn(BaseModel):
    token: str
    new_password: str


class AdminOverrideIn(BaseModel):
    email: EmailStr
    reason: Optional[str] = None


# ────────────────────────────────────────────────────────────────────────────
# 1. Demande de réactivation
# ────────────────────────────────────────────────────────────────────────────


@router.post("/auth/reactivation/request")
async def request_reactivation(payload: ReactivationRequestIn, request: Request):
    """
    Génère un token de réactivation et envoie un email au user.
    Idempotent côté réponse (on ne révèle jamais si l'email existe ou non
    dans le message d'erreur générique pour éviter les fuites d'info).

    Réponses possibles :
    - 200 { ok: true, message: "..." }  → email envoyé (ou faux-positif silencieux)
    - 409 { code: "ACCOUNT_DELETED_QUOTA_EXHAUSTED", message: "..." }
    """
    email = payload.email.lower().strip()
    user = await _find_deleted_user_by_email(email)

    # Réponse générique (anti-énumération) si l'email n'a jamais eu de compte
    # ou si le compte n'a jamais été supprimé.
    generic_response = {
        "ok": True,
        "message": (
            "Si votre adresse correspond à un compte supprimé récemment, "
            "vous allez recevoir un email de réactivation dans quelques minutes."
        ),
    }

    if not user:
        # Pas de compte supprimé → réponse générique (pas d'erreur)
        return generic_response

    # Vérif quota
    count = int(user.get("reactivation_count", 0) or 0)
    if count >= REACTIVATION_QUOTA_MAX:
        raise HTTPException(
            status_code=409,
            detail={
                "code": CODE_QUOTA_EXHAUSTED,
                "message": (
                    "Votre quota de réactivation est atteint. Veuillez "
                    "utiliser un nouvel identifiant (autre adresse email) "
                    "pour créer un compte, ou contactez info@mesurechassis.com "
                    "pour un cas exceptionnel."
                ),
            },
        )

    # Génération du token (32 bytes urlsafe) + expiration 24 h
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=REACTIVATION_TOKEN_TTL_HOURS)
    ).isoformat()

    # Enregistrement atomique du token + incrément du compteur
    await db.reactivation_tokens.insert_one(
        {
            "token": token,
            "user_id": user["id"],
            "email_hash": user["original_email_hash"],
            "created_at": _now_iso(),
            "expires_at": expires_at,
            "used_at": None,
        }
    )

    await db.users.update_one(
        {"id": user["id"]},
        {
            "$inc": {"reactivation_count": 1},
            "$set": {"reactivation_requested_at": _now_iso()},
        },
    )

    # Envoi de l'email de réactivation
    original_email = user.get("original_email") or email
    name = user.get("name") or "Cher artisan"

    link = _build_link("/reactivation", token)
    subject = "🔓 Réactivation de votre compte MesureChâssis"
    body_text = (
        f"Bonjour {name},\n\n"
        "Vous avez demandé à réactiver votre compte MesureChâssis. "
        "Bonne nouvelle : vous pouvez le faire dès maintenant en cliquant "
        "sur le lien ci-dessous.\n\n"
        f"👉 Réactiver mon compte : {link}\n\n"
        "⚠️ Important :\n"
        "• Ce lien est valable 24 heures.\n"
        "• Vous devrez définir un nouveau mot de passe lors de la réactivation.\n"
        "• Cette réactivation est unique — vous ne pourrez plus réactiver "
        "ce compte après cette fois.\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez simplement "
        "cet email. Aucun changement n'a été effectué.\n\n"
        "L'équipe MesureChâssis\n"
        "https://mesurechassis.com"
    )

    try:
        send_email(
            to=original_email,
            subject=subject,
            body=body_text,
            link=link,
            founder_bcc=True,  # 🔔 Michel voit chaque tentative de retour user
        )
    except Exception as e:
        # On log l'erreur mais on ne l'expose pas au user
        logger.exception("Reactivation email delivery failed: %s", e)

    logger.info(
        "Reactivation requested for user_id=%s (count=%d)",
        user["id"],
        count + 1,
    )

    return {
        "ok": True,
        "message": (
            "Un email de réactivation vient de vous être envoyé. "
            "Vérifiez votre boîte de réception (et vos spams). "
            "Le lien est valable 24 heures."
        ),
    }


# ────────────────────────────────────────────────────────────────────────────
# 2. Vérification préalable du token (avant affichage du formulaire mdp)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/auth/reactivation/verify/{token}")
async def verify_reactivation_token(token: str):
    """Endpoint appelé par l'app quand l'utilisateur clique sur le lien magique.
    Vérifie que le token est valide (existe, non expiré, non utilisé) et
    retourne l'email du compte à réactiver pour affichage."""
    doc = await db.reactivation_tokens.find_one({"token": token})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Lien de réactivation invalide ou déjà utilisé.",
        )
    if doc.get("used_at"):
        raise HTTPException(
            status_code=410,
            detail="Ce lien de réactivation a déjà été utilisé.",
        )
    try:
        exp = datetime.fromisoformat(doc["expires_at"])
    except Exception:
        exp = datetime.now(timezone.utc) - timedelta(hours=1)
    if exp <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=410,
            detail="Ce lien de réactivation a expiré. Contactez le support.",
        )

    user = await db.users.find_one(
        {"id": doc["user_id"]},
        {"_id": 0, "id": 1, "name": 1, "original_email": 1, "status": 1},
    )
    if not user:
        raise HTTPException(404, "Compte introuvable")

    return {
        "ok": True,
        "email": user.get("original_email", ""),
        "name": user.get("name", ""),
        "expires_at": doc["expires_at"],
    }


# ────────────────────────────────────────────────────────────────────────────
# 3. Confirmation & restauration du compte
# ────────────────────────────────────────────────────────────────────────────


@router.post("/auth/reactivation/confirm")
async def confirm_reactivation(payload: ReactivationConfirmIn):
    """Restaure le compte : email, statut, nouveau mot de passe.
    Renvoie un JWT pour connecter l'utilisateur directement."""
    token = payload.token.strip()
    new_password = payload.new_password

    if len(new_password) < 8:
        raise HTTPException(
            400, "Le mot de passe doit contenir au moins 8 caractères."
        )

    doc = await db.reactivation_tokens.find_one({"token": token})
    if not doc:
        raise HTTPException(404, "Lien invalide.")
    if doc.get("used_at"):
        raise HTTPException(410, "Ce lien a déjà été utilisé.")
    try:
        exp = datetime.fromisoformat(doc["expires_at"])
    except Exception:
        exp = datetime.now(timezone.utc) - timedelta(hours=1)
    if exp <= datetime.now(timezone.utc):
        raise HTTPException(410, "Ce lien a expiré.")

    user = await db.users.find_one({"id": doc["user_id"]})
    if not user:
        raise HTTPException(404, "Compte introuvable.")

    original_email = user.get("original_email")
    if not original_email:
        raise HTTPException(
            500,
            "Impossible de restaurer le compte : email d'origine perdu. "
            "Contactez info@mesurechassis.com.",
        )

    # Vérifie qu'aucun nouveau user n'a repris l'email entre-temps
    # (cas rarissime mais possible si l'email a été partiellement libéré)
    conflict = await db.users.find_one(
        {"email": original_email.lower(), "status": {"$ne": "deleted"}}
    )
    if conflict:
        raise HTTPException(
            409,
            "Cette adresse email est actuellement utilisée par un autre "
            "compte actif. Contactez info@mesurechassis.com.",
        )

    now = _now_iso()

    # Restauration atomique
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "status": "active",
                "email": original_email.lower(),
                "hashed_password": hash_password(new_password),
                "deleted_at": None,
                "reactivated_at": now,
                "email_verified_at": user.get("email_verified_at") or now,
            }
        },
    )

    # Marquer le token comme consommé
    await db.reactivation_tokens.update_one(
        {"token": token},
        {"$set": {"used_at": now}},
    )

    # Log audit
    await db.reactivation_audit.insert_one(
        {
            "action": "reactivation_confirmed",
            "user_id": user["id"],
            "email_hash": user.get("original_email_hash"),
            "at": now,
        }
    )

    logger.info("Account reactivated: user_id=%s", user["id"])

    # JWT de session immédiate
    access_token = create_access_token(user["id"], user.get("role") or "user")
    return {
        "ok": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": original_email.lower(),
            "name": user.get("name"),
            "role": user.get("role"),
        },
        "message": "🎉 Bienvenue à nouveau ! Votre compte est réactivé.",
    }


# ────────────────────────────────────────────────────────────────────────────
# 4. Admin override — cas exceptionnels (client important, etc.)
# ────────────────────────────────────────────────────────────────────────────


@router.post("/admin/reactivation/override")
async def admin_override_quota(
    payload: AdminOverrideIn,
    _owner: str = Depends(require_platform_owner),
):
    """Reset le compteur de réactivation pour un email donné.
    Réservé au platform owner (info@mesurechassis.com etc.)."""
    user = await _find_deleted_user_by_email(payload.email)
    if not user:
        raise HTTPException(404, "Aucun compte supprimé avec cette adresse.")

    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "reactivation_count": 0,
                "reactivation_override_at": _now_iso(),
                "reactivation_override_reason": (payload.reason or "")[:500],
            }
        },
    )

    await db.reactivation_audit.insert_one(
        {
            "action": "admin_quota_override",
            "user_id": user["id"],
            "email_hash": user.get("original_email_hash"),
            "reason": payload.reason,
            "at": _now_iso(),
        }
    )

    logger.warning(
        "Admin override quota for user_id=%s reason=%r",
        user["id"],
        payload.reason,
    )

    return {
        "ok": True,
        "message": (
            "Quota de réactivation remis à zéro. L'utilisateur peut à "
            "nouveau demander une réactivation."
        ),
        "user_id": user["id"],
    }


# ────────────────────────────────────────────────────────────────────────────
# 5. Endpoint de statut (utilisé par l'app pour afficher le bon message)
# ────────────────────────────────────────────────────────────────────────────


@router.get("/auth/reactivation/status")
async def reactivation_status(email: str):
    """Retourne le statut de réactivation d'un email.
    Utilisé par l'app pour décider quel modal afficher.

    Réponses :
    - { deleted: false }                     → aucun compte supprimé
    - { deleted: true, can_reactivate: true } → 1re chance possible
    - { deleted: true, can_reactivate: false, quota_exhausted: true }
    """
    user = await _find_deleted_user_by_email(email)
    if not user:
        return {"deleted": False}
    count = int(user.get("reactivation_count", 0) or 0)
    can = count < REACTIVATION_QUOTA_MAX
    return {
        "deleted": True,
        "can_reactivate": can,
        "quota_exhausted": not can,
        "count": count,
        "max": REACTIVATION_QUOTA_MAX,
    }
