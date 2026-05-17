"""Routes Company Profile + endpoints plateforme (subscription)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from db import PLATFORM_ADMIN_TOKEN, VALID_PLANS, db
from deps import auth_user, ensure_company, require_admin
from models import CompanyProfile, CompanyProfileUpdate

router = APIRouter()


def _to_profile(doc: dict, company_id: str) -> CompanyProfile:
    return CompanyProfile(
        company_id=doc.get("company_id", company_id),
        name=doc.get("name") or company_id,
        artisan_mode=bool(doc.get("artisan_mode", False)),
        subscription_status=doc.get("subscription_status", "trial"),
        subscription_expires_at=doc.get("subscription_expires_at"),
        plan=doc.get("plan", "trial"),
        chantiers_lifetime_count=int(doc.get("chantiers_lifetime_count", 0)),
        cancel_at_period_end=bool(doc.get("cancel_at_period_end", False)),
        cancelled_at=doc.get("cancelled_at"),
    )


@router.get("/company/profile", response_model=CompanyProfile)
async def get_company_profile(user=Depends(auth_user)):
    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


@router.patch("/company/profile", response_model=CompanyProfile)
async def update_company_profile(
    payload: CompanyProfileUpdate, user=Depends(require_admin)
):
    company_id = user.get("company_id", "default")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if update:
        update["company_id"] = company_id
        await db.companies.update_one(
            {"company_id": company_id},
            {"$set": update},
            upsert=True,
        )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


# --- Subscription cancellation (Master Admin) ---------------------------
@router.post("/company/subscription/cancel", response_model=CompanyProfile)
async def cancel_subscription(user=Depends(require_admin)):
    """Désabonnement gracieux : l'accès Pro est conservé jusqu'à
    `subscription_expires_at`, puis le verrou paywall s'active automatiquement.

    Réservé au Master Admin (role == "admin"). Le Mode Artisan ne bypass pas
    cette action — uniquement les administrateurs déclarés peuvent annuler.
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur peut annuler l'abonnement.",
        )
    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    if doc.get("cancel_at_period_end"):
        raise HTTPException(
            status_code=400,
            detail="L'annulation est déjà programmée.",
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "cancel_at_period_end": True,
                "cancelled_at": now_iso,
            }
        },
        upsert=True,
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


@router.post("/company/subscription/reactivate", response_model=CompanyProfile)
async def reactivate_subscription(user=Depends(require_admin)):
    """Réactive l'abonnement avant la fin de la période payée."""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur peut réactiver l'abonnement.",
        )
    company_id = user.get("company_id", "default")
    await db.companies.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "cancel_at_period_end": False,
                "cancelled_at": None,
            }
        },
        upsert=True,
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


# --- Platform admin: régulariser un abonnement (out-of-band) ------------
@router.post("/platform/companies/{company_id}/subscription")
async def platform_set_subscription(
    company_id: str,
    payload: dict,
    x_platform_token: Optional[str] = Header(None),
):
    if x_platform_token != PLATFORM_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid platform token")
    update: dict = {}
    if "subscription_status" in payload:
        if payload["subscription_status"] not in (
            "trial", "active", "suspended",
        ):
            raise HTTPException(400, "Invalid subscription_status")
        update["subscription_status"] = payload["subscription_status"]
    if "plan" in payload:
        if payload["plan"] not in VALID_PLANS:
            raise HTTPException(
                400, f"plan must be one of {sorted(VALID_PLANS)}"
            )
        update["plan"] = payload["plan"]
        # Lorsqu'on passe en Pro : on remet à zéro l'annulation programmée.
        if payload["plan"] == "pro":
            update["cancel_at_period_end"] = False
            update["cancelled_at"] = None
    if "extend_days" in payload:
        try:
            days = int(payload["extend_days"])
        except (TypeError, ValueError):
            raise HTTPException(400, "extend_days must be int")
        new_dt = datetime.now(timezone.utc) + timedelta(days=days)
        update["subscription_expires_at"] = new_dt.isoformat()
    if (
        "subscription_expires_at" in payload
        and "extend_days" not in payload
    ):
        update["subscription_expires_at"] = payload["subscription_expires_at"]
    if "cancel_at_period_end" in payload:
        update["cancel_at_period_end"] = bool(payload["cancel_at_period_end"])
    if not update:
        raise HTTPException(400, "Nothing to update")
    update["company_id"] = company_id
    await db.companies.update_one(
        {"company_id": company_id}, {"$set": update}, upsert=True
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)
