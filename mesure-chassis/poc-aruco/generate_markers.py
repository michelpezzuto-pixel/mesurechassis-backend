"""
Génère les 12 premiers markers ArUco 4x4_50 (IDs 0-11) en :
  - PNG haute résolution unitaires
  - SVG individuels (vectoriel, qualité d'impression parfaite)
  - PDF A4 planche de 12 markers (50 mm × 50 mm, prêt à imprimer)

Conforme à la recommandation : "Série B : ArUco 4x4_50, taille 50 mm, IDs 0 à 11"

Lance :
    python /app/mesure-chassis/poc-aruco/generate_markers.py

Sortie :
    /app/mesure-chassis/poc-aruco/markers/
        ├── png/             # ArUco_00.png ... ArUco_11.png
        ├── svg/             # ArUco_00.svg ... ArUco_11.svg
        └── markers_A4_50mm.pdf  # Planche A4 prête à imprimer
"""
from __future__ import annotations
import cv2
import cv2.aruco as aruco
import numpy as np
from pathlib import Path

OUT_DIR = Path("/app/mesure-chassis/poc-aruco/markers")
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "png").mkdir(exist_ok=True)
(OUT_DIR / "svg").mkdir(exist_ok=True)

# Dictionnaire ArUco 4x4 avec 50 markers (= 6x6 cellules avec bordure)
DICT = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
TARGET_SIZE_MM = 50.0   # taille physique cible
DPI = 300               # qualité impression
PX_PER_MM = DPI / 25.4  # 11.81 px/mm à 300 DPI
PX_TOTAL = int(round(TARGET_SIZE_MM * PX_PER_MM))  # ≈ 591 px → marker 50mm imprimé à 300 DPI

print(f"Génération de 12 markers ArUco 4x4_50 — taille cible {TARGET_SIZE_MM} mm @ {DPI} DPI ({PX_TOTAL} px)")

# ─── Génération PNG ─────────────────────────────────────────────────────────
for marker_id in range(12):
    img = aruco.generateImageMarker(DICT, marker_id, PX_TOTAL, borderBits=1)
    path = OUT_DIR / "png" / f"ArUco_{marker_id:02d}.png"
    cv2.imwrite(str(path), img)
print(f"  ✓ 12 PNG haute résolution → {OUT_DIR}/png/")

# ─── Génération SVG (vectoriel, qualité parfaite à toute taille) ────────────
def marker_to_svg(marker_id: int, size_mm: float) -> str:
    """Convertit le marker en SVG pur (8x8 grid : 1px bordure + 6x6 marker)."""
    # Récupère le bitmap 6x6 du marker
    bits = DICT.generateImageMarker(marker_id, 6, 1)  # type: ignore
    # Compose un SVG : carré 50mm avec cellules noires/blanches
    # Structure : grille 8x8 (bordure 1 cellule de chaque côté autour du 6x6)
    grid_size = 8
    cell = size_mm / grid_size
    svg = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size_mm}mm" height="{size_mm + 6}mm" '
        f'viewBox="0 0 {size_mm} {size_mm + 6}">',
        # Fond blanc
        f'<rect width="{size_mm}" height="{size_mm + 6}" fill="white"/>',
    ]
    # Le marker complet généré par OpenCV (6x6 + bordure 1 = 8x8)
    img8 = cv2.aruco.generateImageMarker(DICT, marker_id, 8, borderBits=1)
    for y in range(grid_size):
        for x in range(grid_size):
            if img8[y, x] == 0:  # cellule noire
                svg.append(
                    f'<rect x="{x * cell}" y="{y * cell}" '
                    f'width="{cell}" height="{cell}" fill="black"/>'
                )
    # Label ID + taille sous le marker
    svg.append(
        f'<text x="{size_mm / 2}" y="{size_mm + 4.5}" '
        f'font-family="Arial, sans-serif" font-size="3" '
        f'text-anchor="middle" fill="black">'
        f'ArUco 4x4_50  ID={marker_id}  {int(size_mm)}mm</text>'
    )
    svg.append('</svg>')
    return '\n'.join(svg)

for marker_id in range(12):
    svg_content = marker_to_svg(marker_id, TARGET_SIZE_MM)
    (OUT_DIR / "svg" / f"ArUco_{marker_id:02d}.svg").write_text(svg_content, encoding='utf-8')
