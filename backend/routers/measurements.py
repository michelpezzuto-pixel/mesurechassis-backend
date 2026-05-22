"""Measurements: preview, save, validate."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import get_current_user, has_technician_powers, now_utc, require_active_access
from models.schemas import MeasurementInput
from services.stairs import compute_stair

router = APIRouter(prefix="/projects/{pid}/measurement")


@router.post("")
async def save_measurement(pid: str, payload: MeasurementInput, user=Depends(require_active_access)):
    p = await db.projects.find_one({"id": pid})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if not has_technician_powers(user):
        raise HTTPException(status_code=403, detail="Seuls les Techniciens peuvent saisir les mesures")
    if user["role"] == "technicien" and p.get("technicien_id") not in (user["id"], None):
        raise HTTPException(status_code=403, detail="Ce chantier ne vous est pas assigné")
    if user["role"] == "technicien" and p.get("technicien_id") is None:
        await db.projects.update_one({"id": pid}, {"$set": {"technicien_id": user["id"]}})
    if user["role"] == "admin" and user.get("solo_mode") and not p.get("locked"):
        await db.projects.update_one(
            {"id": pid},
            {"$set": {"locked": True, "transmitted_at": now_utc(), "technicien_id": user["id"]}},
        )

    result = compute_stair(payload)
    doc = {
        "project_id": pid,
        **payload.model_dump(),
        "result": result.model_dump(),
        "validated": False,
        "updated_at": now_utc(),
    }
    existing = await db.measurements.find_one({"project_id": pid})
    if existing:
        await db.measurements.update_one({"project_id": pid}, {"$set": doc})
    else:
        doc["created_at"] = now_utc()
        await db.measurements.insert_one(doc)

    await db.projects.update_one({"id": pid}, {"$set": {"status": "a_verifier", "updated_at": now_utc()}})
    doc.pop("_id", None)
    return doc


@router.post("/preview")
async def preview_measurement(pid: str, payload: MeasurementInput, user=Depends(require_active_access)):
    return compute_stair(payload)


@router.post("/validate")
async def validate_measurement(pid: str, user=Depends(require_active_access)):
    if not has_technician_powers(user):
        raise HTTPException(status_code=403, detail="Seuls les Techniciens peuvent valider la conception")
    m = await db.measurements.find_one({"project_id": pid})
    if not m:
        raise HTTPException(status_code=404, detail="Aucune mesure à valider")
    await db.measurements.update_one({"project_id": pid}, {"$set": {"validated": True, "updated_at": now_utc()}})
    await db.projects.update_one({"id": pid}, {"$set": {"status": "valide", "updated_at": now_utc()}})
    return {"ok": True}
