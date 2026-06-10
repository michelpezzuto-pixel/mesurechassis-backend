"""Routes Stripe — Checkout / Customer Portal / Webhook / Status.

Architecture :
  * Tous les appels Stripe (création de checkout, portail, etc.) passent par
    le backend afin de ne JAMAIS exposer la clé secrète au mobile.
  * Le mobile reçoit uniquement des URLs hébergées par Stripe à ouvrir dans
    un in-app browser (expo-web-browser).
  * Le webhook `/stripe/webhook` est l'unique source de vérité pour mettre
    à jour le statut d'abonnement en base : on n'utilise jamais les query
    params du success_url (manipulables) pour débloquer un compte.

Plans MesureChâssis (3 mois d'essai gratuit) :
  * Artisan Solo     — 24,99 €/mois — 1 utilisateur
  * Entreprise       — 54,99 €/mois — 3 utilisateurs + 4,99 €/utilisateur sup.
  * Entreprise Pro   — 84,99 €/mois — 6 utilisateurs + 9,99 €/utilisateur sup.

Variables d'environnement requises (à ajouter sur Railway) :
  * STRIPE_SECRET_KEY                 — sk_test_… ou sk_live_…
  * STRIPE_WEBHOOK_SECRET             — whsec_… (créé après config du webhook)
  * STRIPE_PRICE_SOLO                 — price_… (Artisan Solo)
  * STRIPE_PRICE_ENTREPRISE_BASE      — price_… (Entreprise base 3 users)
  * STRIPE_PRICE_ENTREPRISE_EXTRA     — price_… (Entreprise +1 utilisateur)
  * STRIPE_PRICE_PRO_BASE             — price_… (Pro base 6 users)
  * STRIPE_PRICE_PRO_EXTRA            — price_… (Pro +1 utilisateur)
  * APP_DEEP_LINK_SCHEME              — défaut "mesurechassis"
  * APP_WEB_RETURN_URL                — défaut "https://mesurechassis.com"
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from db import db
from deps import auth_user

logger = logging.getLogger("mesurechassis.stripe")
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────
# Configuration Stripe (lecture des env vars au démarrage)
# ─────────────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
# .strip() : protection contre les espaces / sauts de ligne invisibles
# qui auraient pu être copiés par erreur dans la variable d'environnement.
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
# 🆕 V3 — Support multi-secrets (séparés par virgule).
#   Pratique quand on a 2 endpoints (ex. dev / prod) ou pendant une rotation
#   de secret côté Stripe (on a temporairement l'ancien + le nouveau actifs).
# Chaque secret est trim() puis filtré (vides ignorés).
STRIPE_WEBHOOK_SECRETS = [
    s.strip() for s in (STRIPE_WEBHOOK_SECRET or "").split(",") if s.strip()
]
APP_DEEP_LINK_SCHEME = os.getenv("APP_DEEP_LINK_SCHEME", "mesurechassis")
APP_WEB_RETURN_URL = os.getenv("APP_WEB_RETURN_URL", "https://mesurechassis.com")
TRIAL_PERIOD_DAYS = 90  # 3 mois d'essai gratuit

# Mapping plan → tuple(price_base, price_extra_user, included_seats)
PLAN_PRICE_MAP = {
    "solo": (
        os.getenv("STRIPE_PRICE_SOLO", ""),
        None,  # pas de prix sup
        1,
    ),
    "entreprise": (
        os.getenv("STRIPE_PRICE_ENTREPRISE_BASE", ""),
        os.getenv("STRIPE_PRICE_ENTREPRISE_EXTRA", ""),
        3,
    ),
    "pro": (
        os.getenv("STRIPE_PRICE_PRO_BASE", ""),
        os.getenv("STRIPE_PRICE_PRO_EXTRA", ""),
        6,
    ),
}

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("✅ Stripe configuré (clé %s…)", STRIPE_SECRET_KEY[:10])
else:
    logger.warning("⚠️ STRIPE_SECRET_KEY non définie — module Stripe désactivé")


def _require_stripe():
    """Garde-fou : refuse toute opération si Stripe n'est pas configuré."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            503,
            "Le module abonnement n'est pas encore activé sur ce serveur. "
            "Contactez l'administrateur.",
        )


async def _get_or_create_stripe_customer(user: dict, company: Optional[dict]) -> str:
    """Récupère ou crée le customer Stripe associé à la company."""
    company_id = user.get("company_id")
    if not company_id:
        raise HTTPException(400, "Utilisateur sans entreprise — abonnement impossible.")

    company = company or await db.companies.find_one({"company_id": company_id})
    if not company:
        raise HTTPException(404, "Entreprise introuvable.")

    if cust_id := company.get("stripe_customer_id"):
        return cust_id

    customer = stripe.Customer.create(
        email=user.get("email"),
        name=company.get("name") or user.get("name"),
        metadata={
            "company_id": company_id,
            "app_user_id": user.get("id", ""),
        },
    )
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"stripe_customer_id": customer.id}},
    )
    logger.info("Stripe customer créé pour company=%s → %s", company_id, customer.id)
    return customer.id