print(f"  ✓ 12 SVG vectoriels → {OUT_DIR}/svg/")

# ─── Planche A4 PDF — 12 markers 50mm avec cotes et marges de coupe ────────
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    pdf_path = OUT_DIR / "markers_A4_50mm.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    page_w, page_h = A4  # 595.27 × 841.89 pt
    page_w_mm, page_h_mm = page_w / mm, page_h / mm

    # Layout : 3 colonnes × 4 lignes = 12 markers
    # Marges 15 mm de chaque côté, espacement 5 mm
    margin = 15
    gap = 10
    n_cols, n_rows = 3, 4
    cell_w = (page_w_mm - 2 * margin - (n_cols - 1) * gap) / n_cols
    marker_size = min(cell_w, TARGET_SIZE_MM)  # 50 mm garanti
    cell_h = marker_size + 12  # marker + label + marge

    # En-tête
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin * mm, (page_h_mm - 8) * mm, "Mesure Escalier — Planche ArUco 4x4_50")
    c.setFont("Helvetica", 9)
    c.drawString(margin * mm, (page_h_mm - 13) * mm,
                 f"12 markers · taille {TARGET_SIZE_MM:.0f} mm · IDs 0–11 · "
                 f"Imprimer à 100% (pas «adapter à la page»)")

    # Trait de calibration : un segment de 50 mm exact à mesurer pour vérifier
    cal_y = page_h_mm - 18
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.line(margin * mm, cal_y * mm, (margin + 50) * mm, cal_y * mm)
    c.line(margin * mm, (cal_y - 1.5) * mm, margin * mm, (cal_y + 1.5) * mm)
    c.line((margin + 50) * mm, (cal_y - 1.5) * mm, (margin + 50) * mm, (cal_y + 1.5) * mm)
    c.setFont("Helvetica-Oblique", 7)
    c.drawString((margin + 52) * mm, (cal_y - 1) * mm,
                 "← Repère 50 mm (mesurer au pied à coulisse après impression)")

    # Placement des 12 markers
    start_y_mm = cal_y - 12
    for idx in range(12):
        row = idx // n_cols
        col = idx % n_cols
        x_mm = margin + col * (cell_w + gap)
        y_top_mm = start_y_mm - row * cell_h
        y_marker_bottom = y_top_mm - marker_size

        # Dessin du marker (cellules noires/blanches)
        img8 = cv2.aruco.generateImageMarker(DICT, idx, 8, borderBits=1)
        cell = marker_size / 8
        for yy in range(8):
            for xx in range(8):
                if img8[yy, xx] == 0:
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(
                        (x_mm + xx * cell) * mm,
                        (y_marker_bottom + (7 - yy) * cell) * mm,
                        cell * mm, cell * mm,
                        fill=1, stroke=0,
                    )

        # Cadre de coupe (pointillé 0.2 mm pour ne pas perturber détection)
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.setDash(1, 1)
        c.setLineWidth(0.2)
        c.rect(x_mm * mm, y_marker_bottom * mm, marker_size * mm, marker_size * mm, fill=0)
        c.setDash([])

        # Label sous chaque marker
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(
            (x_mm + marker_size / 2) * mm,
            (y_marker_bottom - 4) * mm,
            f"ID = {idx:02d}",
        )

    # Pied de page
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(margin * mm, 8 * mm,
                 "Imprimer sur papier mat blanc · Découper aux pointillés gris · "
                 "Coller sur support rigide 1-3 mm · Éviter reflets et papier brillant")
    c.showPage()
    c.save()
    print(f"  ✓ Planche PDF A4 → {pdf_path}")
except ImportError:
    print("  ! reportlab non installé — PDF skip")

print("\n✅ Génération terminée.")
print(f"\nProchaines étapes :")
print(f"  1. Ouvrir {OUT_DIR / 'markers_A4_50mm.pdf'}")
print(f"  2. Imprimer A4 à 100% (NE PAS cocher «adapter à la page»)")
print(f"  3. Mesurer le repère 50 mm en haut de page pour vérifier la taille")
print(f"  4. Découper aux pointillés, coller sur support rigide")
