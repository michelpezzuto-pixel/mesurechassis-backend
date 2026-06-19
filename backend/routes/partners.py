"""Système de Partenaires Affiliés — Build 9 (juin 2026).

Modèle métier (validé avec Michel — juin 2026) :
  Un Partenaire Affilié = influenceur / créateur de contenu / professionnel
  recommandé qui promeut MesureChâssis en échange d'une commission
  récurrente sur les abonnements générés via son code unique.

Différence avec le système de parrainage standard :
  • Le parrain "classique" est un CLIENT qui gagne 2 mois offerts par filleul actif.
  • Le partenaire affilié est une PERSONNE EXTERNE qui gagne une commission
    en EUROS (par défaut 20 % du CA pendant 12 mois). Souvent influenceur.

Tracking :
  • À l'inscription, si un code partenaire est saisi → un document
    `affiliate_signups` est créé (référence partenaire + utilisateur).
  • À chaque facture payée du filleul → un document
    `affiliate_commissions` est créé (montant dû au partenaire).

Endpoints :
  • Admin (RBAC strict) : CRUD partenaires + stats + rapport mensuel.
  • Public limité : POST /affiliate/track-click pour stats marketing.
  • Auth user : récupère info partenaire au moment de l'inscription.
"""
from __future__ import annotations

import logging
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from deps import auth_user

logger = logging.getLogger("mesurechassis.partners")
router = APIRouter()

# Constantes métier (par défaut, surchargeables par partenaire)
DEFAULT_COMMISSION_RATE = 20.0  # %
DEFAULT_COMMISSION_DURATION_MONTHS = 12

CODE_REGEX = re.compile(r"^[A-Z0-9-]{4,24}$")
RESERVED_PREFIXES = {"MC-", "ADMIN", "TEST"}

PLATFORMS = {"tiktok", "youtube", "instagram", "facebook", "linkedin", "blog", "podcast", "other"}
STATUSES = {"pending", "active", "paused", "terminated"}


def _generate_partner_code(name: str) -> str:
    """Génère un code à partir du nom (ex. 'Jean Durand' → 'JEAN-DURAND-A3F7')."""
    clean = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()[:14]
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"{clean}-{suffix}" if clean else f"AFF-{suffix}"


def _admin_only(user: dict) -> None:
    """Lève 403 si l'utilisateur n'est pas admin."""
    role = (user.get("role") or "").lower()
    if role not in ("admin", "owner", "superadmin"):
        raise HTTPException(403, "Réservé aux administrateurs")


# ════════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ════════════════════════════════════════════════════════════════════════════
class PartnerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    platform: str = Field(..., description="tiktok | youtube | instagram | …")
    handle: str = Field("", description="@username sur la plateforme")
    audience_size: int = Field(0, ge=0)
    commission_rate: float = Field(DEFAULT_COMMISSION_RATE, ge=0, le=100)
    commission_duration_months: int = Field(DEFAULT_COMMISSION_DURATION_MONTHS, ge=1, le=60)
    custom_code: Optional[str] = Field(None, description="Code promo personnalisé (optionnel)")
    iban: Optional[str] = Field(None, description="IBAN pour les virements (BE/FR)")
    notes: Optional[str] = ""


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    platform: Optional[str] = None
    handle: Optional[str] = None
    audience_size: Optional[int] = None
    commission_rate: Optional[float] = None
    commission_duration_months: Optional[int] = None
    iban: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    contract_signed: Optional[bool] = None


class PartnerOut(BaseModel):
    id: str
    name: str
    email: str
    platform: str
    handle: str
    audience_size: int
    code: str
    commission_rate: float
    commission_duration_months: int
    iban: Optional[str] = None
    status: str
    contract_signed: bool
    contract_signed_at: Optional[str] = None
    notes: str = ""
    created_at: str


