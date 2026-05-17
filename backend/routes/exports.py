"""Routes d'export d'un chantier : PDF (avec photos), CSV, XLSX, JSON."""
from __future__ import annotations

import base64
import csv
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image as RLImage, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from db import db
from deps import require_active_subscription
from utils import WALL_TYPE_LABELS, block_label, status_label

router = APIRouter()


# ---------------------------- PDF --------------------------------------
@router.get("/chantiers/{chantier_id}/export.pdf")
async def export_pdf(
    chantier_id: str, user=Depends(require_active_subscription)
):
    chantier = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = (
        await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0})
        .sort("created_at", 1)
        .to_list(500)
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, title=f"MesureChâssis - {chantier['client_name']}"
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(
        Paragraph("<b>MesureChâssis</b> — Fiche Chantier", styles["Title"])
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(f"<b>Client :</b> {chantier['client_name']}", styles["Normal"])
    )
    story.append(
        Paragraph(f"<b>Adresse :</b> {chantier['address']}", styles["Normal"])
    )
    story.append(
        Paragraph(
            f"<b>Statut :</b> {status_label(chantier['status'])}",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Date :</b> {chantier['created_at'][:10]}", styles["Normal"]
        )
    )
    story.append(Spacer(1, 18))
    story.append(
        Paragraph(f"<b>Ouvertures ({len(mesures)})</b>", styles["Heading2"])
    )

    for i, m in enumerate(mesures, 1):
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                f"<b>#{i} — {m.get('label', '')} ({block_label(m['block_type'])})</b>",
                styles["Heading3"],
            )
        )
        rows = [["Mesure", "Valeur (mm)"]]
        fields = [
            ("Hauteur baie", m.get("bay_height")),
            ("Largeur baie", m.get("bay_width")),
            ("Diagonale 1", m.get("bay_diagonal_1") or m.get("bay_diagonal")),
            ("Diagonale 2", m.get("bay_diagonal_2") or m.get("bay_diagonal")),
            ("Réserve Sol Fini", m.get("floor_reserve")),
            ("Épaisseur Bloc Béton", m.get("bloc_thickness")),
            ("Épaisseur Isolant", m.get("insulation_thickness")),
            ("Finition extérieure", m.get("finish_outer")),
            ("Finition intérieure", m.get("finish_inner")),
            ("Type paroi", m.get("wall_type")),
            # Legacy
            ("Largeur haut", m.get("width_top")),
            ("Largeur milieu", m.get("width_middle")),
            ("Largeur bas", m.get("width_bottom")),
            ("Hauteur gauche", m.get("height_left")),
            ("Hauteur milieu", m.get("height_middle")),
            ("Hauteur droite", m.get("height_right")),
            ("Diagonale 1", m.get("diag_1")),
            ("Diagonale 2", m.get("diag_2")),
            ("Hauteur 1/4 gauche", m.get("height_quarter_left")),
            ("Hauteur 1/4 droite", m.get("height_quarter_right")),
            ("Hauteur petite", m.get("height_small")),
            ("Hauteur grande", m.get("height_large")),
            ("Largeur petite", m.get("width_small")),
            ("Largeur intermédiaire", m.get("width_intermediate")),
        ]
        for label, val in fields:
            if val is not None:
                if label == "Type paroi":
                    rows.append(
                        [label, WALL_TYPE_LABELS.get(str(val), str(val))]
                    )
                else:
                    rows.append([label, str(val)])
        if m.get("slope_angle_deg") is not None:
            rows.append(["Angle de pente", f"{m['slope_angle_deg']}°"])
        tbl = Table(rows, colWidths=[260, 200])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF5A00")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        story.append(tbl)
        if m.get("alerts"):
            story.append(Spacer(1, 4))
            for a in m["alerts"]:
                story.append(
                    Paragraph(
                        f'<font color="#CC0000">{a}</font>', styles["Normal"]
                    )
                )

    # --- Photos site (Anti-litige) ------------------------------------
    site_photos = chantier.get("site_photos") or []
    if site_photos:
        story.append(Spacer(1, 18))
        story.append(
            Paragraph(
                f"<b>📷 Photos chantier — Anti-litige ({len(site_photos)})</b>",
                styles["Heading2"],
            )
        )
        story.append(
            Paragraph(
                '<font size="9" color="#666666"><i>Preuves photographiques '
                "de l'état existant au moment de la prise de mesures.</i></font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 8))

        caption_style = ParagraphStyle(
            "PhotoCaption",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=colors.HexColor("#444444"),
            alignment=1,
            leading=11,
        )
        photo_cells: list[list[Any]] = []
        row: list[Any] = []
        for idx, ph in enumerate(site_photos, 1):
            uri = ph.get("uri") or ""
            caption = (ph.get("caption") or "").strip() or f"Photo {idx}"
            cell_content: list[Any] = []
            try:
                if uri.startswith("data:"):
                    _, b64 = uri.split(",", 1)
                else:
                    b64 = uri
                img_bytes = base64.b64decode(b64)
                img_io = io.BytesIO(img_bytes)
                img = RLImage(
                    img_io, width=80 * mm, height=60 * mm, kind="proportional"
                )
                cell_content.append(img)
            except Exception:
                cell_content.append(
                    Paragraph(
                        f'<font color="#999999">[Photo {idx} illisible]</font>',
                        styles["Normal"],
                    )
                )
            cell_content.append(Spacer(1, 4))
            cell_content.append(
                Paragraph(f"#{idx} — {caption}", caption_style)
            )
            row.append(cell_content)
            if len(row) == 2:
                photo_cells.append(row)
                row = []
        if row:
            row.append("")
            photo_cells.append(row)
        if photo_cells:
            photo_table = Table(photo_cells, colWidths=[90 * mm, 90 * mm])
            photo_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            story.append(photo_table)

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="chantier-{chantier_id}.pdf"'
            )
        },
    )


