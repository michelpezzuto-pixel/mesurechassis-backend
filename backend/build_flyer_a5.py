"""Genere l'affiche de prospection MesureChassis - 2 flyers A5 sur 1 page A4.

Approche : HTML/CSS -> Chromium headless (Playwright) -> PDF pret a imprimer.
Format sortie : A4 paysage (297 x 210 mm) contenant 2 flyers A5 identiques
cote a cote (148 x 210 mm chacun) avec reperes de coupe au centre.

Utilisation :
    cd /app/backend && python build_flyer_a5.py

Sortie :
    /app/backend/public_downloads/flyer_a4_2up.pdf   (a imprimer + decouper)
    /app/backend/public_downloads/flyer_a4_2up.png   (apercu haute def)
    /app/backend/public_downloads/flyer_a5_single.pdf (version 1 flyer A5)
"""
from __future__ import annotations

import asyncio
import base64
import io
import os

import qrcode
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads"
os.makedirs(OUT_DIR, exist_ok=True)

# ======================================================================
# QR CODE - genere en base64 pour etre embarque dans l'HTML
# ======================================================================
QR_URL = "https://mesurechassis.com"


def _qr_data_uri(url: str) -> str:
    """Genere un QR code haute resolution en data URI (PNG base64)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0A0C", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


QR_DATA_URI = _qr_data_uri(QR_URL)


# ======================================================================
# HTML - un seul flyer A5 (contenu reutilise pour les 2 copies)
# ======================================================================
FLYER_HTML = f"""
<div class="flyer">
  <div class="card">
    <!-- HEADER -->
    <div class="header">
      <div>
        <div class="brand">Mesure<span class="brand-accent">Châssis</span></div>
        <div class="brand-tag">L'app terrain des menuisiers</div>
      </div>
      <div class="badge-be">
        <span class="flag"></span>
        Made in Belgium
      </div>
    </div>

    <!-- HERO -->
    <div class="hero">
      <div class="hero-eyebrow">Menuisiers pros - Wallonie - Bruxelles - Flandre</div>
      <div class="hero-title">
        Fini les carnets<br>
        perdus dans<br>
        le camion. <em>Enfin.</em>
      </div>
      <div class="hero-sub">
        Photographiez un cahier des charges, l'IA extrait vos 22 fenêtres
        en 45 secondes. Vous validez sur place, vous envoyez le devis.
      </div>
    </div>

    <!-- FREE BANNER -->
    <div class="free-banner">
      <div class="free-banner-eyebrow">Zero risque</div>
      <div class="free-banner-headline">100% GRATUIT</div>
      <div class="free-banner-detail">Sans carte bancaire - Sans engagement - Toutes fonctions incluses</div>
    </div>

    <!-- 3 ARGUMENTS -->
    <div class="args">
      <div class="arg">
        <div class="arg-icon">AI</div>
        <div class="arg-title">Relevé intelligent</div>
        <div class="arg-desc">L'IA lit vos cahiers des charges PDF et extrait toutes les ouvertures.</div>
      </div>
      <div class="arg">
        <div class="arg-icon">&#8595;</div>
        <div class="arg-title">Export en 1 clic</div>
        <div class="arg-desc">PDF client, Excel devis, CSV ERP. Directement depuis le chantier.</div>
      </div>
      <div class="arg">
        <div class="arg-icon">&#8226;</div>
        <div class="arg-title">Chantier hors-ligne</div>
        <div class="arg-desc">Cave, sous-sol, sans 4G : ça marche. Synchro auto au retour.</div>
      </div>
    </div>

    <!-- QR BLOCK -->
    <div class="qr-block">
      <img class="qr-img" src="{QR_DATA_URI}" alt="QR Code MesureChâssis">
      <div class="qr-copy">
        <div class="qr-cta">Scannez.<br><em>Essayez.</em><br>C'est gratuit.</div>
        <div class="qr-sub">mesurechassis.com - Disponible sur iPhone &amp; iPad. Version Android bientôt.</div>
        <div class="qr-badges">
          <span class="qr-badge">iOS</span>
          <span class="qr-badge">iPad</span>
          <span class="qr-badge">RGPD</span>
        </div>
      </div>
    </div>

    <!-- SIGNATURE -->
    <div class="sig">
      <div class="sig-avatar">MP</div>
      <div class="sig-copy">
        <div class="sig-line1">Michel Pezzuto - menuisier &amp; fondateur</div>
        <div class="sig-line2">Une question ? Je réponds directement, en Belge, sans robot.</div>
      </div>
      <div class="sig-phone">0496 65 00 32</div>
    </div>

    <!-- FOOTER -->
    <div class="footer">
      <div class="footer-teaser">Conçu par un menuisier, pour les menuisiers</div>
      <div class="footer-web">
        <strong>mesurechassis.com</strong>
      </div>
    </div>
  </div>
