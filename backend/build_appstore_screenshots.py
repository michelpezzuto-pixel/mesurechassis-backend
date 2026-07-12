"""📸 Génère les 5 screenshots App Store (format iPhone 6.9" — 1320×2868).

Étapes :
    1. Ouvre l'app dans Chromium headless (viewport 430×932)
    2. Navigue vers 5 écrans clés
    3. Sauvegarde les captures PNG
    4. Compose chaque capture avec un bandeau titre marketing (Pillow)
    5. Zippe le tout dans /app/backend/public_downloads/appstore_screenshots_v114.zip
"""
from __future__ import annotations

import asyncio
import os
import shutil
import zipfile

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads/appstore_screenshots"
os.makedirs(OUT_DIR, exist_ok=True)
CAPTURES_DIR = "/tmp/appstore_captures"
os.makedirs(CAPTURES_DIR, exist_ok=True)

# Format cible Apple : iPhone 6.9" — 1320 × 2868 (portrait)
TARGET_W, TARGET_H = 1320, 2868
# Taille du viewport pour capture (device pixel ratio 3 → 430x932)
VP_W, VP_H = 430, 932

# 5 slides — titre marketing + credentials/actions
SLIDES = [
    {
        "id": "01_login",
        "title": "Sécurisé & pro",
        "subtitle": "Connexion FR · NL · EN",
        "action": None,
    },
    {
        "id": "02_dashboard",
        "title": "Tous tes chantiers, en un clin d'œil",
        "subtitle": "Filtres, recherche & statuts en temps réel",
        "action": None,
    },
    {
        "id": "03_modal_new_chantier",
        "title": "Création chantier en 30 secondes",
        "subtitle": "L'IA remplit les coordonnées si tu scannes un CDC",
        "action": "modal",
    },
    {
        "id": "04_fiche_chantier_wall_opt",
        "title": "Mesure sans contrainte",
        "subtitle": "Configuration des murs devenue optionnelle",
        "action": None,
    },
    {
        "id": "05_wizard_passer",
        "title": "Wizard flexible en 3 étapes",
        "subtitle": "Passe ou remplis à ton rythme",
        "action": None,
    },
]


# ═══════════════════════════════════════════════════════════════════════
# CAPTURE
# ═══════════════════════════════════════════════════════════════════════
async def capture_all():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": VP_W, "height": VP_H},
            device_scale_factor=3,  # ⇒ capture native ≈ 1290×2796
        )
        page = await ctx.new_page()

        # --- Prep : onboarding + login commercial ---
        await page.goto("http://localhost:3000/")
        await page.wait_for_timeout(4000)
        try:
            await page.get_by_text("Passer", exact=True).first.click(timeout=1500)
            await page.wait_for_timeout(1200)
        except Exception:
            pass
        try:
            await page.get_by_text("FR", exact=True).first.click(timeout=1500)
            await page.wait_for_timeout(600)
        except Exception:
            pass

        # 01 — Login
        await page.screenshot(path=f"{CAPTURES_DIR}/01_login.png", full_page=False, type="png")
        print("  ✅ 01 Login")

        # Login
        await page.get_by_placeholder("prenom.nom@entreprise.fr", exact=False).first.fill(
            "commercial@mesurechassis.fr"
        )
        await page.locator("input[type=password]").first.fill("commercial123")
        await page.get_by_text("SE CONNECTER", exact=True).first.click()
        await page.wait_for_timeout(6500)

        # 02 — Dashboard
        await page.screenshot(path=f"{CAPTURES_DIR}/02_dashboard.png", full_page=False, type="png")
        print("  ✅ 02 Dashboard")

        # 03 — Modal Nouveau chantier
        try:
            await page.get_by_text("Nouveau chantier", exact=False).first.click(timeout=4000)
            await page.wait_for_timeout(2500)
            await page.screenshot(
                path=f"{CAPTURES_DIR}/03_modal_new_chantier.png",
                full_page=False, type="png",
            )
            print("  ✅ 03 Modal Nouveau chantier")
        except Exception as e:
            print("  ❌ 03 err:", e)

        # 04 — Fiche chantier (navigation directe vers le chantier vierge DEMO-APPSTORE)
        chantier_id = "484f1045-937f-4afd-a439-43eea5970912"
        try:
            await page.goto(f"http://localhost:3000/chantier/{chantier_id}")
            await page.wait_for_timeout(6500)
            # Scroll to footer
            try:
                btn = page.get_by_test_id("edit-wall-config-button")
                await btn.scroll_into_view_if_needed(timeout=4000)
                await page.wait_for_timeout(700)
            except Exception:
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(600)
            await page.screenshot(
                path=f"{CAPTURES_DIR}/04_fiche_chantier_wall_opt.png",
                full_page=False, type="png",
            )
            print("  ✅ 04 Fiche chantier")
        except Exception as e:
            print("  ❌ 04 err:", e)

        # 05 — Wizard étape 1 (avec bouton PASSER) — navigation directe
        try:
            await page.goto(f"http://localhost:3000/chantier/{chantier_id}/new-mesure")
            await page.wait_for_timeout(5500)
            await page.mouse.wheel(0, 5000)
            await page.wait_for_timeout(700)
            await page.screenshot(
                path=f"{CAPTURES_DIR}/05_wizard_passer.png",
                full_page=False, type="png",
            )
            print("  ✅ 05 Wizard PASSER")
        except Exception as e:
            print("  ❌ 05 err:", e)

        await browser.close()


