"""CRUD multi-stair v2 : stairs / niveaux / troncons + endpoint compute."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import (
    get_current_user, now_utc, project_visible_to, require_active_access,
)
from models.schemas import (
    NiveauCreate, NiveauUpdate, StairCreate, StairUpdate,
    TronconCreate, TronconUpdate,
)
from services.stairs_v2 import compute_stair as compute_stair_v2

router = APIRouter(prefix="/projects/{pid}/stairs")


# ── Helpers ────────────────────────────────────────────────────────────────

async def _load_project(pid: str, user) -> Dict[str, Any]:
    p = await db.projects.find_one({"id": pid, **project_visible_to(user)}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    return p


def _find_stair(project: Dict[str, Any], sid: str) -> Dict[str, Any]:
    for s in project.get("stairs", []) or []:
        if s["id"] == sid:
            return s
    raise HTTPException(status_code=404, detail="Escalier introuvable")


def _find_niveau(stair: Dict[str, Any], nid: str) -> Dict[str, Any]:
    for n in stair.get("niveaux", []) or []:
        if n["id"] == nid:
            return n
    raise HTTPException(status_code=404, detail="Niveau introuvable")


def _find_troncon(niveau: Dict[str, Any], tid: str) -> Dict[str, Any]:
    for t in niveau.get("troncons", []) or []:
        if t["id"] == tid:
            return t
    raise HTTPException(status_code=404, detail="Tronçon introuvable")


async def _save_project(pid: str, stairs: List[Dict[str, Any]]):
    await db.projects.update_one(
        {"id": pid},
        {"$set": {"stairs": stairs, "updated_at": now_utc()}},
    )


# ── Stairs ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_stairs(pid: str, user=Depends(get_current_user)):
    p = await _load_project(pid, user)
    return p.get("stairs", []) or []


@router.post("")
async def create_stair(pid: str, payload: StairCreate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    new_stair = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip()[:80] or "Escalier",
        "niveaux": [],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    stairs = p.get("stairs", []) or []
    stairs.append(new_stair)
    await _save_project(pid, stairs)
    return new_stair


@router.get("/{sid}")
async def get_stair(pid: str, sid: str, user=Depends(get_current_user)):
    p = await _load_project(pid, user)
    return _find_stair(p, sid)


@router.patch("/{sid}")
async def update_stair(pid: str, sid: str, payload: StairUpdate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    if payload.name is not None:
        stair["name"] = payload.name.strip()[:80] or stair["name"]
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return stair


@router.delete("/{sid}")
async def delete_stair(pid: str, sid: str, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stairs = [s for s in (p.get("stairs") or []) if s["id"] != sid]
    if len(stairs) == len(p.get("stairs") or []):
        raise HTTPException(status_code=404, detail="Escalier introuvable")
    await _save_project(pid, stairs)
    return {"ok": True}


# ── Niveaux ────────────────────────────────────────────────────────────────

@router.post("/{sid}/niveaux")
async def create_niveau(pid: str, sid: str, payload: NiveauCreate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    new_niv = {
        "id": str(uuid.uuid4()),
        "label": payload.label.strip()[:40] or f"Niveau {len(stair.get('niveaux', [])) + 1}",
        "hauteur_mm": float(payload.hauteur_mm),
        "sol_fini": bool(payload.sol_fini),
        "reserve_mm": float(payload.reserve_mm or 0),
        "troncons": [],
        "order": len(stair.get("niveaux", []) or []),
    }
    stair.setdefault("niveaux", []).append(new_niv)
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return new_niv


@router.patch("/{sid}/niveaux/{nid}")
async def update_niveau(pid: str, sid: str, nid: str, payload: NiveauUpdate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    niveau = _find_niveau(stair, nid)
    data = payload.model_dump(exclude_none=True)
    niveau.update(data)
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return niveau


@router.delete("/{sid}/niveaux/{nid}")
async def delete_niveau(pid: str, sid: str, nid: str, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    before = len(stair.get("niveaux", []) or [])
    stair["niveaux"] = [n for n in (stair.get("niveaux") or []) if n["id"] != nid]
    if len(stair["niveaux"]) == before:
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return {"ok": True}


# ── Tronçons ───────────────────────────────────────────────────────────────

@router.post("/{sid}/niveaux/{nid}/troncons")
async def create_troncon(pid: str, sid: str, nid: str, payload: TronconCreate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    niveau = _find_niveau(stair, nid)
    new_t = {
        "id": str(uuid.uuid4()),
        "type": payload.type,
        "longueur_mm": float(payload.longueur_mm),
        "largeur_mm": float(payload.largeur_mm or 900),
        "order": len(niveau.get("troncons", []) or []),
    }
    niveau.setdefault("troncons", []).append(new_t)
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return new_t


@router.patch("/{sid}/niveaux/{nid}/troncons/{tid}")
async def update_troncon(pid: str, sid: str, nid: str, tid: str, payload: TronconUpdate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    niveau = _find_niveau(stair, nid)
    troncon = _find_troncon(niveau, tid)
    data = payload.model_dump(exclude_none=True)
    troncon.update(data)
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return troncon


@router.delete("/{sid}/niveaux/{nid}/troncons/{tid}")
async def delete_troncon(pid: str, sid: str, nid: str, tid: str, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    niveau = _find_niveau(stair, nid)
    before = len(niveau.get("troncons", []) or [])
    niveau["troncons"] = [t for t in (niveau.get("troncons") or []) if t["id"] != tid]
    if len(niveau["troncons"]) == before:
        raise HTTPException(status_code=404, detail="Tronçon introuvable")
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return {"ok": True}


# ── Compute ────────────────────────────────────────────────────────────────

@router.get("/{sid}/compute")
async def compute_v2(pid: str, sid: str, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    return compute_stair_v2(stair)
