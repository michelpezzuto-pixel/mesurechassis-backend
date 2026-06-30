"""
🎬 Génération du contenu TikTok — Script #5 "5 erreurs à 1000€/chantier"

Génère :
  - 8 images verticales 9:16 (slides du diaporama) via Gemini Nano Banana
  - 1 voix-off MP3 (40 sec, voix "onyx" française) via OpenAI TTS

Sortie : /app/backend/static/promo/tiktok_script5/
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Charger les variables d'env du backend
load_dotenv("/app/backend/.env")

API_KEY = os.getenv("EMERGENT_LLM_KEY")
if not API_KEY:
    print("❌ EMERGENT_LLM_KEY introuvable dans /app/backend/.env")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script5")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 8 PROMPTS POUR LES 8 IMAGES DU DIAPORAMA
# Format : (filename, prompt, text overlay)
# ═══════════════════════════════════════════════════════════════
SLIDES = [
    (
        "01_hook.png",
        "Vertical 9:16 portrait poster, bold dramatic minimalist design, "
        "dark background (charcoal black #0C0C0E), giant typography in "
        "vibrant orange (#FF6F00) reading '5 ERREURS QUI COÛTENT 1000€', "
        "with a small red euro symbol bleeding red, French carpentry "
        "professional aesthetic, cinematic lighting, hero shot, "
        "TikTok-style attention-grabbing first slide",
    ),
    (
        "02_diagonale.png",
        "Vertical 9:16 portrait, photorealistic close-up of a window "
        "frame slightly tilted (askew), measuring tape showing 8mm gap, "
        "professional construction site lighting, orange warning overlay "
        "in corner reading '-300 €', dramatic shadow, French carpenter "
        "worksite background blurred, cinematic dramatic mood",
    ),
    (
        "03_tableau_baie.png",
        "Vertical 9:16 portrait, clean technical diagram comparing two "
        "rectangles labeled 'TABLEAU' (raw wall opening) and 'BAIE' "
        "(finished opening), arrows showing 5cm difference between them, "
        "minimalist white background, orange and black labels, "
        "architectural blueprint style, professional French carpentry "
        "education content, with '-400 €' tag",
    ),
    (
        "04_seuil_porte.png",
        "Vertical 9:16 portrait, photorealistic close-up of a door "
        "threshold detail, showing concrete subfloor vs finished floor "
        "level, measuring tape laid across, professional construction "
        "site, red arrow highlighting the height difference, orange "
        "overlay text '-200 €', warm cinematic lighting",
    ),
    (
        "05_reculement.png",
        "Vertical 9:16 portrait, top-down view of carpentry hardware "
        "and hinges spread on a workshop table, brown craft paper "
        "background, orange tag overlay '-100 €', professional product "
        "photography style, dramatic side lighting, French artisan "
        "carpentry workshop aesthetic",
    ),
    (
        "06_pas_de_photo.png",
        "Vertical 9:16 portrait, dramatic image of a smartphone with "
        "empty photo gallery on construction site, orange warning icon, "
        "blurred carpenter in background looking concerned, cinematic "
        "tension lighting, text overlay 'PAS DE PHOTO = PAS DE PREUVE'",
    ),
    (
        "07_solution.png",
        "Vertical 9:16 portrait, hand holding modern smartphone showing "
        "the MesureChâssis app dashboard with green checkmarks and a "
        "measurement form, professional carpenter blue work shirt blurred "
        "in background, bright clean lighting, orange accent on UI, "
        "high-tech professional B2B SaaS aesthetic, French interface",
    ),
    (
        "08_cta.png",
        "Vertical 9:16 portrait, clean dark background charcoal #0C0C0E, "
        "centered logo of MesureChâssis (modern orange '#FF6F00' window "
        "frame icon), bold white text '19€/MOIS' and below smaller text "
        "'Essai 14 jours gratuit · Lien en bio 👇', minimalist premium "
        "SaaS branding, French carpentry B2B aesthetic, professional "
        "social media call-to-action slide",
    ),
]

# ═══════════════════════════════════════════════════════════════
# VOICE-OVER SCRIPT (FRENCH, ~40 SEC, VOICE "ONYX")
# ═══════════════════════════════════════════════════════════════
VOICE_SCRIPT = (
    "Cinq erreurs qui te coûtent mille euros par chantier. "
    "Numéro un : oublier la diagonale. Huit millimètres de différence "
    "et ton châssis est en biais. Tu refais la pose : moins trois cents "
    "euros. "
    "Numéro deux : confondre tableau et baie. Tu mesures la baie au lieu "
    "du tableau ? Châssis cinq centimètres trop petit. Moins quatre cents "
    "euros. "
    "Numéro trois : mal mesurer le seuil de porte. Tu pars de la chape au "
    "lieu du sol fini ? La porte frotte. Moins deux cents euros de pose "
    "en plus. "
    "Numéro quatre : pas de relevé du reculement. Tu peux pas commander "
    "la quincaillerie. Tu repasses sur chantier. Moins cent euros. "
    "Numéro cinq : pas de photo, pas de preuve. Litige client, ta parole "
    "contre la sienne. "
    "MesureChâssis vérifie tout ça automatiquement. "
    "Dix-neuf euros par mois. Rentabilisé en un chantier. Lien en bio."
)


# ═══════════════════════════════════════════════════════════════
# GÉNÉRATION DES IMAGES via Gemini Nano Banana
# ═══════════════════════════════════════════════════════════════
async def generate_image(filename: str, prompt: str) -> bool:
    """Génère une image PNG via Gemini Nano Banana."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"tiktok-script5-{filename}",
        system_message="You are a professional graphic designer creating TikTok content.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(text=prompt)

    try:
        text, images = await chat.send_message_multimodal_response(msg)
        if not images:
            print(f"   ⚠️  Aucune image générée pour {filename}")
            return False

        # Garde uniquement la première image
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        output_path = OUTPUT_DIR / filename
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"   ✅ {filename} ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"   ❌ {filename} : {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# GÉNÉRATION DE LA VOIX-OFF via OpenAI TTS (proxy Emergent)
# ═══════════════════════════════════════════════════════════════
async def generate_voiceover() -> bool:
    """Génère le MP3 de la voix-off via OpenAI TTS-1-HD voix onyx."""
    from openai import AsyncOpenAI

    # Le proxy Emergent expose les endpoints OpenAI compatibles
    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url="https://integrations.emergentagent.com/llm",
    )

    try:
        response = await client.audio.speech.create(
            model="tts-1-hd",
            voice="onyx",  # masculin grave et naturel
            input=VOICE_SCRIPT,
            speed=1.0,
            response_format="mp3",
        )

        output_path = OUTPUT_DIR / "voiceover.mp3"
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"   ✅ voiceover.mp3 ({len(response.content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"   ❌ voiceover.mp3 : {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
async def main():
    print("🎬 Génération TikTok Script #5 — '5 erreurs à 1000€/chantier'")
    print(f"📂 Sortie : {OUTPUT_DIR}")
    print()
    print("🖼️  Génération des 8 images (Gemini Nano Banana)…")

    success_count = 0
    for filename, prompt in SLIDES:
        ok = await generate_image(filename, prompt)
        if ok:
            success_count += 1

    print()
    print(f"📊 {success_count}/{len(SLIDES)} images générées")
    print()
    print("🎙️  Génération de la voix-off (OpenAI TTS-1-HD onyx)…")
    await generate_voiceover()
    print()
    print("✅ Terminé !")
    print()
    print("📥 URLs publiques :")
    for filename, _ in SLIDES:
        print(
            f"   https://window-field-app.preview.emergentagent.com/"
            f"api/promo/tiktok_script5/{filename}"
        )
    print(
        "   https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script5/voiceover.mp3"
    )


if __name__ == "__main__":
    asyncio.run(main())
