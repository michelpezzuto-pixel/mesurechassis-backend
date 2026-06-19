"""Politique d'accès à l'Assistant IA Yann.

Règle métier (Build 9 — juin 2026) :
  Yann est inclus dans :
    • La période gratuite (BETA_MODE = True) jusqu'au 30 septembre 2026
    • Les 14 jours d'essai (subscription_status == "trial")
    • Le plan Entreprise Pro
    • L'add-on Yann +5 €/mois (companies.yann_addon_active = True)

Pour tout autre cas (Gratuit hors beta, Artisan Solo sans add-on,
Entreprise sans add-on, abonnement suspendu / expiré) → l'accès est refusé.

Cette politique est ré-évaluée à CHAQUE appel (POST /yann/chat) plutôt
qu'au démarrage de la session, pour qu'un upgrade soit reflété
immédiatement sans devoir se reconnecter.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from db import BETA_MODE


def is_yann_allowed(user: dict, company_doc: Optional[dict] = None) -> tuple[bool, str]:
    """Retourne `(allowed, reason)` — `reason` est un code court explicatif.

    Codes possibles :
      • "beta"            — accès via la période freemium globale
      • "trial"           — accès via les 14 jours d'essai
      • "pro"             — accès inclus dans Entreprise Pro
      • "addon"           — accès via l'add-on Yann à 5 €/mois
      • "no_subscription" — pas de compte actif → bloqué
      • "plan_too_low"    — plan insuffisant, add-on désactivé → bloqué
      • "expired"         — abonnement expiré → bloqué
    """
    # ─── 1) BETA mondiale (jusqu'au 30 sept 2026) ─────────────────────
    if BETA_MODE:
        return True, "beta"

    # ─── 2) Période d'essai (14 jours d'office après inscription) ─────
    sub_status = (user.get("subscription_status") or "").lower()
    if sub_status == "trial":
        # Vérifie aussi que l'essai n'est pas expiré
        expires_at = user.get("subscription_expires_at")
        if _is_future(expires_at):
            return True, "trial"
        return False, "expired"

    # ─── 3) Plan / add-on ─────────────────────────────────────────────
    if sub_status == "suspended":
        return False, "no_subscription"

    plan = (user.get("plan") or "").lower()
    if plan == "pro":
        # Entreprise Pro inclut Yann d'office
        return True, "pro"

    # Vérifie l'add-on Yann sur la company
    if company_doc is None:
        company_doc = {}
    yann_addon_active = bool(company_doc.get("yann_addon_active"))
    if yann_addon_active:
        return True, "addon"

    return False, "plan_too_low"


def _is_future(iso_or_dt) -> bool:
    """True si la date donnée est dans le futur (ou None = sans limite)."""
    if not iso_or_dt:
        return False
    if isinstance(iso_or_dt, datetime):
        dt = iso_or_dt
    else:
        try:
            dt = datetime.fromisoformat(str(iso_or_dt).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt > datetime.now(timezone.utc)