# ─────────────────────────────────────────────────────────────────────────
# 1) Création d'une session Checkout (subscription)
# ─────────────────────────────────────────────────────────────────────────
class CheckoutRequest(BaseModel):
    plan: str  # "solo" | "entreprise" | "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/stripe/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    user=Depends(auth_user),
):
    """Crée une session Stripe Checkout pour souscrire au plan demandé.

    Comportement :
      * 3 mois d'essai gratuit appliqués automatiquement
      * Si plan Entreprise/Pro : une 2ème line item est ajoutée avec quantité 0
        (utilisateurs supplémentaires — sera mise à jour quand l'équipe grossira)
      * Le success_url et cancel_url utilisent un deep link → l'app se rouvre
    """
    _require_stripe()

    plan = body.plan.lower().strip()
    if plan not in PLAN_PRICE_MAP:
        raise HTTPException(400, f"Plan inconnu : {plan}")

    price_base, price_extra, _included = PLAN_PRICE_MAP[plan]
    if not price_base:
        raise HTTPException(
            503,
            f"Le plan « {plan} » n'est pas encore configuré sur Stripe. "
            "Contactez l'administrateur.",
        )

    company = await db.companies.find_one({"company_id": user.get("company_id") or ""})
    customer_id = await _get_or_create_stripe_customer(user, company)

    # Items du checkout : base + (si applicable) prix par utilisateur supplémentaire
    line_items = [{"price": price_base, "quantity": 1}]
    if price_extra:
        # Quantité 0 par défaut : la quantité sera ajustée plus tard via webhook
        # ou via une action manuelle quand un nouvel utilisateur est invité.
        # ⚠️ Stripe n'accepte pas quantity=0, on l'omet pour l'instant —
        # on l'ajoutera lors du premier dépassement.
        pass

    success_url = (
        f"{APP_DEEP_LINK_SCHEME}://stripe-success"
        "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = f"{APP_DEEP_LINK_SCHEME}://stripe-cancel"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=line_items,
            subscription_data={
                "trial_period_days": TRIAL_PERIOD_DAYS,
                "metadata": {
                    "company_id": user.get("company_id") or "",
                    "plan": plan,
                },
            },
            payment_method_types=["card", "sepa_debit"],
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            locale="fr",
            metadata={
                "company_id": user.get("company_id") or "",
                "plan": plan,
            },
        )
    except stripe.StripeError as e:
        logger.exception("Erreur Stripe lors de la création de checkout")
        raise HTTPException(500, f"Erreur Stripe : {e.user_message or str(e)}")

    return CheckoutResponse(checkout_url=session.url)


# ─────────────────────────────────────────────────────────────────────────
# 2) Customer Portal (gestion de l'abonnement par le client)
# ─────────────────────────────────────────────────────────────────────────
class PortalResponse(BaseModel):
    portal_url: str


@router.post("/stripe/customer-portal", response_model=PortalResponse)
async def create_customer_portal(user=Depends(auth_user)):
    """Ouvre le portail Stripe (change méthode paiement, factures, annulation)."""
    _require_stripe()
    company = await db.companies.find_one({"company_id": user.get("company_id") or ""})
    if not company or not company.get("stripe_customer_id"):
        raise HTTPException(
            400,
            "Aucun abonnement actif — souscrivez d'abord à un plan.",
        )

    return_url = f"{APP_DEEP_LINK_SCHEME}://stripe-portal-return"

    try:
        session = stripe.billing_portal.Session.create(
            customer=company["stripe_customer_id"],
            return_url=return_url,
        )
    except stripe.StripeError as e:
        logger.exception("Erreur portail Stripe")
        raise HTTPException(500, f"Erreur Stripe : {e.user_message or str(e)}")

    return PortalResponse(portal_url=session.url)


# ─────────────────────────────────────────────────────────────────────────
# 3) Statut d'abonnement (lu par l'app mobile au démarrage)
# ─────────────────────────────────────────────────────────────────────────
class SubscriptionStatus(BaseModel):
    has_subscription: bool
    plan: Optional[str] = None
    status: Optional[str] = None  # trialing / active / past_due / canceled / unpaid
    trial_end: Optional[str] = None
    current_period_end: Optional[str] = None
    is_locked: bool  # True = bloquer accès aux fonctionnalités payantes
    days_left_in_trial: Optional[int] = None
    # 🆕 V3 — Plan préféré choisi à l'inscription (solo/entreprise/pro).
    # Utilisé par l'app mobile pour pré-sélectionner / surligner le plan
    # correspondant sur l'écran de souscription.
    preferred_plan: Optional[str] = None


