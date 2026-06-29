"""Projects CRUD + transmit + assign + photos."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import (
    get_current_user, now_utc, project_visible_to, require_active_access,
    require_roles,
)
from models.schemas import (
    AssignRequest, PhotoCreate, PhotoUpdate, ProjectCreate, ProjectUpdate,
)

router = APIRouter(prefix="/projects")


@router.get("")
async def list_projects(user=Depends(require_active_access), status_filter: Optional[str] = None):
    q = project_visible_to(user)
    if status_filter and status_filter != "tous":
        q["status"] = status_filter
    # Exclude photos array from list view (can be heavy base64 payload)
    return await db.projects.find(q, {"_id": 0, "photos": 0}).sort("created_at", -1).to_list(2000)


@router.post("")
async def create_project(payload: ProjectCreate, user=Depends(require_roles("admin"))):
    pid = str(uuid.uuid4())
    doc = {
        "id": pid,
        **payload.model_dump(),
        "status": "brouillon",
        "commercial_id": user["id"],
        "creator_id": user["id"],
        "technicien_id": user["id"] if user.get("solo_mode") else None,
        "company_id": user.get("company_id"),  # SEC-002: tenant ownership
        "company_name": user.get("company_name"),
        "locked": bool(user.get("solo_mode")),
        "transmitted_at": now_utc() if user.get("solo_mode") else None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    if user.get("solo_mode"):
        doc["status"] = "a_mesurer"
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/{pid}")
async def get_project(pid: str, user=Depends(require_active_access)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    p["measurement"] = m
    return p


@router.put("/{pid}")
async def update_project(pid: str, payload: ProjectUpdate, user=Depends(require_active_access)):
    # SEC-002: scope by tenant
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q)
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Seuls les Admin peuvent modifier l'identification client")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = now_utc()
    await db.projects.update_one(q, {"$set": update})
    return await db.projects.find_one(q, {"_id": 0})


@router.delete("/{pid}")
async def delete_project(pid: str, user=Depends(require_active_access)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q)
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Suppression réservée aux Admin")
    await db.projects.delete_one(q)
    await db.measurements.delete_many({"project_id": pid})
    return {"ok": True}


@router.post("/{pid}/transmit")
async def transmit_project(pid: str, user=Depends(require_roles("admin"))):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q)
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    await db.projects.update_one(
        q,
        {"$set": {
            "locked": True, "status": "a_mesurer",
            "transmitted_at": now_utc(), "updated_at": now_utc(),
        }},
    )
    return {"ok": True}


@router.post("/{pid}/unlock")
async def unlock_project(pid: str, user=Depends(require_roles("admin"))):
    """Admin uniquement : déverrouille un chantier transmis pour pouvoir
    le ré-éditer (corriger des mesures, ajouter un escalier oublié, etc.)."""
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q)
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    await db.projects.update_one(
        q,
        {"$set": {
            "locked": False, "status": "brouillon",
            "updated_at": now_utc(),
        }, "$unset": {"transmitted_at": ""}},
    )
    return {"ok": True}


@router.post("/{pid}/assign")
async def assign_technicien(pid: str, payload: AssignRequest, user=Depends(require_roles("admin"))):
    # SEC-002: project must belong to admin's company AND technician must too
    q = {"id": pid, **project_visible_to(user)}
    if not await db.projects.find_one(q, {"id": 1}):
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    tech = await db.users.find_one({
        "id": payload.technicien_id,
        "role": "technicien",
        "company_id": user.get("company_id"),
    })
    if not tech:
        raise HTTPException(status_code=404, detail="Technicien introuvable")
    await db.projects.update_one(
        q,
        {"$set": {"technicien_id": payload.technicien_id, "updated_at": now_utc()}},
    )
    return {"ok": True}


# ---------------------- Photos ----------------------
PHOTO_MAX_PER_PROJECT = 10


async def _ensure_can_edit_photos(pid: str, user) -> dict:
    p = await db.projects.find_one({"id": pid, **project_visible_to(user)})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    # Admin (anywhere) + Solo + Technicien assigné peuvent éditer photos
    is_admin = user["role"] == "admin"
    is_solo = bool(user.get("solo_mode"))
    is_assigned_tech = user["role"] == "technicien" and p.get("technicien_id") == user["id"]
    if not (is_admin or is_solo or is_assigned_tech):
        raise HTTPException(status_code=403, detail="Accès interdit")
    return p


@router.get("/{pid}/photos")
async def list_photos(pid: str, user=Depends(require_active_access)):
    p = await db.projects.find_one({"id": pid, **project_visible_to(user)}, {"_id": 0, "photos": 1})
    if p is None:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    return p.get("photos", []) or []


@router.post("/{pid}/photos")
async def add_photo(pid: str, payload: PhotoCreate, user=Depends(require_active_access)):
    p = await _ensure_can_edit_photos(pid, user)
    photos = p.get("photos", []) or []
    if len(photos) >= PHOTO_MAX_PER_PROJECT:
        raise HTTPException(
            status_code=400,
            detail=f"Limite atteinte ({PHOTO_MAX_PER_PROJECT} photos max par chantier)",
        )
    b64 = (payload.base64 or "").strip()
    if not b64:
        raise HTTPException(status_code=400, detail="Image vide")
    photo = {
        "id": str(uuid.uuid4()),
        "base64": b64,
        "caption": (payload.caption or "")[:200],
        "created_at": now_utc(),
    }
    await db.projects.update_one(
        {"id": pid},
        {"$push": {"photos": photo}, "$set": {"updated_at": now_utc()}},
    )
    return photo


@router.patch("/{pid}/photos/{photo_id}")
async def update_photo(pid: str, photo_id: str, payload: PhotoUpdate, user=Depends(require_active_access)):
    await _ensure_can_edit_photos(pid, user)
    if payload.caption is None:
        return {"ok": True}
    res = await db.projects.update_one(
        {"id": pid, "photos.id": photo_id},
        {"$set": {"photos.$.caption": payload.caption[:200], "updated_at": now_utc()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    return {"ok": True}


@router.delete("/{pid}/photos/{photo_id}")
async def delete_photo(pid: str, photo_id: str, user=Depends(require_active_access)):
    await _ensure_can_edit_photos(pid, user)
    res = await db.projects.update_one(
        {"id": pid},
        {"$pull": {"photos": {"id": photo_id}}, "$set": {"updated_at": now_utc()}},
    )
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    return {"ok": True}
