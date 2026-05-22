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


@router.get("/dxf")
async def export_dxf(pid: str, user=Depends(require_active_access)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=400, detail="Aucune mesure disponible pour DXF")
    dxf = build_dxf_text(p, m)
    filename = f"chantier_{p.get('client_nom', 'export').lower()}.dxf"
    return StreamingResponse(
        io.BytesIO(dxf.encode()), media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
