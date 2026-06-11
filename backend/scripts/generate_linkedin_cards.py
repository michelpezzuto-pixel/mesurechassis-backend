"""Génère les 15 visuels LinkedIn (1080×1080) aux couleurs MesureChâssis.

Usage : python3 scripts/generate_linkedin_cards.py
Sortie : backend/static/linkedin/jour_01.png ... jour_15.png
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from routes.linkedin import POSTS  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "static" / "linkedin"
OUT.mkdir(parents=True, exist_ok=True)

W = H = 1080
BG = "#0C0C0E"
SURFACE = "#18181B"
ORANGE = "#FF5A00"
WHITE = "#FAFAFA"
GREY = "#A1A1AA"

FONT_DIR = "/usr/share/fonts/truetype/liberation"
F_BOLD = f"{FONT_DIR}/LiberationSans-Bold.ttf"
F_REG = f"{FONT_DIR}/LiberationSans-Regular.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    """Découpe le texte en lignes qui tiennent dans max_w pixels."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(post: dict) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    M = 80  # marge

    # Bande orange supérieure
    d.rectangle([0, 0, W, 14], fill=ORANGE)

    # Badge "JOUR X/15"
    badge_f = font(F_BOLD, 34)
    badge_txt = f"JOUR {post['day']}/15"
    bw = d.textlength(badge_txt, font=badge_f)
    d.rounded_rectangle([M, 90, M + bw + 56, 90 + 64], radius=32, fill=ORANGE)
    d.text((M + 28, 90 + 13), badge_txt, font=badge_f, fill="#FFFFFF")

    # Kicker (catégorie)
    kicker_f = font(F_BOLD, 30)
    kicker = post.get("visual_kicker", "")
    if kicker:
        d.text((M, 215), kicker, font=kicker_f, fill=ORANGE)

    # Titre principal (wrap)
    title_f = font(F_BOLD, 76)
    y = 275
    for line in wrap(d, post["title"], title_f, W - 2 * M):
        d.text((M, y), line, font=title_f, fill=WHITE)
        y += 92

    # Sous-titre
    sub_f = font(F_REG, 42)
    y += 16
    for line in wrap(d, post["subtitle"], sub_f, W - 2 * M):
        d.text((M, y), line, font=sub_f, fill=GREY)
        y += 56

    # Carte "écran app" stylisée (rappel visuel produit)
    cy = max(y + 50, 600)
    d.rounded_rectangle([M, cy, W - M, cy + 250], radius=24, fill=SURFACE)
    d.rounded_rectangle([M + 36, cy + 40, M + 96, cy + 100], radius=14, fill=ORANGE)
    d.text((M + 120, cy + 42), "MesureChâssis", font=font(F_BOLD, 44), fill=WHITE)
    d.text(
        (M + 120, cy + 100),
        "L'app de prise de mesures des menuisiers",
        font=font(F_REG, 30),
        fill=GREY,
    )
    # Fausses lignes de cotes (déco)
    for i, lw in enumerate([520, 380, 450]):
        ly = cy + 165 + i * 26
        d.rounded_rectangle([M + 120, ly, M + 120 + lw, ly + 12], radius=6, fill="#27272A")

    # Pied de page (deux lignes à gauche — pas de chevauchement)
    d.rectangle([0, H - 120, W, H], fill=SURFACE)
    d.text((M, H - 102), "mesurechassis.com", font=font(F_BOLD, 36), fill=ORANGE)
    d.text(
        (M, H - 52),
        "Créée par un menuisier, pour les menuisiers",
        font=font(F_REG, 27),
        fill=GREY,
    )

    out = OUT / f"jour_{post['day']:02d}.png"
    img.save(out, "PNG", optimize=True)
    print(f"✅ {out.name} — {post['title']}")


if __name__ == "__main__":
    for p in POSTS:
        make_card(p)
    print(f"\n{len(POSTS)} visuels générés dans {OUT}")
