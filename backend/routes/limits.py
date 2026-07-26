"""
routes/limits.py — Vérification des limites Freemium (juillet 2026)
=====================================================================
Endpoints et helpers pour vérifier si un utilisateur peut effectuer une
action limitée par son plan (créer chantier, ajouter ouverture, poser
question Yann, importer un CDC).

Utilisation depuis un autre endpoint :
    from routes.limits import (
        check_free_plan_limit,
        LimitExceededError,
        FreeLimitType,
    )

    await check_free_plan_limit(user, company, FreeLimitType.CHANTIERS)

Si limite atteinte → lève HTTPException 402 avec code d'erreur
`free_limit_reached` + le type de limite (utile pour afficher le bon
paywall côté frontend).
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from db import (
    BETA_MODE,
    FREE_PLAN_MAX_CHANTIERS,
    FREE_PLAN_MAX_OUVERTURES,
    FREE_YANN_QUESTIONS_MONTHLY,
    FREE_IA_IMPORTS_MONTHLY,
    TRIAL_DAYS,
    db,
)
from deps import auth_user

logger = logging.getLogger("mesurechassis.limits")
router = APIRouter(prefix="/limits", tags=["limits"])


# ============================================================
# ENUMS & EXCEPTIONS
# ============================================================
class FreeLimitType(str, Enum):
    """Types de limites du plan gratuit — utilisés pour le paywall côté frontend."""

    CHANTIERS = "chantiers"          # Max 3 chantiers actifs
    OUVERTURES = "ouvertures"        # Max 5 ouvertures cumulées
    YANN_QUESTION = "yann_question"  # Max 10 questions Yann/mois
    IA_CDC_IMPORT = "ia_cdc_import"  # Max 3 imports IA CDC/mois
    EXPORT_FORMAT = "export_format"  # PDF seulement (pas Excel/CSV/JSON)


LIMIT_MESSAGES = {
    FreeLimitType.CHANTIERS: (
        "Tu as atteint la limite de 3 chantiers du plan gratuit. "
        "Passe à Artisan Pro (19€/mois) pour des chantiers illimités."
    ),
    FreeLimitType.OUVERTURES: (
        "Tu as atteint la limite de 5 ouvertures du plan gratuit. "
        "Passe à Artisan Pro (19€/mois) pour des ouvertures illimitées."
    ),
    FreeLimitType.YANN_QUESTION: (
        "Tu as atteint la limite de 10 questions Yann par mois du plan gratuit. "
        "Passe à Artisan Pro (19€/mois) pour poser autant de questions que tu veux."
    ),
    FreeLimitType.IA_CDC_IMPORT: (
        "Tu as atteint la limite de 3 imports de cahier des charges par mois. "
        "Passe à Artisan Pro (19€/mois) pour des imports illimités."
    ),
    FreeLimitType.EXPORT_FORMAT: (
        "L'export Excel/CSV/JSON est réservé aux plans Artisan Pro et Entreprise Pro. "
        "L'export PDF reste disponible en gratuit."
    ),
}


# ============================================================
# HELPER — Déterminer si un user est en "plan gratuit" effectif
# ============================================================
def _is_effectively_free(user: dict, company: Optional[dict]) -> bool:
    """
    Retourne True si l'user doit être soumis aux limites du plan gratuit.

    Logique :
      1. BETA_MODE actif       → False (personne n'est limité)
      2. Plan actif = "pro"    → False
      3. Plan actif = "entreprise" avec paiement OK → False
      4. Trial en cours        → False
      5. Sinon                 → True (plan gratuit / trial expiré / non payé)
    """
    if BETA_MODE:
        return False

    # Grandfathering : les users "à vie" (flag ajouté lors de la migration)
    if user.get("grandfathered_lifetime_free"):
        return False

    plan = (user.get("plan") or "").lower()
    if plan in ("pro", "entreprise", "artisan_pro", "entreprise_pro"):
        # Vérifier que l'abonnement Stripe est actif
        sub_status = (user.get("subscription_status") or "").lower()
        if sub_status in ("active", "trialing"):
            return False

    # Vérifier si le trial est en cours (via trial_ends_at)
    trial_ends = user.get("trial_ends_at")
    if trial_ends:
        try:
            trial_ends_dt = trial_ends if isinstance(trial_ends, datetime) else datetime.fromisoformat(str(trial_ends).replace("Z", "+00:00"))
            if trial_ends_dt.tzinfo is None:
                trial_ends_dt = trial_ends_dt.replace(tzinfo=timezone.utc)
            if trial_ends_dt > datetime.now(timezone.utc):
                return False
        except Exception:
            pass  # Format invalide → on considère qu'il n'y a pas de trial

    return True


# ============================================================
# COMPTEURS — Interrogent MongoDB pour connaître l'état actuel
# ============================================================
async def _count_active_chantiers(company_id: str) -> int:
    """Nombre de chantiers non archivés/non supprimés pour une company."""
    query = {
        "company_id": company_id,
        "$or": [
            {"archived": {"$ne": True}},
            {"archived": {"$exists": False}},
        ],
        "$and": [
            {"$or": [
                {"deleted": {"$ne": True}},
                {"deleted": {"$exists": False}},
            ]}
        ],
    }
    return await db.chantiers.count_documents(query)


async def _count_total_ouvertures(company_id: str) -> int:
    """Nombre total d'ouvertures créées pour une company (tous chantiers actifs)."""
    # Récupère les IDs des chantiers actifs, puis compte les ouvertures
    active_ids_cursor = db.chantiers.find(
        {
            "company_id": company_id,
            "$or": [
                {"archived": {"$ne": True}},
                {"archived": {"$exists": False}},
            ],
        },
        {"chantier_id": 1, "_id": 0},
    )
    chantier_ids = [d.get("chantier_id") async for d in active_ids_cursor if d.get("chantier_id")]
    if not chantier_ids:
        return 0
    return await db.ouvertures.count_documents({"chantier_id": {"$in": chantier_ids}})


async def _count_yann_questions_this_month(user_id: str) -> int:
    """Nombre de questions Yann posées par l'user depuis le début du mois calendaire."""
    now = datetime.now(timezone.utc)
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return await db.yann_conversations.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": first_day},
    })


