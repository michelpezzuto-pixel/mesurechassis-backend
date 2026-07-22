"""
🎬 GÉNÉRATION COMPLÈTE des 22 assets restants pour la pub 45s MesureChâssis.

Angle : "Fait par un menuisier, pour les menuisiers"
Style cartoon : personnage Michel — casquette orange à l'envers, t-shirt noir,
                yeux expressifs (style Duolingo/Dr Cash premium)
Style photo   : réaliste pub Apple, coucher de soleil, chantier belge

Sortie : /app/backend/static/promo/video_pub_45s/
"""
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

API_KEY = os.getenv("EMERGENT_LLM_KEY")
if not API_KEY:
    print("❌ EMERGENT_LLM_KEY introuvable")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo/video_pub_45s")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CHARACTER BASE — Description commune à toutes les poses de Michel
# ============================================================================
MICHEL_BASE = (
    "Michel is a Belgian male carpenter in his early 30s, PURE WHITE background, "
    "isolated character sticker style. Style: modern flat 2D cartoon with clean "
    "thick black outlines, like Duolingo mascot meets Dr Cash / Ousama TikTok "
    "viral character. NOT a stickman — proper cartoon proportions with slightly "
    "larger head, cute but professional. "
    "APPEARANCE: ORANGE BASEBALL CAP TURNED BACKWARDS (color #F58220, strap "
    "visible on forehead), short brown hair peeking from sides, plain BLACK "
    "T-SHIRT, light peachy tan skin, LARGE EXPRESSIVE EYES with visible pupils "
    "and highlights, thick eyebrows, cartoon 4-finger hands. Vertical 9:16 "
    "format. Character fills 80% of frame, centered. Isolated on pure white "
    "for easy compositing in CapCut. Sharp lines, flat vibrant colors, slight "
    "drop shadow under feet. Polished professional cartoon — avoid childish or "
    "generic clipart look."
)

# ============================================================================
# PROMPTS — 6 poses cartoon restantes (eureka déjà en sample_01)
# ============================================================================
CARTOON_PROMPTS = {
    "01_michel_overwhelmed.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: OVERWHELMED / STRESSED. Michel stands facing camera, both hands "
        "raised up to his temples, mouth open in an 'AAAH' expression of panic. "
        "His eyes are WIDE with worry (visible eye whites, small pupils), "
        "eyebrows angled inward and up. A small blue SWEAT DROP on his temple. "
        "Body posture: shoulders raised, slight hunch of stress. "
        "He is standing on a small circular ground shadow, no other elements — "
        "just him overwhelmed. Around him are 4-5 small FLYING PAPERS in the "
        "air (with lines suggesting they are papers/documents), drawn cartoon "
        "style, some crumpled. Style: same viral TikTok cartoon look."
    ),
    "02_michel_calculating.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: LATE-NIGHT ADMIN STRESS. Michel is seated behind a small desk, "
        "elbow on desk, forehead resting on one hand looking exhausted. His "
        "other hand pokes at a big vintage yellow-cream CALCULATOR (drawn in "
        "cartoon style with clear button grid and small screen). His eyes are "
        "half-closed and tired, mouth in a sad flat line, small yawn visible. "
        "On the desk: a stack of papers, an open notebook, a coffee mug. "
        "A wall clock in the background shows '21:37'. Overall vibe: burnout "
        "carpenter doing admin at night after long day."
    ),
    "04_michel_phone_pointing.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: PROUD PHONE PRESENTER (Dr Cash / Ousama classic pose). Michel "
        "stands confidently facing camera, arms slightly forward, holding a "
        "modern iPhone with BOTH HANDS in front of his chest, phone facing "
        "the camera. His face has a big confident SMILE, one eyebrow slightly "
        "raised, eyes narrow and knowing (like 'check this out'). "
        "Phone screen shows the MesureChâssis app UI: bright ORANGE header "
        "'MesureChâssis' at top, a big GREEN 'TOUT VALIDÉ' badge in center, "
        "small icons below (mesures, photos, diagonales). "
        "Slight thumb up gesture optional. Overall vibe: the winner showing "
        "his secret weapon."
    ),
    "05_michel_laser.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: MEASURING PROFESSIONAL. Michel stands slightly turned, focused "
        "expression (concentrating eyebrows, tongue slightly out corner of "
        "mouth optional). He holds a GREEN LASER RANGEFINDER (Bosch-style, "
        "green plastic body, clearly a professional measuring tool) in his "
        "right hand, arm extended forward at chest level. A GREEN DASHED LINE "
        "(the laser beam) shoots from the device toward the right side of the "
        "image. In his left hand, he holds a small yellow tape measure. His "
        "eyes are focused, small ✓ green icon floats near the laser. "
        "Vibe: precise craftsman at work."
    ),
    "06_michel_shield.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: PROTECTOR / GUARDIAN. Michel stands facing camera, confident "
        "smile, one hand on hip, the other hand holds up a BLUE HEROIC SHIELD "
        "(round or triangular, blue #1E88E5 with dark blue border, a white "
        "checkmark ✓ in the center). His posture is heroic slightly leaning "
        "back — 'I got this'. Eyes confident, smug half-smile with one raised "
        "eyebrow. Small padlock icons 🔒 floating in the air around the "
        "shield to symbolize security/anti-litige. Vibe: safe, trustworthy, "
        "'your chantier is protected'."
    ),
    "07_michel_cta_pointing_down.png": (
        f"{MICHEL_BASE}\n\n"
        "POSE: ENTHUSIASTIC CTA POINTER (final scene). Michel jumps slightly "
        "in the air (both feet mid-air, exaggerated arms up), BIG open smile "
        "showing teeth, eyes closed with joy or wide with excitement. His "
        "RIGHT INDEX FINGER points DOWN dramatically toward the bottom of "
        "the frame (as if pointing at the CTA button below). His left arm is "
        "raised up in celebration. Sparkles ✨ or small stars around him "
        "showing energy. Vibe: 'DOWNLOAD IT NOW!' celebration pose."
    ),
}

