"""Gestion centralisée des sièges d'équipe selon le plan d'abonnement.

Tarification officielle (juillet 2026) — alignée sur le site vitrine et
les guides PDF (débutant, pro, artisan pro) :

  * Freemium        —  0,00 €/mois       — 3 chantiers À VIE (non renouvelables
                                            même après suppression), 1 admin.
  * Standard        — 19,99 € HTVA/mois  — 1 utilisateur (admin ou artisan
                                            solo), chantiers illimités.
  * Team            — 49,99 € HTVA/mois  — 5 utilisateurs inclus (1 admin +
                                            4 rôles), puis +9,99 € HTVA/mois
                                            par utilisateur supplémentaire.
  * Pro             — 99,99 € HTVA/mois  — utilisateurs ILLIMITÉS, Yann IA
                                            expert, API custom, support prio.
  * Entreprise MAX  — À venir (Q4 2026)  — Odoo, auto-devis, laser BT avancé,
                                            offline sync, SSO, account manager.

Le « siège » ne compte que les rôles commercial/technicien : l'admin
principal n'est jamais facturé comme siège.

Alias historiques préservés :
  - « entreprise » → alias de « team » (ancien nom du plan à 5 sièges).
  - Les prix historiques (24,99/54,99/89,99) sont conservés au niveau des
    company docs déjà persistés (rétro-compat) : c'est Stripe qui décide
    au final via `STRIPE_PRICE_*` env variables.
"""

import logging
import os

import stripe

from db import db

logger = logging.getLogger("mesurechassis.seats")

# ═══════════════════════════════════════════════════════════════════════
# GRILLE TARIFAIRE — Source de vérité pour l'app + les guides.
# ═══════════════════════════════════════════════════════════════════════
SEAT_PLANS = {
    # 🆓 Freemium — Découverte de l'app. AUCUN siège équipe.
    #    Limité à 3 chantiers À VIE (compteur lifetime, non-décrémenté à
    #    la suppression — voir /app/backend/routes/chantiers.py).
    "freemium": {
        "label": "Freemium",
        "price_eur": 0.00,
        "free_team_seats": 0,
        "seat_price_eur": 0.00,
        "chantiers_lifetime_cap": 3,
        "unlimited_seats": False,
        "extra_price_env": None,
    },
    # 📦 Standard — Artisan solo ou admin unique.
    "standard": {
        "label": "Standard",
        "price_eur": 19.99,
        "free_team_seats": 0,  # solo (l'admin ne compte pas comme siège)
        "seat_price_eur": 0.00,
        "chantiers_lifetime_cap": None,
        "unlimited_seats": False,
        "extra_price_env": None,
    },
    # 👥 Team — La plus populaire. Admin + 4 rôles.
    "team": {
        "label": "Team",
        "price_eur": 49.99,
        "free_team_seats": 4,  # + 1 admin = 5 comptes inclus
        "seat_price_eur": 9.99,
        "chantiers_lifetime_cap": None,
        "unlimited_seats": False,
        "extra_price_env": "STRIPE_PRICE_TEAM_EXTRA",
    },
    # 🚀 Pro — Utilisateurs illimités.
    "pro": {
        "label": "Pro",
        "price_eur": 99.99,
        "free_team_seats": 9999,  # de facto illimité
        "seat_price_eur": 0.00,
        "chantiers_lifetime_cap": None,
        "unlimited_seats": True,
        "extra_price_env": None,
    },
    # 🔗 Alias historique — l'ancien plan « entreprise » = nouveau « team ».
    #    Conservé pour ne pas casser les company docs déjà persistés.
    "entreprise": {
        "label": "Team (ex-Entreprise)",
        "price_eur": 49.99,
        "free_team_seats": 4,
        "seat_price_eur": 9.99,
        "chantiers_lifetime_cap": None,
        "unlimited_seats": False,
        "extra_price_env": "STRIPE_PRICE_TEAM_EXTRA",
    },
}


def seat_config_for_plan(plan: str | None) -> dict:
    """Retourne la config sièges du plan (fallback : Team)."""
    return SEAT_PLANS.get((plan or "").lower(), SEAT_PLANS["team"])


async def get_company_plan(company_id: str) -> str:
    """Plan d'abonnement actuel de la société ("entreprise" par défaut)."""
    company = await db.companies.find_one(
        {"company_id": company_id}, {"_id": 0, "subscription": 1}
    ) or {}
    return ((company.get("subscription") or {}).get("plan") or "entreprise").lower()


async def count_team_seats(company_id: str) -> int:
    """Nombre de sièges équipe occupés (commercial + technicien, non supprimés)."""
    return await db.users.count_documents(
        {
            "company_id": company_id,
            "status": {"$ne": "deleted"},
            "role": {"$in": ["commercial", "technician"]},
        }
    )


async def sync_stripe_seats(company_id: str) -> None:
    """Aligne la quantité de la ligne « utilisateur supplémentaire » de
    l'abonnement Stripe sur la taille réelle de l'équipe.

    No-op silencieux si : pas d'abonnement Stripe, plan sans sièges extra,
    ou prix extra non configuré. Ne bloque JAMAIS l'opération appelante :
    toute erreur Stripe est loggée puis avalée (la facturation sera
    réalignée au prochain changement d'équipe).
    """
    try:
        if not (os.getenv("STRIPE_SECRET_KEY") or "").strip():
            return
        company = await db.companies.find_one({"company_id": company_id}) or {}
        sub_doc = company.get("subscription") or {}
        sub_id = sub_doc.get("id")
        plan = (sub_doc.get("plan") or "").lower()
        if not sub_id or plan not in SEAT_PLANS:
            return
        cfg = SEAT_PLANS[plan]
        price_extra = (os.getenv(cfg["extra_price_env"]) or "").strip()
        if not price_extra:
            return

        seats = await count_team_seats(company_id)
        extra_qty = max(0, seats - cfg["free_team_seats"])

        sub = stripe.Subscription.retrieve(sub_id)
        items = (sub.get("items") or {}).get("data", [])
        extra_item = next(
            (it for it in items if (it.get("price") or {}).get("id") == price_extra),
            None,
        )

        if extra_item:
            if extra_qty == 0:
                stripe.SubscriptionItem.delete(extra_item["id"])
            elif extra_item.get("quantity") != extra_qty:
                stripe.SubscriptionItem.modify(extra_item["id"], quantity=extra_qty)
        elif extra_qty > 0:
            stripe.SubscriptionItem.create(
                subscription=sub_id, price=price_extra, quantity=extra_qty
            )
        logger.info(
            "Sièges Stripe synchronisés : company=%s plan=%s équipe=%s extra=%s",
            company_id, plan, seats, extra_qty,
        )
    except Exception as exc:  # noqa: BLE001 — ne jamais bloquer l'appelant
        logger.warning("Sync sièges Stripe échouée (company=%s) : %s", company_id, exc)