async def _count_ia_imports_this_month(user_id: str) -> int:
    """Nombre d'imports IA CDC effectués par l'user depuis le début du mois."""
    now = datetime.now(timezone.utc)
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return await db.spec_imports.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": first_day},
    })


# ============================================================
# CHECK PRINCIPAL — À appeler depuis les endpoints métier
# ============================================================
async def check_free_plan_limit(
    user: dict,
    limit_type: FreeLimitType,
    company: Optional[dict] = None,
) -> None:
    """
    Vérifie si l'user peut effectuer l'action selon son plan actuel.
    Ne fait RIEN si l'user n'est pas en plan gratuit (BETA_MODE, pro, trial actif).
    Lève HTTPException 402 si limite atteinte.
    """
    if not _is_effectively_free(user, company):
        return  # user Pro ou beta → aucune limite

    company_id = user.get("company_id")
    user_id = user.get("user_id") or user.get("id") or str(user.get("_id", ""))

    if limit_type == FreeLimitType.CHANTIERS:
        if not company_id:
            return
        count = await _count_active_chantiers(company_id)
        if count >= FREE_PLAN_MAX_CHANTIERS:
            raise _limit_reached(limit_type, current=count, maximum=FREE_PLAN_MAX_CHANTIERS)

    elif limit_type == FreeLimitType.OUVERTURES:
        if not company_id:
            return
        count = await _count_total_ouvertures(company_id)
        if count >= FREE_PLAN_MAX_OUVERTURES:
            raise _limit_reached(limit_type, current=count, maximum=FREE_PLAN_MAX_OUVERTURES)

    elif limit_type == FreeLimitType.YANN_QUESTION:
        if not user_id:
            return
        count = await _count_yann_questions_this_month(user_id)
        if count >= FREE_YANN_QUESTIONS_MONTHLY:
            raise _limit_reached(limit_type, current=count, maximum=FREE_YANN_QUESTIONS_MONTHLY)

    elif limit_type == FreeLimitType.IA_CDC_IMPORT:
        if not user_id:
            return
        count = await _count_ia_imports_this_month(user_id)
        if count >= FREE_IA_IMPORTS_MONTHLY:
            raise _limit_reached(limit_type, current=count, maximum=FREE_IA_IMPORTS_MONTHLY)


def _limit_reached(limit_type: FreeLimitType, current: int, maximum: int) -> HTTPException:
    """Retourne l'exception HTTP standardisée pour paywall (frontend écoute code=free_limit_reached)."""
    return HTTPException(
        status_code=402,  # 402 Payment Required
        detail={
            "code": "free_limit_reached",
            "limit_type": limit_type.value,
            "current": current,
            "maximum": maximum,
            "message": LIMIT_MESSAGES.get(limit_type, "Limite du plan gratuit atteinte."),
            "upgrade_url": "https://mesurechassis.com/tarifs.html",
        },
    )


# ============================================================
# ENDPOINT — État actuel des compteurs pour l'user connecté
# ============================================================
@router.get("/status")
async def limits_status(user: dict = Depends(auth_user)):
    """
    Retourne l'état actuel des compteurs Freemium pour l'user connecté.
    Utilisé par le frontend pour afficher :
      - Bannière "il te reste X chantiers / X questions Yann"
      - Bloquer proactivement les CTAs (grisés) au lieu d'attendre l'erreur 402
    """
    company_id = user.get("company_id")
    user_id = user.get("user_id") or user.get("id") or str(user.get("_id", ""))
    is_free = _is_effectively_free(user, None)

    if not is_free:
        return {
            "is_free_plan": False,
            "unlimited": True,
            "plan": user.get("plan"),
            "subscription_status": user.get("subscription_status"),
            "trial_ends_at": user.get("trial_ends_at"),
        }

    chantiers = await _count_active_chantiers(company_id) if company_id else 0
    ouvertures = await _count_total_ouvertures(company_id) if company_id else 0
    yann = await _count_yann_questions_this_month(user_id) if user_id else 0
    imports = await _count_ia_imports_this_month(user_id) if user_id else 0

    return {
        "is_free_plan": True,
        "unlimited": False,
        "usage": {
            "chantiers": {"current": chantiers, "max": FREE_PLAN_MAX_CHANTIERS},
            "ouvertures": {"current": ouvertures, "max": FREE_PLAN_MAX_OUVERTURES},
            "yann_questions_month": {"current": yann, "max": FREE_YANN_QUESTIONS_MONTHLY},
            "ia_cdc_imports_month": {"current": imports, "max": FREE_IA_IMPORTS_MONTHLY},
        },
        "upgrade_url": "https://mesurechassis.com/tarifs.html",
    }