</div>
"""


# ======================================================================
# PAGE A4 : 2 flyers A5 cote a cote + reperes de coupe
# ======================================================================
HTML_A4 = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<title>Flyer prospection MesureChassis - A4 (2 A5)</title>
<style>
  @page {{
    size: 297mm 210mm;
    margin: 0;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  body {{
    width: 297mm;
    height: 210mm;
    background: #FFFFFF;
    position: relative;
    display: flex;
    flex-direction: row;
  }}

  /* Chaque flyer occupe exactement 148.5mm de large sur 210mm de haut */
  .flyer {{
    width: 148.5mm;
    height: 210mm;
    position: relative;
    overflow: hidden;
    color: #F5F5F5;
    background: #0A0A0C;
  }}

  /* Halos orange decoratifs */
  .flyer::before {{
    content: "";
    position: absolute;
    top: -60mm; right: -50mm;
    width: 160mm; height: 160mm;
    background: radial-gradient(circle, rgba(255,90,0,0.20) 0%, transparent 60%);
    z-index: 0;
  }}
  .flyer::after {{
    content: "";
    position: absolute;
    bottom: -35mm; left: -35mm;
    width: 120mm; height: 120mm;
    background: radial-gradient(circle, rgba(255,90,0,0.12) 0%, transparent 60%);
    z-index: 0;
  }}

  .card {{
    position: absolute;
    inset: 0;
    padding: 7mm 8mm;
    z-index: 1;
    display: flex;
    flex-direction: column;
  }}

  /* HEADER */
  .header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 3mm;
    border-bottom: 1px solid rgba(255,255,255,0.10);
  }}
  .brand {{
    font-weight: 900;
    font-size: 20px;
    letter-spacing: -0.5px;
    color: #FFFFFF;
  }}
  .brand-accent {{ color: #FF5A00; }}
  .brand-tag {{
    font-size: 8.5px;
    color: #A8A8B0;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    margin-top: 1mm;
    font-weight: 500;
  }}
  .flag {{
    background: linear-gradient(180deg, #000 33%, #FDDA24 33% 66%, #EF3340 66%);
    width: 14px; height: 10px;
    border-radius: 2px;
    display: inline-block;
    vertical-align: middle;
  }}
  .badge-be {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.14);
    padding: 4px 9px;
    border-radius: 20px;
    font-size: 8.5px;
    font-weight: 700;
    letter-spacing: 0.4px;
    color: #F5F5F5;
    text-transform: uppercase;
  }}

  /* HERO */
  .hero {{ margin-top: 5mm; }}
  .hero-eyebrow {{
    font-size: 9px;
    color: #FF5A00;
    letter-spacing: 2px;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 3mm;
  }}
  .hero-title {{
    font-weight: 900;
    font-size: 26px;
    line-height: 1.05;
    letter-spacing: -0.8px;
    color: #FFFFFF;
  }}
  .hero-title em {{
    font-style: normal;
    color: #FF5A00;
  }}
  .hero-sub {{
    margin-top: 3mm;
    font-size: 11.5px;
    line-height: 1.45;
    color: #C4C4C8;
    font-weight: 400;
  }}

  /* FREE BANNER */
  .free-banner {{
    margin: 5mm 0;
    background: #FF5A00;
    border-radius: 10px;
    padding: 4.5mm 5mm;
    color: #0A0A0C;
    position: relative;
    box-shadow: 0 6px 24px rgba(255,90,0,0.30);
  }}
  .free-banner-eyebrow {{
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    opacity: 0.9;
  }}
  .free-banner-headline {{
    font-weight: 900;
    font-size: 26px;
    line-height: 1;
    letter-spacing: -0.5px;
    margin-top: 1.5mm;
  }}
  .free-banner-detail {{
    font-size: 9.5px;
    font-weight: 700;
    margin-top: 2mm;
    line-height: 1.4;
  }}

  /* 3 ARGUMENTS */
  .args {{
    display: flex;
    gap: 2.5mm;
    margin-bottom: 4mm;
  }}
  .arg {{
    flex: 1;
    background: #131318;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 3mm 2.8mm;
  }}
  .arg-icon {{
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: rgba(255,90,0,0.18);
    color: #FF5A00;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 900;
    margin-bottom: 2mm;
  }}
  .arg-title {{
    font-size: 10.5px;
    font-weight: 800;
    color: #F5F5F5;
    line-height: 1.15;
    margin-bottom: 1.2mm;
  }}
  .arg-desc {{
    font-size: 8.5px;
    color: #9EA1AA;
    line-height: 1.35;
  }}

  /* QR BLOCK */
  .qr-block {{
    display: flex;
    gap: 4mm;
    align-items: center;
    padding: 3.5mm;
    background: #FFFFFF;
    border-radius: 10px;
    margin-bottom: 3.5mm;
  }}
  .qr-img {{
    width: 38mm; height: 38mm;
    background: #fff;
    flex-shrink: 0;
  }}
  .qr-copy {{ flex: 1; }}
  .qr-cta {{
    font-weight: 900;
    font-size: 14px;
    color: #0A0A0C;
    line-height: 1.15;
    letter-spacing: -0.3px;
  }}
  .qr-cta em {{
    font-style: normal;
    color: #FF5A00;
  }}
  .qr-sub {{
    font-size: 9px;
    color: #4B4B54;
    margin-top: 2mm;
    line-height: 1.35;
  }}
  .qr-badges {{
    display: flex;
    gap: 4px;
    margin-top: 2.5mm;
  }}
  .qr-badge {{
    background: #0A0A0C;
    color: #fff;
    font-size: 8px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 12px;
    letter-spacing: 0.3px;
  }}

  /* SIGNATURE */
  .sig {{
    display: flex;
    align-items: center;
    gap: 3mm;
    padding: 3mm 3.5mm;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    margin-bottom: 3mm;
  }}
  .sig-avatar {{
    width: 30px; height: 30px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FF5A00, #D94800);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 12px;
    flex-shrink: 0;
  }}
  .sig-copy {{ flex: 1; }}
  .sig-line1 {{
    font-size: 10.5px;
    font-weight: 700;
    color: #F5F5F5;
    line-height: 1.15;
  }}
  .sig-line2 {{
    font-size: 8.5px;
    color: #A8A8B0;
    margin-top: 1mm;
    line-height: 1.3;
  }}
  .sig-phone {{
    font-weight: 900;
    font-size: 13px;
    color: #FF5A00;
    letter-spacing: -0.3px;
    white-space: nowrap;
  }}

  /* FOOTER */
  .footer {{
    margin-top: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 2.5mm;
    border-top: 1px solid rgba(255,255,255,0.10);
    font-size: 8px;
    color: #7A7A80;
  }}
  .footer-teaser {{
    color: #FF5A00;
    font-weight: 700;
    letter-spacing: 0.2px;
  }}
  .footer-web strong {{ color: #F5F5F5; font-weight: 600; }}

  /* REPERES DE COUPE (marques au centre entre les deux flyers) */
  .cut-guides {{
    position: absolute;
    top: 0;
    left: 148.5mm;
    width: 0;
    height: 100%;
    z-index: 10;
    pointer-events: none;
  }}
  .cut-line {{
    position: absolute;
    left: -0.15mm;
    top: 5mm;
    bottom: 5mm;
    width: 0.3mm;
    background-image: linear-gradient(to bottom, #FFFFFF 50%, transparent 50%);
    background-size: 100% 3mm;
    opacity: 0.35;
  }}
  .cut-mark {{
    position: absolute;
    width: 5mm;
    height: 0.3mm;
    background: #000;
    left: -2.5mm;
  }}
  .cut-mark.top {{ top: 0; }}
  .cut-mark.bottom {{ bottom: 0; }}
</style></head>
<body>
  {FLYER_HTML}
  {FLYER_HTML}
  <div class="cut-guides">
    <div class="cut-mark top"></div>
    <div class="cut-line"></div>
    <div class="cut-mark bottom"></div>
  </div>
</body></html>"""


