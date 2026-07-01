"""
🎬 TikTok Script #6 — "Tableau vs Baie : l'erreur à 5cm"

  - 15 slides ULTRA DYNAMIQUES (rythme viral TikTok ~2.5s/image)
  - Voix Nova féminine, sans prix, CTA gratuit
  - Slide 15 = affiche outro fond noir premium
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

OUTPUT_DIR = Path("/app/backend/static/promo/tiktok_script6")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALU_STYLE = (
    "Vertical 9:16 portrait, photorealistic ULTRA high quality, "
    "professional French aluminum carpentry context, anthracite grey or "
    "black aluminum window frames (modern Schüco/Reynaers profile), "
    "modern CONCRETE house facade or contemporary architecture in "
    "background, cinematic golden hour lighting, high-end B2B SaaS "
    "marketing visual, premium quality, sharp focus, shallow depth of field"
)

VOICE_SCRIPT = (
    "L'erreur qui te coûte un châssis entier. Tu arrives sur chantier. "
    "Ouverture nickel, murs bruts. Tu sors ton mètre. Tu mesures : "
    "mille cent quatre-vingt-quinze par deux mille cent quarante-cinq. "
    "Tu notes. T'es content. Trois semaines plus tard, jour de pose. Le "
    "châssis n'entre pas. Cinq centimètres de vide tout autour. Le "
    "drame. Tu viens de mesurer la BAIE, pas le TABLEAU. La baie, c'est "
    "l'ouverture finie. Le tableau, c'est le trou brut, plus grand. "
    "Avec MesureChâssis, l'application te demande à chaque fois : "
    "tableau ou baie ? Elle te bloque si tu confonds. Zéro châssis foutu. "
    "Viens la télécharger gratuitement. Lien en bio."
)

SLIDES = [
    # 1 — HOOK dramatique
    (
        "01_hook.png",
        "dark charcoal background (#0C0C0E), giant dramatic typography "
        "in vibrant orange (#FF6F00) reading 'L'ERREUR A 5 CM', bold "
        "sans-serif French uppercase, subtle broken/cracked measurement "
        "line background effect, cinematic dramatic lighting, "
        "TikTok-style attention-grabbing first frame, minimalist",
    ),
    # 2 — Arrivée chantier
    (
        "02_arrivee_chantier.png",
        "wide shot of a French male carpenter (40s, anthracite work "
        "jacket, tape measure clipped to belt) walking confidently "
        "toward a modern raw concrete villa facade with a large "
        "aluminum window opening, morning golden light, professional "
        "B2B mood, hero-shot approach",
    ),
    # 3 — POV ouverture brute
    (
        "03_ouverture_brute.png",
        "first-person POV looking at a large raw concrete wall opening "
        "(tableau brut) with rough concrete edges, no plaster or finish "
        "yet, exposed steel lintel on top, morning daylight streaming "
        "through, French construction site, wide angle",
    ),
    # 4 — Sortir le mètre
    (
        "04_metre_ouvert.png",
        "close-up dynamic action shot of a male carpenter's hand "
        "pulling open a yellow Stanley Fatmax measuring tape, tape "
        "ribbon in motion, sharp focus on the metallic thumb-lock, "
        "concrete wall in blurred background, dramatic side light",
    ),
    # 5 — MAUVAISE mesure (BAIE finie)
    (
        "05_mesure_baie.png",
        "photorealistic close-up: carpenter's yellow measuring tape "
        "stretched horizontally across a FINISHED window opening (baie) "
        "with plaster edges already smooth and flat, reading '1195 mm' "
        "visible on the tape, warm interior lighting, this is the WRONG "
        "reference point to measure",
    ),
    # 6 — Note sur carnet
    (
        "06_carnet_note.png",
        "top-down close-up of a small worn Moleskine-style notebook "
        "opened on a dark wooden workbench, black pen writing "
        "handwritten measurements '1195 × 2145 mm' in French carpenter "
        "style, tape measure and pencil around, warm workshop lighting, "
        "shallow depth of field",
    ),
    # 7 — Retour atelier (content)
    (
        "07_atelier_content.png",
        "wide shot of a modern aluminum carpentry workshop, "
        "anthracite aluminum profiles neatly stacked, carpenter in "
        "background smiling confidently with the notebook in hand, "
        "warm industrial LED lighting, cinematic professional mood",
    ),
    # 8 — Fabrication du châssis
    (
        "08_fabrication.png",
        "close-up of automated aluminum window frame assembly in a "
        "modern workshop, silver aluminum profiles being cut/welded, "
        "sparks and precision, industrial B2B photography, deep blue "
        "and orange color grade, hero product shot",
    ),
    # 9 — Livraison jour de pose
    (
        "09_livraison.png",
        "wide shot of a large finished anthracite aluminum window "
        "frame being carefully carried by two carpenters into a modern "
        "concrete villa construction site, blue sky, professional "
        "installation crew, editorial mood",
    ),
    # 10 — CHÂSSIS N'ENTRE PAS (dramatic)
    (
        "10_ne_rentre_pas.png",
        "dramatic photo of a finished anthracite aluminum window frame "
        "placed inside a raw concrete opening (tableau), with obvious "
        "5cm gap of empty space visible around all sides, carpenter's "
        "hand on head expressing frustration, red warning tint overlay, "
        "cinematic despair mood",
    ),
    # 11 — Zoom sur l'écart 5cm
    (
        "11_ecart_5cm.png",
        "extreme close-up macro shot of the empty 5 centimeter gap "
        "between the aluminum window frame edge and the raw concrete "
        "wall, yellow measuring tape stretched across showing exactly "
        "'50 mm', bold red arrow indicator, harsh dramatic lighting, "
        "technical failure documentation style",
    ),
    # 12 — Client fâché
    (
        "12_client_fache.png",
        "medium shot of a French male client (50s, casual smart "
        "attire) crossed arms with disapproving frowning expression, "
        "standing in front of a construction site with the failed "
        "window installation blurred behind him, natural daylight, "
        "editorial reportage style",
    ),
    # 13 — Diagramme technique Tableau vs Baie
    (
        "13_schema_tableau_baie.png",
        "clean technical architectural diagram showing side-by-side "
        "comparison: LEFT rectangle labeled 'TABLEAU' (raw concrete "
        "opening, larger) with dimensions 1245 × 2195 mm, RIGHT "
        "rectangle labeled 'BAIE' (finished opening, smaller) with "
        "1195 × 2145 mm, orange (#FF6F00) accent labels, minimalist "
        "white background, architectural blueprint style, French "
        "carpentry education infographic",
    ),
    # 14 — App demande Tableau ou Baie ?
    (
        "14_app_prompt.png",
        "photorealistic smartphone screen close-up showing MesureChâssis "
        "app: a large modal dialog in the center with two big buttons: "
        "'TABLEAU (brut)' with a rough opening icon (orange background) "
        "and 'BAIE (finie)' with a smooth opening icon (grey border), "
        "title in bold dark grey 'Tu mesures quoi ?', orange header "
        "'MesureChâssis', native iOS flat UI, hand of carpenter holding "
        "phone, blurred alu window in background",
    ),
    # 15 — AFFICHE OUTRO fond noir
    (
        "15_outro.png",
        "Premium marketing outro poster, PURE BLACK background "
        "(#000000) with very subtle orange radial glow behind the logo. "
        "Composition top-to-bottom: "
        "(1) Large centered MesureChâssis logo (orange window-frame "
        "icon + white wordmark 'MesureChâssis' in bold sans-serif). "
        "(2) Bold white uppercase headline '20+ MESURES PROFESSIONNELLES'. "
        "(3) Small elegant tagline in warm light-grey "
        "'L'app des menuisiers alu' (italic). "
        "(4) Thin orange horizontal divider line. "
        "(5) Vibrant orange (#FF6F00) rounded CTA button 'TÉLÉCHARGE "
        "GRATUITEMENT' in white bold text. "
        "(6) Bottom line in medium grey 'sur mesurechassis.com'. "
        "Ultra-clean minimalist modern SaaS marketing final slide, "
        "premium editorial typography (Inter / SF Pro), 9:16 vertical, "
        "TikTok outro card style",
    ),
]


async def generate_image(filename: str, prompt: str) -> bool:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    if filename == "15_outro.png":
        full_prompt = prompt
    else:
        full_prompt = ALU_STYLE + ". " + prompt

    chat = LlmChat(
        api_key=API_KEY,
        session_id=f"tiktok-script6-{filename}",
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


async def retry_failed(failed_list):
    """Réessaye une seule fois les slides qui ont échoué."""
    if not failed_list:
        return
    print(f"\n🔄 Retry {len(failed_list)} slide(s) échouée(s)...")
    for filename, prompt in failed_list:
        await asyncio.sleep(2)
        await generate_image(filename, prompt)


async def main():
    print("🎬 TikTok Script #6 — Tableau vs Baie (15 slides ULTRA DYNAMIQUE)")
    print(f"📂 Sortie : {OUTPUT_DIR}\n")

    print("🖼️  Génération des 15 images (Gemini Nano Banana)...")
    failed = []
    success = 0
    for filename, prompt in SLIDES:
        if await generate_image(filename, prompt):
            success += 1
        else:
            failed.append((filename, prompt))
    print(f"   📊 {success}/{len(SLIDES)} images générées\n")

    if failed:
        await retry_failed(failed)

    print("\n🎙️  Génération voix-off (Nova féminine)...")
    await generate_voiceover()

    print("\n✅ Terminé !")
    base = (
        "https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script6"
    )
    print("\n📥 URLs publiques :")
    for filename, _ in SLIDES:
        print(f"   {base}/{filename}")
    print(f"   {base}/voiceover.mp3")


if __name__ == "__main__":
    asyncio.run(main())
