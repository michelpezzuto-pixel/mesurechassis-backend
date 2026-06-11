"""Gestion centralisée des sièges d'équipe selon le plan d'abonnement.

Tarification (juin 2026) :
  * Artisan Solo   — 24,99 €/mois — 1 utilisateur (pas d'équipe)
  * Entreprise     — 59,99 €/mois — 3 comptes inclus (1 admin + 2 équipe),
                     puis +4,99 €/mois par utilisateur supplémentaire
  * Entreprise Pro — 89,99 €/mois — 6 comptes inclus (1 admin + 5 équipe),
                     puis +9,99 €/mois par utilisateur supplémentaire

Le « siège » ne compte que les rôles commercial/technicien : l'admin
principal n'est jamais facturé comme siège.
"""

import logging
import os

import stripe

from db import db

logger = logging.getLogger("mesurechassis.seats")

SEAT_PLANS = {
    "entreprise": {
        "label": "Entreprise",
        "free_team_seats": 2,  # + 1 admin = 3 comptes inclus
        "seat_price_eur": 4.99,
        "extra_price_env": "STRIPE_PRICE_ENTREPRISE_EXTRA",
    },
    "pro": {
        "label": "Entreprise Pro",
        "free_team_seats": 5,  # + 1 admin = 6 comptes inclus
        "seat_price_eur": 9.99,
        "extra_price_env": "STRIPE_PRICE_PRO_EXTRA",
    },
}


def seat_config_for_plan(plan: str | None) -> dict:
    """Retourne la config sièges du plan (fallback : Entreprise)."""
    return SEAT_PLANS.get((plan or "").lower(), SEAT_PLANS["entreprise"])


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
