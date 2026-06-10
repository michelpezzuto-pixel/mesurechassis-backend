"""Système de parrainage — Build 9 (juin 2026).

Règles métier (validées avec le client) :
  • Récompense PARRAIN : 2 mois offerts par filleul actif.
  • Récompense FILLEUL : aucune (le filleul devient parrain à son tour s'il le souhaite).
  • Déclenchement : à la PREMIÈRE facture payée du filleul (hook Stripe `invoice.paid`).
  • Limite : 10 filleuls max par parrain.
  • Code parrain : personnalisable par l'utilisateur (style "JEAN-MENUISERIE").
    Auto-généré au format `MC-XXXXXX` à la création du compte si non défini.

Anti-abus :
  • Un compte ne peut JAMAIS être son propre filleul.
  • Un filleul ne peut valider QU'UN seul code à vie (1 compte = 1 parrain max).
  • Le code est unique en base (index unique).
  • Si le parrain atteint la limite de 10, l'inscription du filleul reste OK
    mais aucune récompense n'est créditée (avec log).
"""
from __future__ import annotations

import logging
import random
import re
import string
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import auth_user

logger = logging.getLogger("mesurechassis.referral")
router = APIRouter()

MAX_REFERRALS_PER_PARRAIN = 10
MONTHS_PER_REFERRAL = 2

# Format autorisé pour les codes personnalisables.
# Lettres ASCII (insensible à la casse, normalisé en MAJ), chiffres, tiret.
# Longueur 4–24 caractères pour rester ergonomique sur les share-buttons.
CODE_REGEX = re.compile(r"^[A-Z0-9-]{4,24}$")


def _generate_code() -> str:
    """Génère un code aléatoire `MC-XXXXXX` (chiffres + lettres majuscules)."""
    alphabet = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(alphabet, k=6))
    return f"MC-{suffix}"


def _normalize_code(raw: str) -> str:
    """Normalise un code utilisateur : MAJUSCULES + trim + supprime espaces."""
    return (raw or "").strip().upper().replace(" ", "-")


async def ensure_referral_code(company_id: str) -> str:
    """Garantit qu'une `company` possède un `referral_code` unique.

    Appelé au boot de l'écran parrainage (lazy init), évite de devoir
    migrer toutes les companies existantes en base.
    """
    company = await db.companies.find_one({"company_id": company_id})
    if not company:
        raise HTTPException(404, "Société introuvable")
    existing = company.get("referral_code")
    if existing:
        return existing
    # Tentative jusqu'à 10× de générer un code unique (collisions très rares).
    for _ in range(10):
        candidate = _generate_code()
        if not await db.companies.find_one({"referral_code": candidate}):
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": {"referral_code": candidate}},
            )
            logger.info("Référence créée pour company=%s code=%s", company_id, candidate)
            return candidate
    raise HTTPException(500, "Impossible de générer un code unique — réessayez")


# ════════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ════════════════════════════════════════════════════════════════════════════
class ReferralStatus(BaseModel):
    code: str
    code_is_custom: bool
    max_referrals: int
    referrals_used: int
    referrals_pending: int  # filleuls inscrits mais qui n'ont pas encore payé
    credit_months_total: int  # nb total de mois offerts gagnés (incl. déjà utilisés)
    credit_months_remaining: int  # mois encore à appliquer
    referred_by_code: Optional[str] = None  # qui m'a parrainé ?


class UpdateCodeRequest(BaseModel):
    # ⚠️ Pas de `min_length`/`max_length` Pydantic ici — on préfère lever
    # un HTTPException(400) explicite dans l'endpoint (cohérence avec les
    # autres erreurs métier qui sont en 400, pas en 422).
    code: str


class ValidateCodeRequest(BaseModel):
    code: str


class ValidateCodeResponse(BaseModel):
    valid: bool
    parrain_name: Optional[str] = None
    error: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════
