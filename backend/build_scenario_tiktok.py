"""
Génère un scénario PDF imprimable pour le tournage des 5 vidéos TikTok
"Vrai ou Faux" MesureChâssis.

Sortie : /app/backend/public_downloads/scenario-tournage-tiktok.pdf (A4, ~10 pages)

Usage :
    python /app/backend/build_scenario_tiktok.py
"""
from __future__ import annotations

import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "/app/backend/public_downloads"
OUT_PDF = f"{OUT_DIR}/scenario-tournage-tiktok.pdf"
OUT_HTML = f"{OUT_DIR}/scenario-tournage-tiktok.html"


# ─────────────────────────────────────────────────────────────────
# 5 SCÉNARIOS "VRAI OU FAUX" — scripts mot pour mot
# ─────────────────────────────────────────────────────────────────
SCENARIOS = [
    {
        "num": 1,
        "titre": "Le devis en 2 heures ? FAUX",
        "hook_visuel": "Tu es au chantier, tablette à la main, tu regardes ta montre.",
        "question": "Faire un devis châssis, ça prend 2 heures ?",
        "reponse": "FAUX",
        "voice_off": [
            ("0-1 s", "*Tu marches vers la caméra, casque de chantier, tablette à la main*"),
            ("1-3 s", "« Faire un devis châssis correctement, ça prend 2 heures ? »"),
            ("3-4 s", "« FAUX. »  *Tu secoues la tête, geste ferme*"),
            ("5-7 s", "« Avec MesureChâssis : 30 secondes chrono. »"),
            ("7-8 s", "« Prise de cotes, calcul auto, PDF client — signé sur place. »"),
            ("8-10 s", "« Le futur du devis, c'est maintenant. » *Sourire caméra*"),
        ],
        "bullets_ecran": [
            "30 secondes chrono",
            "PDF client généré auto",
            "Logo perso intégré",
            "Envoi WhatsApp direct",
            "Signature sur place",
        ],
        "hashtags": "#menuiserie #artisan #chantier #devis #productivite",
    },
    {
        "num": 2,
        "titre": "Un trapèze en 4 mesures ? FAUX",
        "hook_visuel": "Tu montres avec le doigt un châssis en trapèze au mur.",
        "question": "Un châssis en trapèze, il faut 4 mesures ?",
        "reponse": "FAUX",
        "voice_off": [
            ("0-1 s", "*Tu pointes un châssis trapèze sur le mur, expression sérieuse*"),
            ("1-3 s", "« Sur un trapèze, la plupart prennent 4 mesures... »"),
            ("3-4 s", "« FAUX. »  *Regard caméra*"),
            ("5-7 s", "« Il en faut 6. Sinon retour chantier garanti. »"),
            ("7-8 s", "« La diagonale, l'angle... les 2 mesures oubliées. »"),
            ("8-10 s", "« MesureChâssis les demande automatiquement. »"),
        ],
        "bullets_ecran": [
            "Larg. haut",
            "Larg. milieu",
            "Larg. bas",
            "Hauteur G / M / D",
            "+ Diagonale",
            "+ Angle incliné",
        ],
        "hashtags": "#menuisier #chassis #artisan #belgique #precision",
    },
    {
        "num": 3,
        "titre": "Une erreur de cote = 400 € ? FAUX",
        "hook_visuel": "Plan large sur un chantier, tu ramasses un châssis mal dimensionné.",
        "question": "Une erreur de mesure, ça coûte 400 € ?",
        "reponse": "FAUX",
        "voice_off": [
            ("0-1 s", "*Tu poses un châssis avec un air désabusé*"),
            ("1-3 s", "« Une erreur de mesure, ça coûte 400 € ? »"),
            ("3-4 s", "« FAUX. » *Petit sourire ironique*"),
            ("4-6 s", "« 1 200 €. En moyenne. Matière, main-d'œuvre, retour. »"),
            ("6-8 s", "« Sur 20 chantiers par an, ça fait 24 000 € qui partent. »"),
            ("8-10 s", "« Une app qui bloque les erreurs = ton assurance vie. »"),
        ],
        "bullets_ecran": [
            "Matière refaite : 450 €",
            "Main-d'œuvre : 600 €",
            "Retour chantier : 150 €",
            "Client remise : -12 %",
            "Total moyen : 1 200 €",
        ],
        "hashtags": "#menuiserie #erreur #chantier #chassis #artisan",
    },
    {
        "num": 4,
        "titre": "TVA 21 % obligatoire ? FAUX",
        "hook_visuel": "Tu tapes sur ta calculatrice ou tablette avec conviction.",
        "question": "Sur un devis rénovation, TVA à 21 % ?",
        "reponse": "FAUX",
        "voice_off": [
            ("0-1 s", "*Tu montres ta tablette avec un devis à l'écran*"),
            ("1-3 s", "« En rénovation, tu factures à 21 % de TVA ? »"),
            ("3-4 s", "« FAUX. » *Regard direct*"),
            ("4-6 s", "« Logement +10 ans, en Belgique, c'est 6 %. »"),
            ("6-8 s", "« 80 % des artisans oublient de cocher la case. »"),
            ("8-10 s", "« Client économise 15 %. Ton devis passe direct. »"),
        ],
        "bullets_ecran": [
            "Rénovation logement +10 ans",
            "TVA 6 % au lieu de 21 %",
            "Case à cocher dans le devis",
            "Économie client : -15 %",
            "Devis signé + vite",
        ],
        "hashtags": "#tva #belgique #renovation #artisan #hack",
    },
    {
        "num": 5,
        "titre": "Prendre des cotes au crayon ? DANGEREUX",
        "hook_visuel": "Plan sur des cotes griffonnées au crayon sur un mur.",
        "question": "Noter les cotes au crayon sur le mur, c'est safe ?",
        "reponse": "FAUX",
        "voice_off": [
            ("0-1 s", "*Tu passes un chiffon sur un mur, les cotes s'effacent*"),
            ("1-3 s", "« Tu notes tes cotes au crayon sur le mur ? »"),
            ("3-4 s", "« FAUX bon plan. » *Grimace*"),
            ("4-6 s", "« Un coup de karcher, un stagiaire... tout est perdu. »"),
            ("6-8 s", "« 3 jours de retour chantier. Client qui râle. »"),
            ("8-10 s", "« Cloud + photo automatique. Le seul vrai backup. »"),
        ],
        "bullets_ecran": [
            "Papier = perdable",
            "Crayon = effaçable",
            "Photos galerie = introuvables",
            "Cloud sécurisé = infaillible",
            "PDF client = pro",
        ],
        "hashtags": "#menuisier #chantier #digital #chassis #productivite",
    },
]


