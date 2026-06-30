"""
🎬 Régénération COMPLÈTE TikTok Script #4 — "Yann, ton chef d'atelier IA"

  - 8 nouvelles images verticales 9:16 (style alu/béton conforme)
  - Voix-off MP3 (Nova féminine, sans prix, CTA gratuit)
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

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script4")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALU_STYLE = (
    "Vertical 9:16 portrait, photorealistic ULTRA high quality, "
    "professional French aluminum carpentry context, anthracite grey or "
    "black aluminum window frames (modern Schüco/Reynaers profile), "
    "modern CONCRETE house facade or contemporary architecture in "
    "background, cinematic golden hour lighting, high-end B2B SaaS "
    "marketing visual, premium quality, sharp focus, shallow depth of field"
)

# Nouveau texte — pas de mention de prix ni de "plans payants"
VOICE_SCRIPT = (
    "Tu mesures un châssis alu. Yann, l'assistant IA, te checke en "
    "temps réel. Tu tapes : hauteur deux cent dix-huit. Yann : "
    "« T'as vu le seuil ? Mesure depuis le sol fini, pas la chape. » "
    "Tu corriges. Tu sauves ton chantier. Tu tapes : reculement douze "
    "centimètres. Yann : « OK pour pose en applique. Vérifie le tableau "
    "côté extérieur. » Tu prends une photo, tu valides. Diagonales : "
    "mille huit cent vingt-deux, mille huit cent vingt-cinq. Yann : "
    "« Châssis d'aplomb. Tu peux poser. » Confiance : cent pour cent. "
    "Yann, ton chef d'atelier de poche. "
    "Viens la télécharger gratuitement. Lien en bio."
)

SLIDES = [
    (
        "01_yann_intro.png",
        "close-up smartphone in male carpenter's hand displaying the "
        "MesureChâssis app chat interface with 'Yann' AI assistant "
        "speaking: white chat bubble with text 'Salut, je suis Yann, "
        "ton assistant', orange (#FF6F00) header bar, hand on a real "
        "modern construction site, blurred anthracite aluminum window "
        "behind, professional B2B mood",
    ),
    (
        "02_yann_seuil.png",
        "smartphone screen close-up: Yann AI chat bubble in orange "
        "saying 'T'as vu le seuil ? Mesure depuis le sol fini, pas la "
        "chape', user message above showing 'Hauteur : 218 cm', "
        "background is a blurred anthracite aluminum sliding door at a "
        "modern construction site, dramatic cinematic lighting",
    ),
    (
        "03_seuil_correction.png",
        "extreme close-up macro photo of a yellow Stanley measuring "
        "tape stretched vertically between the rough concrete subfloor "
        "and the finished tile/oak floor at the threshold of a modern "
        "anthracite aluminum door, showing the exact 'sol fini' "
        "reference point, sharp technical detail shot, warm natural "
        "side light, premium editorial style",
    ),
    (
        "04_yann_reculement.png",
        "smartphone chat screen close-up: Yann AI message in orange "
        "bubble 'OK pour pose en applique. Vérifie le tableau côté "
        "extérieur.', user message 'Reculement : 12 cm', a hand of a "
        "carpenter visibly holding the phone while a measuring tape is "
        "pressed against an anthracite aluminum frame on a modern "
        "concrete wall in the background",
    ),
    (
        "05_photo_tableau.png",
        "first-person POV through a smartphone camera viewfinder "
        "shooting a precise architectural shot of an aluminum window "
        "frame opening (tableau) in raw concrete, camera UI elements "
        "visible (focus square, capture button), bright daylight from "
        "outside, professional construction site context",
    ),
    (
        "06_diagonales_ok.png",
        "smartphone screen close-up showing MesureChâssis 'Diagonales' "
        "validation screen: 'D1 = 1822 mm' and 'D2 = 1825 mm' in large "
        "dark text, small technical rectangle diagram with crossed "
        "diagonals, big GREEN rounded badge with white check icon "
        "'D'APLOMB ✓', native iOS flat UI, orange header "
        "'MesureChâssis', perfectly readable typography",
    ),
    (
        "07_carpenter_confident.png",
        "wide shot of a confident French male carpenter (40s, short "
        "beard, anthracite work jacket) standing arms crossed in front "
        "of a perfectly installed large anthracite aluminum sliding "
        "window on the facade of a modern concrete villa, late "
        "afternoon golden light, slight smile, hero portrait, premium "
        "B2B editorial photography",
    ),
    (
        "08_cta.png",
        "minimalist dark premium background (charcoal #0C0C0E with "
        "subtle gradient), centered MesureChâssis logo (orange icon + "
        "white wordmark), bold white text 'YANN, TON CHEF D'ATELIER "
        "DE POCHE', below it vibrant orange CTA 'TÉLÉCHARGE "
        "GRATUITEMENT — LIEN EN BIO', ultra-clean modern SaaS "
        "marketing slide",
    ),
]


async def generate_image(filename: str, prompt: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    full_prompt = ALU_STYLE + ". " + prompt
    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"tiktok-script4-{filename}",
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
    print("🎬 Régénération COMPLÈTE TikTok Script #4 — Yann assistant IA")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

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

    print("\n✅ Terminé !")
    base = (
        "https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script4"
    )
    print("\n📥 URLs publiques :")
    for filename, _ in SLIDES:
        print(f"   {base}/{filename}")
    print(f"   {base}/voiceover.mp3")


if __name__ == "__main__":
    asyncio.run(main())