# ════════════════════════════════════════════════════════════════════════════
# Endpoints — CRUD
# ════════════════════════════════════════════════════════════════════════════
@router.post("/partners", response_model=PartnerOut)
async def create_partner(payload: PartnerCreate, user=Depends(auth_user)):
    """Crée un nouveau partenaire affilié (admin seulement)."""
    _admin_only(user)

    if payload.platform not in PLATFORMS:
        raise HTTPException(400, f"Plateforme invalide : {sorted(PLATFORMS)}")

    # Génération / validation du code
    if payload.custom_code:
        code = (payload.custom_code or "").strip().upper().replace(" ", "-")
        if not CODE_REGEX.match(code):
            raise HTTPException(400, "Code invalide : 4-24 caractères, A-Z, 0-9 et tirets.")
        for prefix in RESERVED_PREFIXES:
            if code.startswith(prefix):
                raise HTTPException(400, f"Le préfixe '{prefix}' est réservé.")
    else:
        code = _generate_partner_code(payload.name)

    # Unicité du code (partenaires ET parrains classiques)
    if await db.affiliate_partners.find_one({"code": code}):
        raise HTTPException(409, f"Code déjà utilisé par un autre partenaire : {code}")
    if await db.companies.find_one({"referral_code": code}):
        raise HTTPException(409, f"Code déjà utilisé en parrainage : {code}")

    partner_id = secrets.token_urlsafe(12)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": partner_id,
        "name": payload.name,
        "email": payload.email,
        "platform": payload.platform,
        "handle": payload.handle or "",
        "audience_size": payload.audience_size,
        "code": code,
        "commission_rate": payload.commission_rate,
        "commission_duration_months": payload.commission_duration_months,
        "iban": payload.iban,
        "status": "pending",
        "contract_signed": False,
        "contract_signed_at": None,
        "notes": payload.notes or "",
        "created_at": now,
        "created_by_user_id": user.get("user_id"),
    }
    await db.affiliate_partners.insert_one(doc)
    logger.info("Partner créé : %s (code=%s)", payload.name, code)
    return PartnerOut(**doc)


@router.get("/partners")
async def list_partners(user=Depends(auth_user)):
    """Liste tous les partenaires (admin)."""
    _admin_only(user)
    items = []
    async for doc in db.affiliate_partners.find().sort("created_at", -1):
        doc.pop("_id", None)
        items.append(doc)
    return {"partners": items, "total": len(items)}


@router.get("/partners/{partner_id}")
async def get_partner(partner_id: str, user=Depends(auth_user)):
    """Détail d'un partenaire (admin)."""
    _admin_only(user)
    doc = await db.affiliate_partners.find_one({"id": partner_id})
    if not doc:
        raise HTTPException(404, "Partenaire introuvable")
    doc.pop("_id", None)
    return doc


@router.patch("/partners/{partner_id}")
async def update_partner(partner_id: str, payload: PartnerUpdate, user=Depends(auth_user)):
    """Met à jour un partenaire (admin)."""
    _admin_only(user)
    existing = await db.affiliate_partners.find_one({"id": partner_id})
    if not existing:
        raise HTTPException(404, "Partenaire introuvable")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}

    if "status" in updates and updates["status"] not in STATUSES:
        raise HTTPException(400, f"Statut invalide : {sorted(STATUSES)}")
    if "platform" in updates and updates["platform"] not in PLATFORMS:
        raise HTTPException(400, f"Plateforme invalide : {sorted(PLATFORMS)}")

    if updates.get("contract_signed") and not existing.get("contract_signed_at"):
        updates["contract_signed_at"] = datetime.now(timezone.utc).isoformat()
        # Active automatiquement à la signature
        if existing.get("status") == "pending":
            updates["status"] = "active"

    await db.affiliate_partners.update_one({"id": partner_id}, {"$set": updates})
    refreshed = await db.affiliate_partners.find_one({"id": partner_id})
    refreshed.pop("_id", None)
    return refreshed


