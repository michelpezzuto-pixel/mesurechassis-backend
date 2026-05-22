"""PDF + DXF export endpoints."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.db import db
from core.security import get_current_user, project_visible_to, require_active_access
from services.exports import build_dxf_text, build_pdf_bytes

router = APIRouter(prefix="/projects/{pid}/export")


@router.get("/pdf")
async def export_pdf(pid: str, user=Depends(require_active_access)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    # Fallback v2 : si pas de mesure legacy mais des stairs[], on synthétise.
    if not m and p.get("stairs"):
        m = _synthesize_measurement_from_stairs(p)
    # Fetch the company logo from the project owner (admin)
    owner_id = p.get("creator_id") or p.get("commercial_id")
    owner = await db.users.find_one({"id": owner_id}, {"_id": 0, "company_logo_base64": 1, "company_name": 1}) if owner_id else None
    company_logo = (owner or {}).get("company_logo_base64") or None
    pdf = build_pdf_bytes(p, m, company_logo_base64=company_logo)
    filename = f"chantier_{p.get('client_nom', 'export').lower()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _synthesize_measurement_from_stairs(project: dict) -> dict | None:
    """Synthesize a 'measurement' dict from the first stair of a v2 project for legacy PDF/DXF."""
    from services.stairs_v2 import compute_stair as compute_v2
    first = next(iter(project.get("stairs") or []), None)
    if not first or not first.get("niveaux"):
        return None
    c = compute_v2(first)
    niv0 = c["niveaux_calc"][0] if c["niveaux_calc"] else {}
    total_long = sum(t.get("longueur_mm", 0) for niv in first["niveaux"] for t in (niv.get("troncons") or []))
    largeur_max = max(
        (t.get("largeur_mm", 900) for niv in first["niveaux"] for t in (niv.get("troncons") or [])),
        default=900,
    )
    return {
        "element_title": first.get("name", "Escalier"),
        "material": "bois",
        "hauteur_brute": c["total_height"],
        "sols_finis_zero": True,
        "reserve_bas": 0, "reserve_haut": 0,
        "epaisseur_dalle": 200,
        "tremie_longueur": total_long, "tremie_largeur": largeur_max,
        "reculement_max": c["total_reculement"],
        "remarques": "",
        "result": {
            "true_height": c["total_height"],
            "n_steps": c["total_steps"],
            "h": niv0.get("h", 0),
            "g": niv0.get("g", 0),
            "slope_angle": niv0.get("slope_angle", 0),
            "hypotenuse": c["limon_length"],
            "limon_length": c["limon_length"],
            "reculement_needed": c["total_reculement"],
            "shape": f"{c['n_niveaux']} niveau(x) — multi-tronçons",
            "is_tournant": False,
            "blondel_value": niv0.get("blondel_value", 0),
            "valid_blondel": niv0.get("valid_blondel", True),
            "notes": list(c.get("warnings", [])),
        },
    }


@router.get("/dxf")
async def export_dxf(pid: str, user=Depends(require_active_access)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    if not m and p.get("stairs"):
        m = _synthesize_measurement_from_stairs(p)
    if not m:
        raise HTTPException(status_code=400, detail="Aucune mesure disponible pour DXF")
    dxf = build_dxf_text(p, m)
    filename = f"chantier_{p.get('client_nom', 'export').lower()}.dxf"
    return StreamingResponse(
        io.BytesIO(dxf.encode()), media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