def build_html() -> str:
    """Génère le HTML complet du scénario."""
    scenarios_html = ""
    for s in SCENARIOS:
        vo_rows = "".join(
            f'<tr><td class="t">{t}</td><td class="v">{v}</td></tr>'
            for t, v in s["voice_off"]
        )
        bullets = "".join(
            f'<li>✅ {b}</li>' for b in s["bullets_ecran"]
        )
        scenarios_html += f"""
<section class="scenario">
  <div class="header">
    <div class="num">{s['num']:02d}</div>
    <h2>{s['titre']}</h2>
  </div>

  <div class="hook">
    🎬 <strong>Setup visuel :</strong> {s['hook_visuel']}
  </div>

  <h3>🎙️ Voice-off &amp; direction (mot pour mot)</h3>
  <table class="voxtable">
    <thead>
      <tr><th style="width:65px">Temps</th><th>Ce que tu dis / fais</th></tr>
    </thead>
    <tbody>{vo_rows}</tbody>
  </table>

  <div class="two-col">
    <div class="col">
      <h3>📱 Textes overlay à l'écran</h3>
      <ul class="bullets">{bullets}</ul>
    </div>
    <div class="col">
      <h3>#️⃣ Hashtags TikTok</h3>
      <p class="hashtags">{s['hashtags']}</p>
      <h3 style="margin-top:16px">🎯 Caption post</h3>
      <p class="caption">« {s['question']} »<br>Réponse dans la vidéo 👇</p>
    </div>
  </div>
</section>
"""

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>MesureChâssis · Kit tournage TikTok</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  html, body {{
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1c1c1e; background: #fff;
    font-size: 10.5pt; line-height: 1.5;
  }}

  /* ═════ COUVERTURE ═════ */
  .cover {{
    height: 297mm;
    padding: 30mm 22mm;
    background: linear-gradient(160deg, #001B44 0%, #003580 55%, #005BA6 100%);
    color: #fff;
    page-break-after: always;
    display: flex; flex-direction: column; justify-content: space-between;
    position: relative; overflow: hidden;
  }}
  .cover::before {{
    content: ""; position: absolute; right: -80mm; top: -60mm;
    width: 180mm; height: 180mm; border-radius: 50%;
    background: rgba(0,200,83,0.15);
  }}
  .cover-logo {{ font-size: 12pt; font-weight: 700; letter-spacing: 2px; position: relative; z-index: 2; }}
  .cover-eyebrow {{
    font-size: 10pt; text-transform: uppercase; letter-spacing: 3px;
    color: #00C853; font-weight: 700; margin-bottom: 8mm; position: relative; z-index: 2;
  }}
  .cover-title {{
    font-size: 34pt; line-height: 1.05; font-weight: 800;
    margin: 0 0 8mm; position: relative; z-index: 2;
  }}
  .cover-title em {{ color: #00C853; font-style: normal; }}
  .cover-subtitle {{
    font-size: 13pt; line-height: 1.5; font-weight: 400;
    color: rgba(255,255,255,0.85); max-width: 130mm; margin: 0 0 18mm;
    position: relative; z-index: 2;
  }}
  .cover-meta {{
    display: flex; gap: 14mm; position: relative; z-index: 2;
    font-size: 9.5pt; color: rgba(255,255,255,0.7);
  }}
  .cover-meta strong {{ display: block; color: #fff; font-size: 20pt; font-weight: 700; margin-bottom: 1mm; }}
  .cover-footer {{
    font-size: 9pt; color: rgba(255,255,255,0.6);
    border-top: 1px solid rgba(255,255,255,0.15); padding-top: 4mm;
    position: relative; z-index: 2;
  }}

  /* ═════ CHECKLIST ═════ */
  .checklist {{
    padding: 20mm 22mm;
    page-break-after: always;
  }}
  .checklist h1 {{
    font-size: 24pt; font-weight: 800; margin: 0 0 4mm;
    color: #003580;
  }}
  .checklist .sub {{ font-size: 11pt; color: #6c6c70; margin: 0 0 10mm; }}
  .check-block {{
    background: #F5F7FA; padding: 8mm; border-radius: 6px;
    border-left: 4px solid #00C853; margin-bottom: 6mm;
  }}
  .check-block h3 {{ margin: 0 0 4mm; font-size: 12pt; color: #003580; }}
  .check-block ul {{ margin: 0; padding-left: 18px; }}
  .check-block li {{ margin: 3mm 0; font-size: 10.5pt; color: #2c2c2e; line-height: 1.5; }}
  .check-block strong {{ color: #003580; }}

  /* ═════ SCÉNARIO ═════ */
  .scenario {{
    padding: 18mm 20mm;
    page-break-after: always;
  }}
  .scenario .header {{
    display: flex; align-items: center; gap: 6mm;
    border-bottom: 3px solid #003580; padding-bottom: 5mm; margin-bottom: 6mm;
  }}
  .scenario .num {{
    font-size: 38pt; font-weight: 900;
    background: linear-gradient(135deg, #003580, #00C853);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1; letter-spacing: -2px;
  }}
  .scenario h2 {{
    font-size: 20pt; font-weight: 700; margin: 0; line-height: 1.15;
    color: #1c1c1e; flex: 1;
  }}
  .hook {{
    background: #FFF3CD; border-left: 4px solid #F5A623;
    padding: 4mm 6mm; border-radius: 4px;
    font-size: 10pt; color: #7A5C00; margin-bottom: 6mm;
  }}
  .scenario h3 {{
    font-size: 10.5pt; font-weight: 700; margin: 6mm 0 3mm;
    color: #003580; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .voxtable {{
    width: 100%; border-collapse: collapse;
    background: #F5F7FA; border-radius: 6px; overflow: hidden;
  }}
  .voxtable th {{
    background: #003580; color: #fff; font-size: 9pt;
    padding: 3mm 4mm; text-align: left; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .voxtable td {{
    padding: 3mm 4mm; font-size: 10pt; vertical-align: top;
    border-top: 1px solid #E5E7EB;
  }}
  .voxtable td.t {{
    font-weight: 700; color: #003580; white-space: nowrap;
    font-family: "SF Mono", Monaco, Consolas, monospace; font-size: 9pt;
  }}
  .voxtable td.v {{ color: #2c2c2e; line-height: 1.5; }}
  .two-col {{
    display: flex; gap: 8mm; margin-top: 6mm;
  }}
  .two-col .col {{ flex: 1; }}
  .bullets {{
    list-style: none; padding: 0; margin: 0;
    background: #F0FBF3; border-left: 4px solid #00C853;
    padding: 4mm 6mm; border-radius: 4px;
  }}
  .bullets li {{ padding: 1.5mm 0; font-size: 10pt; color: #2c2c2e; }}
  .hashtags {{
    background: #F5F7FA; padding: 3mm 5mm; border-radius: 4px;
    font-size: 9.5pt; color: #003580; font-family: "SF Mono", Monaco, Consolas, monospace;
    word-wrap: break-word; margin: 0;
  }}
  .caption {{
    background: #FDF2F2; padding: 3mm 5mm; border-radius: 4px;
    border-left: 4px solid #D0021B; margin: 0;
    font-size: 9.5pt; color: #A00013; font-style: italic;
  }}

  /* ═════ APRÈS TOURNAGE ═════ */
  .post {{
    padding: 20mm 22mm;
    background: linear-gradient(160deg, #F5F7FA 0%, #E8EEF5 100%);
    min-height: 297mm;
  }}
  .post h1 {{
    font-size: 24pt; font-weight: 800; margin: 0 0 4mm;
    color: #003580;
  }}
  .post .lead {{ font-size: 12pt; color: #3a3a3c; margin-bottom: 10mm; line-height: 1.55; }}
  .step {{
    background: #fff; border-radius: 8px; padding: 6mm 8mm;
    margin-bottom: 5mm; box-shadow: 0 1px 4px rgba(0,0,0,.05);
    display: flex; gap: 5mm; align-items: flex-start;
  }}
  .step-num {{
    background: #00C853; color: #001B44; width: 30px; height: 30px;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 14pt; flex-shrink: 0;
  }}
  .step-content h4 {{ margin: 0 0 2mm; font-size: 12pt; color: #003580; }}
  .step-content p {{ margin: 0; font-size: 10.5pt; color: #3a3a3c; line-height: 1.55; }}
</style>
</head>
<body>

<!-- ═════ COUVERTURE ═════ -->
<section class="cover">
  <div class="cover-logo">MESURECHÂSSIS · Kit tournage</div>
  <div>
    <div class="cover-eyebrow">Scénario complet · Édition 2026</div>
    <h1 class="cover-title">5 vidéos TikTok<br>« <em>Vrai ou Faux ?</em> »<br>À tourner en 1 après-midi.</h1>
    <p class="cover-subtitle">
      Scripts mot pour mot, timing seconde par seconde, direction visuelle,
      hashtags et captions. Objectif : viraliser MesureChâssis auprès des menuisiers belges.
    </p>
    <div class="cover-meta">
      <div><strong>5</strong>vidéos scriptées</div>
      <div><strong>10 s</strong>chacune</div>
      <div><strong>2 h</strong>de tournage</div>
    </div>
  </div>
  <div class="cover-footer">
    © 2026 MesureChâssis · Michel · Bruxelles · mesurechassis.com
  </div>
</section>

<!-- ═════ CHECKLIST AVANT TOURNAGE ═════ -->
<section class="checklist">
  <h1>📋 Checklist avant tournage</h1>
  <p class="sub">30 secondes pour tout préparer. Suis dans l'ordre.</p>

  <div class="check-block">
    <h3>🎬 Setup technique</h3>
    <ul>
      <li>📱 <strong>Format vertical 9:16</strong> — tourne direct en portrait, pas horizontal.</li>
      <li>🔆 <strong>Lumière</strong> — face à une fenêtre ou en extérieur. Jamais dos à la lumière.</li>
      <li>🎯 <strong>Cadrage</strong> — buste + tête, 15-20 cm de marge au-dessus de la tête (l'avatar IA en a besoin).</li>
      <li>🎤 <strong>Son</strong> — endroit calme. Si chantier, on pourra nettoyer après.</li>
      <li>🎥 <strong>Stabilité</strong> — pose le téléphone sur un trépied ou un tas de briques.</li>
    </ul>
  </div>

  <div class="check-block">
    <h3>👕 Look & attitude</h3>
    <ul>
      <li><strong>Tenue chantier</strong> — casque de sécurité + gilet jaune si possible. C'est ton uniforme = crédibilité.</li>
      <li><strong>Sur-joue les expressions à +20 %</strong> — l'IA lisse tout de 20 % au rendu final.</li>
      <li><strong>Regarde l'objectif dans les yeux</strong> — pas ton écran, sinon l'avatar aura le regard fuyant.</li>
      <li><strong>Gestures naturelles</strong> — pointer, ouvrir les mains, secouer la tête. L'avatar les reproduira.</li>
      <li><strong>Si tu bafouilles</strong> — refais toute la phrase, on découpe au montage.</li>
    </ul>
  </div>

  <div class="check-block">
    <h3>⏱️ Timing global</h3>
    <ul>
      <li><strong>Chaque vidéo = 10 secondes max</strong> — TikTok pénalise au-delà.</li>
      <li><strong>3 prises par vidéo</strong> — take 1 pour te chauffer, take 2 la bonne, take 3 sécurité.</li>
      <li><strong>Tourne les 5 en enchaîné</strong> — 2 h max total avec pauses.</li>
    </ul>
  </div>

  <div class="check-block">
    <h3>🎭 Rappel du principe</h3>
    <ul>
      <li>Tu tournes → tu me l'envoies (URL ou WeTransfer) → je te dis quel outil IA (HeyGen, Runway Act-One…) est adapté.</li>
      <li>Ton visage sera remplacé par un avatar. <strong>Tu ne parais PAS sur les réseaux.</strong></li>
      <li>Tu peux garder ta voix ou en cloner une (ElevenLabs, 5 €/mois).</li>
    </ul>
  </div>
</section>

{scenarios_html}

<!-- ═════ APRÈS TOURNAGE ═════ -->
<section class="post">
  <h1>✅ Après le tournage</h1>
  <p class="lead">
    Une fois les 5 vidéos brutes en boîte, envoie-moi tout et je m'occupe
    de la suite. Voici la roadmap.
  </p>

  <div class="step">
    <div class="step-num">1</div>
    <div class="step-content">
      <h4>📤 Tu m'envoies les vidéos</h4>
      <p>WeTransfer, Google Drive ou Dropbox — un dossier avec les 5 fichiers bruts. Nomme-les <em>video1_devis.mp4</em>, <em>video2_trapeze.mp4</em>, etc.</p>
    </div>
  </div>

  <div class="step">
    <div class="step-num">2</div>
    <div class="step-content">
      <h4>👀 J'analyse la qualité</h4>
      <p>Je vérifie éclairage, cadrage, expressivité pour savoir quel outil IA convient : HeyGen (photoréaliste), Runway Act-One (stylisé), ou refaire une prise.</p>
    </div>
  </div>

  <div class="step">
    <div class="step-num">3</div>
    <div class="step-content">
      <h4>🎭 Génération avatar</h4>
      <p>Ton visage est remplacé par un avatar IA qui reproduit tes gestures, tes expressions et ta voix (ou une voix clonée). Rendu final ~5 min par vidéo.</p>
    </div>
  </div>

  <div class="step">
    <div class="step-num">4</div>
    <div class="step-content">
      <h4>✂️ Montage final CapCut</h4>
      <p>Ajout des sous-titres animés (Whisper), du texte overlay (« FAUX » en géant), des bullets ✅, du logo MesureChâssis, et de la musique tendance TikTok.</p>
    </div>
  </div>

  <div class="step">
    <div class="step-num">5</div>
    <div class="step-content">
      <h4>📅 Programmation</h4>
      <p>1 vidéo publiée toutes les 48 h pendant 10 jours. Meilleur créneau : mardi/jeudi 18h-20h (pause du soir des artisans).</p>
    </div>
  </div>

  <div class="step">
    <div class="step-num">6</div>
    <div class="step-content">
      <h4>📊 Suivi</h4>
      <p>On analyse quelle vidéo performe le mieux (vues, engagement, clics profil), puis on double la mise sur ce format.</p>
    </div>
  </div>
</section>

</body>
</html>
"""


async def render():
    os.makedirs(OUT_DIR, exist_ok=True)
    html = build_html()
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 794, "height": 1123})
        page = await ctx.new_page()
        await page.goto(f"file://{OUT_HTML}", wait_until="domcontentloaded")
        await page.wait_for_timeout(600)
        await page.pdf(
            path=OUT_PDF,
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()

    size_kb = os.path.getsize(OUT_PDF) // 1024
    print(f"OK — {OUT_PDF} ({size_kb} Ko)")


if __name__ == "__main__":
    asyncio.run(render())