@router.get("/referral/me", response_model=ReferralStatus)
async def get_my_referral(user=Depends(auth_user)):
    """Retourne le statut de parrainage de ma société.

    Inclut le code, les compteurs, le crédit accumulé et — si applicable —
    le code de mon parrain.
    """
    company_id = user.get("company_id") or ""
    code = await ensure_referral_code(company_id)
    company = await db.companies.find_one({"company_id": company_id}) or {}

    # Compteurs filleuls
    referrals_used = await db.companies.count_documents(
        {"referred_by_company_id": company_id, "referral_paid": True}
    )
    referrals_pending = await db.companies.count_documents(
        {"referred_by_company_id": company_id, "referral_paid": {"$ne": True}}
    )
    credit_total = int(company.get("referral_credit_months_total") or 0)
    credit_remaining = int(company.get("referral_credit_months_remaining") or 0)

    # Code du parrain
    referred_by_code = None
    referred_by_id = company.get("referred_by_company_id")
    if referred_by_id:
        parrain = await db.companies.find_one(
            {"company_id": referred_by_id}, {"referral_code": 1}
        )
        if parrain:
            referred_by_code = parrain.get("referral_code")

    return ReferralStatus(
        code=code,
        code_is_custom=bool(company.get("referral_code_is_custom")),
        max_referrals=MAX_REFERRALS_PER_PARRAIN,
        referrals_used=referrals_used,
        referrals_pending=referrals_pending,
        credit_months_total=credit_total,
        credit_months_remaining=credit_remaining,
        referred_by_code=referred_by_code,
    )


@router.post("/referral/code", response_model=ReferralStatus)
async def update_my_code(payload: UpdateCodeRequest, user=Depends(auth_user)):
    """Personnalise mon code de parrainage.

    Restrictions :
      • Format `[A-Z0-9-]{4,24}` (normalisé automatiquement en MAJ)
      • Unique en base (autre société ne peut pas avoir le même)
      • Pas de mots réservés (admin, mesurechassis…)
    """
    company_id = user.get("company_id") or ""
    new_code = _normalize_code(payload.code)
    # Validation manuelle (cohérence 400 partout, pas de 422 Pydantic)
    if not new_code or len(new_code) < 4 or len(new_code) > 24:
        raise HTTPException(400, "Le code doit faire entre 4 et 24 caractères.")
    if not CODE_REGEX.match(new_code):
        raise HTTPException(
            400,
            "Format invalide. Utilisez 4 à 24 caractères : lettres, chiffres et tirets.",
        )
    reserved = {"ADMIN", "MESURECHASSIS", "TEST", "DEMO", "NULL", "UNDEFINED"}
    # Les codes auto-générés démarrent par `MC-` → réservé au système.
    if new_code in reserved or new_code.startswith("MC-"):
        raise HTTPException(400, "Ce code est réservé. Choisissez-en un autre.")

    # Vérifie l'unicité (sauf si c'est déjà le mien)
    existing = await db.companies.find_one(
        {"referral_code": new_code, "company_id": {"$ne": company_id}},
        {"_id": 1},
    )
    if existing:
        raise HTTPException(409, "Ce code est déjà utilisé. Essayez une variante.")

    await db.companies.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "referral_code": new_code,
                "referral_code_is_custom": True,
                "referral_code_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    logger.info("Code parrainage personnalisé : company=%s code=%s", company_id, new_code)
    return await get_my_referral(user)


@router.post("/referral/validate", response_model=ValidateCodeResponse)
async def validate_code(payload: ValidateCodeRequest):
    """Valide qu'un code parrainage existe (sans authentification).

    Utilisé à l'inscription : on vérifie en live que le code saisi est valide
    et on affiche le nom du parrain pour rassurer le filleul.
    """
    code = _normalize_code(payload.code)
    if not code:
        return ValidateCodeResponse(valid=False, error="Code vide")
    parrain = await db.companies.find_one(
        {"referral_code": code}, {"_id": 0, "name": 1, "company_id": 1}
    )
    if not parrain:
        return ValidateCodeResponse(valid=False, error="Code introuvable")
    return ValidateCodeResponse(valid=True, parrain_name=parrain.get("name"))


