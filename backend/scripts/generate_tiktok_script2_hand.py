"""
🎬 Génération de l'image "main d'artisan tenant un téléphone avec écran
validation diagonales" pour le TikTok script #2 (menuiserie alu).

Style : photoréaliste, calqué sur la composition de la photo référence
        IMG_0451.jpeg envoyée par l'utilisateur (main + phone + chantier).

Sortie : /app/backend/static/promo/tiktok_script2/00_hand_phone_diagonale.png
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

API_KEY = os.getenv("EMERGENT_LLM_KEY")
if not API_KEY:
    print("❌ EMERGENT_LLM_KEY introuvable dans /app/backend/.env")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Prompt très détaillé pour Gemini Nano Banana
PROMPT = (
    "Vertical 9:16 portrait photograph, ULTRA photorealistic cinematic shot. "
    "A male carpenter's hand (slightly calloused, slight dust on skin, tanned) "
    "holds a modern smartphone in the foreground, thumb near the bottom of the "
    "screen ready to tap. The phone is tilted slightly toward the camera at a "
    "low-angle perspective, the screen clearly visible and well-lit. "
    "\n\n"
    "ON THE PHONE SCREEN, display a clean modern mobile app UI in French with: "
    "- Top header bar in vibrant orange (#FF6F00) with white text 'MesureChâssis' "
    "and a small back arrow. "
    "- Title in bold dark gray: 'Validation diagonales'. "
    "- A small technical diagram of a rectangle with two crossing diagonals "
    "(D1 in orange, D2 in dark gray). "
    "- Two large numeric values: 'D1 = 1850 mm' and 'D2 = 1851 mm'. "
    "- A row showing 'Écart : 1 mm' in small text. "
    "- A bright GREEN rounded badge with a white check icon and text 'VALIDÉ ✓' "
    "occupying the lower-third of the screen. "
    "- Bottom: a large orange button 'Étape suivante'. "
    "The UI must look sharp, modern, flat-design, native iOS style, "
    "with clean Inter/SF Pro typography, high contrast, perfectly readable. "
    "\n\n"
    "BACKGROUND (out of focus, shallow depth of field, bokeh): "
    "modern construction site interior with an ALUMINIUM black/anthracite window "
    "frame being installed against a raw concrete wall. A yellow professional "
    "Stanley measuring tape lies on the windowsill. Soft diffused natural daylight "
    "streams through the window from behind, creating a slight rim light on the "
    "phone and hand. Aluminium silver tones, concrete gray, anthracite black, "
    "subtle warm highlights. "
    "\n\n"
    "Carpenter wears a dark anthracite work jacket sleeve, slightly visible. "
    "Mood: professional, modern, problem-solved, reassuring. "
    "Color grade: cinematic, slightly desaturated, with the orange app header and "
    "green VALIDÉ badge popping as the focal accents. "
    "Style: high-end commercial photography for a SaaS product targeting French "
    "aluminium window professionals. Sharp focus on the phone screen, soft "
    "bokeh background. 9:16 vertical TikTok format."
)


async def generate_image() -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=API_KEY,
        session_id="tiktok-script2-hand-phone",
        system_message=(
            "You are a world-class commercial photographer and UI designer "
            "creating ultra-realistic product photography for a SaaS mobile app."
        ),
    )
    chat.with_model(
        "gemini", "gemini-3.1-flash-image-preview"
    ).with_params(modalities=["image", "text"])

    msg = UserMessage(text=PROMPT)

    try:
        _text, images = await chat.send_message_multimodal_response(msg)
        if not images:
            print("⚠️  Aucune image générée par Gemini")
            return False

        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        output_path = OUTPUT_DIR / "00_hand_phone_diagonale.png"
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"✅ {output_path.name} ({len(image_bytes) // 1024} KB)")
        print(
            "🌐 URL publique : "
            "https://window-field-app.preview.emergentagent.com/"
            "api/promo/tiktok_script2/00_hand_phone_diagonale.png"
        )
        return True
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False


if __name__ == "__main__":
    print("🎬 Génération image 'main + phone + validation diagonale'")
    print(f"📂 Sortie : {OUTPUT_DIR}")
    asyncio.run(generate_image())