# ============================================================================
# PROMPTS — 10 objets photoréalistes fond blanc
# ============================================================================
OBJ_BASE_STYLE = (
    "PURE WHITE background (#FFFFFF), studio product photography, sharp focus, "
    "no shadow behind (only very subtle contact shadow at base), 9:16 vertical "
    "framing but object centered and cropped small enough to be a sticker. "
    "Isolated for easy compositing in CapCut. Photo-realistic style, HD "
    "commercial photography quality."
)

OBJECT_PROMPTS = {
    "obj_papers.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A messy pile of paper documents, some flying/floating around, "
        "like an explosion of paperwork. Includes: a folded architectural "
        "blueprint with visible technical drawings of windows and doors, a "
        "'CAHIER DES CHARGES' cover page with French text (client name, "
        "address), a couple of crumpled sticky notes with handwritten measurements, "
        "and a torn quote/devis paper. Mid-air motion blur suggests chaos. "
        "Overall look: 'I hate paperwork'. Sepia/aged paper tones."
    ),
    "obj_calculator.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A vintage worn-out CANON or CASIO desk calculator with big "
        "grey and black buttons and an LCD screen showing '21:37' or a random "
        "calculation result. The plastic is slightly dusty, one corner "
        "scratched. Sitting at a slight angle showing the buttons clearly. "
        "This is a symbol of 'old way of working'."
    ),
    "obj_iphone_app.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A modern iPhone (space grey or titanium) standing upright, "
        "screen facing camera. Screen displays the MesureChâssis mobile app: "
        "ORANGE header bar (#F58220) with white 'MesureChâssis' logo text, "
        "a large GREEN circular badge 'TOUT VALIDÉ ✓', below it a checklist "
        "with 5 items (Mesures, Photos, Diagonales, Rendez-vous, Client) each "
        "with a green checkmark. Modern flat UI, iOS style, sharp typography. "
        "The phone has slight reflection on the glass, professional product "
        "shot look."
    ),
    "obj_laser.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A modern professional GREEN LASER DISTANCE MEASURING TOOL "
        "(Bosch GLM style), lime green and black plastic body, LCD display "
        "showing '1852 mm' or a measurement value. Small keypad visible. "
        "Positioned at slight 3/4 angle. This is a pro carpenter's tool. "
        "Optional: a thin green laser beam shooting out from the front nose."
    ),
    "obj_window.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A modern white PVC double-glazed window unit, closed, "
        "shown at slight 3/4 angle. Standard rectangular casement window with "
        "visible handle in silver. Some subtle reflection on the glass. Clean "
        "professional product shot of a new window ready to install."
    ),
    "obj_cash.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A generous stack of EURO banknotes (50€ and 100€ bills "
        "clearly visible with distinctive orange/red and green EU designs) "
        "held together with a paper band. Some coins (gold-colored 1 or 2 "
        "euro coins) piled next to the stack. Cash symbolizes profit/gain "
        "de temps = argent. Studio lit, slight top-down angle, similar to "
        "the 'Ousama Dr Cash' TikTok visual style but more premium."
    ),
    "obj_chrono.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A professional silver STOPWATCH / CHRONOMETER (old-school "
        "athletic style) with a large round face displaying '5:00' in big "
        "digital or analog style. Metallic chrome body, button on top. "
        "Slight tilt to show volume. Symbolizes 'seulement 5 minutes chrono'."
    ),
    "obj_checkmark.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A very LARGE bright green CHECKMARK ✓ symbol, chunky rounded "
        "3D style, glossy finish, floating in center of frame. Slight bevel "
        "and highlight to give it dimension. Deep vibrant green color "
        "(#22C55E). This is a bold 'validated / approved' symbol for the "
        "video."
    ),
    "obj_odoo.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: A stylized modern purple-toned business logo icon (similar "
        "in spirit to Odoo brand but a generic version) — a purple/magenta "
        "gradient rounded square badge (color #714B67) with a white letter "
        "'O' or abstract mark inside. Below or next to it, small text 'CRM' "
        "or 'ERP'. Represents integration with external business systems. "
        "Clean modern SaaS logo design, glossy."
    ),
    "obj_appstore.png": (
        f"{OBJ_BASE_STYLE}\n\n"
        "SUBJECT: Two side-by-side app store download badges displayed "
        "prominently: LEFT is the black 'Download on the App Store' Apple "
        "badge (rounded rectangle, white text, small Apple logo), RIGHT is "
        "the multicolor Google Play badge. Both drawn in official style, "
        "clean, high resolution, ready to be tapped. Under the badges, small "
        "text 'MesureChâssis · gratuit'."
    ),
}

