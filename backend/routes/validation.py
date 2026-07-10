"""
Module de validation "Double-Phase" — Contrôle d'accès pour la transition
gratuit → payant.

═══════════════════════════════════════════════════════════════════════════
LOGIQUE MÉTIER
═══════════════════════════════════════════════════════════════════════════

Phase 1 (actuelle) : PAYWALL_ENFORCE_VALIDATION=false → tout est libre.
Phase 2 (jour J)   : PAYWALL_ENFORCE_VALIDATION=true  → verrouillage actif.

Un utilisateur peut utiliser l'app si (règle OR) :
  a) PAYWALL_ENFORCE_VALIDATION == false                    (Phase 1)
  b) user.role == "admin"                                    (le gérant)
  c) user.account_type == "artisan"                          (solo)
  d) user.validation_status == "validated"                   (approuvé)
  e) user.validation_status == "legacy" ET dans la période de grâce (30 j)

Sinon → 403 avec le code métier PAYWALL_VALIDATION_REQUIRED.

═══════════════════════════════════════════════════════════════════════════
CHAMPS AJOUTÉS SUR CHAQUE USER
═══════════════════════════════════════════════════════════════════════════

validation_status: "unvalidated" | "pending" | "validated" | "rejected" | "legacy"
validated_at: ISO datetime (quand approuvé)
validated_by: user_id du gérant qui a approuvé
validation_requested_at: ISO datetime (dernière demande)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import auth_user, require_roles
from email_service import send_email

load_dotenv()
logger = logging.getLogger("mesurechassis.validation")

router = APIRouter()

# ────────────────────────────────────────────────────────────────────────
# Feature flag & période de grâce (contrôlés par variables d'environnement)
# ────────────────────────────────────────────────────────────────────────


def is_enforcement_active() -> bool:
    """True si le kill switch est activé (Phase 2)."""
    return os.environ.get("PAYWALL_ENFORCE_VALIDATION", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def grace_period_end() -> Optional[datetime]:
    """Retourne la date de fin de la période de grâce (30 jours après le
    basculement en Phase 2) ou None si non défini.

    Contrôlé par la variable d'env PAYWALL_GRACE_PERIOD_START (ISO date).
    Ex : PAYWALL_GRACE_PERIOD_START=2027-01-15T00:00:00+00:00
    """
    start = os.environ.get("PAYWALL_GRACE_PERIOD_START")
    if not start:
        return None
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return None
    return start_dt + timedelta(days=30)


def in_grace_period() -> bool:
    end = grace_period_end()
    if end is None:
        return False
    return datetime.now(timezone.utc) < end


def user_can_access(user: dict) -> tuple[bool, Optional[str]]:
    """Retourne (True, None) si l'user peut accéder, sinon (False, reason)."""
    if not is_enforcement_active():
        return True, None  # Phase 1 → tout est libre
    if user.get("role") == "admin":
        return True, None
    if user.get("account_type") == "artisan":
        return True, None
    status = user.get("validation_status", "unvalidated")
    if status == "validated":
        return True, None
    if status == "legacy" and in_grace_period():
        return True, None
    if status == "rejected":
        return False, "rejected"
    return False, "unvalidated"


# ────────────────────────────────────────────────────────────────────────
# Modèles
# ────────────────────────────────────────────────────────────────────────


class ValidationDecision(BaseModel):
    reason: Optional[str] = None


# ────────────────────────────────────────────────────────────────────────
# Endpoints — côté GÉRANT (admin de la company)
# ────────────────────────────────────────────────────────────────────────


@router.get("/team/pending-validation")
async def list_pending_members(user=Depends(require_roles(["admin"]))):
    """Liste les membres de l'équipe en attente de validation par le gérant."""
    company_id = user.get("company_id")
    if not company_id:
        raise HTTPException(400, "Aucune company associée.")

    pending = await db.users.find(
        {
            "company_id": company_id,
            "validation_status": "pending",
            "status": "active",
            "id": {"$ne": user["id"]},
        },
        {
            "_id": 0,
            "id": 1,
            "email": 1,
            "name": 1,
            "role": 1,
            "validation_requested_at": 1,
            "created_at": 1,
        },
    ).to_list(200)

    return {"pending": pending, "count": len(pending)}


