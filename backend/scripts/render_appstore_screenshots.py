"""Génère les 11 captures App Store en PNG à la dimension exacte iOS.
Utilise Playwright pour rendre le template HTML puis screenshot fullPage.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8001/api/marketing/appstore-screenshot"
OUT = Path("/app/backend/static/promo/appstore_screenshots")
OUT.mkdir(parents=True, exist_ok=True)

# Dimensions exactes App Store Connect (2026)
IPHONE_W, IPHONE_H = 1290, 2796   # iPhone 6.9" (16 Pro Max) — fallback pour 6.5"
IPAD_W, IPAD_H = 2064, 2752       # iPad 13"

TARGETS = []
for i in range(1, 7):
    TARGETS.append(("iphone", i, IPHONE_W, IPHONE_H))
for i in range(1, 6):
    TARGETS.append(("ipad", i, IPAD_W, IPAD_H))


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for device, slide, w, h in TARGETS:
            context = await browser.new_context(viewport={"width": w, "height": h},
                                                 device_scale_factor=1)
            page = await context.new_page()
            url = f"{BASE_URL}?device={device}&slide={slide}"
            await page.goto(url, wait_until="load")
            await page.wait_for_timeout(600)
            out = OUT / f"{device}-{slide:02d}.png"
            await page.screenshot(path=str(out), full_page=False, omit_background=False)
            print(f"✅ {out.name} ({w}×{h})")
            await context.close()
        await browser.close()

    # ZIP tout
    import zipfile
    zip_path = OUT.parent / "appstore_screenshots_pack.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT.iterdir()):
            zf.write(p, arcname=f"appstore_screenshots/{p.name}")
    print(f"\n📦 ZIP créé : {zip_path} ({zip_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
