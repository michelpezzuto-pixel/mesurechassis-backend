#!/usr/bin/env python3
"""Génère la feature graphic Google Play (1024×500) pour MesureChâssis.

Usage : python3 /app/scripts/generate_feature_graphic.py
Sortie : /app/backend/static/play_feature_graphic_1024x500.png
"""

import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
BG = (17, 19, 24)          # charbon profond
SURFACE = (24, 24, 27)
ORANGE = (255, 90, 0)      # #FF5A00 — orange MesureChâssis
ORANGE_DARK = (204, 72, 0)
WHITE = (255, 255, 255)
GREY = (161, 161, 170)

FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_REG = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

OUT_DIR = "/app/backend/static"
OUT = os.path.join(OUT_DIR, "play_feature_graphic_1024x500.png")
ICON = "/app/frontend/assets/images/icon.png"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ── Bande diagonale orange en fond (dynamisme) ────────────────────
    d.polygon([(W - 330, 0), (W, 0), (W, H), (W - 170, H)], fill=(28, 26, 28))
    d.polygon([(W - 310, 0), (W - 270, 0), (W - 110, H), (W - 150, H)], fill=ORANGE_DARK)

    # ── Icône de l'app (gauche) ───────────────────────────────────────
    icon = Image.open(ICON).convert("RGBA").resize((150, 150))
    # coins arrondis
    mask = Image.new("L", icon.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 150, 150], radius=32, fill=255)
    img.paste(icon, (64, 60), mask)

    # ── Wordmark + slogan ─────────────────────────────────────────────
    f_title = ImageFont.truetype(FONT_BOLD, 64)
    f_slogan = ImageFont.truetype(FONT_REG, 30)
    f_small = ImageFont.truetype(FONT_BOLD, 22)

    d.text((240, 88), "Mesure", font=f_title, fill=WHITE)
    w_mesure = d.textlength("Mesure", font=f_title)
    d.text((240 + w_mesure, 88), "Châssis", font=f_title, fill=ORANGE)

    d.text((66, 260), "Le relevé de mesures des pros", font=f_slogan, fill=WHITE)
    d.text((66, 302), "de la menuiserie.", font=f_slogan, fill=WHITE)

    # puces fonctionnalités
    feats = ["Wizard de mesures guidé", "Exports PDF & Excel", "Gestion d'équipe & chantiers"]
    y = 368
    for feat in feats:
        d.ellipse([66, y + 7, 78, y + 19], fill=ORANGE)
        d.text((92, y), feat, font=f_small, fill=GREY)
        y += 38

    # ── Schéma châssis coté (droite) ──────────────────────────────────
    fx, fy, fw, fh = 700, 90, 240, 320  # cadre fenêtre
    # cadre extérieur
    d.rounded_rectangle([fx, fy, fx + fw, fy + fh], radius=8, outline=WHITE, width=6)
    # montant central + traverse (2 vantaux)
    d.line([fx + fw // 2, fy + 6, fx + fw // 2, fy + fh - 6], fill=WHITE, width=4)
    d.line([fx + 6, fy + fh // 3, fx + fw - 6, fy + fh // 3], fill=WHITE, width=3)
    # vitrage (léger remplissage)
    d.rectangle([fx + 12, fy + 12, fx + fw // 2 - 6, fy + fh // 3 - 6], fill=(36, 42, 52))
    d.rectangle([fx + fw // 2 + 6, fy + 12, fx + fw - 12, fy + fh // 3 - 6], fill=(36, 42, 52))
    d.rectangle([fx + 12, fy + fh // 3 + 6, fx + fw // 2 - 6, fy + fh - 12], fill=(36, 42, 52))
    d.rectangle([fx + fw // 2 + 6, fy + fh // 3 + 6, fx + fw - 12, fy + fh - 12], fill=(36, 42, 52))

    f_dim = ImageFont.truetype(FONT_BOLD, 24)

    # cote horizontale (largeur) sous le cadre
    cy = fy + fh + 34
    d.line([fx, cy, fx + fw, cy], fill=ORANGE, width=3)
    for x in (fx, fx + fw):
        d.line([x, cy - 10, x, cy + 10], fill=ORANGE, width=3)
    txt = "1200 mm"
    tw = d.textlength(txt, font=f_dim)
    d.rectangle([fx + fw / 2 - tw / 2 - 8, cy - 16, fx + fw / 2 + tw / 2 + 8, cy + 16], fill=BG)
    d.text((fx + fw / 2 - tw / 2, cy - 13), txt, font=f_dim, fill=ORANGE)

    # cote verticale (hauteur) à gauche du cadre
    cx = fx - 34
    d.line([cx, fy, cx, fy + fh], fill=ORANGE, width=3)
    for yy in (fy, fy + fh):
        d.line([cx - 10, yy, cx + 10, yy], fill=ORANGE, width=3)
    txt_v = "1450"
    tv = d.textlength(txt_v, font=f_dim)
    d.rectangle([cx - tv / 2 - 6, fy + fh / 2 - 18, cx + tv / 2 + 6, fy + fh / 2 + 18], fill=BG)
    d.text((cx - tv / 2, fy + fh / 2 - 13), txt_v, font=f_dim, fill=ORANGE)

    img.save(OUT, "PNG")
    print(f"OK → {OUT} ({os.path.getsize(OUT) // 1024} Ko)")


if __name__ == "__main__":
    main()