# ============================================================================
# PROMPTS — 4 flèches vertes hand-drawn
# ============================================================================
ARROW_BASE_STYLE = (
    "PURE WHITE background (#FFFFFF), single hand-drawn green marker arrow, "
    "isolated element for compositing in CapCut. Style: like drawn with a "
    "green marker pen on paper, slight irregular line, green ink color "
    "(#22C55E), thick strokes (about 8-12 pixels wide), with a big arrow "
    "head. Casual sketchy vibe like the 'Ousama Dr Cash' TikTok arrows "
    "connecting scenes. 9:16 vertical frame but arrow itself takes maybe "
    "60-80% of frame. NO OTHER ELEMENTS — just the arrow on white."
)

ARROW_PROMPTS = {
    "arrow_down.png": (
        f"{ARROW_BASE_STYLE}\n\n"
        "SUBJECT: A single big DOWNWARD curving arrow, starting from top-left "
        "and curving down to bottom-center, ending with a big arrowhead "
        "pointing straight down."
    ),
    "arrow_right.png": (
        f"{ARROW_BASE_STYLE}\n\n"
        "SUBJECT: A single big RIGHTWARD arrow, mostly horizontal with a "
        "slight upward curve, ending with a big arrowhead pointing right. "
        "Starts from the left side of frame, ends on the right."
    ),
    "arrow_left.png": (
        f"{ARROW_BASE_STYLE}\n\n"
        "SUBJECT: A single big LEFTWARD arrow, mostly horizontal with a "
        "slight upward curve, ending with a big arrowhead pointing left. "
        "Starts from the right side of frame, ends on the left."
    ),
    "arrow_curly.png": (
        f"{ARROW_BASE_STYLE}\n\n"
        "SUBJECT: A dramatic CURLY / SWIRLY arrow that makes a small loop "
        "before ending with a big arrowhead pointing down and to the right. "
        "Very expressive and dynamic, like an excited annotation on paper. "
        "Loose sketchy style."
    ),
}