@router.delete("/partners/{partner_id}")
async def delete_partner(partner_id: str, user=Depends(auth_user)):
    """Désactive un partenaire (soft delete : status='terminated')."""
    _admin_only(user)
    result = await db.affiliate_partners.update_one(
        {"id": partner_id},
        {"$set": {"status": "terminated", "terminated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Partenaire introuvable")
    return {"ok": True}


# ════════════════════════════════════════════════════════════════════════════
# Tracking (public et auth)
# ════════════════════════════════════════════════════════════════════════════
class TrackClickInput(BaseModel):
    code: str
    platform_source: Optional[str] = None  # d'où vient le clic
    user_agent: Optional[str] = None


@router.post("/affiliate/track-click")
async def track_click(payload: TrackClickInput):
    """Enregistre un clic sur un lien partenaire. Endpoint public (pas d'auth)."""
    code = payload.code.strip().upper()
    partner = await db.affiliate_partners.find_one({"code": code, "status": "active"})
    if not partner:
        return {"ok": False, "reason": "code_not_active"}

    await db.affiliate_clicks.insert_one({
        "partner_id": partner["id"],
        "code": code,
        "platform_source": payload.platform_source or "unknown",
        "user_agent": payload.user_agent or "",
        "clicked_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "redirect_to": "/signup", "partner_name": partner["name"]}


@router.get("/affiliate/lookup/{code}")
async def lookup_code(code: str):
    """Public — résolution d'un code partenaire (utilisé par le signup pour
    afficher 'Vous êtes invité par X')."""
    code = code.strip().upper()
    partner = await db.affiliate_partners.find_one({"code": code, "status": "active"})
    if not partner:
        return {"found": False}
    return {
        "found": True,
        "partner_name": partner["name"],
        "platform": partner["platform"],
        "handle": partner.get("handle", ""),
    }


# ════════════════════════════════════════════════════════════════════════════
# Stats & rapports
# ════════════════════════════════════════════════════════════════════════════
@router.get("/partners/{partner_id}/stats")
async def partner_stats(partner_id: str, user=Depends(auth_user)):
    """Stats d'un partenaire : clics / inscriptions / conversions / commission due."""
    _admin_only(user)
    partner = await db.affiliate_partners.find_one({"id": partner_id})
    if not partner:
        raise HTTPException(404, "Partenaire introuvable")

    clicks = await db.affiliate_clicks.count_documents({"partner_id": partner_id})
    signups = await db.affiliate_signups.count_documents({"partner_id": partner_id})
    conversions = await db.affiliate_commissions.count_documents({"partner_id": partner_id})

    # Total commission due (somme des commissions non payées)
    total_due = 0.0
    async for comm in db.affiliate_commissions.find(
        {"partner_id": partner_id, "paid_to_partner": {"$ne": True}}
    ):
        total_due += float(comm.get("commission_amount_eur", 0))

    # CTR & taux de conversion
    ctr = (signups / clicks * 100) if clicks else 0.0
    conversion_rate = (conversions / signups * 100) if signups else 0.0

    return {
        "partner_id": partner_id,
        "code": partner["code"],
        "name": partner["name"],
        "clicks": clicks,
        "signups": signups,
        "conversions": conversions,
        "click_to_signup_rate_pct": round(ctr, 2),
        "signup_to_paid_rate_pct": round(conversion_rate, 2),
        "total_commission_due_eur": round(total_due, 2),
        "currency": "EUR",
    }


@router.get("/partners/stats/summary")
async def partners_summary(user=Depends(auth_user)):
    """Récap global tous partenaires (admin)."""
    _admin_only(user)
    total_partners = await db.affiliate_partners.count_documents({})
    active = await db.affiliate_partners.count_documents({"status": "active"})
    pending = await db.affiliate_partners.count_documents({"status": "pending"})

    total_clicks = await db.affiliate_clicks.count_documents({})
    total_signups = await db.affiliate_signups.count_documents({})
    total_conv = await db.affiliate_commissions.count_documents({})

    total_paid_out = 0.0
    total_due_total = 0.0
    async for comm in db.affiliate_commissions.find():
        amt = float(comm.get("commission_amount_eur", 0))
        if comm.get("paid_to_partner"):
            total_paid_out += amt
        else:
            total_due_total += amt

    return {
        "total_partners": total_partners,
        "active": active,
        "pending": pending,
        "total_clicks": total_clicks,
        "total_signups": total_signups,
        "total_conversions": total_conv,
        "total_commission_due_eur": round(total_due_total, 2),
        "total_commission_paid_eur": round(total_paid_out, 2),
    }


# ════════════════════════════════════════════════════════════════════════════
# Hook conversion (appelé par stripe_routes lors d'invoice.paid)
# ════════════════════════════════════════════════════════════════════════════
async def record_affiliate_conversion(
    user_id: str,
    company_id: str,
    invoice_amount_eur: float,
    stripe_invoice_id: str,
) -> Optional[dict]:
    """Crédite la commission au partenaire si l'utilisateur s'est inscrit
    via un code partenaire. Appelé par le webhook Stripe invoice.paid.

    Retourne le document commission créé, ou None si pas de partenaire lié.
    """
    signup = await db.affiliate_signups.find_one({"user_id": user_id})
    if not signup:
        return None

    partner_id = signup["partner_id"]
    partner = await db.affiliate_partners.find_one({"id": partner_id})
    if not partner or partner.get("status") not in ("active", "paused"):
        return None

    # Vérifie qu'on est encore dans la fenêtre de commission
    signup_date = datetime.fromisoformat(signup["signed_up_at"].replace("Z", "+00:00"))
    duration = partner.get("commission_duration_months", DEFAULT_COMMISSION_DURATION_MONTHS)
    end_date = signup_date + timedelta(days=duration * 31)
    if datetime.now(timezone.utc) > end_date:
        return None  # commission expirée

    rate = float(partner.get("commission_rate", DEFAULT_COMMISSION_RATE)) / 100.0
    commission = round(invoice_amount_eur * rate, 2)

    doc = {
        "partner_id": partner_id,
        "user_id": user_id,
        "company_id": company_id,
        "stripe_invoice_id": stripe_invoice_id,
        "invoice_amount_eur": invoice_amount_eur,
        "commission_rate_pct": partner["commission_rate"],
        "commission_amount_eur": commission,
        "paid_to_partner": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.affiliate_commissions.insert_one(doc)
    logger.info(
        "Commission affiliée enregistrée : partner=%s amount=%.2f€",
        partner["name"], commission,
    )
    return doc