@router.get("/stripe/subscription-status", response_model=SubscriptionStatus)
async def get_subscription_status(user=Depends(auth_user)):
    """Retourne le statut d'abonnement consolidé pour l'app mobile.

    Logique de verrouillage :
      * trialing + trial_end > now           → UNLOCKED
      * active + current_period_end > now    → UNLOCKED
      * past_due                              → UNLOCKED (grace period)
      * unpaid / canceled / pas d'abonnement  → LOCKED
    """
    company = await db.companies.find_one({"company_id": user.get("company_id") or ""})
    if not company:
        return SubscriptionStatus(has_subscription=False, is_locked=True)

    # 🆕 V3 — Récupère le plan préféré dès que possible (utilisé pour pré-sélection).
    preferred_plan = company.get("preferred_plan")

    sub_doc = company.get("subscription") or {}
    if not sub_doc:
        return SubscriptionStatus(
            has_subscription=False,
            is_locked=True,
            preferred_plan=preferred_plan,
        )

    now = datetime.now(timezone.utc)
    status = sub_doc.get("status")
    trial_end_str = sub_doc.get("trial_end")
    period_end_str = sub_doc.get("current_period_end")

    trial_end = _parse_dt(trial_end_str)
    period_end = _parse_dt(period_end_str)

    is_locked = True
    days_left = None

    if status == "trialing" and trial_end and trial_end > now:
        is_locked = False
        days_left = max(0, (trial_end - now).days)
    elif status == "active" and period_end and period_end > now:
        is_locked = False
    elif status == "past_due":
        # Grace period : on laisse passer mais on prévient
        is_locked = False

    return SubscriptionStatus(
        has_subscription=True,
        plan=sub_doc.get("plan"),
        status=status,
        trial_end=trial_end_str,
        current_period_end=period_end_str,
        is_locked=is_locked,
        days_left_in_trial=days_left,
        preferred_plan=preferred_plan,
    )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────
