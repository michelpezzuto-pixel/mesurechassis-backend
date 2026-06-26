"""
Construit la vidéo motion-design MesureChâssis V2 (images STATIQUES).
Storyboard validé par Michel le 26/06/2026.
"""
import subprocess
from pathlib import Path

ASSETS = Path("/app/backend/static/promo/motion_assets")
OUT_DIR = Path("/app/backend/static/promo")
WORK = Path("/tmp/motion_work_v2")
WORK.mkdir(exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_REG = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

ORANGE = "0xFF5A00"
DARK = "0x0C0C0E"
W, H = 1280, 720
FPS = 24


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ {r.stderr[-300:]}")
        return False
    return True


def esc(s):
    """Échappe le texte pour ffmpeg drawtext."""
    return s.replace("'", "\u2019").replace(":", "\\:")


def make_image_scene(image_path, duration, title, subtitle, output,
                     title_pos="bottom", text_below=None):
    """Scène STATIQUE avec image en fond + titre/sous-titre.

    title_pos = 'top' ou 'bottom'
    text_below = ligne supplémentaire (ex 'mesurechassis.com')
    """
    title_safe = esc(title) if title else None
    sub_safe = esc(subtitle) if subtitle else None
    below_safe = esc(text_below) if text_below else None

    # Texte band noir + textes
    if title_pos == "bottom":
        band_y = H - 220
        title_y = H - 170
        sub_y = H - 90
    else:  # top
        band_y = 0
        title_y = 60
        sub_y = 140

    filters = [
        # Image fit en cover 1280x720 (sans crop trop violent)
        f"scale=1280:720:force_original_aspect_ratio=increase",
        f"crop={W}:{H}",
        f"vignette=PI/5",
        # Bande sombre transparente pour lisibilité texte
        f"drawbox=x=0:y={band_y}:w={W}:h=220:color=black@0.55:t=fill",
    ]

    if title_safe:
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{title_safe}':fontcolor={ORANGE}:"
            f"fontsize=56:x=(w-text_w)/2:y={title_y}:"
            f"alpha='if(lt(t,0.25),0,if(lt(t,0.7),(t-0.25)/0.45,if(lt(t,{duration}-0.4),1,({duration}-t)/0.4)))'"
        )
    if sub_safe:
        filters.append(
            f"drawtext=fontfile={FONT_REG}:text='{sub_safe}':fontcolor=white:"
            f"fontsize=32:x=(w-text_w)/2:y={sub_y}:"
            f"alpha='if(lt(t,0.5),0,if(lt(t,0.95),(t-0.5)/0.45,if(lt(t,{duration}-0.4),1,({duration}-t)/0.4)))'"
        )
    filters.append("format=yuv420p")

    cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
           "-i", str(image_path), "-t", str(duration),
           "-vf", ",".join(filters),
           "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def make_app_screen_scene(phone_image, duration, title, subtitle, output):
    """Capture d'écran d'app affichée sur fond noir, statique avec glow orange."""
    title_safe = esc(title)
    sub_safe = esc(subtitle)
    # On garde l'image native (portrait), padding noir autour
    filters = (
        f"scale=-1:600,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={DARK},"
        f"drawtext=fontfile={FONT_BOLD}:text='{title_safe}':fontcolor={ORANGE}:"
        f"fontsize=48:x=(w-text_w)/2:y=40:"
        f"alpha='if(lt(t,0.25),0,if(lt(t,0.7),(t-0.25)/0.45,if(lt(t,{duration}-0.4),1,({duration}-t)/0.4)))',"
        f"drawtext=fontfile={FONT_REG}:text='{sub_safe}':fontcolor=white:"
        f"fontsize=30:x=(w-text_w)/2:y={H-60}:"
        f"alpha='if(lt(t,0.5),0,if(lt(t,0.95),(t-0.5)/0.45,if(lt(t,{duration}-0.4),1,({duration}-t)/0.4)))',"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
           "-i", str(phone_image), "-t", str(duration),
           "-vf", filters, "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def make_title_card(duration, lines, output, bg="black"):
    """Carte titre noire : plusieurs lignes empilées centrées.

    lines = [(text, color, fontsize, fade_start), ...]
    """
    n = len(lines)
    base_y = H // 2 - (n * 60)  # rough centering
    drawtexts = []
    for i, (text, color, fs, fade_start) in enumerate(lines):
        text_safe = esc(text)
        y = base_y + i * (fs + 30)
        drawtexts.append(
            f"drawtext=fontfile={FONT_BOLD if 'bold' in color else FONT_REG}:"
            f"text='{text_safe}':fontcolor={color.replace('-bold','')}:"
            f"fontsize={fs}:x=(w-text_w)/2:y={y}:"
            f"alpha='if(lt(t,{fade_start}),0,if(lt(t,{fade_start}+0.5),(t-{fade_start})/0.5,if(lt(t,{duration}-0.4),1,({duration}-t)/0.4)))'"
        )
    vf = ",".join(drawtexts) + ",format=yuv420p"
    cmd = ["ffmpeg", "-y", "-f", "lavfi",
           "-i", f"color=c={bg}:s={W}x{H}:d={duration}:r={FPS}",
           "-vf", vf, "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def concat_scenes(clips, output):
    list_file = WORK / "concat.txt"
    with list_file.open("w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(list_file), "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def main():
    print("🎬 Construction motion video V2 (statique, scénario Michel)")
    scenes = []

    # ── ACTE 1 — Intro (3s) ─────────────────────────────────────
    s = WORK / "01_intro.mp4"
    make_title_card(3, [
        ("MesureChâssis", "white-bold", 110, 0.2),
        ("présente", "0xFF5A00", 38, 0.8),
    ], s)
    scenes.append(s)
    print(f"  ✓ {s.name}")

    # ── ACTE 2 — La galère (4 plans × 4s) ────────────────────────
    s = WORK / "02_office_phone.mp4"
    make_image_scene(ASSETS / "p2_office_phone.jpg", 4,
                     "9h15 — Appel pour un mesurage",
                     "Carnet, mètre, smartphone…", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "03_pen_on_desk.mp4"
    make_image_scene(ASSETS / "p3_pen.jpg", 4,
                     "Mais…",
                     "Le bic est resté au bureau.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "04_concrete_opening.mp4"
    make_image_scene(ASSETS / "p4_concrete_opening.jpg", 4,
                     "Sur le chantier",
                     "Mesures à prendre. Mais pas de bic.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "05_frustrated.mp4"
    make_image_scene(ASSETS / "p5_frustrated.jpg", 4,
                     "La galère.",
                     "Journée gâchée. Retour bureau.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    # ── ACTE 3 — Transition (2s) ────────────────────────────────
    s = WORK / "06_transition.mp4"
    make_title_card(2, [
        ("Et si…", "white-bold", 90, 0.2),
        ("tout tenait dans ta poche ?", "0xFF5A00", 40, 0.6),
    ], s, bg=DARK)
    scenes.append(s); print(f"  ✓ {s.name}")

    # ── ACTE 4 — La solution (4 plans × 5s) ─────────────────────
    s = WORK / "07_login.mp4"
    make_app_screen_scene(ASSETS / "login_screen.png", 5,
                          "1. Connecte-toi",
                          "Une app pensée pour les pros.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "08_cdc.mp4"
    make_image_scene(ASSETS / "p8_doc_smartphone.jpg", 5,
                     "2. Photographie ton CDC",
                     "L'IA détecte tous les châssis.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "09_chassis_list.mp4"
    make_app_screen_scene(ASSETS / "chassis_list.png", 5,
                          "3. Tous tes châssis en 1 tap",
                          "Plus de papier, plus de saisie.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    s = WORK / "10_measuring.mp4"
    make_image_scene(ASSETS / "p10_measuring.jpg", 5,
                     "4. Mesure & Valide",
                     "Sur le terrain, en 3 taps.", s)
    scenes.append(s); print(f"  ✓ {s.name}")

    # ── ACTE 5 — Outro & CTA (4s) ───────────────────────────────
    s = WORK / "11_outro.mp4"
    make_title_card(4, [
        ("MesureChâssis", "white-bold", 110, 0.2),
        ("Mesures terrain · Menuiseries pro", "0xFF5A00", 36, 0.7),
        ("mesurechassis.com", "white", 28, 1.2),
    ], s)
    scenes.append(s); print(f"  ✓ {s.name}")

    # ── Assemblage ──────────────────────────────────────────────
    output = OUT_DIR / "video_motion_v2.mp4"
    print(f"\n🪡 Assemblage final ({len(scenes)} plans)…")
    if concat_scenes(scenes, output):
        size_mb = output.stat().st_size / 1024 / 1024
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
            capture_output=True, text=True)
        duration = float(r.stdout.strip())
        print(f"\n✅ {output}")
        print(f"   {size_mb:.1f} MB | {duration:.1f} sec")
        print(f"   URL: /api/promo/video_motion_v2.mp4")


if __name__ == "__main__":
    main()
