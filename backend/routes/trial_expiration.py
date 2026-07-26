"""
routes/trial_expiration.py — Gestion de l'expiration des essais 14 jours
=========================================================================
Approche paresseuse ("lazy") : plutôt qu'un cron externe, on vérifie
l'état du trial à CHAQUE requête authentifiée. Simple, robuste, pas de
dépendance à un scheduler externe.

Fonctionne en 2 étapes :
1. `check_and_downgrade_if_trial_expired(user)` :
   - Si trial_ends_at < now et pas d'abo actif → user.plan = "free"
   - Émet un événement `trial_expired` dans une collection audit

2. Endpoint admin : `/api/admin/expire-trials` (batch idempotent) pour
   nettoyer d'un coup tous les trials expirés (utile si l'app n'a pas
   été ouverte par un user depuis longtemps).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from db import BETA_MODE, TRIAL_DAYS, db
from deps import auth_user

logger = logging.getLogger("mesurechassis.trial")
router = APIRouter()


def _parse_dt(value) -> Optional[datetime]:
    """Parse un datetime depuis ISO string ou datetime object."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


async def check_and_downgrade_if_trial_expired(user: dict) -> dict:
    """
    Vérifie si le trial d'un user est expiré et le rétrograde si oui.
    À appeler à chaque requête authentifiée sensible.

    Retourne le user (potentiellement modifié).
    """
    if BETA_MODE:
        return user  # personne n'est rétrogradé en beta

    # Users grandfathered = protégés
    if user.get("grandfathered_lifetime_free"):
        return user

    # Users avec abonnement Stripe actif = protégés
    sub_status = (user.get("subscription_status") or "").lower()
    if sub_status in ("active", "trialing"):
        return user

    plan = (user.get("plan") or "").lower()
    if plan == "free":
        return user  # déjà rétrogradé

    # Vérifier trial_ends_at
    trial_ends = _parse_dt(user.get("trial_ends_at"))
    if not trial_ends:
        return user  # pas de trial en cours, rien à faire

    now = datetime.now(timezone.utc)
    if trial_ends > now:
        return user  # trial encore actif

    # 🔻 Trial expiré → rétrograder en "free"
    user_id = user.get("user_id") or user.get("id") or str(user.get("_id"))
    if not user_id:
        return user

    logger.info("Trial expiré pour user_id=%s (plan=%s, ends=%s)", user_id, plan, trial_ends)

    # Update MongoDB
    await db.users.update_one(
        {"user_id": user_id} if user.get("user_id") else {"_id": user.get("_id")},
        {
            "$set": {
                "plan": "free",
                "trial_expired_at": now.isoformat(),
                "previous_plan_before_expiry": plan,
            }
        },
    )

    # Log audit
    await db.audit_events.insert_one({
        "type": "trial_expired_auto_downgrade",
        "user_id": user_id,
        "previous_plan": plan,
        "trial_ends_at": trial_ends.isoformat(),
        "downgraded_at": now.isoformat(),
    })

    # Mutation locale du dict pour cohérence session
    user["plan"] = "free"
    user["trial_expired_at"] = now.isoformat()

    return user


@router.get("/trial/status")
async def get_trial_status(user=Depends(auth_user)):
    """
    Retourne l'état du trial de l'user connecté.
    Utilisé par le frontend pour afficher la bannière "il te reste X jours".
    """
    # Auto-downgrade si expiré (paresseux)
    user = await check_and_downgrade_if_trial_expired(user)

    plan = (user.get("plan") or "").lower()
    sub_status = (user.get("subscription_status") or "").lower()
    grandfathered = bool(user.get("grandfathered_lifetime_free"))

    # État "no trial" pour Pro / grandfathered / free définitif
    trial_ends = _parse_dt(user.get("trial_ends_at"))
    now = datetime.now(timezone.utc)

    if BETA_MODE:
        return {
            "in_trial": False,
            "beta_mode": True,
            "plan": plan,
            "message": "Accès Pro illimité (bêta)",
        }

    if grandfathered:
        return {
            "in_trial": False,
            "grandfathered": True,
            "plan": plan,
            "message": "Accès à vie (utilisateur historique)",
        }

    if sub_status in ("active", "trialing"):
        return {
            "in_trial": False,
            "subscription_active": True,
            "plan": plan,
            "subscription_status": sub_status,
        }

    if not trial_ends:
        return {
            "in_trial": False,
            "plan": plan,
            "trial_expired": plan == "free",
            "message": (
                "Plan gratuit limité — passe à Artisan Pro (19€/mois) pour l'illimité"
                if plan == "free"
                else "Aucun trial en cours"
            ),
        }

    if trial_ends > now:
        seconds_left = int((trial_ends - now).total_seconds())
        days_left = seconds_left // 86400
        hours_left = (seconds_left % 86400) // 3600
        return {
            "in_trial": True,
            "trial_ends_at": trial_ends.isoformat(),
            "days_left": days_left,
            "hours_left": hours_left,
            "total_trial_days": TRIAL_DAYS,
            "plan": plan,
            "message": f"Essai Pro — il te reste {days_left} jour(s) et {hours_left}h",
        }

    return {
        "in_trial": False,
        "trial_expired": True,
        "plan": "free",
        "trial_ended_at": trial_ends.isoformat(),
        "message": "Ton essai est terminé — passe à Artisan Pro (19€/mois) pour continuer",
    }