# ======================================================================
# HTML - version A5 seule (au cas ou l'utilisateur veut 1 seul flyer)
# ======================================================================
HTML_A5_SINGLE = HTML_A4.replace(
    "@page {\n    size: 297mm 210mm;",
    "@page {\n    size: 148.5mm 210mm;",
).replace(
    "width: 297mm;\n    height: 210mm;",
    "width: 148.5mm;\n    height: 210mm;",
).replace(
    f"  {FLYER_HTML}\n  {FLYER_HTML}\n",
    f"  {FLYER_HTML}\n",
).replace(
    '<div class="cut-guides">',
    '<div class="cut-guides" style="display:none">',
)


# ======================================================================
# RENDU via Playwright
# ======================================================================
async def render(html: str, out_pdf: str, out_png: str | None, w_mm: float, h_mm: float):
    html_path = out_pdf.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # 1mm = 3.78 px @ 96dpi ; on prend 4 pour un peu de marge
        viewport_w = int(round(w_mm * 3.78))
        viewport_h = int(round(h_mm * 3.78))
        ctx = await browser.new_context(
            viewport={"width": viewport_w, "height": viewport_h},
            device_scale_factor=3,
        )
        page = await ctx.new_page()
        await page.goto(f"file://{html_path}", wait_until="domcontentloaded")
        await page.wait_for_timeout(800)

        if out_png:
            await page.screenshot(
                path=out_png,
                full_page=True,
                type="png",
                omit_background=False,
            )

        await page.pdf(
            path=out_pdf,
            width=f"{w_mm}mm",
            height=f"{h_mm}mm",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()


async def main():
    # 1. Version A4 avec 2 flyers cote a cote (celle demandee par l'utilisateur)
    a4_pdf = f"{OUT_DIR}/flyer_a4_2up.pdf"
    a4_png = f"{OUT_DIR}/flyer_a4_2up.png"
    await render(HTML_A4, a4_pdf, a4_png, w_mm=297, h_mm=210)
    print(f"OK A4 PDF  : {a4_pdf}  ({os.path.getsize(a4_pdf) // 1024} Ko)")
    print(f"OK A4 PNG  : {a4_png}  ({os.path.getsize(a4_png) // 1024} Ko)")

    # 2. Version A5 seule (bonus)
    a5_pdf = f"{OUT_DIR}/flyer_a5_single.pdf"
    await render(HTML_A5_SINGLE, a5_pdf, None, w_mm=148.5, h_mm=210)
    print(f"OK A5 PDF  : {a5_pdf}  ({os.path.getsize(a5_pdf) // 1024} Ko)")


if __name__ == "__main__":
    asyncio.run(main())
