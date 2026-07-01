"""
🎬 Régénération COMPLÈTE TikTok Script #5 — "5 erreurs à ne plus faire"

  - 8 slides principales régénérées (sans prix affichés)
  - 1 NOUVELLE affiche outro 09_outro.png (fond noir premium)
  - Voix-off Nova féminine, sans prix, CTA gratuit
"""
import asyncio
import base64
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

API_KEY = os.getenv("EMERGENT_LLM_KEY")
if not API_KEY:
    print("❌ EMERGENT_LLM_KEY introuvable")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script5")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALU_STYLE = (
    "Vertical 9:16 portrait, photorealistic ULTRA high quality, "
    "professional French aluminum carpentry context, anthracite grey or "
    "black aluminum window frames (modern Schüco/Reynaers profile), "
    "modern CONCRETE house facade or contemporary architecture in "
    "background, cinematic golden hour lighting, high-end B2B SaaS "
    "marketing visual, premium quality, sharp focus, shallow depth of field"
)

# Nouveau texte — plus aucune mention de prix
VOICE_SCRIPT = (
    "Cinq erreurs à ne plus jamais faire sur ton chantier alu. "
    "Numéro un : oublier la diagonale. Huit millimètres de différence "
    "et ton châssis est en biais. Tu refais la pose. "
    "Numéro deux : confondre tableau et baie. Tu mesures la baie au "
    "lieu du tableau ? Châssis cinq centimètres trop petit. "
    "Numéro trois : mal mesurer le seuil de porte. Tu pars de la chape "
    "au lieu du sol fini ? La porte frotte. "
    "Numéro quatre : pas de relevé du reculement. Tu peux pas commander "
    "la quincaillerie. Tu repasses sur chantier. "
    "Numéro cinq : pas de photo, pas de preuve. Litige client, ta "
    "parole contre la sienne. "
    "MesureChâssis vérifie tout ça automatiquement. "
    "Viens la télécharger gratuitement. Lien en bio."
)

SLIDES = [
    (
        "01_hook.png",
        "dark charcoal background (#0C0C0E), giant dramatic typography "
        "in vibrant orange (#FF6F00) reading '5 ERREURS QUI TUENT TON "
        "CHANTIER', bold sans-serif, French aluminium carpentry "
        "professional aesthetic, cinematic lighting, hero shot, "
        "TikTok-style attention-grabbing first slide, minimalist",
    ),
    (
        "02_diagonale.png",
        "photorealistic close-up of an anthracite aluminum window frame "
        "slightly tilted (askew, out of square), yellow measuring tape "
        "showing 8mm gap between the diagonals, professional "
        "construction site lighting, subtle red warning arrow, "
        "dramatic shadow, French carpenter worksite background blurred, "
        "cinematic dramatic mood (NO price overlay)",
    ),
    (
        "03_tableau_baie.png",
        "clean technical architectural diagram comparing two rectangles "
        "side-by-side labeled 'TABLEAU' (raw wall opening) and 'BAIE' "
        "(finished opening), arrows showing 5 cm difference between "
        "them, minimalist white background, orange and dark grey labels, "
        "architectural blueprint style, French carpentry education "
        "content (NO price overlay)",
    ),
    (
        "04_seuil_porte.png",
        "photorealistic close-up of an aluminum door threshold detail "
        "on a modern construction site, showing raw concrete subfloor "
        "vs finished tile floor level, yellow Stanley measuring tape "
        "laid vertically across the gap, subtle red arrow highlighting "
        "the height difference, warm cinematic side lighting "
        "(NO price overlay)",
    ),
    (
        "05_reculement.png",
        "top-down flat lay of aluminum window hinges and quincaillerie "
        "hardware neatly arranged on a dark walnut wooden workshop "
        "table, brown craft paper accents, professional product "
        "photography, dramatic side lighting, French artisan carpentry "
        "workshop aesthetic (NO price overlay)",
    ),
    (
        "06_pas_de_photo.png",
        "dramatic image of a smartphone with an empty photo gallery "
        "screen on a construction site, orange warning icon in the "
        "corner, blurred concerned male carpenter in background looking "
        "at the phone, cinematic mood, anthracite aluminum window "
        "visible in background",
    ),
    (
        "07_solution.png",
        "smartphone in a male carpenter's hand showing the MesureChâssis "
        "app main dashboard with a bright green 'TOUT VALIDÉ ✓' banner, "
        "five small check icons for the five categories (diagonale, "
        "tableau, seuil, reculement, photo), clean modern orange UI, "
        "anthracite aluminum window blurred in background",
    ),
    (
        "08_cta.png",
        "minimalist dark premium background (charcoal #0C0C0E with "
        "subtle radial gradient), centered MesureChâssis logo (orange "
        "icon + white wordmark), bold white text 'ZÉRO ERREUR SUR TES "
        "CHANTIERS', below it vibrant orange CTA 'TÉLÉCHARGE "
        "GRATUITEMENT — LIEN EN BIO', ultra-clean modern SaaS "
        "marketing slide",
    ),
    # ───────────────────────────────────────────────────────────
    # NOUVELLE AFFICHE OUTRO (9e slide)
    # ───────────────────────────────────────────────────────────
    (
        "09_outro.png",
        "Premium marketing outro poster, PURE BLACK background (#000000) "
        "with very subtle orange radial glow behind the logo. "
        "Composition top-to-bottom: "
        "(1) Large centered MesureChâssis logo (orange window-frame "
        "icon + white wordmark 'MesureChâssis' in bold sans-serif). "
        "(2) Below the logo, bold white uppercase headline "
        "'20+ MESURES PROFESSIONNELLES' with slight letter-spacing. "
        "(3) Small elegant tagline in warm light-grey "
        "'L'app des menuisiers alu' (italic). "
        "(4) Thin orange horizontal divider line. "
        "(5) Vibrant orange (#FF6F00) rounded CTA button 'TÉLÉCHARGE "
        "GRATUITEMENT' in white bold text. "
        "(6) Bottom line in medium grey 'sur mesurechassis.com' with "
        "the website URL styled cleanly. "
        "Ultra-clean minimalist modern SaaS marketing final slide, "
        "premium editorial typography (Inter / SF Pro), 9:16 vertical, "
        "TikTok outro card style, absolutely no other decoration",
    ),
]


