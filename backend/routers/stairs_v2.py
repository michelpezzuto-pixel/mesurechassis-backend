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

# ── Floor index helpers (-3..+7) ──────────────────────────────────────────

MIN_FLOOR = -3
MAX_FLOOR = 7


def floor_index_to_label(idx: int) -> str:
    """Convertit un index numérique en libellé FR (-1=Sous-sol, 0=RDC, 1=R+1...)."""
    if idx == 0:
        return "RDC"
    if idx == -1:
        return "Sous-sol"
    if idx < 0:
        return f"Sous-sol {idx}"
    return f"R+{idx}"


def _validate_floor_index(idx: int) -> None:
    if not (MIN_FLOOR <= idx <= MAX_FLOOR):
        raise HTTPException(
            status_code=422,
            detail=f"floor_index hors plage [{MIN_FLOOR}..{MAX_FLOOR}]",
        )


def _validate_contiguity(niveaux: List[Dict[str, Any]], new_idx: int, exclude_id: str | None = None) -> None:
    """La séquence des floor_index (avec le nouveau) doit être contiguë (sans saut).
    Les niveaux ghost (is_ghost=True) comptent pour préserver la continuité.
    """
    existing = [n["floor_index"] for n in niveaux if n.get("id") != exclude_id and "floor_index" in n]
    indices = sorted(set(existing + [new_idx]))
    if not indices:
        return
    for prev, nxt in zip(indices, indices[1:]):
        if nxt - prev != 1:
            missing = list(range(prev + 1, nxt))
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Saut de niveau détecté : il manque {missing}. "
                    "Créez d'abord les niveaux intermédiaires ou cochez « Pas d'escalier ici »."
                ),
            )


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
        "shape": payload.shape,
        "niveaux": [],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    # If shape == "droit", create a default niveau RDC (floor_index=0) with single tronçon
    if payload.shape == "droit":
        n_id = str(uuid.uuid4())
        new_stair["niveaux"].append({
            "id": n_id,
            "label": floor_index_to_label(0),
            "floor_index": 0,
            "is_ghost": False,
            "hauteur_mm": 2700,
            "sol_fini": True,
            "reserve_mm": 0,
            "troncons": [{
                "id": str(uuid.uuid4()),
                "type": "droit",
                "longueur_mm": 3500,
                "largeur_mm": 900,
                "order": 0,
            }],
            "order": 0,
        })
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
    if payload.shape is not None:
        stair["shape"] = payload.shape
        # When switching to "droit" and no niveau exists, seed default RDC + 1 tronçon
        # so the DroitForm has data to bind to (UX continuity).
        if payload.shape == "droit" and not (stair.get("niveaux") or []):
            n_id = str(uuid.uuid4())
            stair["niveaux"] = [{
                "id": n_id,
                "label": floor_index_to_label(0),
                "floor_index": 0,
                "is_ghost": False,
                "hauteur_mm": 2700,
                "sol_fini": True,
                "reserve_mm": 0,
                "epaisseur_dalle_mm": 200,
                "hauteur_sous_plafond_mm": 2500,
                "entry_mode": "hauteur",
                "troncons": [{
                    "id": str(uuid.uuid4()),
                    "type": "droit",
                    "longueur_mm": 3500,
                    "largeur_mm": 900,
                    "order": 0,
                }],
                "order": 0,
            }]
        # When switching to a tournant shape (1/4 or 2/4) and no niveau exists,
        # seed a default RDC niveau with the canonical tronçon sequence.
        # - quart_tournant (1/4 T)   → [droit, quart_bas, droit]   (1 angle)
        # - demi_tournant  (2/4 T)   → [droit, quart_bas, droit, quart_haut, droit] (2 angles)
        elif payload.shape in ("quart_tournant", "demi_tournant") and not (stair.get("niveaux") or []):
            if payload.shape == "quart_tournant":
                template = [
                    ("droit",     1500),
                    ("quart_bas", 1200),
                    ("droit",     1500),
                ]
            else:  # demi_tournant
                template = [
                    ("droit",     1200),
                    ("quart_bas", 1000),
                    ("droit",      900),
                    ("quart_haut", 1000),
                    ("droit",     1200),
                ]
            stair["niveaux"] = [{
                "id": str(uuid.uuid4()),
                "label": floor_index_to_label(0),
                "floor_index": 0,
                "is_ghost": False,
                "hauteur_mm": 2700,
                "sol_fini": True,
                "reserve_mm": 0,
                "epaisseur_dalle_mm": 200,
                "hauteur_sous_plafond_mm": 2500,
                "entry_mode": "hauteur",
                "troncons": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": t_type,
                        "longueur_mm": t_len,
                        "largeur_mm": 900,
                        "order": i,
                    }
                    for i, (t_type, t_len) in enumerate(template)
                ],
                "order": 0,
            }]
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
    _validate_floor_index(payload.floor_index)
    existing = stair.get("niveaux", []) or []
    # Reject duplicate floor_index
    if any(n.get("floor_index") == payload.floor_index for n in existing):
        raise HTTPException(
            status_code=400,
            detail=f"Le niveau {floor_index_to_label(payload.floor_index)} existe déjà sur cet escalier",
        )
    _validate_contiguity(existing, payload.floor_index)
    label = (payload.label or "").strip() or floor_index_to_label(payload.floor_index)
    new_niv = {
        "id": str(uuid.uuid4()),
        "label": label[:40],
        "floor_index": payload.floor_index,
        "is_ghost": bool(payload.is_ghost),
        "hauteur_mm": float(payload.hauteur_mm),
        "sol_fini": bool(payload.sol_fini),
        "reserve_mm": float(payload.reserve_mm or 0),
        "troncons": [],
        "order": payload.floor_index,
    }
    existing.append(new_niv)
    existing.sort(key=lambda n: n.get("floor_index", 0))
    stair["niveaux"] = existing
    stair["updated_at"] = now_utc()
    await _save_project(pid, p["stairs"])
    return new_niv


@router.patch("/{sid}/niveaux/{nid}")
async def update_niveau(pid: str, sid: str, nid: str, payload: NiveauUpdate, user=Depends(require_active_access)):
    p = await _load_project(pid, user)
    stair = _find_stair(p, sid)
    niveau = _find_niveau(stair, nid)
    data = payload.model_dump(exclude_none=True)
    if "floor_index" in data:
        _validate_floor_index(data["floor_index"])
        _validate_contiguity(stair.get("niveaux") or [], data["floor_index"], exclude_id=nid)
        # Auto-update the label if user didn't provide one explicitly
        if "label" not in data:
            data["label"] = floor_index_to_label(data["floor_index"])
        data["order"] = data["floor_index"]
    if data.get("is_ghost"):
        # Vider les tronçons quand on rend le niveau ghost
        niveau["troncons"] = []
    niveau.update(data)
    # Re-sort niveaux par floor_index pour cohérence
    niveaux = sorted(stair.get("niveaux") or [], key=lambda n: n.get("floor_index", n.get("order", 0)))
    stair["niveaux"] = niveaux
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
