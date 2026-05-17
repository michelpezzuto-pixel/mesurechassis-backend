"""Routes CRUD chantiers (métier de base + signatures)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from db import FREE_PLAN_MAX_CHANTIERS, VALID_STATUSES, db
from deps import (
    require_active_subscription,
    require_roles,
    send_push_to_user,
)
from models import (
    Chantier,
    ChantierCreate,
    ChantierUpdate,
    SignatureIn,
)

router = APIRouter()


@router.post("/chantiers", response_model=Chantier)
async def create_chantier(
    payload: ChantierCreate,
    user=Depends(require_roles(["admin", "commercial"])),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    # --- Anti-fraud Freemium lifetime limit -------------------------------
    # Le compteur lifetime n'est jamais décrémenté : impossible de
    # contourner en supprimant un chantier.
    if (user.get("plan") == "free") and not user.get("artisan_mode", False):
        used = int(user.get("chantiers_lifetime_count", 0))
        if used >= FREE_PLAN_MAX_CHANTIERS:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "free_plan_limit",
                    "message": (
                        f"Limite Freemium atteinte ({FREE_PLAN_MAX_CHANTIERS} "
                        "chantiers maximum sur la durée de vie du compte). "
                        "Passez en Pro pour créer des chantiers illimités."
                    ),
                    "limit": FREE_PLAN_MAX_CHANTIERS,
                    "used": used,
                },
            )
    client_name = payload.client_name
    if not client_name:
        parts = [p for p in [payload.last_name, payload.first_name] if p]
        client_name = " ".join(parts).strip() or "Sans nom"
    doc = {
        "id": str(uuid.uuid4()),
        "client_name": client_name,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "address": payload.address,
        "postal_code": payload.postal_code,
        "city": payload.city,
        "status": payload.status,
        "created_by": user["id"],
        "assigned_to": payload.assigned_to,
        "appointment_at": payload.appointment_at,
        "notes": payload.notes,
        "company_id": user.get("company_id", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "site_photos": payload.site_photos or [],
    }
    await db.chantiers.insert_one(doc)
    doc.pop("_id", None)
    # Incrément lifetime — quel que soit le plan (utile pour bascules ultérieures).
    await db.companies.update_one(
        {"company_id": user.get("company_id", "default")},
        {"$inc": {"chantiers_lifetime_count": 1}},
        upsert=True,
    )
    if payload.assigned_to:
        await send_push_to_user(
            payload.assigned_to,
            "📌 Nouveau chantier assigné",
            f"{client_name} — Prise de rendez-vous à faire",
            {"type": "chantier_assigned", "chantier_id": doc["id"]},
        )
    return Chantier(**doc)


@router.get("/chantiers", response_model=List[Chantier])
async def list_chantiers(
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    user=Depends(require_active_subscription),
):
    query: dict = {"company_id": user.get("company_id", "default")}
    if status_filter and status_filter in VALID_STATUSES:
        query["status"] = status_filter
    if q:
        import re as _re
        safe = _re.escape(q.strip())
        query["$or"] = [
            {"client_name": {"$regex": safe, "$options": "i"}},
            {"address": {"$regex": safe, "$options": "i"}},
        ]
    docs = (
        await db.chantiers.find(query, {"_id": 0})
        .sort("created_at", -1)
        .to_list(500)
    )
    return [Chantier(**d) for d in docs]


@router.get("/chantiers/{chantier_id}", response_model=Chantier)
async def get_chantier(
    chantier_id: str, user=Depends(require_active_subscription)
):
    doc = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    return Chantier(**doc)


@router.patch("/chantiers/{chantier_id}", response_model=Chantier)
async def update_chantier(
    chantier_id: str,
    payload: ChantierUpdate,
    user=Depends(require_roles(["admin", "commercial"])),
):
    company = user.get("company_id", "default")
    existing = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}
    )
    if not existing:
        raise HTTPException(404, "Chantier introuvable")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    if update:
        await db.chantiers.update_one(
            {"id": chantier_id, "company_id": company}, {"$set": update}
        )
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    new_assignee = update.get("assigned_to")
    if new_assignee and new_assignee != existing.get("assigned_to"):
        await send_push_to_user(
            new_assignee,
            "Nouveau chantier affecté",
            f"{doc['client_name']} — {doc['address']}",
            {"type": "chantier_assigned", "chantier_id": chantier_id},
        )
    return Chantier(**doc)


@router.delete("/chantiers/{chantier_id}")
async def delete_chantier(
    chantier_id: str,
    user=Depends(require_roles(["admin", "commercial"])),
):
    company = user.get("company_id", "default")
    res = await db.chantiers.delete_one(
        {"id": chantier_id, "company_id": company}
    )
    if res.deleted_count:
        await db.mesures.delete_many({"chantier_id": chantier_id})
    return {"ok": True}


# --- Signatures ----------------------------------------------------------
@router.post("/chantiers/{chantier_id}/signature", response_model=Chantier)
async def save_signature(
    chantier_id: str,
    payload: SignatureIn,
    user=Depends(require_active_subscription),
):
    company = user.get("company_id", "default")
    if not payload.signature.strip():
        raise HTTPException(400, "Signature vide")
    res = await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {
            "$set": {
                "client_signature": payload.signature,
                "signed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Chantier introuvable")
    doc = await db.chantiers.find_one({"id": chantier_id}, {"_id": 0})
    return Chantier(**doc)


@router.delete("/chantiers/{chantier_id}/signature", response_model=Chantier)
async def delete_signature(
    chantier_id: str, user=Depends(require_active_subscription)
):
    company = user.get("company_id", "default")
    await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {"$set": {"client_signature": None, "signed_at": None}},
    )
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    return Chantier(**doc)