# ---------------------------- JSON -------------------------------------
@router.get("/chantiers/{chantier_id}/export.json")
async def export_json(
    chantier_id: str, user=Depends(require_active_subscription)
):
    chantier = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = (
        await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0})
        .sort("created_at", 1)
        .to_list(500)
    )

    def _mesure_struct(m: dict) -> dict:
        bt = m.get("block_type")
        common = {
            "id": m.get("id"),
            "label": m.get("label"),
            "block_type": bt,
            "created_at": m.get("created_at"),
        }
        if bt == "trapeze":
            return {
                **common,
                "shape": "trapezoidal",
                "dimensions_mm": {
                    "width": m.get("bay_width"),
                    "height_left": m.get("height_left"),
                    "height_right": m.get("height_right"),
                },
            }
        dims = {
            "width": m.get("bay_width"),
            "height": m.get("bay_height"),
            "diagonal_1": m.get("bay_diagonal_1") or m.get("bay_diagonal"),
            "diagonal_2": m.get("bay_diagonal_2") or m.get("bay_diagonal"),
        }
        if bt in ("porte", "coulissant"):
            dims["floor_reserve"] = m.get("floor_reserve")
        return {
            **common,
            "shape": "rectangular",
            "dimensions_mm": dims,
            "diagonals_verified": {
                "d1": bool(m.get("diag_1_verified")),
                "d2": bool(m.get("diag_2_verified")),
            },
        }

    return {
        "schema_version": "mc.v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "company_id": chantier.get("company_id"),
        "client": {
            "display_name": chantier.get("client_name"),
            "first_name": chantier.get("first_name"),
            "last_name": chantier.get("last_name"),
            "address": chantier.get("address"),
            "postal_code": chantier.get("postal_code"),
            "city": chantier.get("city"),
        },
        "project": {
            "id": chantier.get("id"),
            "status": chantier.get("status"),
            "appointment_at": chantier.get("appointment_at"),
            "notes": chantier.get("notes"),
            "created_at": chantier.get("created_at"),
            "assigned_to": chantier.get("assigned_to"),
        },
        "openings_count": len(mesures),
        "openings": [_mesure_struct(m) for m in mesures],
    }


