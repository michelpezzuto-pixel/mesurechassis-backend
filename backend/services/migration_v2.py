"""
Migration v2 — Transforme les anciens projets `measurement` en `stairs[]` v2.

Au démarrage de l'app :
1. Pour chaque project sans `stairs[]` ou stairs vide :
2. On lit son `measurement` (collection séparée) ou `project.measurement` legacy
3. On construit 1 escalier "Escalier Principal" / 1 niveau "Niveau 1" / 1 tronçon droit
4. On le persiste dans project.stairs (non destructif : le measurement legacy reste)

v2.1 (refactor mai 2025) :
5. Backfill `shape` sur les stairs existantes (heuristique : 1 niveau + 1 troncon droit → "droit", sinon "tournant").
6. Backfill `floor_index` sur les niveaux (RDC→0, R+1→1, Sous-sol→-1, sinon order).
7. Backfill `is_ghost=False` partout par défaut.
"""
from __future__ import annotations

import logging
import re
import uuid

from core.db import db
from core.security import now_utc

logger = logging.getLogger("mesure_escalier.migration")


def _infer_floor_index(label: str, order: int) -> int:
    """Map label legacy → floor_index numérique.

    Conventions :
    - "RDC" / "Rez" → 0
    - "R+N" → N
    - "Sous-sol" → -1, "Sous-sol -N" → -N
    - "Niveau N" → N-1 (Niveau 1 = RDC, Niveau 2 = R+1, ...)
    - fallback : `order`
    """
    s = (label or "").strip().lower()
    if not s:
        return order
    if "rdc" in s or s in ("0", "rez", "rez-de-chaussée"):
        return 0
    if "sous-sol" in s or s.startswith("ss") or s.startswith("-"):
        m = re.search(r"-?\d+", s)
        if m:
            v = int(m.group())
            return v if v < 0 else -v
        return -1
    if s.startswith("niveau"):
        m = re.search(r"\d+", s)
        return int(m.group()) - 1 if m else order
    m = re.search(r"r\+?(\d+)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"\d+", s)
    if m:
        return int(m.group())
    return order


def _infer_shape(stair: dict) -> str:
    """Heuristique : 1 niveau + 1 tronçon de type droit → droit ; sinon tournant."""
    niveaux = stair.get("niveaux") or []
    if len(niveaux) == 1:
        ts = niveaux[0].get("troncons") or []
        if len(ts) <= 1 and all(t.get("type") == "droit" for t in ts):
            return "droit"
    return "tournant"


async def backfill_v2_fields() -> int:
    """Ajoute shape/floor_index/is_ghost aux documents existants (idempotent)."""
    touched = 0
    async for p in db.projects.find({"stairs": {"$exists": True, "$ne": []}}):
        changed = False
        for stair in p.get("stairs", []) or []:
            if "shape" not in stair:
                stair["shape"] = _infer_shape(stair)
                changed = True
            for idx, niv in enumerate(stair.get("niveaux") or []):
                if "floor_index" not in niv:
                    niv["floor_index"] = _infer_floor_index(niv.get("label", ""), niv.get("order", idx))
                    changed = True
                if "is_ghost" not in niv:
                    niv["is_ghost"] = False
                    changed = True
        if changed:
            await db.projects.update_one({"id": p["id"]}, {"$set": {"stairs": p["stairs"]}})
            touched += 1
    if touched:
        logger.info("Backfill v2.1 : %d projet(s) enrichi(s) avec shape/floor_index", touched)
    return touched


async def migrate_projects_to_stairs() -> int:
    """Backfill stairs[] depuis l'ancien measurement. Idempotent."""
    migrated = 0
    async for p in db.projects.find({"$or": [{"stairs": {"$exists": False}}, {"stairs": []}]}):
        # Tente de lire la mesure liée (collection séparée)
        meas = await db.measurements.find_one({"project_id": p["id"]}, {"_id": 0})
        # Fallback : champ legacy embarqué
        if not meas and isinstance(p.get("measurement"), dict):
            meas = p["measurement"]

        if not meas:
            # Pas de mesure → on crée tout de même un escalier vide pour ne pas casser l'UI
            stairs = [{
                "id": str(uuid.uuid4()),
                "name": "Escalier Principal",
                "shape": "tournant",
                "niveaux": [],
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }]
        else:
            hauteur = float(meas.get("hauteur_brute") or 2700)
            sols_finis = bool(meas.get("sols_finis_zero", True))
            reserve = float(meas.get("reserve_bas", 0) or 0) + float(meas.get("reserve_haut", 0) or 0)
            reculement = float(meas.get("reculement_max") or 3500)
            largeur = float(meas.get("largeur_volee") or 900)
            name = meas.get("element_title") or "Escalier Principal"

            niveau = {
                "id": str(uuid.uuid4()),
                "label": "RDC",
                "floor_index": 0,
                "is_ghost": False,
                "hauteur_mm": hauteur,
                "sol_fini": sols_finis,
                "reserve_mm": reserve,
                "troncons": [{
                    "id": str(uuid.uuid4()),
                    "type": "droit",
                    "longueur_mm": reculement,
                    "largeur_mm": largeur,
                    "order": 0,
                }],
                "order": 0,
            }
            stairs = [{
                "id": str(uuid.uuid4()),
                "name": str(name)[:80],
                "shape": "droit",
                "niveaux": [niveau],
                "created_at": now_utc(),
                "updated_at": now_utc(),
            }]

        await db.projects.update_one(
            {"id": p["id"]},
            {"$set": {"stairs": stairs, "schema_version": 2, "updated_at": now_utc()}},
        )
        migrated += 1

    if migrated:
        logger.info("Migration v2 : %d projet(s) migré(s) vers stairs[]", migrated)
    # Always backfill new v2.1 fields after migration
    await backfill_v2_fields()
    return migrated
