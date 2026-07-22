"""
🎬 SAMPLE — Génère 2 images pour valider le style de la pub 45s :
  - 1x Personnage cartoon Michel (pose "Eureka" tenant l'iPhone)
  - 1x Photo réaliste menuisier devant chantier avec app

Style demandé :
  - Cartoon : PAS un stickman. Détaillé, yeux expressifs, casquette orange,
              t-shirt noir, style Duolingo/Dr Cash mais artisan menuisier.
  - Photo   : Style ton précédent visuel — menuisier belge chantier iPhone.

Sortie : /app/backend/static/promo/video_pub_45s/samples/
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

OUTPUT_DIR = Path("/app/backend/static/promo/video_pub_45s")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# SAMPLE 1 : Personnage cartoon "Michel" — pose Eureka
# ============================================================================
PROMPT_CARTOON = (
    "Vertical 9:16 cartoon character illustration, PURE WHITE background, "
    "isolated character for use as a sticker/asset in a marketing video. "
    "\n\n"
    "CHARACTER: A friendly Belgian male carpenter named Michel, early 30s. "
    "Style: modern flat 2D cartoon, clean thick black outlines (like Duolingo "
    "mascot meets 'Dr Cash / Ousama' TikTok viral style). "
    "NOT a stickman — the character has proper human proportions but slightly "
    "stylized (head is slightly larger, cute but not childish). "
    "\n\n"
    "APPEARANCE: "
    "- Wearing an ORANGE BASEBALL CAP TURNED BACKWARDS (visible cap strap on "
    "  forehead, orange color #F58220). "
    "- Short brown hair peeking out from under the cap sides. "
    "- Wearing a plain BLACK T-SHIRT with short sleeves. "
    "- Skin tone: light peachy tan (carpenter who works outside). "
    "- Face: LARGE EXPRESSIVE EYES with visible pupils and highlights (Duolingo "
    "  style), thick eyebrows raised in excitement, big open smile showing teeth, "
    "  small nose. NO stick-figure face — proper cartoon face. "
    "- Hands: cartoon 4-finger hands (not sticks), well drawn with visible fingers. "
    "- Body: slightly muscular carpenter build, visible under the t-shirt. "
    "\n\n"
    "POSE (EUREKA / DISCOVERY): "
    "Michel is holding up a modern iPhone in his right hand, screen facing the "
    "camera. The phone screen shows the MesureChâssis app UI: bright ORANGE "
    "header bar with white text 'MesureChâssis', a big GREEN 'TOUT VALIDÉ ✓' "
    "badge, and a list of checkmarks. His left index finger is pointing at the "
    "phone with a big 'aha!' expression. A YELLOW LIGHTBULB with rays appears "
    "above his head (small icon, cartoon style). "
    "\n\n"
    "COLORS: flat vibrant colors — orange cap (#F58220), black t-shirt, peach "
    "skin, white background. Green highlight for the phone badge. "
    "Clean modern cartoon, sharp lines, slight shadow under the character. "
    "\n\n"
    "COMPOSITION: Character fills 80% of the vertical frame, centered, feet "
    "cropped mid-calf. Camera slightly low angle for hero feel. PURE WHITE "
    "background (#FFFFFF) — completely isolated for easy compositing. "
    "\n\n"
    "STYLE REFERENCES: Ousama Dr Cash TikTok character, Duolingo owl mascot "
    "style, modern French SaaS advertising cartoon, CapCut viral video assets. "
    "AVOID: stick figures, ugly proportions, childish faces, flat colors only, "
    "generic clipart look. Make it POLISHED and PROFESSIONAL."
)

# ============================================================================
# SAMPLE 2 : Photo réaliste menuisier chantier + iPhone
# ============================================================================
PROMPT_PHOTO = (
    "Vertical 9:16 portrait photograph, ULTRA photorealistic cinematic shot, "
    "high-end commercial photography for a SaaS product. "
    "\n\n"
    "SUBJECT: A Belgian carpenter named Michel, early 30s, wearing a dark grey "
    "MesureChâssis branded work vest with small orange logo on chest, dust-worn "
    "jeans slightly visible. He has short brown hair, light stubble, friendly "
    "confident smile. He is holding a modern iPhone in his outstretched right "
    "hand, screen clearly facing the camera. "
    "\n\n"
    "PHONE SCREEN: The iPhone screen shows the MesureChâssis mobile app: "
    "- Vibrant ORANGE header bar (#F58220) with white bold 'MesureChâssis' text "
    "- A big GREEN rounded badge saying 'TOUT VALIDÉ ✓' with white check icon "
    "- A list of items with green check marks: 'Mesures', 'Photos', 'Diagonales', "
    "  'Rendez-vous', 'Client' "
    "- Bottom: subtle 'v1.0.30' small text "
    "The UI is sharp, well-lit, perfectly readable. "
    "\n\n"
    "BACKGROUND: Modern residential construction site, out of focus (shallow "
    "depth of field, beautiful bokeh). Behind Michel: a newly installed large "
    "black aluminium window frame against grey raw concrete wall, showing pine "
    "trees and a wooden house facade through the window in soft sunset light. "
    "Yellow Stanley measuring tape and cordless drill visible on the concrete "
    "windowsill (blurred). "
    "\n\n"
    "LIGHTING: Warm golden hour light streaming from behind, creating a subtle "
    "rim light on Michel's shoulders and cap. Soft natural fill on his face. "
    "Slight lens flare from the sun. Cinematic color grade with warm oranges "
    "and cool teals in shadows. "
    "\n\n"
    "MOOD: Confident, proud, authentic. 'A carpenter who solved his own problem "
    "and now shares the tool.' Trustworthy Belgian craftsman vibe. "
    "\n\n"
    "STYLE: High-end commercial SaaS product photography, similar to Apple's "
    "product ads but for a French/Belgian craft SaaS. Sharp focus on the phone "
    "screen AND Michel's face. Bokeh background. Professional grading, no "
    "amateur look. Realistic skin texture, natural facial expression. "
    "\n\n"
    "AVOID: cartoon look, plastic AI-generated face, unrealistic lighting, "
    "generic stock photo feel. Make it look like a REAL PHOTO taken by a "
    "professional photographer for a real brand campaign."
)


async def generate_one(prompt: str, filename: str, label: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"video-pub-45s-sample-{filename}",
        system_message=(
            "You are a world-class illustrator and commercial photographer "
            "creating premium marketing assets for a Belgian SaaS mobile app "
            "targeting professional carpenters."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(text=prompt)
    print(f"⏳ Génération : {label} ...")

    try:
        _text, images = await chat.send_message_multimodal_response(msg)
        if not images:
            print(f"⚠️  Aucune image générée pour {label}")
            return False

        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        output_path = OUTPUT_DIR / filename
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"✅ {output_path.name} ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"❌ Erreur {label} : {e}")
        return False


async def main():
    print("🎬 GÉNÉRATION SAMPLES pour Pub 45s MesureChâssis")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

    ok1 = await generate_one(
        PROMPT_CARTOON, "sample_01_cartoon_michel_eureka.png",
        "Cartoon Michel — pose Eureka"
    )
    ok2 = await generate_one(
        PROMPT_PHOTO, "sample_02_photo_michel_chantier.png",
        "Photo réaliste Michel — chantier + iPhone"
    )

    print(f"\n📊 Résultat : {int(ok1) + int(ok2)}/2 images générées")
    if ok1 and ok2:
        print("\n🌐 URLs publiques :")
        print("  https://window-field-app.preview.emergentagent.com/api/promo/video_pub_45s/sample_01_cartoon_michel_eureka.png")
        print("  https://window-field-app.preview.emergentagent.com/api/promo/video_pub_45s/sample_02_photo_michel_chantier.png")


if __name__ == "__main__":
    asyncio.run(main())
