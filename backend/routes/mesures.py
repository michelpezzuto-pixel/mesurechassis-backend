"""Routes CRUD mesures (ouvertures)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from db import VALID_BLOCK_TYPES, db
from deps import require_active_subscription, require_roles
from models import Mesure, MesureCreate
from routes.limits import check_free_plan_limit, FreeLimitType
from utils import check_chantier_access, compute_alerts

router = APIRouter()

# Mesures éditables uniquement par Commercial / Technicien.
# Admin est exclu (bypass possible via Mode Artisan Unique).
# Admin inclus : un Master Admin (Artisan solo OU Entreprise) doit pouvoir
# créer/éditer/supprimer ses propres mesures sans dépendre d'un commercial
# ou technicien — sinon un compte solo serait bloqué.
EDIT_ROLES = ["admin", "commercial", "technician"]


@router.post("/mesures", response_model=Mesure)
async def create_mesure(
    payload: MesureCreate, user=Depends(require_roles(EDIT_ROLES))
):
    if payload.block_type not in VALID_BLOCK_TYPES:
        raise HTTPException(400, "Invalid block_type")
    # 🎯 Juillet 2026 — Paywall Freemium : max 5 ouvertures cumulées
    await check_free_plan_limit(user, FreeLimitType.OUVERTURES)
    await check_chantier_access(db, payload.chantier_id, user)
    alerts, slope = compute_alerts(payload)
    doc = payload.model_dump()
    doc.update(
        {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "alerts": alerts,
            "slope_angle_deg": slope,
        }
    )
    await db.mesures.insert_one(doc)
    doc.pop("_id", None)
    return Mesure(**doc)


@router.get(
    "/chantiers/{chantier_id}/mesures", response_model=List[Mesure]
)
async def list_mesures(
    chantier_id: str, user=Depends(require_active_subscription)
):
    await check_chantier_access(db, chantier_id, user)
    docs = (
        await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0})
        .sort("created_at", 1)
        .to_list(500)
    )
    return [Mesure(**d) for d in docs]


@router.delete("/mesures/{mesure_id}")
async def delete_mesure(
    mesure_id: str, user=Depends(require_roles(EDIT_ROLES))
):
    mesure = await db.mesures.find_one({"id": mesure_id})
    if mesure:
        await check_chantier_access(db, mesure["chantier_id"], user)
        await db.mesures.delete_one({"id": mesure_id})
    return {"ok": True}


@router.get("/mesures/{mesure_id}", response_model=Mesure)
async def get_mesure(
    mesure_id: str, user=Depends(require_active_subscription)
):
    mesure = await db.mesures.find_one({"id": mesure_id}, {"_id": 0})
    if not mesure:
        raise HTTPException(404, "Mesure introuvable")
    await check_chantier_access(db, mesure["chantier_id"], user)
    return Mesure(**mesure)


@router.patch("/mesures/{mesure_id}", response_model=Mesure)
async def update_mesure(
    mesure_id: str,
    payload: MesureCreate,
    user=Depends(require_roles(EDIT_ROLES)),
):
    existing = await db.mesures.find_one({"id": mesure_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Mesure introuvable")
    await check_chantier_access(db, existing["chantier_id"], user)
    if payload.block_type not in VALID_BLOCK_TYPES:
        raise HTTPException(400, "Invalid block_type")
    alerts, slope = compute_alerts(payload)
    update_doc = payload.model_dump()
    update_doc.update(
        {
            "id": existing["id"],
            "chantier_id": existing["chantier_id"],
            "created_at": existing.get("created_at"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "alerts": alerts,
            "slope_angle_deg": slope,
        }
    )
    await db.mesures.replace_one({"id": mesure_id}, update_doc)
    update_doc.pop("_id", None)
    return Mesure(**update_doc)