# ============================================================================
# PROMPTS — 2 photos réalistes supplémentaires (sample_02 déjà OK)
# ============================================================================
PHOTO_PROMPTS = {
    "real_michel_portrait.png": (
        "Vertical 9:16 ULTRA photorealistic close-up portrait photograph. "
        "SUBJECT: Michel, Belgian male carpenter in early 30s, same person "
        "as in the previous shot: short brown hair, light stubble, warm "
        "friendly confident smile, wearing dark grey MesureChâssis-branded "
        "work vest with small orange logo. He is looking directly at camera, "
        "half body shot, arms crossed proudly across his chest showing "
        "confidence and authority. "
        "\n\n"
        "BACKGROUND: Out of focus modern residential construction site, "
        "beautiful bokeh, subtle warm sunset light. Behind him: hints of a "
        "newly installed window frame and wooden house facade in warm golden "
        "hour tones. "
        "\n\n"
        "LIGHTING: Warm cinematic golden hour, rim light on hair and "
        "shoulders, soft natural fill on face. Slight lens flare. Sharp focus "
        "on his eyes and smile. "
        "\n\n"
        "MOOD: The proud craftsman who solved his own problem, testimonial "
        "vibe. Authentic Belgian carpenter, not a model. Realistic skin, "
        "natural expression. High-end commercial SaaS ad photography, similar "
        "to Apple product shots. AVOID: cartoon look, plastic AI face, "
        "generic stock photo feel."
    ),
    "real_team_menuisiers.png": (
        "Vertical 9:16 ULTRA photorealistic group photograph, high-end "
        "commercial SaaS advertising style. "
        "SUBJECT: THREE Belgian male carpenters in their 30s-40s, standing "
        "close together outside a construction site, all wearing dark grey "
        "or blue work jackets/vests (one with a small orange MesureChâssis "
        "logo). Different builds and slight age variation for diversity: one "
        "with beard and dark hair, one clean-shaven with lighter hair, one "
        "with a cap. All smiling naturally, warm and confident. Each holds "
        "a smartphone showing the same orange MesureChâssis app (screens can "
        "be slightly out of focus). Casual pose, arms around each other's "
        "shoulders or looking friendly. "
        "\n\n"
        "BACKGROUND: A residential construction site with a modern wooden "
        "chalet in Belgian countryside style, pine trees, warm golden hour "
        "sunset light. A yellow tape measure and cordless drill visible on "
        "a concrete windowsill behind them (blurred bokeh). "
        "\n\n"
        "LIGHTING: Warm sunset backlight creating strong rim light on their "
        "silhouettes. Soft natural fill on faces. Slight lens flare. "
        "\n\n"
        "MOOD: Team of trusted professional carpenters. 'The tool that "
        "carpenters use'. Authentic and warm. AVOID: model-looking, cartoon "
        "faces, stock photo feel."
    ),
}


# ============================================================================
# BATCH RUNNER
# ============================================================================
async def generate_one(prompt: str, filename: str, label: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"video-pub-45s-{filename}",
        system_message=(
            "You are a world-class illustrator and commercial photographer "
            "creating premium marketing assets for a Belgian SaaS mobile app "
            "targeting professional carpenters. Deliver polished professional "
            "results matching modern TikTok viral advertising aesthetics."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )

    msg = UserMessage(text=prompt)
    t0 = time.time()

    try:
        _text, images = await chat.send_message_multimodal_response(msg)
        if not images:
            print(f"⚠️  [{filename}] Aucune image générée")
            return False

        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        output_path = OUTPUT_DIR / filename
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        dur = time.time() - t0
        print(f"✅ [{filename}] {len(image_bytes) // 1024} KB · {dur:.1f}s · {label}")
        return True
    except Exception as e:
        print(f"❌ [{filename}] Erreur : {e}")
        return False


async def main():
    print("🎬 GÉNÉRATION BATCH 22 assets — Pub 45s MesureChâssis")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

    # Assemble all prompts
    all_prompts = []
    all_prompts.extend(
        [(p, f, "Cartoon Michel") for f, p in CARTOON_PROMPTS.items()]
    )
    all_prompts.extend(
        [(p, f, "Objet réaliste") for f, p in OBJECT_PROMPTS.items()]
    )
    all_prompts.extend(
        [(p, f, "Flèche verte") for f, p in ARROW_PROMPTS.items()]
    )
    all_prompts.extend(
        [(p, f, "Photo réaliste") for f, p in PHOTO_PROMPTS.items()]
    )

    total = len(all_prompts)
    print(f"📋 {total} assets à générer\n")

    ok_count = 0
    fail_count = 0
    t_start = time.time()

    for idx, (prompt, filename, label) in enumerate(all_prompts, 1):
        # Skip if already exists (allows restarts)
        if (OUTPUT_DIR / filename).exists():
            print(f"⏭️  [{idx}/{total}] {filename} → déjà existant, skip")
            ok_count += 1
            continue

        print(f"⏳ [{idx}/{total}] {filename} ({label}) ...")
        ok = await generate_one(prompt, filename, label)
        if ok:
            ok_count += 1
        else:
            fail_count += 1
        # Petite pause pour éviter rate limit
        await asyncio.sleep(1.5)

    dur_total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"📊 RÉSULTAT FINAL : {ok_count}/{total} OK · {fail_count} échecs")
    print(f"⏱️  Durée : {dur_total/60:.1f} min")
    print(f"📂 Assets dans : {OUTPUT_DIR}")
    print(f"{'='*60}")

    # List all files
    print("\n📄 Fichiers présents :")
    for f in sorted(OUTPUT_DIR.iterdir()):
        size_kb = f.stat().st_size // 1024
        print(f"  • {f.name} ({size_kb} KB)")


if __name__ == "__main__":
    asyncio.run(main())
