"""
Script de génération des 2 vidéos promotionnelles MesureChâssis.

Génère 8 clips Sora 2 (4 par vidéo), strip audio, concat ffmpeg → 2 MP4 finaux.

Coût estimé : ~15-25 $ via Emergent LLM key (sora-2, 8 clips × 8s en 720p).

Usage:
    cd /app/backend && python -m scripts.generate_promo_videos

Sortie:
    /app/backend/static/promo/video1_galere.mp4   (~32 sec, muet)
    /app/backend/static/promo/video2_magie.mp4    (~32 sec, muet)
    /app/backend/static/promo/clips/*.mp4         (clips bruts conservés)
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Charger .env (clé Emergent LLM)
load_dotenv()

from emergentintegrations.llm.openai.video_generation import OpenAIVideoGeneration

EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")
if not EMERGENT_LLM_KEY:
    print("❌ EMERGENT_LLM_KEY manquante dans .env")
    sys.exit(1)

OUTPUT_DIR = Path("/app/backend/static/promo")
CLIPS_DIR = OUTPUT_DIR / "clips"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────
# STORYBOARDS — 3D animation style (Pixar-light), sans dialogue, narratif visuel
# Style commun : 3D cartoon, couleurs chaudes, personnages stylisés, expressions
# faciales très lisibles. Pas de texte dans les vidéos (sous-titres ajoutés
# plus tard si besoin par Michel via Premiere/CapCut).
# ─────────────────────────────────────────────────────────────────────────

COMMON_STYLE = (
    "3D animated cartoon style, Pixar-inspired, warm lighting, vibrant colors, "
    "stylized realistic characters with expressive faces, clean modern look, "
    "no text on screen, no logos visible, smooth camera motion, professional "
    "B2B brand-friendly aesthetic. "
)

VIDEO_1_CLIPS = [
    {
        "name": "v1_s1_office_leaving",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: A 3D cartoon carpenter character (40 years old, friendly face, "
            "wearing a navy blue work polo shirt with rolled-up sleeves) in a "
            "small modern carpentry workshop office. He grabs a paper sheet "
            "with hand-drawn window measurements from his desk and walks toward "
            "the door, smiling, confident. A pen is clearly visible LEFT BEHIND "
            "on the desk, in focus. He doesn't notice it. Morning sunlight "
            "through the window. Wide shot, cinematic depth of field."
        ),
    },
    {
        "name": "v1_s2_construction_site_no_pen",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Same 3D cartoon carpenter now standing outside, in front of "
            "a residential construction site with bricks and scaffolding. He "
            "holds the paper measurement sheet in one hand. He pats his chest "
            "pocket, then his pants pockets — searching frantically for a pen. "
            "His face shifts from confident to confused to frustrated. He looks "
            "at his empty palm. The paper sheet visibly empty (no measurements "
            "written yet). Mid-day natural light. Close-up of his face then "
            "wide shot of him in front of the windows to measure."
        ),
    },
    {
        "name": "v1_s3_rain_starts",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Same 3D cartoon carpenter, still at the construction site, "
            "now visibly annoyed. Suddenly raindrops start falling — first slow, "
            "then heavier. The paper measurement sheet in his hand gets wet and "
            "begins to crumple and disintegrate. He tries to shield it with his "
            "other hand but it's hopeless. Stormy gray clouds overhead. His "
            "expression: pure frustration and resignation. He throws his head "
            "back in despair. Cinematic raindrops in slow motion, dramatic mood."
        ),
    },
    {
        "name": "v1_s4_office_colleague_solution",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Same 3D cartoon carpenter back in the workshop office, "
            "soaking wet, hair dripping, holding the destroyed soggy paper. He "
            "looks defeated, slumped against the wall. A second 3D cartoon "
            "character — a younger female colleague (30 years old, friendly "
            "smile, wearing a light blue polo) — approaches him and gently "
            "shows him a smartphone screen. On the smartphone screen we see a "
            "clean modern mobile app interface with orange accent colors (the "
            "MesureChâssis brand orange #FF5A00) showing window measurements "
            "neatly organized. The carpenter's eyes widen with surprise and "
            "hope. A small lightbulb expression. Warm interior lighting."
        ),
    },
]

VIDEO_2_CLIPS = [
    {
        "name": "v2_s1_plan_on_table",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Top-down 3D cartoon shot of a wooden workshop desk. On the "
            "desk: a large architectural plan/blueprint showing the front "
            "facade elevation of a modern European house with multiple windows "
            "of different sizes (rectangular, square, arched). The plan has "
            "clean technical drawing style — black lines on white paper, "
            "dimensions labels. A 3D cartoon carpenter's hands enter frame, "
            "holding a smartphone. Warm desk lamp lighting. Cinematic close-up "
            "establishing shot."
        ),
    },
    {
        "name": "v2_s2_taking_photo",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Continuing from previous scene. 3D cartoon carpenter holds "
            "his smartphone above the architectural plan on the desk, framing "
            "the facade drawing in the phone's camera viewfinder. We see the "
            "phone screen clearly showing the live camera view of the plan, "
            "with corner-detection brackets aligning on the drawing. He taps "
            "the capture button — a quick white flash on screen. Subtle camera "
            "shutter sound visual effect (light ripple). His face concentrated, "
            "professional. Close-up over-the-shoulder shot."
        ),
    },
    {
        "name": "v2_s3_ai_detecting_with_to_validate_badges",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: Close-up of a smartphone screen filling 80% of the frame. "
            "The phone shows a photo of an architectural facade blueprint with "
            "several window outlines. Orange rectangle outlines (color #FF5A00) "
            "appear gently one after another around each window in the "
            "blueprint, each accompanied by a small green checkmark icon. A "
            "side panel slides in smoothly from the right showing a clean list "
            "of items: 'Window 1', 'Window 2', 'Window 3', 'Window 4', each "
            "row displaying numerical dimensions like '1200 x 1500 mm'. Each "
            "row also shows a small orange rounded pill label with the text "
            "'TO VALIDATE' gently fading in and out. Modern professional "
            "mobile app interface, dark theme background with orange accents. "
            "Clean software demonstration aesthetic, no special effects, no "
            "particles, just polished UI motion design."
        ),
    },
    {
        "name": "v2_s4_back_on_site_measure_and_validate",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: The 3D cartoon carpenter is back on the sunny residential "
            "construction site (same setting as Video 1, but now blue sky, "
            "bright sunshine). He holds a laser distance meter in one hand "
            "and his smartphone in the other. He points the laser at a window "
            "frame — the laser meter display shows '1240 mm'. Then close-up "
            "shift to the smartphone screen showing a window-editing screen "
            "of the app with dimensions filled in, and a large prominent "
            "ORANGE 'VALIDATE' button at the bottom. His thumb presses the "
            "button — a satisfying green checkmark animation appears, and the "
            "small orange 'TO VALIDATE' badge transforms into a GREEN "
            "'VALIDATED ✓' badge. His face shows satisfaction and control. "
            "Smooth camera motion. Confident, professional mood."
        ),
    },
    {
        "name": "v2_s5_back_to_office_serene",
        "prompt": (
            f"{COMMON_STYLE}"
            "Scene: The 3D cartoon carpenter walks back into his workshop "
            "office (same setting as Video 1's first scene). Warm late-day "
            "lighting — golden hour orange sunset through the window. He "
            "walks in with a relaxed, confident, smiling expression — total "
            "calm. He places his smartphone gently on the desk and stretches "
            "his arms above his head in a 'mission accomplished' gesture. The "
            "desk is clean and organized — no crumpled paper in sight. He "
            "picks up a coffee mug, sits in his armchair, looks at his "
            "smartphone one last time with a small proud smile. Hero final "
            "shot, 'perfect end of day' mood, uplifting and serene."
        ),
    },
]


def generate_clip(client: OpenAIVideoGeneration, clip_spec: dict) -> Path | None:
    """Génère un clip Sora 2 et le sauve."""
    name = clip_spec["name"]
    output = CLIPS_DIR / f"{name}.mp4"
    if output.exists() and output.stat().st_size > 1000:
        print(f"⏭️  {name}: déjà existant ({output.stat().st_size // 1024} KB), skip")
        return output

    print(f"\n🎬 Génération {name}…")
    print(f"   Prompt: {clip_spec['prompt'][:120]}…")
    t0 = time.time()
    video_bytes = client.text_to_video(
        prompt=clip_spec["prompt"],
        model="sora-2",
        size="1280x720",
        duration=8,
        max_wait_time=900,
    )
    elapsed = int(time.time() - t0)
    if not video_bytes:
        print(f"❌ {name}: échec génération après {elapsed}s")
        return None
    output.write_bytes(video_bytes)
    print(f"✅ {name}: {len(video_bytes) // 1024} KB en {elapsed}s")
    return output


def strip_audio(input_path: Path) -> Path:
    """Strip audio track via ffmpeg."""
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
    """Concat clips MP4 via ffmpeg concat demuxer."""
    list_file = output_path.parent / f".concat_{output_path.stem}.txt"
    with list_file.open("w") as f:
        for p in clip_paths:
            f.write(f"file '{p.resolve()}'\n")
    # Re-encode pour garantir compatibilité (clips Sora peuvent différer)
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
    """Strip audio + concat les clips en une vidéo finale."""
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
    print("🎬 MesureChâssis — Génération des 2 vidéos promo via Sora 2")
    print("=" * 70)

    client = OpenAIVideoGeneration(api_key=EMERGENT_LLM_KEY)

    # Phase 1 : Génération des 8 clips
    print("\n📦 PHASE 1 — Génération des 8 clips Sora 2 (~8-15 min)")
    all_specs = VIDEO_1_CLIPS + VIDEO_2_CLIPS
    failures = []
    for spec in all_specs:
        result = generate_clip(client, spec)
        if not result:
            failures.append(spec["name"])

    if failures:
        print(f"\n⚠️  Clips échoués : {failures}")
        print("Relancez le script pour retry les clips manquants.")
        sys.exit(1)

    # Phase 2 : Assemblage
    print("\n📦 PHASE 2 — Assemblage ffmpeg")
    v1 = assemble_video(VIDEO_1_CLIPS, "video1_galere.mp4")
    v2 = assemble_video(VIDEO_2_CLIPS, "video2_magie.mp4")

    print("\n" + "=" * 70)
    if v1 and v2:
        print("🎉 SUCCÈS — Vidéos prêtes !")
        print(f"   📹 Vidéo 1 (galère) : {v1}")
        print(f"   📹 Vidéo 2 (magie)  : {v2}")
        print("\n   URLs publiques après restart backend :")
        print("   - /api/promo/video1_galere.mp4")
        print("   - /api/promo/video2_magie.mp4")
    else:
        print("⚠️  Assemblage partiel")
    print("=" * 70)


if __name__ == "__main__":
    main()
