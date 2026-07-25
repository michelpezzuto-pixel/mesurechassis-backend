"""
Animation MP4 mettant en évidence les 6 formats d'export MesureChâssis :
PDF · CSV · Excel · JSON · Virtua · Adou.
Focus visuel sur Virtua & Adou (glow orange + taille supérieure).

Sortie : /app/backend/public_downloads/export-formats-animated.mp4
         (1080x1920, ~5 s, 30fps)
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads"
FRAMES_DIR = "/tmp/exportfmt_frames"
OUT_MP4 = f"{OUT_DIR}/export-formats-animated.mp4"
OUT_HTML = f"{OUT_DIR}/export-formats-animated.html"
FPS = 30
DURATION_S = 5.0
TOTAL_FRAMES = int(FPS * DURATION_S)


def build_html() -> str:
    """
    Animation 5 s :
    - 0.0 s : titre "Partage en 1 clic" apparaît (fade up)
    - 0.7 s : PDF   pop-in
    - 1.0 s : CSV   pop-in
    - 1.3 s : Excel pop-in
    - 1.6 s : JSON  pop-in
    - 2.4 s : VIRTUA (large, glow orange) bounce-in
    - 3.0 s : ADOU  (large, glow orange) bounce-in
    - 3.8 s : phrase "Compatible avec tes logiciels métier" apparaît
    """
    return """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; }
  html, body {
    margin: 0; padding: 0; width: 1080px; height: 1920px;
    background: #000; color: #fff; overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "SF Pro Display", Arial, sans-serif;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
  }

  .title {
    font-size: 92px; font-weight: 900; letter-spacing: -2px;
    text-align: center; margin: 0 0 20px 0; line-height: 1.05;
    opacity: 0; transform: translateY(30px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 100ms forwards;
  }
  .subtitle {
    font-size: 42px; font-weight: 400; letter-spacing: -0.5px;
    color: rgba(255,255,255,0.6); text-align: center;
    margin: 0 0 80px 0;
    opacity: 0; transform: translateY(20px);
    animation: fade-up 400ms cubic-bezier(.2,.8,.3,1) 350ms forwards;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 40px 40px;
    width: 880px;
    padding: 0 40px;
  }

  .pill {
    background: #1c1c1e;
    border: 3px solid #2c2c2e;
    border-radius: 32px;
    padding: 32px 40px;
    display: flex; align-items: center; gap: 24px;
    font-size: 54px; font-weight: 800;
    color: #fff;
    opacity: 0; transform: scale(0.6);
  }
  .pill .badge {
    width: 84px; height: 84px;
    border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 32px; font-weight: 900; letter-spacing: 0.5px;
    flex-shrink: 0;
  }

  /* Standards */
  .pill.pdf   { animation: pop-in 500ms cubic-bezier(.15,1.4,.4,1)  700ms forwards; }
  .pill.csv   { animation: pop-in 500ms cubic-bezier(.15,1.4,.4,1) 1000ms forwards; }
  .pill.excel { animation: pop-in 500ms cubic-bezier(.15,1.4,.4,1) 1300ms forwards; }
  .pill.json  { animation: pop-in 500ms cubic-bezier(.15,1.4,.4,1) 1600ms forwards; }
  .pill.pdf .badge   { background: #E42D2D; }
  .pill.csv .badge   { background: #16A34A; }
  .pill.excel .badge { background: #217346; }
  .pill.json .badge  { background: #F5A623; color: #1c1c1e; }

  /* Highlights — Virtua & Adou */
  .pill.pro {
    grid-column: 1 / -1;
    background: linear-gradient(90deg, rgba(255,106,0,0.15), rgba(255,106,0,0.05));
    border: 3px solid #FF6A00;
    box-shadow: 0 0 40px rgba(255,106,0,0.4);
    font-size: 66px;
    padding: 38px 44px;
  }
  .pill.pro .badge {
    background: #FF6A00;
    width: 100px; height: 100px;
    font-size: 34px;
  }
  .pill.pro .tag {
    margin-left: auto;
    font-size: 26px;
    background: #FF6A00;
    color: #1c1c1e;
    font-weight: 900;
    padding: 8px 16px;
    border-radius: 100px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .pill.virtua { animation: bounce-in 700ms cubic-bezier(.15,1.4,.4,1) 2400ms forwards; }
  .pill.adou   { animation: bounce-in 700ms cubic-bezier(.15,1.4,.4,1) 3000ms forwards; }

  .footer {
    margin-top: 60px;
    font-size: 44px; font-weight: 500;
    color: rgba(255,255,255,0.85);
    text-align: center;
    max-width: 880px;
    opacity: 0; transform: translateY(20px);
    animation: fade-up 500ms cubic-bezier(.2,.8,.3,1) 3800ms forwards;
  }
  .footer strong { color: #FF6A00; }

  @keyframes fade-up { to { opacity: 1; transform: translateY(0); } }
  @keyframes pop-in {
    0%   { opacity: 0; transform: scale(0.6); }
    60%  { opacity: 1; transform: scale(1.08); }
    100% { opacity: 1; transform: scale(1); }
  }
  @keyframes bounce-in {
    0%   { opacity: 0; transform: scale(0.7); }
    55%  { opacity: 1; transform: scale(1.10); }
    100% { opacity: 1; transform: scale(1); }
  }
</style>
</head>
<body>

  <h1 class="title">Partage en 1 clic</h1>
  <p class="subtitle">→ 6 formats · zéro friction</p>

  <div class="grid">
    <div class="pill pdf">
      <div class="badge">PDF</div>
      <span>PDF</span>
    </div>
    <div class="pill csv">
      <div class="badge">CSV</div>
      <span>CSV</span>
    </div>
    <div class="pill excel">
      <div class="badge">XLS</div>
      <span>Excel</span>
    </div>
    <div class="pill json">
      <div class="badge">JSON</div>
      <span>JSON</span>
    </div>

    <div class="pill pro virtua">
      <div class="badge">V</div>
      <span>Virtua</span>
      <span class="tag">Devis</span>
    </div>
    <div class="pill pro adou">
      <div class="badge">A</div>
      <span>Adou</span>
      <span class="tag">Devis</span>
    </div>
  </div>

  <p class="footer">
    Compatible avec <strong>tes logiciels métier</strong>
  </p>

</body>
</html>
"""


async def capture_frames():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    for f in os.listdir(FRAMES_DIR):
        os.remove(os.path.join(FRAMES_DIR, f))
    html = build_html()
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
        await page.wait_for_timeout(50)

        for i in range(TOTAL_FRAMES):
            t_ms = int(i * 1000 / FPS)
            await page.evaluate(f"""
                document.querySelectorAll('*').forEach(el => {{
                    el.getAnimations().forEach(a => {{
                        a.pause();
                        a.currentTime = {t_ms};
                    }});
                }});
            """)
            await page.screenshot(path=f"{FRAMES_DIR}/frame_{i:04d}.png", type="png")
            if i % 15 == 0:
                print(f"  frame {i+1}/{TOTAL_FRAMES}")
        await browser.close()


def encode_mp4():
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{FRAMES_DIR}/frame_%04d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        OUT_MP4,
    ], check=True, capture_output=True)


async def main():
    print("1/2 — Capture frames…")
    await capture_frames()
    print("2/2 — Encodage MP4…")
    encode_mp4()
    print(f"OK — {OUT_MP4} ({os.path.getsize(OUT_MP4)//1024} Ko)")


if __name__ == "__main__":
    asyncio.run(main())
