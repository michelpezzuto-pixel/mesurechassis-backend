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

OUT_DIR_ROOT = "/app/backend/public_downloads/appstore_screenshots"
CAPTURES_DIR = "/tmp/appstore_captures"
os.makedirs(CAPTURES_DIR, exist_ok=True)

# 3 formats iPhone acceptés par Apple App Store Connect (juillet 2026) :
#   • 6.9" — iPhone 16 Pro Max (le plus récent)
#   • 6.7" — iPhone 15/14 Pro Max
#   • 6.5" — iPhone 11 Pro Max / XS Max (encore requis dans certains onglets)
#
# Apple downscale automatiquement 6.9" → tailles inférieures depuis 04/2024,
# MAIS certains comptes/apps demandent encore explicitement le 6.5". On génère
# donc les 3 tailles pour couvrir tous les cas.
TARGET_SIZES = [
    {"label": "6_9", "w": 1320, "h": 2868, "human": "iPhone 6.9 pouces"},
    {"label": "6_7", "w": 1290, "h": 2796, "human": "iPhone 6.7 pouces"},
    {"label": "6_5", "w": 1242, "h": 2688, "human": "iPhone 6.5 pouces"},
]

# Taille du viewport pour capture (device pixel ratio 3 → 1290×2796 natif)
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


def compose_slide(slide: dict, target: dict, out_dir: str) -> str:
    src = f"{CAPTURES_DIR}/{slide['id']}.png"
    if not os.path.isfile(src):
        print(f"  ⚠️ Source introuvable : {src}")
        return ""

    W, H = target["w"], target["h"]
    # Ratios adaptatifs sur la hauteur pour bandeau/footer
    banner_h = int(H * 0.147)   # ~14,7% de la hauteur
    footer_h = int(H * 0.045)   # ~4,5%
    # Canvas final Apple
    canvas = Image.new("RGB", (W, H), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)

    # Bandeau titre haut — dégradé orange
    for y in range(banner_h):
        t = y / banner_h
        r = int(255 * (1 - 0.15 * t))
        g = int(90 * (1 - 0.35 * t))
        b = int(0 + 20 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Fonts adaptatives
    title_size = int(H * 0.027)   # ~27pt
    sub_size = int(H * 0.0132)
    font_title = _load_font(title_size, bold=True)
    font_sub = _load_font(sub_size, bold=False)

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

    y = int(H * 0.052)
    w1, h1 = _tw(title_l1, font_title)
    draw.text(((W - w1) // 2, y), title_l1, font=font_title, fill="#FFFFFF")
    if title_l2:
        y2 = y + h1 + 10
        w2, _ = _tw(title_l2, font_title)
        draw.text(((W - w2) // 2, y2), title_l2, font=font_title, fill="#FFFFFF")
        y = y2 + h1
    else:
        y += h1

    ws, _ = _tw(slide["subtitle"], font_sub)
    draw.text(((W - ws) // 2, y + int(H * 0.014)),
              slide["subtitle"], font=font_sub, fill=(255, 220, 180))

    # Screenshot centré sous le bandeau
    shot = Image.open(src).convert("RGB")
    max_w = int(W * 0.895)
    ratio = max_w / shot.width
    new_w = int(shot.width * ratio)
    new_h = int(shot.height * ratio)
    shot = shot.resize((new_w, new_h), Image.LANCZOS)

    device_pad = 12
    device_bg = Image.new("RGB",
                          (new_w + device_pad * 2, new_h + device_pad * 2),
                          (30, 30, 34))
    device_bg.paste(shot, (device_pad, device_pad))

    px = (W - device_bg.width) // 2
    py = banner_h + int(H * 0.028)
    # Si dépasse en bas, on redimensionne
    if py + device_bg.height > H - footer_h - 20:
        max_dev_h = H - banner_h - footer_h - int(H * 0.06)
        dev_ratio = max_dev_h / device_bg.height
        new_dw = int(device_bg.width * dev_ratio)
        new_dh = int(device_bg.height * dev_ratio)
        device_bg = device_bg.resize((new_dw, new_dh), Image.LANCZOS)
        px = (W - device_bg.width) // 2
    canvas.paste(device_bg, (px, py))

    # Footer branding
    footer_y = H - footer_h - int(H * 0.023)
    draw.rectangle([(0, footer_y), (W, H)], fill=(20, 20, 24))
    logo_font = _load_font(int(H * 0.0135), bold=True)
    tag_font = _load_font(int(H * 0.0077), bold=False)
    logo_text = "MESURECHÂSSIS"
    lw, _ = _tw(logo_text, logo_font)
    draw.text(((W - lw) // 2, footer_y + int(H * 0.008)),
              logo_text, font=logo_font, fill="#FF5A00")
    tag = "Mesures terrain · Menuiseries pro"
    tw, _ = _tw(tag, tag_font)
    draw.text(((W - tw) // 2, footer_y + int(H * 0.026)),
              tag, font=tag_font, fill=(160, 160, 168))

    out_path = f"{out_dir}/{slide['id']}.png"
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def compose_all():
    print("🎨 Composition des screenshots App Store...")
    all_zips = []
    for target in TARGET_SIZES:
        out_dir = f"{OUT_DIR_ROOT}_{target['label']}"
        os.makedirs(out_dir, exist_ok=True)
        print(f"\n  ▸ Taille {target['human']} ({target['w']}x{target['h']})")
        outputs = []
        for slide in SLIDES:
            path = compose_slide(slide, target, out_dir)
            if path:
                outputs.append(path)
                print(f"    ✅ {os.path.basename(path)} ({os.path.getsize(path)//1024} Ko)")
        if outputs:
            zip_path = f"/app/backend/public_downloads/appstore_screenshots_{target['label']}_v114.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in outputs:
                    z.write(f, os.path.basename(f))
            print(f"    📦 ZIP : {zip_path} ({os.path.getsize(zip_path)//1024} Ko)")
            all_zips.append((target, zip_path, outputs))
    return all_zips


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("SCREENSHOTS APP STORE — Version 1.0.24")
    print("=" * 60)
    print("Étape 1/2 : Capture des 5 écrans dans l'app")
    asyncio.run(capture_all())
    print()
    print("Étape 2/2 : Composition dans les 3 tailles Apple + ZIP")
    all_zips = compose_all()
    print()
    print("✅ TERMINÉ. Tailles générées :")
    for target, zip_path, outputs in all_zips:
        print(f"  {target['human']} ({target['w']}x{target['h']}) : {len(outputs)} PNG, {os.path.getsize(zip_path)//1024} Ko")
