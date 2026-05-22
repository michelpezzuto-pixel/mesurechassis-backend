"""PDF (ReportLab) + DXF (ASCII) builders for stair reports.

v2 enhancement (mai 2025):
- `build_pdf_bytes` ajoute une section riche par escalier (Stairs > Niveaux > Tronçons)
  lorsque le projet contient des `stairs[]` (non-mutuellement-exclusif avec la mesure legacy).
- `build_dxf_text` produit un profil DXF multi-niveau / multi-tronçon précis dès qu'un
  escalier v2 existe (paliers = horizontaux, marches = montée répartie, quart-tournants
  marqués comme calques distincts pour le découpage atelier).
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Any, Dict, List  # noqa: F401

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

from core.security import now_utc
from services.stairs_v2 import compute_stair as compute_v2

# Labels FR pour tronçons
TRONCON_LABEL = {
    "droit": "Droit",
    "palier": "Palier",
    "quart_bas": "Quart-tournant BAS",
    "quart_haut": "Quart-tournant HAUT",
}

log = logging.getLogger("mesure_escalier.exports")

# Page geometry
PAGE_W, PAGE_H = A4
LEFT_M = RIGHT_M = 20 * mm
TOP_M = 28 * mm   # leave headroom for logo header
BOTTOM_M = 18 * mm


def _decode_base64_image(b64: str) -> ImageReader | None:
    """Decode a base64 image (with or without data URI prefix) into an ImageReader."""
    if not b64:
        return None
    try:
        raw = b64.strip()
        if "," in raw and raw.lower().startswith("data:"):
            raw = raw.split(",", 1)[1]
        return ImageReader(io.BytesIO(base64.b64decode(raw)))
    except Exception as exc:  # noqa: BLE001
        log.warning("Bad base64 image (%s): %s", type(exc).__name__, exc)
        return None


def _make_header_footer(company_name: str, logo_reader: ImageReader | None):
    """Return an `on_page` callback drawing logo + company name as header,
    and pagination as footer."""

    def _draw(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        # ---- Header ----
        header_y = PAGE_H - 18 * mm
        if logo_reader is not None:
            try:
                # Logo box: 22mm wide max, 16mm tall, top-left
                canvas.drawImage(
                    logo_reader,
                    LEFT_M, header_y - 4 * mm,
                    width=22 * mm, height=16 * mm,
                    preserveAspectRatio=True, anchor="nw", mask="auto",
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Header logo draw failed: %s", exc)

        # Company name (top-right)
        canvas.setFillColor(colors.HexColor("#1A1E2A"))
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(PAGE_W - RIGHT_M, header_y + 6, company_name or "MesureEscalier")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8CC63F"))
        canvas.drawRightString(PAGE_W - RIGHT_M, header_y - 5, "Rapport de chantier")

        # Accent rule
        canvas.setStrokeColor(colors.HexColor("#8CC63F"))
        canvas.setLineWidth(1.4)
        canvas.line(LEFT_M, header_y - 10, PAGE_W - RIGHT_M, header_y - 10)

        # ---- Footer ----
        canvas.setFillColor(colors.HexColor("#9098A8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            LEFT_M, BOTTOM_M - 8,
            f"Généré le {now_utc().strftime('%d/%m/%Y %H:%M UTC')} — MesureEscalier",
        )
        canvas.drawRightString(PAGE_W - RIGHT_M, BOTTOM_M - 8, f"Page {doc.page}")
        canvas.restoreState()

    return _draw


def _stair_drawing(r: dict) -> Drawing:
    W, H = 170 * mm, 90 * mm
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=colors.HexColor("#F7F8FC"), strokeColor=colors.HexColor("#E0E0E6")))
    n = max(1, int(r["n_steps"]))
    true_h = r["true_height"]
    reculement = r["reculement_needed"]
    margin = 15 * mm
    avail_w = W - 2 * margin
    avail_h = H - 2 * margin
    scale = min(avail_w / max(reculement, 1), avail_h / max(true_h, 1))
    sw = reculement * scale
    sh = true_h * scale
    x0 = margin
    y0 = margin
    d.add(Line(x0, y0, x0 + sw, y0 + sh, strokeColor=colors.HexColor("#8CC63F"), strokeWidth=1.4))
    h_px = sh / n
    g_px = sw / max(n - 1, 1)
    pts = [x0, y0]
    cx, cy = x0, y0
    for _ in range(n):
        cy += h_px
        pts += [cx, cy]
        cx += g_px
        pts += [cx, cy]
    d.add(Polygon(pts, fillColor=None, strokeColor=colors.HexColor("#1A1E2A"), strokeWidth=1.0))
    d.add(Line(x0 - 8, y0, x0 + sw + 8, y0, strokeColor=colors.HexColor("#9098A8"), strokeWidth=0.8))
    d.add(Line(x0 - 8, y0 + sh, x0 + sw + 8, y0 + sh, strokeColor=colors.HexColor("#9098A8"),
               strokeWidth=0.8, strokeDashArray=[3, 2]))
    d.add(String(x0 + sw / 2, y0 - 10, f"Reculement {round(reculement)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="middle"))
    d.add(String(x0 - 10, y0 + sh / 2, f"H {round(true_h)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="end"))
    d.add(String(x0 + sw / 2, y0 + sh + 6, f"{n} marches · h {r['h']} · g {r['g']}",
                 fontSize=9, fillColor=colors.HexColor("#8CC63F"), textAnchor="middle"))
    return d


def _stair_v2_drawing(stair: dict, compute: dict) -> Drawing:
    """Render a multi-niveau / multi-tronçon profile for a v2 stair.

    Stack levels vertically. Within each level, walk tronçons left-to-right:
    - palier   → horizontal segment (no rise)
    - droit/quart_bas/quart_haut → ramp climbing by n_marches/h
    Quart-tournants are colored differently for visual cue.
    """
    W, H = 170 * mm, 100 * mm
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, fillColor=colors.HexColor("#F7F8FC"),
               strokeColor=colors.HexColor("#E0E0E6")))

    total_height = max(compute.get("total_height", 1), 1)
    total_reculement = max(compute.get("total_reculement", 1), 1)
    margin_x = 18 * mm
    margin_y = 14 * mm
    avail_w = W - 2 * margin_x
    avail_h = H - 2 * margin_y
    sx = avail_w / total_reculement
    sy = avail_h / total_height

    x0, y0 = margin_x, margin_y
    # Reference floor + ceiling
    d.add(Line(x0 - 6, y0, x0 + avail_w + 6, y0,
               strokeColor=colors.HexColor("#9098A8"), strokeWidth=0.8))
    d.add(Line(x0 - 6, y0 + avail_h, x0 + avail_w + 6, y0 + avail_h,
               strokeColor=colors.HexColor("#9098A8"), strokeWidth=0.6,
               strokeDashArray=[3, 2]))

    # Walk through niveaux/tronçons
    cx, cy = x0, y0
    color_marche = colors.HexColor("#8CC63F")  # vert pomme
    color_palier = colors.HexColor("#5BA8C7")  # bleu palier
    color_quart = colors.HexColor("#F59E0B")   # orange tournant

    niveaux = stair.get("niveaux") or []
    niveaux_sorted = sorted(niveaux, key=lambda n: n.get("order", 0))
    niveaux_calc = compute.get("niveaux_calc", [])

    for ni, niv in enumerate(niveaux_sorted):
        ncalc = next((c for c in niveaux_calc if c.get("niveau_id") == niv["id"]), None)
        if not ncalc:
            continue
        niv_eff = ncalc.get("hauteur_effective", 0)
        niv_n = max(ncalc.get("n_steps_niveau", 0), 1) if ncalc.get("n_steps_niveau") else 0
        for t in sorted(niv.get("troncons") or [], key=lambda x: x.get("order", 0)):
            tcalc = next((tc for tc in ncalc.get("troncons_calc", []) if tc.get("troncon_id") == t["id"]), None)
            longueur = float(t.get("longueur_mm") or 0)
            wpx = longueur * sx
            if t["type"] == "palier":
                d.add(Line(cx, cy, cx + wpx, cy, strokeColor=color_palier, strokeWidth=2.0))
                cx += wpx
            else:
                # Rise proportional to marches assigned
                marches = (tcalc or {}).get("n_marches", 0)
                rise_mm = (marches / niv_n) * niv_eff if niv_n else 0
                rise_px = rise_mm * sy
                color = color_quart if t["type"] in ("quart_bas", "quart_haut") else color_marche
                d.add(Line(cx, cy, cx + wpx, cy + rise_px, strokeColor=color, strokeWidth=2.0))
                cx += wpx
                cy += rise_px

        # Marker between niveaux (small horizontal tick at niveau boundary)
        if ni < len(niveaux_sorted) - 1:
            d.add(Line(cx - 3, cy, cx + 3, cy, strokeColor=colors.HexColor("#1A1E2A"), strokeWidth=0.6))

    # Hypotenuse / limon
    d.add(Line(x0, y0, x0 + total_reculement * sx, y0 + total_height * sy,
               strokeColor=colors.HexColor("#1A1E2A"), strokeWidth=0.5, strokeDashArray=[2, 2]))

    # Labels
    d.add(String(W / 2, y0 - 10,
                 f"Reculement total {round(total_reculement)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="middle"))
    d.add(String(x0 - 10, y0 + avail_h / 2,
                 f"H {round(total_height)} mm",
                 fontSize=9, fillColor=colors.HexColor("#1A1E2A"), textAnchor="end"))
    d.add(String(x0 + avail_w / 2, y0 + avail_h + 6,
                 f"{compute.get('total_steps', 0)} marches · limon {round(compute.get('limon_length', 0))} mm",
                 fontSize=9, fillColor=colors.HexColor("#8CC63F"), textAnchor="middle"))
    # Legend
    d.add(Rect(x0, H - 10, 8, 4, fillColor=color_marche, strokeColor=color_marche))
    d.add(String(x0 + 12, H - 8, "Marches", fontSize=7, fillColor=colors.HexColor("#1A1E2A")))
    d.add(Rect(x0 + 50, H - 10, 8, 4, fillColor=color_palier, strokeColor=color_palier))
    d.add(String(x0 + 62, H - 8, "Palier", fontSize=7, fillColor=colors.HexColor("#1A1E2A")))
    d.add(Rect(x0 + 95, H - 10, 8, 4, fillColor=color_quart, strokeColor=color_quart))
    d.add(String(x0 + 107, H - 8, "Quart-tournant", fontSize=7, fillColor=colors.HexColor("#1A1E2A")))
    return d


def _build_v2_stair_story(stair: dict, h_style: ParagraphStyle, body: ParagraphStyle,
                          table_style: TableStyle, sub_style: ParagraphStyle,
                          warn_style: ParagraphStyle) -> list:
    """Build a story section for one v2 stair (Niveaux + Tronçons + drawing)."""
    out: list = []
    c = compute_v2(stair)
    out.append(Paragraph(f"Escalier — <b>{stair.get('name', 'Escalier')}</b>", h_style))

    # Stair-level summary
    summary_rows = [
        ["Nombre de niveaux", str(c["n_niveaux"])],
        ["Hauteur totale (mm)", str(round(c["total_height"]))],
        ["Reculement total (mm)", str(round(c["total_reculement"]))],
        ["Nombre de marches total", str(c["total_steps"])],
        ["Longueur du limon (mm)", str(round(c["limon_length"]))],
    ]
    out.append(Table(summary_rows, colWidths=[60 * mm, 110 * mm], style=table_style))
    out.append(Spacer(1, 8))

    # Per-niveau tables
    niveaux = sorted(stair.get("niveaux") or [], key=lambda n: n.get("order", 0))
    for niv in niveaux:
        ncalc = next((x for x in c["niveaux_calc"] if x.get("niveau_id") == niv["id"]), None)
        if not ncalc:
            continue
        out.append(Spacer(1, 4))
        out.append(Paragraph(f"Niveau · <b>{niv.get('label', '')}</b>", sub_style))
        niv_rows = [
            ["Hauteur (mm)", str(round(niv.get("hauteur_mm", 0)))],
            ["Sol fini", "Oui" if niv.get("sol_fini", True) else "Non"],
            ["Réserve sol (mm)", str(round(niv.get("reserve_mm", 0)))],
            ["Hauteur effective (mm)", str(round(ncalc["hauteur_effective"]))],
            ["Nombre de marches", str(ncalc["n_steps_niveau"])],
            ["Hauteur marche h (mm)", str(round(ncalc["h"]))],
            ["Giron g (mm)", str(round(ncalc["g"]))],
            ["Loi de Blondel (2h+g)",
             f'{round(ncalc["blondel_value"])}  ({"OK" if ncalc["valid_blondel"] else "Hors plage 560-670"})'],
            ["Pente (°)", str(round(ncalc["slope_angle"], 1))],
        ]
        out.append(Table(niv_rows, colWidths=[60 * mm, 110 * mm], style=table_style))

        # Tronçons table for this niveau
        troncons = sorted(niv.get("troncons") or [], key=lambda x: x.get("order", 0))
        if troncons:
            tron_rows = [["#", "Type", "Longueur (mm)", "Largeur (mm)", "Marches"]]
            for i, t in enumerate(troncons, 1):
                tcalc = next((tc for tc in ncalc.get("troncons_calc", []) if tc.get("troncon_id") == t["id"]), {})
                tron_rows.append([
                    str(i),
                    TRONCON_LABEL.get(t["type"], t["type"]),
                    str(round(float(t.get("longueur_mm") or 0))),
                    str(round(float(t.get("largeur_mm") or 900))),
                    str(tcalc.get("n_marches", 0)),
                ])
            tron_style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1E2A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#8CC63F")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E6")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ])
            out.append(Spacer(1, 4))
            out.append(Table(tron_rows, colWidths=[10 * mm, 50 * mm, 35 * mm, 35 * mm, 40 * mm], style=tron_style))

        # Per-niveau warnings
        for w in ncalc.get("warnings", []) or []:
            out.append(Paragraph(f"⚠ {w}", warn_style))

    # Stair drawing
    out.append(Spacer(1, 8))
    out.append(Paragraph("Schéma de profil — multi-niveaux & tronçons", sub_style))
    out.append(_stair_v2_drawing(stair, c))
    out.append(Spacer(1, 10))
    return out


def _photo_flowable(photo: dict, body_style: ParagraphStyle, caption_style: ParagraphStyle):
    """Build a flowable: photo (max ~80mm tall) + caption + spacer. Returns list or None."""
    img_reader = _decode_base64_image(photo.get("base64", ""))
    if img_reader is None:
        return None
    # Force a max bounding box: full width (170mm) × 80mm tall, keep aspect ratio
    try:
        img_w, img_h = img_reader.getSize()
    except Exception:  # noqa: BLE001
        img_w, img_h = 1280, 960
    max_w = 170 * mm
    max_h = 80 * mm
    scale = min(max_w / img_w, max_h / img_h, 1.0)
    draw_w = img_w * scale
    draw_h = img_h * scale
    # Re-wrap via Image() — needs a path-like, but accepts ImageReader via a small buffer trick:
    # Easiest: re-decode bytes and feed BytesIO
    raw = photo.get("base64", "")
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    img_bytes = base64.b64decode(raw)
    img = Image(io.BytesIO(img_bytes), width=draw_w, height=draw_h)
    caption = (photo.get("caption") or "").strip() or "—"
    parts = [
        img,
        Spacer(1, 4),
        Paragraph(f"<i>{caption}</i>", caption_style),
        Spacer(1, 12),
    ]
    return KeepTogether(parts)


def build_pdf_bytes(project: dict, measurement: dict, company_logo_base64: str | None = None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LEFT_M, rightMargin=RIGHT_M,
        topMargin=TOP_M, bottomMargin=BOTTOM_M,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=20,
                                 textColor=colors.HexColor("#1A1E2A"), spaceAfter=8)
    h_style = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                             textColor=colors.HexColor("#8CC63F"), spaceBefore=10, spaceAfter=4)
    body = styles["BodyText"]
    caption_style = ParagraphStyle(
        "caption", parent=body, fontSize=9, textColor=colors.HexColor("#1A1E2A"),
        alignment=1,  # center
    )
    sub_style = ParagraphStyle(
        "sub_h", parent=styles["Heading3"], fontSize=11,
        textColor=colors.HexColor("#1A1E2A"), spaceBefore=6, spaceAfter=2,
    )
    warn_style = ParagraphStyle(
        "warn", parent=body, fontSize=9, textColor=colors.HexColor("#A66A00"),
        spaceBefore=2, spaceAfter=2,
    )
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F5F7")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1A1E2A")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E6")),
    ])

    story = []
    title_main = f"Chantier — {project.get('client_nom', '')} {project.get('client_prenom', '')}".strip()
    story.append(Paragraph(title_main, title_style))

    if measurement and (measurement.get("element_title") or "").strip():
        story.append(Paragraph(
            f"<font color='#8CC63F'>Élément :</font> {measurement['element_title']}",
            ParagraphStyle("elemTitle", parent=styles["BodyText"], fontSize=11,
                           textColor=colors.HexColor("#1A1E2A"), spaceAfter=10),
        ))

    story.append(Paragraph("Client", h_style))
    client_rows = [
        ["Nom", f"{project.get('client_nom', '')} {project.get('client_prenom', '')}".strip()],
        ["Adresse", project.get("address", "")],
        ["Ville", f"{project.get('postal_code', '')} {project.get('city', '')}".strip()],
        ["Téléphone", project.get("phone", "") or "-"],
        ["Notes", project.get("notes", "") or "-"],
    ]
    story.append(Table(client_rows, colWidths=[40 * mm, 130 * mm], style=table_style))

    if measurement:
        m = measurement
        r = m["result"]
        story.append(Paragraph("Mesures terrain", h_style))
        meas_rows = [
            ["Matériau", m["material"].capitalize()],
            ["Hauteur brute (mm)", str(m["hauteur_brute"])],
            ["Sols finis à zéro", "Oui" if m["sols_finis_zero"] else "Non"],
            ["Réserve bas (mm)", str(m.get("reserve_bas", 0))],
            ["Réserve haut (mm)", str(m.get("reserve_haut", 0))],
            ["Épaisseur dalle (mm)", str(m["epaisseur_dalle"])],
            ["Trémie (mm)", f'{m["tremie_longueur"]} × {m["tremie_largeur"]}'],
            ["Reculement max (mm)", str(m["reculement_max"])],
            ["Remarques", m.get("remarques", "") or "-"],
        ]
        story.append(Table(meas_rows, colWidths=[60 * mm, 110 * mm], style=table_style))

        story.append(Paragraph("Calculs (Loi de Blondel + règles de l'art)", h_style))
        res_rows = [
            ["Forme déduite", r["shape"]],
            ["Hauteur effective H (mm)", str(r["true_height"])],
            ["Nombre de marches", str(r["n_steps"])],
            ["Hauteur marche h (mm)", str(r["h"])],
            ["Giron g (mm)" + (" (ligne de foulée)" if r.get("is_tournant") else ""), str(r["g"])],
            ["2h+g (mm)", f'{r["blondel_value"]} ({"OK" if r["valid_blondel"] else "Hors plage 560-670"})'],
            ["Angle de pente (°)", str(r["slope_angle"])],
            ["Reculement requis (mm)", str(r["reculement_needed"])],
            ["LONGUEUR DU LIMON (mm)", str(r.get("limon_length", r["hypotenuse"]))],
        ]
        if r.get("echappee") is not None:
            label = f'{r["echappee"]} mm'
            if r.get("echappee_critique"):
                label += " ⚠ CRITIQUE (<2000)"
            res_rows.append(["Échappée sous trémie", label])
        story.append(Table(res_rows, colWidths=[60 * mm, 110 * mm], style=table_style))

        if r.get("ligne_foulee_note"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"<i>Note balancement : {r['ligne_foulee_note']}</i>",
                ParagraphStyle("foulee", parent=body, fontSize=9, textColor=colors.HexColor("#6FA32E")),
            ))

        story.append(Spacer(1, 10))
        story.append(Paragraph("Schéma d'élévation", h_style))
        story.append(_stair_drawing(r))

        if r.get("notes"):
            story.append(Paragraph("Notes du moteur de calcul", h_style))
            for n in r["notes"]:
                story.append(Paragraph(f"• {n}", body))

    # ---- V2 — Multi-stair / Niveaux / Tronçons ----
    stairs_v2 = project.get("stairs") or []
    if stairs_v2:
        story.append(Spacer(1, 14))
        for idx, stair in enumerate(stairs_v2):
            if idx > 0:
                story.append(PageBreak())
            story.extend(_build_v2_stair_story(stair, h_style, body, table_style, sub_style, warn_style))

    # ---- Photos de chantier ----
    photos = project.get("photos") or []
    if photos:
        story.append(PageBreak())
        story.append(Paragraph("Photos de chantier", h_style))
        story.append(Spacer(1, 8))
        for ph in photos:
            flow = _photo_flowable(ph, body, caption_style)
            if flow is not None:
                story.append(flow)

    # Build with header/footer
    logo_reader = _decode_base64_image(company_logo_base64)
    company_name = project.get("company_name") or "MesureEscalier"
    page_cb = _make_header_footer(company_name, logo_reader)
    doc.build(story, onFirstPage=page_cb, onLaterPages=page_cb)
    return buf.getvalue()


def _append_dxf_v2_stair(out: list, stair: dict, x_offset: float = 0.0) -> float:
    """Append DXF lines for a v2 stair starting at x_offset. Returns next x_offset."""
    c = compute_v2(stair)
    cx, cy = x_offset, 0.0
    layer_base = f"STAIR_{(stair.get('name') or 'X').upper().replace(' ', '_')[:16]}"

    def line(x1, y1, x2, y2, layer):
        out.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0",
        ])

    def text(x, y, txt, height=20, layer="LABELS"):
        out.extend([
            "0", "TEXT", "8", layer,
            "10", f"{x:.3f}", "20", f"{y:.3f}", "30", "0.0",
            "40", f"{height:.3f}",
            "1", txt,
        ])

    niveaux = sorted(stair.get("niveaux") or [], key=lambda n: n.get("order", 0))
    niv_calc_by_id = {nc["niveau_id"]: nc for nc in c["niveaux_calc"]}

    for niv in niveaux:
        ncalc = niv_calc_by_id.get(niv["id"])
        if not ncalc:
            continue
        niv_eff = ncalc["hauteur_effective"]
        niv_n = max(ncalc["n_steps_niveau"], 1) if ncalc["n_steps_niveau"] else 0
        troncons = sorted(niv.get("troncons") or [], key=lambda t: t.get("order", 0))
        for t in troncons:
            longueur = float(t.get("longueur_mm") or 0)
            t_layer = f"{layer_base}_{t['type'].upper()}"
            if t["type"] == "palier":
                # Horizontal segment (top/bottom edge of palier)
                line(cx, cy, cx + longueur, cy, f"{layer_base}_PALIER")
                cx += longueur
            else:
                tcalc = next((tc for tc in ncalc.get("troncons_calc", []) if tc.get("troncon_id") == t["id"]), {})
                marches = tcalc.get("n_marches", 0)
                rise = (marches / niv_n) * niv_eff if niv_n else 0
                if marches > 0 and rise > 0:
                    h_step = rise / marches
                    g_step = longueur / max(marches, 1)
                    # Draw individual steps (staircase profile)
                    sx, sy = cx, cy
                    for _ in range(marches):
                        sy += h_step
                        line(sx, sy - h_step, sx, sy, t_layer)  # riser
                        line(sx, sy, sx + g_step, sy, t_layer)  # tread
                        sx += g_step
                    # Limon (ramp line)
                    line(cx, cy, cx + longueur, cy + rise, f"{layer_base}_LIMON")
                    cx += longueur
                    cy += rise
                else:
                    line(cx, cy, cx + longueur, cy, t_layer)
                    cx += longueur
        # Niveau boundary label
        text(cx, cy, f"{niv.get('label', '')}: h={round(ncalc['h'])} g={round(ncalc['g'])} "
                    f"{ncalc['n_steps_niveau']}m", height=18, layer=f"{layer_base}_LABEL")

    # Stair summary text
    text(x_offset, -120,
         f"{stair.get('name', 'Escalier')} - {c['total_steps']} marches - "
         f"H={round(c['total_height'])} - L={round(c['total_reculement'])} - "
         f"Limon={round(c['limon_length'])}",
         height=22, layer=f"{layer_base}_SUMMARY")

    # Floor & ceiling refs for this stair
    line(x_offset - 50, 0, cx + 50, 0, f"{layer_base}_FLOOR")
    line(x_offset, c["total_height"], cx, c["total_height"], f"{layer_base}_CEILING")
    return cx + 200  # gap before next stair


def build_dxf_text(project: dict, measurement: dict) -> str:
    """Generate an AutoCAD-readable DXF (ASCII).

    v2 prioritaire : si le projet contient des `stairs[]`, on génère un dessin
    multi-escalier précis (paliers / marches / quart-tournants distincts par calque).
    Sinon, on retombe sur la logique legacy basée sur `measurement.result`.
    """
    out = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC",
           "0", "SECTION", "2", "ENTITIES"]

    # ── V2 path ──
    stairs_v2 = project.get("stairs") or []
    if stairs_v2:
        offset = 0.0
        for stair in stairs_v2:
            offset = _append_dxf_v2_stair(out, stair, x_offset=offset)
        out.extend([
            "0", "TEXT", "8", "PROJECT",
            "10", "0.0", "20", "-240.0", "30", "0.0",
            "40", "28.0",
            "1", f"MesureEscalier - {project.get('client_nom', '')} {project.get('client_prenom', '')}",
        ])
        out.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(out)

    # ── Legacy fallback (single measurement) ──
    r = measurement["result"]
    n = int(r["n_steps"])
    H = float(r["true_height"])
    L = float(r["reculement_needed"])
    h = H / n
    g = L / max(n - 1, 1)

    pts = [(0.0, 0.0)]
    cx, cy = 0.0, 0.0
    for _ in range(n):
        cy += h
        pts.append((cx, cy))
        cx += g
        pts.append((cx, cy))

    out = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC",
           "0", "SECTION", "2", "ENTITIES"]

    def add_line(x1, y1, x2, y2, layer="STAIR"):
        out.extend([
            "0", "LINE", "8", layer,
            "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
            "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0",
        ])

    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        add_line(x1, y1, x2, y2, "STAIR_PROFILE")

    add_line(0, 0, L, H, "HYPOTENUSE")
    add_line(-50, 0, L + 50, 0, "FLOOR")
    add_line(-50, H, L + 50, H, "CEILING")

    tl = float(measurement.get("tremie_longueur", 0))
    tw = float(measurement.get("tremie_largeur", 0))
    if tl > 0 and tw > 0:
        add_line(L - tl, H, L, H, "TREMIE")
        add_line(L - tl, H + tw, L, H + tw, "TREMIE")
        add_line(L - tl, H, L - tl, H + tw, "TREMIE")
        add_line(L, H, L, H + tw, "TREMIE")

    def add_text(x, y, text, height=20, layer="LABELS"):
        out.extend([
            "0", "TEXT", "8", layer,
            "10", f"{x:.3f}", "20", f"{y:.3f}", "30", "0.0",
            "40", f"{height:.3f}",
            "1", text,
        ])

    add_text(L / 2, -60, f"Reculement: {round(L)} mm")
    add_text(-80, H / 2, f"H: {round(H)} mm")
    add_text(L / 2, H + 30, f"{n} marches  h={r['h']}  g={r['g']}")
    limon_len = r.get("limon_length", r.get("hypotenuse"))
    add_text(L * 0.4, H * 0.45,
             f"LIMON: {round(limon_len)} mm (decoupe atelier)",
             height=25, layer="LIMON")
    add_line(0, 0, L, H, "LIMON")
    if r.get("echappee") is not None:
        suffix = " - CRITIQUE" if r.get("echappee_critique") else ""
        add_text(L * 0.7, H * 0.85,
                 f"Echappee: {round(r['echappee'])} mm{suffix}",
                 height=22, layer="ECHAPPEE")
    add_text(0, -120,
             f"MesureEscalier - {project.get('client_nom', '')} {project.get('client_prenom', '')}")

    out.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(out)
