"""📸 Génère les 5 screenshots App Store aux formats iPad Pro."""
from __future__ import annotations

import asyncio
import os
import zipfile

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

CAPTURES_DIR = "/tmp/appstore_captures_ipad"
os.makedirs(CAPTURES_DIR, exist_ok=True)

# 2 formats iPad demandés par App Store Connect (2026)
IPAD_SIZES = [
    {"label": "12_9", "w": 2048, "h": 2732, "human": "iPad Pro 12.9\""},
    {"label": "13", "w": 2064, "h": 2752, "human": "iPad Pro 13\""},
]

# Viewport de capture — mode tablette portrait
VP_W, VP_H = 1024, 1366  # iPad Pro 12.9" CSS

SLIDES = [
    {"id": "01_login", "title": "Sécurisé & pro", "subtitle": "Connexion FR · NL · EN"},
    {"id": "02_dashboard", "title": "Tous tes chantiers, en un clin d'œil", "subtitle": "Filtres, recherche & statuts en temps réel"},
    {"id": "03_modal_new_chantier", "title": "Création chantier en 30 secondes", "subtitle": "L'IA remplit les coordonnées si tu scannes un CDC"},
    {"id": "04_fiche_chantier_wall_opt", "title": "Mesure sans contrainte", "subtitle": "Configuration des murs devenue optionnelle"},
    {"id": "05_wizard_passer", "title": "Wizard flexible en 3 étapes", "subtitle": "Passe ou remplis à ton rythme"},
]

CHANTIER_ID = "484f1045-937f-4afd-a439-43eea5970912"