# 4) Webhook Stripe (vérité unique pour le statut d'abonnement)
# ─────────────────────────────────────────────────────────────────────────
@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """Endpoint de webhook Stripe.

    ⚠️ Signature vérifiée via STRIPE_WEBHOOK_SECRET — toute requête non
    signée est rejetée pour éviter les manipulations de statut.

    🆕 V3 — Support multi-secrets (STRIPE_WEBHOOK_SECRETS via virgule).
    Utilise `stripe.Webhook.construct_event()` (API recommandée Stripe)
    qui combine vérification + parsing en un seul appel atomique.
    """
    if not STRIPE_WEBHOOK_SECRETS:
        logger.error("Webhook reçu mais STRIPE_WEBHOOK_SECRET non configuré")
        raise HTTPException(503, "Webhook non configuré")

    # 🩺 DIAGNOSTIC : log les secrets disponibles (preview) + signature reçue
    secrets_preview = ", ".join(
        f"{s[:10]}...{s[-4:]} ({len(s)}ch)" if len(s) > 14 else f"INVALID({len(s)}ch)"
        for s in STRIPE_WEBHOOK_SECRETS
    )
    sig_preview = (stripe_signature or "")[:40] + "..." if stripe_signature else "MISSING"
    logger.info(
        "🩺 Webhook diag — %d secret(s)=[%s] | sig-header=%s",
        len(STRIPE_WEBHOOK_SECRETS),
        secrets_preview,
        sig_preview,
    )

    if not stripe_signature:
        raise HTTPException(400, "Header Stripe-Signature manquant")

    payload = await request.body()
    logger.info("🩺 Webhook diag — payload bytes=%d", len(payload))

    # 🆕 Boucle sur tous les secrets configurés — Stripe permet d'avoir
    # plusieurs endpoints avec des secrets différents (dev / prod / rotation).
    # On accepte si AU MOINS UN secret valide.
    event = None
    last_err: Optional[Exception] = None
    for secret in STRIPE_WEBHOOK_SECRETS:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=secret,
            )
            logger.info(
                "🩺 Webhook signature OK avec secret %s...%s",
                secret[:10],
                secret[-4:],
            )
            break
        except stripe.SignatureVerificationError as e:
            last_err = e
            continue
        except ValueError as e:
            # Payload non-JSON ou malformé
            logger.exception("Payload webhook invalide")
            raise HTTPException(400, f"Payload invalide : {e}")
        except Exception as e:
            last_err = e
            continue

    if event is None:
        logger.warning(
            "Webhook : aucune signature valide trouvée (testé %d secret(s)) — dernier erreur=%s",
            len(STRIPE_WEBHOOK_SECRETS),
            type(last_err).__name__ if last_err else "?",
        )
        raise HTTPException(400, "Signature invalide")

    # `event` est un StripeObject — on le convertit en dict pur pour
    # éviter les quirks (.get(...) fait des appels API sur certains champs).
    event_dict = (
        event.to_dict_recursive()
        if hasattr(event, "to_dict_recursive")
        else dict(event)
    )

    event_type = event_dict.get("type")
    obj = (event_dict.get("data") or {}).get("object") or {}
    logger.info("Stripe webhook reçu : %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            await _on_checkout_completed(obj)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            await _on_subscription_changed(obj)
        elif event_type == "customer.subscription.deleted":
            await _on_subscription_deleted(obj)
        elif event_type == "invoice.paid":
            await _on_invoice_paid(obj)
        elif event_type == "invoice.payment_failed":
            await _on_invoice_payment_failed(obj)
        else:
            logger.debug("Type d'event ignoré : %s", event_type)
    except Exception:
        logger.exception("Erreur traitement webhook %s", event_type)
        # On renvoie quand même 200 pour éviter que Stripe ne ré-essaie
        # indéfiniment sur une erreur applicative.

    return {"received": True}


async def _on_checkout_completed(session: dict):
    """Checkout terminé → l'abonnement vient d'être créé."""
    company_id = (session.get("metadata") or {}).get("company_id")
    plan = (session.get("metadata") or {}).get("plan")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")
    if not company_id or not subscription_id:
        logger.warning("Webhook checkout.completed sans company_id ou subscription")
        return

    sub_obj = stripe.Subscription.retrieve(subscription_id)
    # Convertir en vrai dict (anti StripeObject quirks)
    sub = (
        sub_obj.to_dict_recursive()
        if hasattr(sub_obj, "to_dict_recursive")
        else dict(sub_obj)
    )
    await _persist_subscription(company_id, plan, sub, customer_id)


async def _on_subscription_changed(sub: dict):
    company_id = (sub.get("metadata") or {}).get("company_id")
    plan = (sub.get("metadata") or {}).get("plan")
    if not company_id:
        # Fallback : remonter au customer pour retrouver la company
        cust_obj = stripe.Customer.retrieve(sub.get("customer"))
        customer = (
            cust_obj.to_dict_recursive()
            if hasattr(cust_obj, "to_dict_recursive")
            else dict(cust_obj)
        )
        company_id = (customer.get("metadata") or {}).get("company_id")
    if not company_id:
        return
    await _persist_subscription(company_id, plan, sub, sub.get("customer"))


async def _on_subscription_deleted(sub: dict):
    company_id = (sub.get("metadata") or {}).get("company_id")
    if not company_id:
        cust_obj = stripe.Customer.retrieve(sub.get("customer"))
        customer = (
            cust_obj.to_dict_recursive()
            if hasattr(cust_obj, "to_dict_recursive")
            else dict(cust_obj)
        )
        company_id = (customer.get("metadata") or {}).get("company_id")
    if not company_id:
        return
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"subscription.status": "canceled"}},
    )
    logger.info("Subscription annulée pour company=%s", company_id)


async def _on_invoice_paid(invoice: dict):
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub_obj = stripe.Subscription.retrieve(sub_id)
    sub = (
        sub_obj.to_dict_recursive()
        if hasattr(sub_obj, "to_dict_recursive")
        else dict(sub_obj)
    )
    await _on_subscription_changed(sub)


async def _on_invoice_payment_failed(invoice: dict):
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub_obj = stripe.Subscription.retrieve(sub_id)
    sub = (
        sub_obj.to_dict_recursive()
        if hasattr(sub_obj, "to_dict_recursive")
        else dict(sub_obj)
    )
    await _on_subscription_changed(sub)


async def _persist_subscription(
    company_id: str,
    plan: Optional[str],
    sub: dict,
    customer_id: Optional[str],
):
    """Persiste les infos d'abonnement dans la company."""
    payload = {
        "id": sub.get("id"),
        "status": sub.get("status"),
        "plan": plan,
        "current_period_end": _ts_to_iso(sub.get("current_period_end")),
        "trial_end": _ts_to_iso(sub.get("trial_end")),
        "cancel_at_period_end": sub.get("cancel_at_period_end", False),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    update = {"subscription": payload}
    if customer_id:
        update["stripe_customer_id"] = customer_id
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": update},
    )
    logger.info(
        "Subscription mise à jour : company=%s plan=%s status=%s",
        company_id,
        plan,
        sub.get("status"),
    )


def _ts_to_iso(ts: Optional[int]) -> Optional[str]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