async def generate_image(filename: str, prompt: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    # L'outro est déjà stylé -> pas besoin d'ajouter ALU_STYLE
    if filename == "09_outro.png":
        full_prompt = prompt
    else:
        full_prompt = ALU_STYLE + ". " + prompt

    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"tiktok-script5-{filename}",
        system_message=(
            "You are a world-class commercial photographer and UI "
            "designer creating premium TikTok content."
        ),
    )
    chat.with_model(
        "gemini", "gemini-3.1-flash-image-preview"
    ).with_params(modalities=["image", "text"])

    try:
        _t, images = await chat.send_message_multimodal_response(
            UserMessage(text=full_prompt)
        )
        if not images:
            print(f"      ⚠️  Aucune image pour {filename}")
            return False
        data = base64.b64decode(images[0]["data"])
        (OUTPUT_DIR / filename).write_bytes(data)
        print(f"      ✅ {filename} ({len(data) // 1024} KB)")
        return True
    except Exception as e:
        print(f"      ❌ {filename}: {str(e)[:90]}")
        return False


async def generate_voiceover() -> bool:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url="https://integrations.emergentagent.com/llm",
    )
    output_path = OUTPUT_DIR / "voiceover.mp3"
    backup_path = OUTPUT_DIR / "voiceover_old.mp3"
    if output_path.exists() and not backup_path.exists():
        shutil.copy(output_path, backup_path)
        print(f"   📦 Backup : {backup_path.name}")

    try:
        response = await client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=VOICE_SCRIPT,
            speed=1.0,
            response_format="mp3",
        )
        output_path.write_bytes(response.content)
        print(f"   ✅ voiceover.mp3 ({len(response.content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"   ❌ voiceover.mp3 : {e}")
        return False


async def main():
    print("🎬 Régénération COMPLÈTE TikTok Script #5 — 5 erreurs à éviter")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

    for filename, _ in SLIDES:
        old = OUTPUT_DIR / filename
        backup = OUTPUT_DIR / f"old_{filename}"
        if old.exists() and not backup.exists():
            shutil.copy(old, backup)

    print("🖼️  Génération des 9 images (8 slides + 1 outro)...")
    success = 0
    for filename, prompt in SLIDES:
        if await generate_image(filename, prompt):
            success += 1
    print(f"   📊 {success}/{len(SLIDES)} images générées\n")

    print("🎙️  Génération voix-off (Nova féminine)...")
    await generate_voiceover()

    print("\n✅ Terminé !")
    base = (
        "https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script5"
    )
    print("\n📥 URLs publiques :")
    for filename, _ in SLIDES:
        print(f"   {base}/{filename}")
    print(f"   {base}/voiceover.mp3")


if __name__ == "__main__":
    asyncio.run(main())
