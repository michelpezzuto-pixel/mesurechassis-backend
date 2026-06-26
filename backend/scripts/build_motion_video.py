"""
Construit une vidéo MOTION DESIGN explainer SaaS pour MesureChâssis.

Style : Stripe / Linear / Notion landing page hero video.
0 $ de coût (pas de Sora) — uniquement ffmpeg + assets existants.

Sortie : /app/backend/static/promo/video_motion_v1.mp4
"""
import subprocess
from pathlib import Path

ASSETS = Path("/app/backend/static/promo/motion_assets")
OUT_DIR = Path("/app/backend/static/promo")
WORK = Path("/tmp/motion_work")
WORK.mkdir(exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_REG = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

ORANGE = "0xFF5A00"
WHITE = "white"
BLACK = "black"
DARK = "0x0C0C0E"

W, H = 1280, 720
FPS = 24


def run(cmd):
    """Exécute une commande ffmpeg et retourne True/False."""
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ Failed: {cmd[:120]}...\n   {r.stderr[-300:]}")
        return False
    return True


def escape_text(s):
    """Échappe le texte pour ffmpeg drawtext (apostrophes typographiques)."""
    return (s.replace("'", "\u2019")  # apostrophe droite → typographique
            .replace(":", "\\:"))


def make_scene_image_bg(image_path, duration, title, subtitle, output, kb_zoom=0.0005):
    """Scène avec photo de fond + Ken Burns + titre + sous-titre."""
    title_safe = escape_text(title)
    subtitle_safe = escape_text(subtitle)
    vf = (
        f"scale=1400:-2,crop={W}:{H},"
        f"zoompan=z='zoom+{kb_zoom}':d={int(FPS*duration)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        # Vignette assombrissement bord pour lisibilité texte
        f"vignette=PI/4,"
        # Overlay bande noire semi-transparente en bas (où le texte sera)
        f"drawbox=x=0:y={H-220}:w={W}:h=220:color=black@0.55:t=fill,"
        # Titre principal (gros, orange, fade-in à 0.3s, fade-out à duration-0.5s)
        f"drawtext=fontfile={FONT_BOLD}:text='{title_safe}':fontcolor={ORANGE}:"
        f"fontsize=56:x=(w-text_w)/2:y={H-170}:"
        f"alpha='if(lt(t,0.3),0,if(lt(t,0.8),(t-0.3)/0.5,if(lt(t,{duration}-0.6),1,({duration}-t)/0.6)))',"
        # Sous-titre (plus petit, blanc)
        f"drawtext=fontfile={FONT_REG}:text='{subtitle_safe}':fontcolor=white:"
        f"fontsize=32:x=(w-text_w)/2:y={H-90}:"
        f"alpha='if(lt(t,0.6),0,if(lt(t,1.1),(t-0.6)/0.5,if(lt(t,{duration}-0.6),1,({duration}-t)/0.6)))',"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
           "-i", str(image_path), "-t", str(duration),
           "-vf", vf, "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def make_scene_phone_screen(phone_image, duration, title, subtitle, output):
    """Scène avec un screenshot d'app dans un téléphone, centré sur fond dark."""
    title_safe = escape_text(title)
    subtitle_safe = escape_text(subtitle)
    vf = (
        # Téléphone redimensionné centré
        f"scale=-1:580,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={DARK},"
        # Ken Burns léger
        f"zoompan=z='zoom+0.0003':d={int(FPS*duration)}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        # Titre en haut
        f"drawtext=fontfile={FONT_BOLD}:text='{title_safe}':fontcolor={ORANGE}:"
        f"fontsize=48:x=(w-text_w)/2:y=60:"
        f"alpha='if(lt(t,0.3),0,if(lt(t,0.8),(t-0.3)/0.5,if(lt(t,{duration}-0.5),1,({duration}-t)/0.5)))',"
        # Sous-titre en bas
        f"drawtext=fontfile={FONT_REG}:text='{subtitle_safe}':fontcolor=white:"
        f"fontsize=28:x=(w-text_w)/2:y={H-80}:"
        f"alpha='if(lt(t,0.6),0,if(lt(t,1.1),(t-0.6)/0.5,if(lt(t,{duration}-0.5),1,({duration}-t)/0.5)))',"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
           "-i", str(phone_image), "-t", str(duration),
           "-vf", vf, "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def make_title_card(duration, big_text, tagline, output, bg="black"):
    """Carte titre noire avec gros texte centré (intro/outro)."""
    big_safe = escape_text(big_text)
    tag_safe = escape_text(tagline)
    vf = (
        f"drawtext=fontfile={FONT_BOLD}:text='{big_safe}':fontcolor=white:"
        f"fontsize=120:x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='if(lt(t,0.3),0,if(lt(t,0.9),(t-0.3)/0.6,if(lt(t,{duration}-0.5),1,({duration}-t)/0.5)))',"
        f"drawtext=fontfile={FONT_REG}:text='{tag_safe}':fontcolor={ORANGE}:"
        f"fontsize=38:x=(w-text_w)/2:y=(h+text_h)/2+50:"
        f"alpha='if(lt(t,0.7),0,if(lt(t,1.3),(t-0.7)/0.6,if(lt(t,{duration}-0.5),1,({duration}-t)/0.5)))',"
        f"format=yuv420p"
    )
    cmd = ["ffmpeg", "-y", "-f", "lavfi",
           "-i", f"color=c={bg}:s={W}x{H}:d={duration}:r={FPS}",
           "-vf", vf, "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def concat_with_xfade(clips, output):
    """Concatène avec crossfade entre chaque clip (0.4s)."""
    # Méthode simple : concat sans xfade pour éviter complexité
    list_file = WORK / "concat_list.txt"
    with list_file.open("w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(list_file), "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-an", str(output)]
    return run(cmd)


def main():
    print("🎬 Construction motion video MesureChâssis")
    scenes = []

    # ── ACTE 1 : Le problème (la galère) ─────────────────────────
    print("\n📦 ACTE 1 — La galère")
    s = WORK / "01_intro.mp4"
    make_title_card(2.5, "MesureChâssis", "Avant…", s)
    scenes.append(s)

    s = WORK / "02_office_morning.mp4"
    make_scene_image_bg(
        ASSETS / "scene_office_morning.jpg", 4,
        "8h00 — Départ chantier", "Carnet, mètre, smartphone…", s)
    scenes.append(s)

    s = WORK / "03_construction.mp4"
    make_scene_image_bg(
        ASSETS / "scene_construction.jpg", 4,
        "9h00 — Sur place", "…mais le bic est resté au bureau.", s)
    scenes.append(s)

    s = WORK / "04_carpenter_frustrated.mp4"
    make_scene_image_bg(
        ASSETS / "carpenter_ref.png", 4,
        "La galère.", "Mesures perdues, retour bureau, journée gâchée.", s)
    scenes.append(s)

    # ── ACTE 2 : La solution (MesureChâssis) ──────────────────────
    print("\n📦 ACTE 2 — La solution")
    s = WORK / "05_solution_intro.mp4"
    make_title_card(2.5, "Et si…", "tout tenait dans ta poche ?", s, bg=DARK)
    scenes.append(s)

    s = WORK / "06_login.mp4"
    make_scene_phone_screen(
        ASSETS / "login_screen.png", 4,
        "1. Connecte-toi", "Une app pensée pour les menuisiers pro.", s)
    scenes.append(s)

    s = WORK / "07_chassis_list.mp4"
    make_scene_phone_screen(
        ASSETS / "chassis_list.png", 5,
        "2. Tous tes châssis en 1 tap", "Importe ton cahier des charges, l'IA fait le reste.", s)
    scenes.append(s)

    s = WORK / "08_validate.mp4"
    make_scene_image_bg(
        ASSETS / "scene_specdoc.jpg", 4,
        "3. Mesure & Valide", "Sur le terrain, en 3 taps. Pas de papier, pas de bic.", s)
    scenes.append(s)

    s = WORK / "09_serene.mp4"
    make_scene_image_bg(
        ASSETS / "scene_serene.jpg", 4,
        "Mission accomplie.", "Toutes les mesures sont déjà au bureau.", s)
    scenes.append(s)

    # ── OUTRO : Brand reveal ──────────────────────────────────────
    print("\n📦 OUTRO — Brand reveal")
    s = WORK / "10_outro.mp4"
    make_title_card(4, "MesureChâssis", "Mesures terrain · Menuiseries pro", s)
    scenes.append(s)

    # ── ASSEMBLAGE ───────────────────────────────────────────────
    print("\n🪡 Assemblage final…")
    output = OUT_DIR / "video_motion_v1.mp4"
    if concat_with_xfade(scenes, output):
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"\n✅ Vidéo prête : {output} ({size_mb:.1f} MB)")
        # Durée
        import json
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
            capture_output=True, text=True)
        print(f"   Durée : {float(r.stdout.strip()):.1f} sec")
        print(f"   URL : /api/promo/video_motion_v1.mp4")
    else:
        print("❌ Échec assemblage")


if __name__ == "__main__":
    main()