async def capture_all():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": VP_W, "height": VP_H},
            device_scale_factor=2,
        )
        page = await ctx.new_page()
        await page.goto("http://localhost:3000/")
        await page.wait_for_timeout(4000)
        # Skip onboarding
        try:
            await page.get_by_text("Passer", exact=True).first.click(timeout=2000)
            await page.wait_for_timeout(1200)
        except Exception:
            pass
        try:
            await page.get_by_text("FR", exact=True).first.click(timeout=1500)
            await page.wait_for_timeout(600)
        except Exception:
            pass

        # 01 - Login
        await page.screenshot(path=f"{CAPTURES_DIR}/01_login.png", full_page=False, type="png")
        print("  ✅ 01 Login")

        await page.get_by_placeholder("prenom.nom@entreprise.fr", exact=False).first.fill("commercial@mesurechassis.fr")
        await page.locator("input[type=password]").first.fill("commercial123")
        await page.get_by_text("SE CONNECTER", exact=True).first.click()
        await page.wait_for_timeout(6500)

        # 02 - Dashboard
        await page.screenshot(path=f"{CAPTURES_DIR}/02_dashboard.png", full_page=False, type="png")
        print("  ✅ 02 Dashboard")

        # 03 - Modal Nouveau chantier
        try:
            await page.get_by_text("Nouveau chantier", exact=False).first.click(timeout=4000)
            await page.wait_for_timeout(2500)
            await page.screenshot(path=f"{CAPTURES_DIR}/03_modal_new_chantier.png", full_page=False, type="png")
            print("  ✅ 03 Modal")
        except Exception as e:
            print(f"  ❌ 03 err: {e}")

        # 04 - Fiche chantier
        try:
            await page.goto(f"http://localhost:3000/chantier/{CHANTIER_ID}")
            await page.wait_for_timeout(6500)
            try:
                btn = page.get_by_test_id("edit-wall-config-button")
                await btn.scroll_into_view_if_needed(timeout=4000)
                await page.wait_for_timeout(700)
            except Exception:
                await page.mouse.wheel(0, 3000)
                await page.wait_for_timeout(600)
            await page.screenshot(path=f"{CAPTURES_DIR}/04_fiche_chantier_wall_opt.png", full_page=False, type="png")
            print("  ✅ 04 Fiche chantier")
        except Exception as e:
            print(f"  ❌ 04 err: {e}")

        # 05 - Wizard
        try:
            await page.goto(f"http://localhost:3000/chantier/{CHANTIER_ID}/new-mesure")
            await page.wait_for_timeout(5500)
            await page.mouse.wheel(0, 5000)
            await page.wait_for_timeout(700)
            await page.screenshot(path=f"{CAPTURES_DIR}/05_wizard_passer.png", full_page=False, type="png")
            print("  ✅ 05 Wizard PASSER")
        except Exception as e:
            print(f"  ❌ 05 err: {e}")

        await browser.close()


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def compose_ipad(slide: dict, target: dict, out_dir: str) -> str:
    """Composition adaptée iPad (ratio 3:4 environ)."""
    src = f"{CAPTURES_DIR}/{slide['id']}.png"
    if not os.path.isfile(src):
        return ""
    W, H = target["w"], target["h"]
    canvas = Image.new("RGB", (W, H), (12, 12, 14))
    draw = ImageDraw.Draw(canvas)

    # Bandeau orange proportionnel (~13% de la hauteur)
    banner_h = int(H * 0.13)
    for y in range(banner_h):
        t = y / banner_h
        r = int(255 * (1 - 0.15 * t))
        g = int(90 * (1 - 0.35 * t))
        b = int(0 + 20 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Titres
    font_title = _load_font(int(H * 0.028), bold=True)
    font_sub = _load_font(int(H * 0.0135), bold=False)

    title = slide["title"]
    words = title.split()
    if len(title) > 25:
        mid = len(words) // 2
        t_l1 = " ".join(words[:mid])
        t_l2 = " ".join(words[mid:])
    else:
        t_l1, t_l2 = title, ""

    def tw(text, font):
        b = draw.textbbox((0, 0), text, font=font)
        return b[2] - b[0], b[3] - b[1]

    y = int(H * 0.028)
    w1, h1 = tw(t_l1, font_title)
    draw.text(((W - w1) // 2, y), t_l1, font=font_title, fill="#FFFFFF")
    if t_l2:
        y2 = y + h1 + 12
        w2, _ = tw(t_l2, font_title)
        draw.text(((W - w2) // 2, y2), t_l2, font=font_title, fill="#FFFFFF")
        y = y2 + h1
    else:
        y += h1
    ws, _ = tw(slide["subtitle"], font_sub)
    draw.text(((W - ws) // 2, y + int(H * 0.012)), slide["subtitle"], font=font_sub, fill=(255, 220, 180))

    # Screenshot centré, respectant le ratio d'origine
    shot = Image.open(src).convert("RGB")
    footer_h = int(H * 0.04)
    available_h = H - banner_h - footer_h - int(H * 0.055)
    max_w = int(W * 0.88)

    # Scale
    ratio_h = available_h / shot.height
    ratio_w = max_w / shot.width
    ratio = min(ratio_h, ratio_w)
    new_w = int(shot.width * ratio)
    new_h = int(shot.height * ratio)
    shot = shot.resize((new_w, new_h), Image.LANCZOS)

    # Cadre autour du screenshot
    pad = 14
    frame = Image.new("RGB", (new_w + pad * 2, new_h + pad * 2), (30, 30, 34))
    frame.paste(shot, (pad, pad))

    px = (W - frame.width) // 2
    py = banner_h + int(H * 0.028)
    canvas.paste(frame, (px, py))

    # Footer branding
    footer_y = H - footer_h - int(H * 0.02)
    draw.rectangle([(0, footer_y), (W, H)], fill=(20, 20, 24))
    logo_font = _load_font(int(H * 0.0135), bold=True)
    tag_font = _load_font(int(H * 0.008), bold=False)
    logo_text = "MESURECHÂSSIS"
    lw, _ = tw(logo_text, logo_font)
    draw.text(((W - lw) // 2, footer_y + int(H * 0.006)), logo_text, font=logo_font, fill="#FF5A00")
    tag = "Mesures terrain · Menuiseries pro"
    twx, _ = tw(tag, tag_font)
    draw.text(((W - twx) // 2, footer_y + int(H * 0.024)), tag, font=tag_font, fill=(160, 160, 168))

    out_path = f"{out_dir}/{slide['id']}.png"
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def compose_and_zip():
    all_out = []
    for target in IPAD_SIZES:
        out_dir = f"/app/backend/public_downloads/appstore_screenshots_ipad_{target['label']}"
        os.makedirs(out_dir, exist_ok=True)
        print(f"\n▸ {target['human']} → {target['w']}x{target['h']}")
        outs = []
        for s in SLIDES:
            p = compose_ipad(s, target, out_dir)
            if p:
                outs.append(p)
                print(f"  ✅ {os.path.basename(p)} ({os.path.getsize(p)//1024} Ko)")
        zpath = f"/app/backend/public_downloads/appstore_screenshots_ipad_{target['label']}_v114.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in outs:
                z.write(f, os.path.basename(f))
        print(f"  📦 ZIP : {os.path.getsize(zpath)//1024} Ko")
        all_out.append((target, zpath))
    return all_out


if __name__ == "__main__":
    print("=" * 60)
    print("SCREENSHOTS iPad — Version 1.0.24")
    print("=" * 60)
    print("Étape 1/2 : Capture en viewport iPad")
    asyncio.run(capture_all())
    print("\nÉtape 2/2 : Composition et ZIP")
    compose_and_zip()
    print("\n✅ TERMINÉ")