@router.post("/team/validate/{user_id}")
async def validate_member(
    user_id: str,
    payload: ValidationDecision,
    user=Depends(require_roles(["admin"])),
):
    """Le gérant approuve un ouvrier de son équipe."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "Utilisateur introuvable.")
    if target.get("company_id") != user.get("company_id"):
        raise HTTPException(403, "Cet utilisateur n'appartient pas à votre équipe.")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "validation_status": "validated",
                "validated_at": now_iso,
                "validated_by": user["id"],
            }
        },
    )

    # Notification par email à l'ouvrier
    try:
        send_email(
            to=target["email"],
            subject="✅ Votre compte MesureChâssis a été approuvé",
            body=(
                f"Bonjour {target.get('name', '')},\n\n"
                f"Bonne nouvelle : votre gérant {user.get('name', '')} vient "
                "d'approuver votre rattachement à l'entreprise sur MesureChâssis.\n\n"
                "Vous pouvez maintenant utiliser toutes les fonctionnalités "
                "de l'application sans restriction.\n\n"
                "Bon travail !\n\n"
                "L'équipe MesureChâssis"
            ),
        )
    except Exception:
        logger.exception("Notification approbation échouée")

    logger.info(
        "User %s validated by admin %s (company=%s)",
        user_id,
        user["id"],
        user.get("company_id"),
    )
    return {"ok": True, "message": f"{target.get('name', target['email'])} approuvé."}


@router.post("/team/reject/{user_id}")
async def reject_member(
    user_id: str,
    payload: ValidationDecision,
    user=Depends(require_roles(["admin"])),
):
    """Le gérant rejette un ouvrier (ex: employé qui n'est pas de l'équipe)."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "Utilisateur introuvable.")
    if target.get("company_id") != user.get("company_id"):
        raise HTTPException(403, "Cet utilisateur n'appartient pas à votre équipe.")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "validation_status": "rejected",
                "rejected_at": now_iso,
                "rejected_by": user["id"],
                "rejection_reason": (payload.reason or "")[:500],
            }
        },
    )

    logger.info(
        "User %s rejected by admin %s (reason=%r)",
        user_id,
        user["id"],
        payload.reason,
    )
    return {"ok": True, "message": "Utilisateur rejeté."}


# ────────────────────────────────────────────────────────────────────────
# Endpoints — côté OUVRIER
# ────────────────────────────────────────────────────────────────────────


@router.post("/auth/request-validation")
async def request_validation(user=Depends(auth_user)):
    """L'ouvrier (re)demande une validation à son gérant.
    Notifie le/les admins de la company par email."""
    if user.get("role") == "admin" or user.get("account_type") == "artisan":
        return {
            "ok": True,
            "message": "Votre compte ne nécessite pas de validation.",
        }
    if user.get("validation_status") == "validated":
        return {"ok": True, "message": "Votre compte est déjà validé."}

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "validation_status": "pending",
                "validation_requested_at": now_iso,
            }
        },
    )

    # Notifier tous les admins de la company
    company_id = user.get("company_id")
    admins = await db.users.find(
        {"company_id": company_id, "role": "admin", "status": "active"},
        {"_id": 0, "email": 1, "name": 1},
    ).to_list(20)

    for adm in admins:
        try:
            send_email(
                to=adm["email"],
                subject=f"🔔 {user.get('name', 'Un membre')} attend votre validation",
                body=(
                    f"Bonjour {adm.get('name', '')},\n\n"
                    f"{user.get('name', user['email'])} ({user['email']}) "
                    "vient de demander à être rattaché à votre structure sur "
                    "MesureChâssis.\n\n"
                    "👉 Ouvrez l'app → Admin → Équipe pour l'approuver ou "
                    "le rejeter en 1 clic.\n\n"
                    "L'équipe MesureChâssis"
                ),
            )
        except Exception:
            logger.exception("Notification admin échouée: %s", adm.get("email"))

    return {
        "ok": True,
        "message": (
            "Demande envoyée à votre gérant. Vous serez notifié par email "
            "dès validation."
        ),
    }


@router.get("/auth/validation-status")
async def my_validation_status(user=Depends(auth_user)):
    """Retourne l'état d'accès de l'utilisateur courant."""
    can_access, reason = user_can_access(user)
    return {
        "can_access": can_access,
        "reason": reason,
        "validation_status": user.get("validation_status", "unvalidated"),
        "enforcement_active": is_enforcement_active(),
        "in_grace_period": in_grace_period(),
        "grace_period_end": (grace_period_end() or "").__str__() if grace_period_end() else None,
        "role": user.get("role"),
        "account_type": user.get("account_type"),
    }


# ────────────────────────────────────────────────────────────────────────
# Guard pour les routes protégées (à importer depuis les autres modules)
# ────────────────────────────────────────────────────────────────────────


async def require_validated_user(user=Depends(auth_user)) -> dict:
    """Dépendance FastAPI : autorise seulement les users qui peuvent accéder
    à l'app selon la règle métier."""
    can_access, reason = user_can_access(user)
    if not can_access:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PAYWALL_VALIDATION_REQUIRED",
                "reason": reason,
                "message": (
                    "Votre compte nécessite une approbation de votre gérant "
                    "pour continuer à utiliser MesureChâssis. Veuillez "
                    "contacter votre direction pour valider votre "
                    "rattachement à la structure de facturation."
                ),
            },
        )
    return user