# ═══════════════════════════════════════════════════════════════════════
# COMPOSITION AVEC BANDEAU MARKETING
# ═══════════════════════════════════════════════════════════════════════
def _load_font(size: int, bold: bool = False):
    """Trouve une police disponible sur le système."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def compose_slide(slide: dict) -> str:
    src = f"{CAPTURES_DIR}/{slide['id']}.png"
    if not os.path.isfile(src):
        print(f"  ⚠️ Source introuvable : {src}")
        return ""

    # Canvas final Apple 6.9"
    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)

    # Bandeau titre haut — dégradé orange
    banner_h = 420
    for y in range(banner_h):
        # Dégradé orange → orange foncé
        t = y / banner_h
        r = int(255 * (1 - 0.15 * t))
        g = int(90 * (1 - 0.35 * t))
        b = int(0 + 20 * t)
        draw.line([(0, y), (TARGET_W, y)], fill=(r, g, b))

    # Texte titre
    font_title = _load_font(76, bold=True)
    font_sub = _load_font(38, bold=False)
    # Wrap simple : titre sur 2 lignes max
    title = slide["title"]
    title_words = title.split()
    if len(title) > 22:
        mid = len(title_words) // 2
        title_l1 = " ".join(title_words[:mid])
        title_l2 = " ".join(title_words[mid:])
    else:
        title_l1, title_l2 = title, ""

    def _tw(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    y = 150
    w1, h1 = _tw(title_l1, font_title)
    draw.text(((TARGET_W - w1) // 2, y), title_l1, font=font_title, fill="#FFFFFF")
    if title_l2:
        y2 = y + h1 + 10
        w2, _ = _tw(title_l2, font_title)
        draw.text(((TARGET_W - w2) // 2, y2), title_l2, font=font_title, fill="#FFFFFF")
        y = y2 + h1
    else:
        y += h1

    ws, _ = _tw(slide["subtitle"], font_sub)
    draw.text(((TARGET_W - ws) // 2, y + 40),
              slide["subtitle"], font=font_sub, fill=(255, 220, 180))

    # Screenshot — resize à ~1200 px de large max, centré sous le bandeau
    shot = Image.open(src).convert("RGB")
    # La capture native fait ~1290×2796. On la met à 1150 px de large max.
    max_w = 1180
    ratio = max_w / shot.width
    new_w = int(shot.width * ratio)
    new_h = int(shot.height * ratio)
    shot = shot.resize((new_w, new_h), Image.LANCZOS)

    # Bordure noire arrondie discrète autour du device
    device_pad = 12
    device_bg = Image.new("RGB", (new_w + device_pad * 2, new_h + device_pad * 2), (30, 30, 34))
    device_bg.paste(shot, (device_pad, device_pad))

    # Position : centré horizontalement, sous le bandeau
    px = (TARGET_W - device_bg.width) // 2
    py = banner_h + 80
    canvas.paste(device_bg, (px, py))

    # Petit logo/branding en bas
    footer_y = TARGET_H - 130
    draw.rectangle([(0, footer_y), (TARGET_W, TARGET_H)], fill=(20, 20, 24))
    logo_font = _load_font(38, bold=True)
    tag_font = _load_font(22, bold=False)
    logo_text = "MESURECHÂSSIS"
    lw, _ = _tw(logo_text, logo_font)
    draw.text(((TARGET_W - lw) // 2, footer_y + 22),
              logo_text, font=logo_font, fill="#FF5A00")
    tag = "Mesures terrain · Menuiseries pro"
    tw, _ = _tw(tag, tag_font)
    draw.text(((TARGET_W - tw) // 2, footer_y + 74),
              tag, font=tag_font, fill=(160, 160, 168))

    out_path = f"{OUT_DIR}/{slide['id']}.png"
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def compose_all():
    print("🎨 Composition des screenshots App Store...")
    outputs = []
    for slide in SLIDES:
        path = compose_slide(slide)
        if path:
            print(f"  ✅ {os.path.basename(path)} ({os.path.getsize(path) // 1024} Ko)")
            outputs.append(path)
    return outputs


def zip_all(files: list[str]) -> str:
    zip_path = "/app/backend/public_downloads/appstore_screenshots_v114.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.basename(f))
    print(f"📦 ZIP créé : {zip_path} ({os.path.getsize(zip_path) // 1024} Ko)")
    return zip_path


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 60)
    print("📸 GÉNÉRATION SCREENSHOTS APP STORE — Version 114")
    print("═" * 60)
    print("Étape 1/3 : Capture des 5 écrans dans l'app")
    asyncio.run(capture_all())
    print()
    print("Étape 2/3 : Composition avec bandeau marketing")
    outputs = compose_all()
    print()
    print("Étape 3/3 : ZIP final")
    zip_all(outputs)
    print()
    print("✅ TERMINÉ. Les fichiers PNG sont dans :")
    print(f"   {OUT_DIR}/")
    print("Et regroupés dans le ZIP téléchargeable via l'endpoint")
    print("   /api/_downloads/appstore-screenshots-v114")
