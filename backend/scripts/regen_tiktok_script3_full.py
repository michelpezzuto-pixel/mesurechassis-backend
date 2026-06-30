"""
🎬 Régénération COMPLÈTE du TikTok Script #3 — "Import CDC en 3 sec."

Génère :
  - 8 nouvelles images verticales 9:16 (style alu/béton conforme guidelines)
  - 1 voix-off MP3 (voix Nova féminine, sans prix, CTA gratuit)

Sortie : /app/backend/static/promo/tiktok_script3/
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

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script3")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ───────────────────────────────────────────────────────────
# STYLE COMMUN — Aluminium + Béton + Premium
# ───────────────────────────────────────────────────────────
ALU_STYLE = (
    "Vertical 9:16 portrait, photorealistic ULTRA high quality, "
    "professional French aluminum carpentry context, anthracite grey or "
    "black aluminum window frames (modern Schüco/Reynaers profile), "
    "modern CONCRETE house facade or contemporary architecture in "
    "background, cinematic golden hour lighting, high-end B2B SaaS "
    "marketing visual, premium quality, sharp focus, shallow depth of field"
)

# ───────────────────────────────────────────────────────────
# NOUVEAU TEXTE VOIX-OFF (sans prix, CTA gratuit)
# ───────────────────────────────────────────────────────────
VOICE_SCRIPT = (
    "Tu reçois un cahier des charges de douze pages... et tu sais déjà "
    "que ta soirée va y passer. Cinquante lignes de cotes, cinq vues, "
    "trois plans, à recopier à la main. Une erreur, et ton châssis alu "
    "est foutu. Avec MesureChâssis, tu prends une seule photo du "
    "document. L'intelligence artificielle lit toutes les cotes en moins "
    "de trois secondes. Châssis fixe mille deux cents par mille cinq "
    "cents. Vasistas huit cents par six cents. Porte-fenêtre deux "
    "vantaux. Tout est extrait automatiquement, prêt à valider, avec les "
    "diagonales calculées. Tu récupères deux heures par chantier. "
    "Viens la télécharger gratuitement. Lien en bio."
)

# ───────────────────────────────────────────────────────────
# 8 PROMPTS POUR LES 8 SLIDES
# ───────────────────────────────────────────────────────────
SLIDES = [
    (
        "01_cdc_pile.png",
        "vertical stack of CDC (cahier des charges) PDF documents and "
        "blueprints piled high on a dark wooden desk, warm evening lamp "
        "creating a moody puddle of light, bold orange overlay text "
        "'12 PAGES' top-right, faint exhausted human silhouette in "
        "background, dramatic shadow, late-night cinematic mood, "
        "blueprints showing aluminum window technical drawings",
    ),
    (
        "02_recopie_main.png",
        "close-up over-the-shoulder shot of a tired male carpenter's hand "
        "writing measurements with a pencil in a worn paper notebook, "
        "scattered architectural blueprints around showing aluminum "
        "window plans, dim warm desk lamp, slight motion blur on the "
        "hand, dust particles in light beam, exhausted late-evening "
        "atmosphere, dark moody colors",
    ),
    (
        "03_clock_2h.png",
        "minimalist analog vintage clock on a dark concrete wall showing "
        "2 hours elapsed (hands going from 21h to 23h with motion trail), "
        "bright orange '2H PERDUES' overlay text in bold sans-serif, "
        "dramatic single-point lighting, time-wasted concept, premium "
        "editorial photography",
    ),
    (
        "04_smartphone_pdf.png",
        "hand of a male carpenter holding a modern smartphone over a "
        "paper PDF blueprint of an aluminum window project lying on a "
        "wooden desk, the phone camera is active scanning the document "
        "with subtle AR overlay frame, modern construction office "
        "background, professional B2B aesthetic, sharp focus on the phone",
    ),
    (
        "05_ai_analyzing.png",
        "close-up smartphone screen showing the MesureChâssis app "
        "scanning a blueprint: AI progress bar at 78% with text "
        "'Analyse en cours...', animated scanning grid effect over the "
        "PDF, orange (#FF6F00) accent UI, multiple detected measurement "
        "boxes appearing on the document (1200x1500, 800x600), futuristic "
        "modern flat UI design, native iOS look",
    ),
    (
        "06_dashboard_filled.png",
        "smartphone screen displaying MesureChâssis app dashboard fully "
        "populated with extracted measurements: list shows 'Châssis fixe "
        "1200×1500', 'Vasistas 800×600', 'Porte-fenêtre 1600×2150', each "
        "with a tiny green check icon, orange header 'MesureChâssis', "
        "clean modern flat iOS UI, perfectly readable typography",
    ),
    (
        "07_stopwatch_3sec.png",
        "premium stopwatch frozen at exactly 3 seconds, brushed aluminum "
        "metal body reflecting orange ambient light, dramatic motion blur "
        "halo around it, dark concrete background, big bold '3 SEC' "
        "overlay text in orange, hero product photography style",
    ),
    (
        "08_cta.png",
        "minimalist dark premium background (charcoal #0C0C0E with subtle "
        "gradient), centered MesureChâssis logo (orange icon + white "
        "wordmark), bold white text '+ 2 HEURES PAR CHANTIER', below it "
        "vibrant orange CTA 'TÉLÉCHARGE GRATUITEMENT — LIEN EN BIO', "
        "ultra-clean modern SaaS marketing slide",
    ),
]


# ───────────────────────────────────────────────────────────
# Génération d'une image via Gemini Nano Banana
# ───────────────────────────────────────────────────────────
async def generate_image(filename: str, prompt: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    full_prompt = ALU_STYLE + ". " + prompt
    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"tiktok-script3-{filename}",
        system_message=(
            "You are a world-class commercial photographer and UI "
            "designer creating premium TikTok content for a French "
            "aluminum carpentry SaaS app."
        ),
    )
    chat.with_model(
        "gemini", "gemini-3.1-flash-image-preview"
    ).with_params(modalities=["image", "text"])

    try:
        _text, images = await chat.send_message_multimodal_response(
            UserMessage(text=full_prompt)
        )
        if not images:
            print(f"      ⚠️  Aucune image pour {filename}")
            return False
        image_bytes = base64.b64decode(images[0]["data"])
        (OUTPUT_DIR / filename).write_bytes(image_bytes)
        print(f"      ✅ {filename} ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"      ❌ {filename}: {str(e)[:90]}")
        return False


# ───────────────────────────────────────────────────────────
# Génération voix-off (OpenAI TTS-1-HD voix Nova féminine)
# ───────────────────────────────────────────────────────────
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
        print(
            f"   ✅ voiceover.mp3 ({len(response.content) // 1024} KB)"
        )
        return True
    except Exception as e:
        print(f"   ❌ voiceover.mp3 : {e}")
        return False


async def main():
    print("🎬 Régénération COMPLÈTE TikTok Script #3 — CDC en 3 sec.")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

    # Backup des anciennes images
    for filename, _ in SLIDES:
        old = OUTPUT_DIR / filename
        backup = OUTPUT_DIR / f"old_{filename}"
        if old.exists() and not backup.exists():
            shutil.copy(old, backup)

    print("🖼️  Génération des 8 images (Gemini Nano Banana)...")
    success = 0
    for filename, prompt in SLIDES:
        if await generate_image(filename, prompt):
            success += 1
    print(f"   📊 {success}/{len(SLIDES)} images générées\n")

    print("🎙️  Génération voix-off (Nova féminine)...")
    await generate_voiceover()
    print()

    print("✅ Terminé !")
    print("\n📥 URLs publiques :")
    base = (
        "https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script3"
    )
    for filename, _ in SLIDES:
        print(f"   {base}/{filename}")
    print(f"   {base}/voiceover.mp3")


if __name__ == "__main__":
    asyncio.run(main())
