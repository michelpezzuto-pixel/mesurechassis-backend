"""
Génère une VIDÉO MP4 animée pour la fin de la vidéo TikTok MesureChâssis.
Texte cascade (fade + slide up) avec "CHÂSSIS" en orange.

Sortie : /app/backend/public_downloads/endcard-tiktok-animated.mp4
          (1080x1920, 3.5 s, ~1-2 Mo)

Rendu via Playwright (capture frame par frame) + FFmpeg (encodage MP4).
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import subprocess
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads"
FRAMES_DIR = "/tmp/endcard_frames"
OUT_MP4 = f"{OUT_DIR}/endcard-tiktok-animated.mp4"
OUT_HTML = f"{OUT_DIR}/endcard-tiktok-animated.html"

APP_STORE_URL = "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930"
FPS = 30
DURATION_S = 3.5
TOTAL_FRAMES = int(FPS * DURATION_S)


def build_qr_png_b64() -> str:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=2,
    )
    qr.add_data(APP_STORE_URL)
    qr.make(fit=True)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(front_color=(0, 0, 0), back_color=(255, 255, 255)),
    ).convert("RGBA")
    # Logo central orange
    lsz = img.size[0] // 5
    logo = Image.new("RGBA", (lsz, lsz), (255, 255, 255, 0))
    ld = ImageDraw.Draw(logo)
    ld.rounded_rectangle((0, 0, lsz, lsz), radius=lsz // 5, fill=(255, 106, 0, 255))
    pad = lsz // 4
    aw = lsz - 2 * pad
    ld.line([(pad, lsz - pad), (lsz - pad, pad)], fill=(255, 255, 255, 255), width=lsz // 12)
    tip = lsz - pad
    ld.polygon([(tip, pad), (tip - aw // 2, pad), (tip, pad + aw // 2)], fill=(255, 255, 255, 255))
    ld.polygon([(pad, tip), (pad + aw // 2, tip), (pad, tip - aw // 2)], fill=(255, 255, 255, 255))
    cx = (img.size[0] - lsz) // 2
    cy = (img.size[1] - lsz) // 2
    img.paste(logo, (cx, cy), logo)
    # Cadre blanc arrondi
    p = 60
    W, H = img.size
    cv = Image.new("RGBA", (W + p * 2, H + p * 2), (255, 255, 255, 0))
    cd = ImageDraw.Draw(cv)
    cd.rounded_rectangle((0, 0, cv.size[0], cv.size[1]), radius=80, fill=(255, 255, 255, 255))
    cv.paste(img, (p, p), img)
    buf = io.BytesIO()
    cv.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def build_html(qr_b64: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; }}
  html, body {{
    margin: 0; padding: 0; width: 1080px; height: 1920px;
    background: #000; color: #fff; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "SF Pro Display", Arial, sans-serif;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }}

  /* ═════ QR ═════ */
  .qr {{
    width: 620px; height: 620px; margin-bottom: 100px;
    opacity: 0; transform: scale(0.85);
    animation: qr-in 700ms cubic-bezier(.2,.9,.3,1.2) 100ms forwards;
  }}
  @keyframes qr-in {{
    to {{ opacity: 1; transform: scale(1); }}
  }}
  .qr img {{ width: 100%; height: 100%; object-fit: contain; }}

  /* ═════ APPLE ═════ */
  .apple {{
    width: 100px; height: 122px; margin-bottom: 50px;
    display: flex; align-items: center; justify-content: center;
    opacity: 0; transform: translateY(30px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 700ms forwards;
  }}
  .apple svg {{ width: 100%; height: 100%; fill: #fff; }}

  /* ═════ TEXTES ═════ */
  .text {{ text-align: center; padding: 0 60px; }}

  .l1 {{
    font-size: 68px; font-weight: 500; letter-spacing: -1px;
    color: rgba(255,255,255,0.9); margin: 0 0 30px 0;
    opacity: 0; transform: translateY(30px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 1100ms forwards;
  }}

  .l2 {{
    font-size: 132px; font-weight: 900; line-height: 1;
    margin: 0 0 40px 0; letter-spacing: -3px;
    text-transform: uppercase;
  }}
  .l2 .white {{
    color: #fff;
    display: inline-block;
    opacity: 0; transform: translateY(40px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 1500ms forwards;
  }}
  .l2 .orange {{
    color: #FF6A00;
    display: inline-block;
    opacity: 0; transform: scale(0.7);
    animation: bounce-in 700ms cubic-bezier(.15,1.4,.4,1) 1900ms forwards;
    text-shadow: 0 0 40px rgba(255,106,0,0.4);
  }}

  .l3 {{
    font-size: 52px; font-weight: 400;
    color: rgba(255,255,255,0.7); letter-spacing: -0.5px;
    margin: 0;
    opacity: 0; transform: translateY(20px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 2500ms forwards;
  }}

  @keyframes fade-up {{
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes bounce-in {{
    0% {{ opacity: 0; transform: scale(0.7); }}
    60% {{ opacity: 1; transform: scale(1.08); }}
    100% {{ opacity: 1; transform: scale(1); }}
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
    <p class="l2"><span class="white">MESURE</span><span class="orange">CHÂSSIS</span></p>
    <p class="l3">sur l&rsquo;App Store</p>
  </div>
</body>
</html>
"""


async def capture_frames():
    """Capture frames from the animated HTML at fixed timesteps."""
    os.makedirs(FRAMES_DIR, exist_ok=True)
    # Clean previous
    for f in os.listdir(FRAMES_DIR):
        os.remove(os.path.join(FRAMES_DIR, f))

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
        # Freeze animations at each timestep using CSS animation-play-state
        # Actually simpler: use Chrome DevTools Protocol to set animationsPlaybackRate
        client = await page.context.new_cdp_session(page)
        await page.goto(f"file://{OUT_HTML}", wait_until="domcontentloaded")

        # Attente courte pour laisser le rendu se stabiliser
        await page.wait_for_timeout(50)

        for i in range(TOTAL_FRAMES):
            t_ms = int(i * 1000 / FPS)
            # Advance animations to specific time via CDP
            try:
                await client.send("Animation.setPlaybackRate", {"playbackRate": 0})
            except Exception:
                pass
            # Simpler alternative: use JS to set currentTime on all animations
            await page.evaluate(f"""
                document.querySelectorAll('*').forEach(el => {{
                    el.getAnimations().forEach(a => {{
                        a.pause();
                        a.currentTime = {t_ms};
                    }});
                }});
            """)
            frame_path = f"{FRAMES_DIR}/frame_{i:04d}.png"
            await page.screenshot(path=frame_path, full_page=False, omit_background=False, type="png")
            if i % 15 == 0:
                print(f"  frame {i+1}/{TOTAL_FRAMES}")

        await browser.close()


def encode_mp4():
    """Combine frames into MP4 using FFmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{FRAMES_DIR}/frame_%04d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "20",
        "-movflags", "+faststart",
        OUT_MP4,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


async def main():
    print("1/2 — Capture des frames…")
    await capture_frames()
    print("2/2 — Encodage MP4…")
    encode_mp4()
    size_kb = os.path.getsize(OUT_MP4) // 1024
    print(f"OK — {OUT_MP4} ({size_kb} Ko, {DURATION_S}s @ {FPS}fps)")


if __name__ == "__main__":
    asyncio.run(main())
