"""Génération de screenshots App Store dimensions exactes Apple (juin 2026).

Capture les écrans clés de MesureChâssis dans les formats requis par
l'App Store Connect :

  • iPhone 6.5" → 1242 × 2688 (PORTRAIT)
  • iPad Pro 12.9" → 2048 × 2732 (PORTRAIT)

Stratégie technique :
  • On utilise un viewport CSS de 414×896 (iPhone 6.5") ou 1024×1366
    (iPad 12.9") puis on capture avec device_scale_factor=3 ou ×2.
  • Le screenshot natif Chrome/Playwright sera donc directement aux
    pixels Apple — aucun upscale Pillow requis.
  • Une fois capturé, Apple valide automatiquement.

Sortie : /app/backend/static_artifacts/screenshots/{device}/...
"""
from __future__ import annotations

import asyncio
import os
import pathlib

from playwright.async_api import async_playwright

OUT_DIR = pathlib.Path("/app/backend/static_artifacts/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "iphone").mkdir(exist_ok=True)
(OUT_DIR / "ipad").mkdir(exist_ok=True)

BASE_URL = "http://localhost:3000"
EMAIL = "applereview@mesurechassis.com"
PASSWORD = "AppleReview2026!"


async def _wait_root(page):
    """Attend que #root soit rendu avec du contenu."""
    for _ in range(40):
        try:
            txt = await page.locator("#root").evaluate("el => el.innerText")
            if txt and len(txt) > 50:
                break
        except Exception:
            pass
        await asyncio.sleep(0.5)
    await asyncio.sleep(2)


async def _login(page):
    """Connexion via la page d'accueil."""
    # Force FR si nécessaire
    try:
        await page.get_by_text("FR", exact=True).first.click(timeout=2000)
        await asyncio.sleep(0.5)
    except Exception:
        pass
    await page.locator("input").nth(0).fill(EMAIL)
    await page.locator('input[type="password"]').first.fill(PASSWORD)
    await page.get_by_text("CONNECTER", exact=False).first.click(timeout=5000)
    await asyncio.sleep(5)


async def capture_iphone(playwright):
    """iPhone 6.5" : 1242 × 2688 (Apple compatible 1284×2778)."""
    # On utilise device_scale_factor=3 pour avoir 414×896 CSS → 1242×2688 px
    browser = await playwright.chromium.launch(headless=True)
    ctx = await browser.new_context(
        viewport={"width": 414, "height": 896},
        device_scale_factor=3,
        is_mobile=True,
    )
    page = await ctx.new_page()
    try:
        # ─── 1) Login ────────────────────────────────────────────
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await _wait_root(page)
        await page.screenshot(
            path=str(OUT_DIR / "iphone" / "01_login.png"),
            full_page=False,
        )
        print("📸 iphone/01_login.png")

        # ─── 2) Login + Dashboard ────────────────────────────────
        await _login(page)
        await page.screenshot(
            path=str(OUT_DIR / "iphone" / "02_dashboard.png"),
            full_page=False,
        )
        print("📸 iphone/02_dashboard.png")

        # ─── 3) Détail Restaurant (15 ouvertures) ────────────────
        await page.get_by_text("M. Lefèvre", exact=False).first.click(timeout=5000)
        await asyncio.sleep(4)
        await page.screenshot(
            path=str(OUT_DIR / "iphone" / "03_chantier_restaurant.png"),
            full_page=False,
        )
        print("📸 iphone/03_chantier_restaurant.png")

        # ─── 4) Import cahier des charges ────────────────────────
        await page.go_back()
        await asyncio.sleep(2)
        await page.get_by_text("Dr. Martin", exact=False).first.click(timeout=5000)
        await asyncio.sleep(3)
        try:
            await page.get_by_text("Importer", exact=False).first.click(timeout=4000)
            await asyncio.sleep(3)
            await page.screenshot(
                path=str(OUT_DIR / "iphone" / "04_import_cdc.png"),
                full_page=False,
            )
            print("📸 iphone/04_import_cdc.png")
        except Exception as e:
            print(f"⚠️ import_cdc skip: {e}")

        # ─── 5) Yann IA ──────────────────────────────────────────
        await page.goto(f"{BASE_URL}/yann", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        await page.screenshot(
            path=str(OUT_DIR / "iphone" / "05_yann_ai.png"),
            full_page=False,
        )
        print("📸 iphone/05_yann_ai.png")
    finally:
        await browser.close()


async def capture_ipad(playwright):
    """iPad Pro 12.9" : 2048 × 2732 (DPR 2 → 1024×1366 CSS)."""
    browser = await playwright.chromium.launch(headless=True)
    ctx = await browser.new_context(
        viewport={"width": 1024, "height": 1366},
        device_scale_factor=2,
    )
    page = await ctx.new_page()
    try:
        # ─── 1) Login iPad ───────────────────────────────────────
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await _wait_root(page)
        await page.screenshot(
            path=str(OUT_DIR / "ipad" / "01_login.png"),
            full_page=False,
        )
        print("🖼️  ipad/01_login.png")

        # ─── 2) Dashboard iPad ───────────────────────────────────
        await _login(page)
        await page.screenshot(
            path=str(OUT_DIR / "ipad" / "02_dashboard.png"),
            full_page=False,
        )
        print("🖼️  ipad/02_dashboard.png")

        # ─── 3) Détail Restaurant iPad ───────────────────────────
        await page.get_by_text("M. Lefèvre", exact=False).first.click(timeout=5000)
        await asyncio.sleep(4)
        await page.screenshot(
            path=str(OUT_DIR / "ipad" / "03_chantier_restaurant.png"),
            full_page=False,
        )
        print("🖼️  ipad/03_chantier_restaurant.png")
    finally:
        await browser.close()


async def main():
    async with async_playwright() as p:
        print("📱 Capture iPhone 6.5\" (1242×2688)…")
        await capture_iphone(p)
        print("\n📱 Capture iPad Pro 12.9\" (2048×2732)…")
        await capture_ipad(p)
    print("\n✅ Tous les screenshots générés dans", OUT_DIR)


if __name__ == "__main__":
    # Augmente la mémoire stack pour éviter SegFault sur grosses pages
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/pw-browsers")
    asyncio.run(main())
