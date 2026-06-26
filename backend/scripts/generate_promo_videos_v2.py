"""
Script de génération des 2 vidéos promotionnelles MesureChâssis — V2.

V2 amélioration :
- reference_image fixe (le menuisier réel) sur les 9 clips → continuité personnage
- CHARACTER_DESCRIPTION ultra-détaillée (gilet HV jaune+orange, barbe 3 jours)
- SILENT_INSTRUCTION explicite (bouche fermée, mime, pas de dialogue)
- APP_UI_DESCRIPTION fidèle (header CHANTIER + liste châssis #20 #21... + badge À VALIDER)
- Cahier des charges au lieu de plan architectural

Usage:
    cd /app/backend && python -m scripts.generate_promo_videos_v2
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")
if not EMERGENT_LLM_KEY:
    print("❌ EMERGENT_LLM_KEY manquante dans .env")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo")
CLIPS_DIR = OUTPUT_DIR / "clips_v2"
REFS_DIR = OUTPUT_DIR / "refs"
CARPENTER_REF = REFS_DIR / "carpenter_ref.png"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

if not CARPENTER_REF.exists():
    print(f"❌ Reference image manquante : {CARPENTER_REF}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────
# CONSTANTES — Reprises à l'identique dans CHAQUE prompt pour garantir
# la cohérence visuelle (personnage, style, mode silencieux, UI app).
# ─────────────────────────────────────────────────────────────────────────

CHARACTER_DESCRIPTION = (
    "The main character is a European male carpenter, 38-42 years old, with "
    "short dark brown hair slightly textured on top, a neatly trimmed "
    "3-day stubble beard of the same dark brown color, an oval-square face "
    "shape with a defined jawline, prominent cheekbones, a straight nose, "
    "and bushy but well-shaped eyebrows. He wears a distinctive high-"
    "visibility work jacket: bright fluorescent yellow front and sleeves "
    "with orange/rust-colored panels on the shoulders and upper back, "
    "wide horizontal silver reflective stripes on chest, arms, and waist, "
    "and an attached hood that can be up or down. Underneath the HV "
    "jacket, a dark gray/black collar is visible. He has a solid medium "
    "build, with a focused, professional demeanor. THIS EXACT SAME "
    "CHARACTER must appear in this scene, matching the reference image "
    "exactly. "
)

SILENT_INSTRUCTION = (
    "CRITICAL: The character does NOT speak. His mouth stays closed at "
    "all times. No talking, no dialogue, no lip movement. Pure silent "
    "mime acting, expressive body language and facial expressions only — "
    "universal visual storytelling that works in any language. "
)

STYLE = (
    "3D animated cartoon style, Pixar-inspired warm look, vibrant "
    "colors, slightly stylized but realistic facial features, clean "
    "modern aesthetic, smooth cinematic camera motion, professional "
    "B2B brand video quality, no text overlays, no logos. "
)

APP_UI_DESCRIPTION = (
    "The smartphone screen shows a mobile app interface with a pure "
    "BLACK background. At the top: a horizontal white-text header reading "
    "'CHANTIER' (with a back arrow icon to its left). Below the header: a "
    "vertical scrollable list of identical rectangular cards on dark gray. "
    "Each card has on the left a small square icon depicting a window "
    "(rectangle with vertical divider inside), then text like '#20 · "
    "Fenêtre coulissante 4' on one line and 'Coulissant levant' in "
    "smaller gray text below, and on the right a small ORANGE pill-shaped "
    "badge with the text 'À VALIDER'. At the very bottom of the screen, "
    "two side-by-side buttons: left button outlined gray reading "
    "'CLÔTURER' with a flag icon, right button solid ORANGE (#FF5A00) "
    "reading '+ AJOUTER'. Modern dark theme UI, professional mobile app. "
)


def base_prompt(scene_specific: str) -> str:
    """Assemble le prompt complet avec toutes les contraintes."""
    return (
        f"{STYLE}{CHARACTER_DESCRIPTION}{SILENT_INSTRUCTION}{scene_specific}"
    )


# ─────────────────────────────────────────────────────────────────────────
# VIDÉO 1 — "La galère sans MesureChâssis"
# ─────────────────────────────────────────────────────────────────────────

VIDEO_1_CLIPS = [
    {
        "name": "v1_s1_office_leaving",
        "prompt": base_prompt(
            "Scene: The carpenter is in a modern small carpentry workshop "
            "office in the morning. Warm sunlight streams through the "
            "window. On his wooden desk lies a paper notebook (cahier des "
            "charges / specification document) showing a printed list of "
            "windows. He picks up the notebook and walks toward the exit "
            "door with a confident, relaxed smile. CRITICAL ELEMENT: a "
            "single blue ballpoint pen sits VERY CLEARLY in focus on the "
            "edge of the desk, abandoned, in the foreground — the camera "
            "lingers briefly on it. He DOES NOT notice the pen. He walks "
            "out, hood down. Cinematic shallow depth of field."
        ),
    },
    {
        "name": "v1_s2_construction_site_no_pen",
        "prompt": base_prompt(
            "Scene: The same carpenter is now standing outside in front of "
            "a residential European construction site with bricks and "
            "scaffolding visible. Bright midday natural light, blue sky "
            "starting to gray. He holds the paper notebook (cahier des "
            "charges with list of windows) open in one hand. He pats his "
            "chest pocket, then his pants pockets, then his jacket inside "
            "pocket, searching for a pen. His face transitions from "
            "confident → puzzled → frustrated. He looks at his empty palm. "
            "Close-up on face then medium shot showing him standing alone "
            "next to the windows of the building."
        ),
    },
    {
        "name": "v1_s3_rain_starts",
        "prompt": base_prompt(
            "Scene: Same carpenter, same construction site. The sky has "
            "turned gray. Raindrops begin to fall — slowly at first, then "
            "heavily. The paper cahier des charges in his hand gets soaked, "
            "ink running, paper crumpling. He tries to shield it with his "
            "free hand but it's hopeless. He pulls his HV jacket hood up "
            "over his head — water drips from the hood edge. His face "
            "shows pure frustration and resignation. He throws his head "
            "back briefly in despair. Dramatic cinematic rain in slight "
            "slow motion."
        ),
    },
    {
        "name": "v1_s4_office_colleague_solution",
        "prompt": base_prompt(
            "Scene: The same carpenter is back inside the workshop office, "
            "still wearing the HV jacket (hood now down) but completely "
            "soaked — water dripping from his hair, his beard wet, jacket "
            "visibly drenched and darker from rain. He looks defeated, "
            "shoulders slumped, holding the ruined soggy paper notebook. "
            "A second character — a colleague (a different European man "
            "in his 30s, wearing a casual blue carpenter polo, clean and "
            "dry, friendly smiling face) — approaches him from the side "
            "and gently shows him a smartphone screen. The smartphone "
            "screen displays a clean mobile app interface with orange "
            "accent color (#FF5A00) showing a list of window measurements. "
            "The wet carpenter's eyes widen with surprise and hope, a "
            "small smile starting to form. Warm interior lighting."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────
# VIDÉO 2 — "La magie avec MesureChâssis"
# ─────────────────────────────────────────────────────────────────────────

VIDEO_2_CLIPS = [
    {
        "name": "v2_s1_specdoc_on_table",
        "prompt": base_prompt(
            "Scene: Top-down view of a wooden workshop desk. On the desk "
            "lies a printed paper SPECIFICATION DOCUMENT (cahier des "
            "charges) — multiple A4 pages stapled together, showing a "
            "structured printed list of windows: 'Fenêtre 1: 1200x1500mm', "
            "'Fenêtre 2: 800x1200mm', 'Fenêtre 3...', technical fields, "
            "numbered rows. The same carpenter's hands enter the frame "
            "from below, holding a smartphone. He places the smartphone "
            "above the document pages. Warm desk lamp lighting, cinematic "
            "establishing shot with close-up on the paper detail."
        ),
    },
    {
        "name": "v2_s2_taking_photo_of_specdoc",
        "prompt": base_prompt(
            "Scene: Continuing from the previous shot — the same carpenter "
            "(visible from chest-up wearing his HV jacket) holds his "
            "smartphone above the open cahier des charges document on the "
            "desk. The phone's camera viewfinder is clearly visible on "
            "screen, framing the printed list of windows on the paper. "
            "Corner-detection brackets align around the document edges. "
            "He taps the capture button with his thumb — a quick white "
            "flash on the phone screen. Focused, professional expression. "
            "Close-up over-the-shoulder shot."
        ),
    },
    {
        "name": "v2_s3_app_shows_chassis_to_validate",
        "prompt": base_prompt(
            f"Scene: Close-up of the smartphone screen filling 80% of the "
            f"frame, held in the carpenter's hand. {APP_UI_DESCRIPTION}"
            "The cards animate by appearing one at a time from top to "
            "bottom: card '#20 · Fenêtre coulissante 4' with orange 'À "
            "VALIDER' badge fades in, then card '#21 · Fenêtre coulissante "
            "5' fades in, then card '#22 · Fenêtre coulissante Salle...', "
            "then card '#23 · Fenêtre coulissante 2'. Each badge gently "
            "pulses softly to draw attention. Smooth, polished mobile UI "
            "motion design. No special effects, no particles — clean "
            "professional software demonstration."
        ),
    },
    {
        "name": "v2_s4_site_measuring_then_validate",
        "prompt": base_prompt(
            "Scene: The same carpenter is now back on the residential "
            "construction site (same setting as Video 1 but now bright "
            "sunny weather, blue sky, no rain). His HV jacket is dry, "
            "hood down. He holds a laser distance meter in his left hand "
            "and his smartphone in his right hand. He points the laser "
            "at a window frame — the laser meter screen shows '1240 mm'. "
            "Close-up shifts to his smartphone screen which shows a "
            "window-editing form with dimension fields filled, and a "
            "LARGE PROMINENT ORANGE button at the bottom labeled "
            "'VALIDER'. His thumb presses the orange button — a green "
            "checkmark animation appears, and the orange 'À VALIDER' "
            "badge on the card transitions into a GREEN 'VALIDÉ ✓' badge. "
            "His face shows quiet satisfaction and professional control. "
            "Smooth camera movement."
        ),
    },
    {
        "name": "v2_s5_back_to_office_serene",
        "prompt": base_prompt(
            "Scene: The same carpenter walks back into his workshop office "
            "(same setting as Video 1 scene 1). Late afternoon golden hour "
            "warm orange light streams through the window. He walks in "
            "with a relaxed, content, slightly proud expression — total "
            "calm. He gently places his smartphone on his clean organized "
            "desk (no crumpled paper, no mess). He stretches his arms "
            "above his head in a satisfied 'mission accomplished' gesture. "
            "He picks up a coffee mug from the desk, sits down in his "
            "office chair, glances one last time at his smartphone with a "
            "small proud closed-mouth smile. Hero final shot, golden-hour "
            "uplifting serene mood."
        ),
    },
]


def generate_clip(client: OpenAIVideoGeneration, clip_spec: dict) -> Path | None:
    """Génère un clip Sora 2 avec reference_image fixe (continuité personnage)."""
    name = clip_spec["name"]
    output = CLIPS_DIR / f"{name}.mp4"
    if output.exists() and output.stat().st_size > 1000:
        print(f"⏭️  {name}: déjà existant ({output.stat().st_size // 1024} KB), skip")
        return output

    print(f"\n🎬 Génération {name}…")
    t0 = time.time()
    video_bytes = client.text_to_video(
        prompt=clip_spec["prompt"],
        model="sora-2",
        size="1280x720",
        duration=8,
        max_wait_time=900,
        # Note: image_path supprimé — le proxy Emergent ne supporte pas
        # le paramètre `reference_image` pour Sora 2. On compte uniquement
        # sur la description textuelle ultra-détaillée du personnage.
    )
    elapsed = int(time.time() - t0)
    if not video_bytes:
        print(f"❌ {name}: échec après {elapsed}s")
        return None
    output.write_bytes(video_bytes)
    print(f"✅ {name}: {len(video_bytes) // 1024} KB en {elapsed}s")
    return output


def strip_audio(input_path: Path) -> Path:
    output = input_path.with_name(f"{input_path.stem}_silent.mp4")
    if output.exists():
        return output
    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-c:v", "copy", "-an",
           str(output)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ Strip audio failed: {r.stderr[-200:]}")
        return input_path
    return output


def concat_clips(clip_paths: list[Path], output_path: Path) -> bool:
    list_file = output_path.parent / f".concat_{output_path.stem}.txt"
    with list_file.open("w") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
           "-c:v", "libx264", "-preset", "medium", "-crf", "23",
           "-pix_fmt", "yuv420p", "-an", str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    if r.returncode != 0:
        print(f"❌ Concat failed: {r.stderr[-300:]}")
        return False
    return True


def assemble_video(clips_spec: list[dict], output_name: str) -> Path | None:
    silent_clips = []
    for spec in clips_spec:
        clip_path = CLIPS_DIR / f"{spec['name']}.mp4"
        if not clip_path.exists():
            print(f"❌ Clip manquant: {clip_path}")
            return None
        silent = strip_audio(clip_path)
        silent_clips.append(silent)
    output = OUTPUT_DIR / output_name
    print(f"\n🪡 Assemblage {output_name} ({len(silent_clips)} clips)…")
    if concat_clips(silent_clips, output):
        print(f"✅ {output_name}: {output.stat().st_size // 1024} KB")
        return output
    return None


def main():
    print("=" * 70)
    print("🎬 MesureChâssis — Génération V2 (continuité + silencieux + UI réelle)")
    print("=" * 70)
    print(f"   Reference image : {CARPENTER_REF}")
    print(f"   Output clips    : {CLIPS_DIR}")
    print(f"   Output finals   : {OUTPUT_DIR}")
    print("=" * 70)

    client = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)

    print("\n📦 PHASE 1 — Génération des 9 clips Sora 2 (~15-20 min)")
    all_specs = VIDEO_1_CLIPS + VIDEO_2_CLIPS
    failures = []
    for spec in all_specs:
        try:
            result = generate_clip(client, spec)
            if not result:
                failures.append(spec["name"])
        except Exception as e:
            print(f"❌ {spec['name']}: exception {e}")
            failures.append(spec["name"])

    if failures:
        print(f"\n⚠️  Clips échoués : {failures}")
        print("Relancez le script pour retry les clips manquants.")
        sys.exit(1)

    print("\n📦 PHASE 2 — Assemblage ffmpeg")
    v1 = assemble_video(VIDEO_1_CLIPS, "video1_galere_v2.mp4")
    v2 = assemble_video(VIDEO_2_CLIPS, "video2_magie_v2.mp4")

    print("\n" + "=" * 70)
    if v1 and v2:
        print("🎉 SUCCÈS — Vidéos V2 prêtes !")
        print(f"   📹 Vidéo 1 (galère) : {v1}")
        print(f"   📹 Vidéo 2 (magie)  : {v2}")
        print("\n   URLs publiques :")
        print("   - /api/promo/video1_galere_v2.mp4")
        print("   - /api/promo/video2_magie_v2.mp4")
    else:
        print("⚠️  Assemblage partiel")
    print("=" * 70)


if __name__ == "__main__":
    main()
