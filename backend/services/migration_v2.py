"""
Migration v2 — Transforme les anciens projets `measurement` en `stairs[]` v2.

Au démarrage de l'app :
1. Pour chaque project sans `stairs[]` ou stairs vide :
2. On lit son `measurement` (collection séparée) ou `project.measurement` legacy
3. On construit 1 escalier "Escalier Principal" / 1 niveau "Niveau 1" / 1 tronçon droit
4. On le persiste dans project.stairs (non destructif : le measurement legacy reste)
"""
from __future__ import annotations

import logging
import uuid

from core.db import db
from core.security import now_utc

logger = logging.getLogger("mesure_escalier.migration")


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
                "label": "Niveau 1",
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
    return migrated
