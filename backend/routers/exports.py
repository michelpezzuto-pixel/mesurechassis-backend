"""PDF + DXF export endpoints."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.db import db
from core.security import get_current_user, project_visible_to
from services.exports import build_dxf_text, build_pdf_bytes

router = APIRouter(prefix="/projects/{pid}/export")


@router.get("/pdf")
async def export_pdf(pid: str, user=Depends(get_current_user)):
    q = {"id": pid, **project_visible_to(user)}
    p = await db.projects.find_one(q, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Chantier introuvable")
    m = await db.measurements.find_one({"project_id": pid}, {"_id": 0})
    pdf = build_pdf_bytes(p, m)
    filename = f"chantier_{p.get('client_nom', 'export').lower()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dxf")
async def export_dxf(pid: str, user=Depends(get_current_user)):
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