# ---------------------------- CSV --------------------------------------
@router.get("/chantiers/{chantier_id}/export.csv")
async def export_csv(
    chantier_id: str, user=Depends(require_active_subscription)
):
    """CSV tabulaire — friendly machines de découpe / atelier."""
    chantier = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = (
        await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0})
        .sort("created_at", 1)
        .to_list(500)
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "Chantier", "Adresse", "Code Postal", "Ville", "Statut",
            "Label", "Type", "Forme",
            "Largeur (mm)", "Hauteur (mm)", "Hauteur G (mm)", "Hauteur D (mm)",
            "Diag 1 (mm)", "Diag 2 (mm)", "Diag1 OK", "Diag2 OK",
            "Réserve sol (mm)", "Épaisseur bloc (mm)", "Paroi",
            "Date mesure",
        ]
    )
    client_disp = chantier.get("client_name") or "—"
    for m in mesures:
        bt = m.get("block_type") or "—"
        is_trap = bt == "trapeze"
        writer.writerow(
            [
                client_disp,
                chantier.get("address") or "",
                chantier.get("postal_code") or "",
                chantier.get("city") or "",
                chantier.get("status") or "",
                m.get("label") or "",
                bt,
                "trapezoidal" if is_trap else "rectangular",
                m.get("bay_width") or "",
                "" if is_trap else (m.get("bay_height") or ""),
                m.get("height_left") or "" if is_trap else "",
                m.get("height_right") or "" if is_trap else "",
                "" if is_trap else (
                    m.get("bay_diagonal_1") or m.get("bay_diagonal") or ""
                ),
                "" if is_trap else (
                    m.get("bay_diagonal_2") or m.get("bay_diagonal") or ""
                ),
                "" if is_trap else (
                    "oui" if m.get("diag_1_verified") else "non"
                ),
                "" if is_trap else (
                    "oui" if m.get("diag_2_verified") else "non"
                ),
                m.get("floor_reserve") or "",
                m.get("bloc_thickness") or "",
                m.get("wall_type") or "",
                (m.get("created_at") or "")[:19].replace("T", " "),
            ]
        )
    content = buf.getvalue().encode("utf-8-sig")
    safe = (chantier.get("client_name") or chantier_id).replace(" ", "_").replace("/", "-")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="MesureChassis_{safe}.csv"'
            )
        },
    )


# ---------------------------- XLSX -------------------------------------
@router.get("/chantiers/{chantier_id}/export.xlsx")
async def export_xlsx(
    chantier_id: str, user=Depends(require_active_subscription)
):
    chantier = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not chantier:
        raise HTTPException(404, "Chantier introuvable")
    mesures = (
        await db.mesures.find({"chantier_id": chantier_id}, {"_id": 0})
        .sort("created_at", 1)
        .to_list(500)
    )

    wb = Workbook()
    info = wb.active
    info.title = "Chantier"
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill(
        start_color="FF5A00", end_color="FF5A00", fill_type="solid"
    )
    info["A1"] = "MesureChâssis — Fiche Chantier"
    info["A1"].font = Font(bold=True, size=14)
    pairs = [
        ("Client", chantier["client_name"]),
        ("Adresse", chantier["address"]),
        ("Statut", status_label(chantier["status"])),
        ("Date", chantier["created_at"][:10]),
        ("Signé le", chantier.get("signed_at") or "—"),
    ]
    for i, (k, v) in enumerate(pairs, start=3):
        info.cell(row=i, column=1, value=k).font = Font(bold=True)
        info.cell(row=i, column=2, value=v)
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 50

    ws = wb.create_sheet("Mesures")
    columns = [
        ("Libellé", "label"),
        ("Type bloc", "block_type"),
        ("H baie (mm)", "bay_height"),
        ("L baie (mm)", "bay_width"),
        ("Diag (mm)", "bay_diagonal"),
        ("Réserve sol fini (mm)", "floor_reserve"),
        ("Épais. bloc béton (mm)", "bloc_thickness"),
        ("Type paroi", "wall_type"),
        ("Épais. isolant (mm)", "insulation_thickness"),
        ("Finition ext. (mm)", "finish_outer"),
        ("Finition int. (mm)", "finish_inner"),
        ("Angle pente (°)", "slope_angle_deg"),
        ("Alertes", "alerts"),
    ]
    for col_idx, (label, _) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = head
        cell.fill = fill
    block_map = {
        "standard": "Standard",
        "coulissant": "Coulissant",
        "porte": "Porte",
        "trapeze": "Trapèze",
    }
    for row_idx, m in enumerate(mesures, start=2):
        for col_idx, (_, key) in enumerate(columns, start=1):
            v: Any = m.get(key)
            if key == "wall_type" and v:
                v = WALL_TYPE_LABELS.get(v, v)
            elif key == "block_type" and v:
                v = block_map.get(v, v)
            elif key == "alerts":
                v = " ; ".join(v) if v else ""
            ws.cell(row=row_idx, column=col_idx, value=v)
    for c in ws.columns:
        max_len = max(
            (len(str(cell.value)) if cell.value is not None else 0)
            for cell in c
        )
        ws.column_dimensions[c[0].column_letter].width = min(max_len + 2, 36)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="chantier-{chantier_id}.xlsx"'
            )
        },
    )