# ════════════════════════════════════════════════════════════════════════════
# Helpers appelés depuis d'autres modules
# ════════════════════════════════════════════════════════════════════════════
async def link_referral_at_signup(
    new_company_id: str, raw_code: Optional[str]
) -> None:
    """Lie un nouveau compte à son parrain à l'inscription.

    Appelé depuis `/auth/register`. Ne lève PAS d'exception si le code est
    invalide ou plein — l'inscription doit aboutir même si le code échoue.
    On log un warning à la place.
    """
    if not raw_code:
        return
    code = _normalize_code(raw_code)
    if not code:
        return
    parrain = await db.companies.find_one(
        {"referral_code": code}, {"company_id": 1, "name": 1}
    )
    if not parrain:
        logger.warning("Code parrainage introuvable à l'inscription : %s", code)
        return
    if parrain.get("company_id") == new_company_id:
        logger.warning("Tentative d'auto-parrainage refusée pour %s", new_company_id)
        return
    # Vérifier la limite côté parrain (informatif — on lie quand même mais sans
    # générer de crédit ultérieur si dépassement détecté au paiement)
    used = await db.companies.count_documents(
        {"referred_by_company_id": parrain["company_id"], "referral_paid": True}
    )
    if used >= MAX_REFERRALS_PER_PARRAIN:
        logger.warning(
            "Parrain %s a atteint la limite de %d filleuls — aucune récompense future",
            parrain["company_id"],
            MAX_REFERRALS_PER_PARRAIN,
        )
    await db.companies.update_one(
        {"company_id": new_company_id},
        {
            "$set": {
                "referred_by_company_id": parrain["company_id"],
                "referred_by_code": code,
                "referral_paid": False,
                "referred_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    logger.info(
        "Filleul %s lié au parrain %s (code=%s)",
        new_company_id,
        parrain["company_id"],
        code,
    )


async def credit_parrain_on_first_payment(filleul_company_id: str) -> None:
    """Crédite le parrain de 2 mois offerts à la 1ère facture payée du filleul.

    Appelé depuis le hook Stripe `invoice.paid` (stripe_routes.py).
    Idempotent : ne crédite QU'UNE seule fois par filleul (flag `referral_paid`).
    """
    filleul = await db.companies.find_one(
        {"company_id": filleul_company_id},
        {"referred_by_company_id": 1, "referral_paid": 1, "name": 1},
    )
    if not filleul:
        return
    if filleul.get("referral_paid"):
        # Déjà crédité au précédent paiement
        return
    parrain_id = filleul.get("referred_by_company_id")
    if not parrain_id:
        # Filleul sans parrain
        return

    # Vérifie la limite côté parrain
    used = await db.companies.count_documents(
        {"referred_by_company_id": parrain_id, "referral_paid": True}
    )
    if used >= MAX_REFERRALS_PER_PARRAIN:
        logger.warning(
            "Parrain %s a atteint la limite — pas de crédit pour filleul %s",
            parrain_id,
            filleul_company_id,
        )
        # On marque quand même le filleul comme payé pour éviter de retenter
        await db.companies.update_one(
            {"company_id": filleul_company_id},
            {"$set": {"referral_paid": True}},
        )
        return

    # Crédite le parrain : +2 mois
    await db.companies.update_one(
        {"company_id": parrain_id},
        {
            "$inc": {
                "referral_credit_months_total": MONTHS_PER_REFERRAL,
                "referral_credit_months_remaining": MONTHS_PER_REFERRAL,
            },
            "$push": {
                "referral_credit_history": {
                    "filleul_company_id": filleul_company_id,
                    "filleul_name": filleul.get("name") or "?",
                    "months_credited": MONTHS_PER_REFERRAL,
                    "credited_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        },
    )
    await db.companies.update_one(
        {"company_id": filleul_company_id},
        {"$set": {"referral_paid": True, "referral_paid_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(
        "🎁 Parrain %s crédité de %d mois (filleul %s)",
        parrain_id,
        MONTHS_PER_REFERRAL,
        filleul_company_id,
    )
