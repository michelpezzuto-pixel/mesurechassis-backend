"""
Génère l'image de fin de vidéo TikTok MesureChâssis (format 9:16).
Corrige les 3 fautes de la vidéo Runway :
  - Tomragez → Téléchargez
  - l'aplication → l'application
  - MesureChâsse → MesureChâssis

Sortie : /app/backend/public_downloads/endcard-tiktok-1080x1920.png
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads"
OUT_PNG = f"{OUT_DIR}/endcard-tiktok-1080x1920.png"
OUT_HTML = f"{OUT_DIR}/endcard-tiktok.html"

APP_STORE_URL = "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930"


def build_qr_png_b64() -> str:
    """QR code stylisé avec modules arrondis + logo orange central au style App Store."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # H = 30% correction, permet un gros logo au milieu
        box_size=20,
        border=2,
    )
    qr.add_data(APP_STORE_URL)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(
            front_color=(0, 0, 0),
            back_color=(255, 255, 255),
        ),
    ).convert("RGBA")

    # Ajoute un logo central : carré orange avec flèche diagonale (style MesureChâssis)
    logo_size = img.size[0] // 5
    logo = Image.new("RGBA", (logo_size, logo_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(logo)
    # Fond orange arrondi
    corner = logo_size // 5
    draw.rounded_rectangle(
        (0, 0, logo_size, logo_size),
        radius=corner,
        fill=(255, 106, 0, 255),  # orange MesureChâssis
    )
    # Flèche diagonale ↗ (arrows resize)
    arrow_pad = logo_size // 4
    aw = logo_size - 2 * arrow_pad
    # Trait diagonal principal
    draw.line(
        [(arrow_pad, logo_size - arrow_pad), (logo_size - arrow_pad, arrow_pad)],
        fill=(255, 255, 255, 255),
        width=logo_size // 12,
    )
    # Pointe haute droite
    tip = logo_size - arrow_pad
    draw.polygon(
        [
            (tip, arrow_pad),
            (tip - aw // 2, arrow_pad),
            (tip, arrow_pad + aw // 2),
        ],
        fill=(255, 255, 255, 255),
    )
    # Pointe basse gauche
    draw.polygon(
        [
            (arrow_pad, tip),
            (arrow_pad + aw // 2, tip),
            (arrow_pad, tip - aw // 2),
        ],
        fill=(255, 255, 255, 255),
    )

    # Colle le logo au centre du QR code
    cx = (img.size[0] - logo_size) // 2
    cy = (img.size[1] - logo_size) // 2
    img.paste(logo, (cx, cy), logo)

    # Ajoute un cadre blanc arrondi autour du QR (style App Store)
    padding = 60
    W, H = img.size
    canvas = Image.new("RGBA", (W + padding * 2, H + padding * 2), (255, 255, 255, 0))
    canvas_draw = ImageDraw.Draw(canvas)
    canvas_draw.rounded_rectangle(
        (0, 0, canvas.size[0], canvas.size[1]),
        radius=80,
        fill=(255, 255, 255, 255),
    )
    canvas.paste(img, (padding, padding), img)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def build_html(qr_b64: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: 1080px 1920px; margin: 0; }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; }}
  html, body {{
    margin: 0; padding: 0; width: 1080px; height: 1920px;
    background: #000; color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }}
  .qr {{
    width: 620px; height: 620px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 120px;
  }}
  .qr img {{ width: 100%; height: 100%; object-fit: contain; }}
  .apple {{
    width: 100px;
    height: 122px;
    margin-bottom: 60px;
    display: flex; align-items: center; justify-content: center;
  }}
  .apple svg {{ width: 100%; height: 100%; fill: #fff; }}
  .text {{
    text-align: center;
    padding: 0 80px;
  }}
  .text .l1 {{
    font-size: 78px;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -1.5px;
    margin: 0;
  }}
  .text .l2 {{
    font-size: 78px;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -1.5px;
    margin: 8px 0 30px 0;
  }}
  .text .l3 {{
    font-size: 56px;
    font-weight: 400;
    color: rgba(255,255,255,0.85);
    line-height: 1.15;
    margin: 0;
    letter-spacing: -0.5px;
  }}
</style>
</head>
<body>
  <div class="qr"><img src="data:image/png;base64,{qr_b64}" alt="QR"></div>
  <div class="apple">
    <svg viewBox="0 0 384 512" xmlns="http://www.w3.org/2000/svg">
      <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/>
    </svg>
  </div>
  <div class="text">
    <p class="l1">Téléchargez l&rsquo;application</p>
    <p class="l2">MesureChâssis</p>
    <p class="l3">sur l&rsquo;App Store</p>
  </div>
</body>
</html>
"""


async def render():
    os.makedirs(OUT_DIR, exist_ok=True)
    qr_b64 = build_qr_png_b64()
    html = build_html(qr_b64)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=1,
        )
        page = await ctx.new_page()
        await page.goto(f"file://{OUT_HTML}", wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        await page.screenshot(
            path=OUT_PNG, full_page=False, omit_background=False, type="png"
        )
        await browser.close()

    size_kb = os.path.getsize(OUT_PNG) // 1024
    print(f"OK — {OUT_PNG} ({size_kb} Ko, 1080x1920)")


if __name__ == "__main__":
    asyncio.run(render())
