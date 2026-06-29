"""Future-proof integration endpoint for sister apps (e.g. MesureGardeCorps)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import get_current_user, project_visible_to

router = APIRouter()


@router.get("/integration/sites/{pid}")
async def integration_site(pid: str, user=Depends(get_current_user)):
    # SEC-002: scope to authenticated user's tenant
    p = await db.projects.find_one(
        {"id": pid, **project_visible_to(user)},
        {"_id": 0},
    )
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    payload = {
        "site_id": pid,
        "client": {
            "nom": p.get("client_nom"),
            "prenom": p.get("client_prenom"),
            "address": p.get("address"),
            "city": p.get("city"),
            "postal_code": p.get("postal_code"),
        },
        "structure": None,
    }
    if m:
        r = m["result"]
        payload["structure"] = {
            "material": m["material"],
            "true_height_mm": r["true_height"],
            "reculement_mm": r["reculement_needed"],
            "slope_angle_deg": r["slope_angle"],
            "hypotenuse_mm": r["hypotenuse"],
            "limon_length_mm": r.get("limon_length", r["hypotenuse"]),
            "n_steps": r["n_steps"],
            "step_h_mm": r["h"],
            "step_g_mm": r["g"],
            "shape": r["shape"],
            "is_tournant": r.get("is_tournant", False),
            "echappee_mm": r.get("echappee"),
            "echappee_critique": r.get("echappee_critique", False),
            "tremie": {
                "longueur_mm": m["tremie_longueur"],
                "largeur_mm": m["tremie_largeur"],
            },
        }
    return payload
