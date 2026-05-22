"""PDF (ReportLab) + DXF (ASCII) builders for stair reports."""
from __future__ import annotations

import base64
import io
import logging

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
    story.append(Paragraph(f"Chantier — {project.get('client_nom', '')} {project.get('client_prenom', '')}".strip(), title_style))

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


def build_dxf_text(project: dict, measurement: dict) -> str:
    """Generate a minimal AutoCAD-readable DXF (ASCII)."""
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
