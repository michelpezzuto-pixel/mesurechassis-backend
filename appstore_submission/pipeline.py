"""
MesureChâssis - Pipeline de préparation pour soumission App Store
- Redimensionne 7 captures en 1290×2796
- Floute l'ID utilisateur sur le Dashboard
- Génère 2 vidéos App Preview (Apple + Social/TikTok)
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import subprocess
import math

BASE = Path("/app/appstore_submission")
RAW = BASE / "raw"
OUT = BASE / "output"
FRAMES = BASE / "frames"
OUT.mkdir(exist_ok=True)
FRAMES.mkdir(exist_ok=True)

# ============================================================
# CONSTANTES APPLE
# ============================================================
APPLE_W, APPLE_H = 1290, 2796   # iPhone 6.9" - format Apple obligatoire

# ============================================================
# STAGE 1 - Resize static screenshots to 1290x2796
# ============================================================
def resize_for_apple(src, dst, blur_region=None):
    """
    Redimensionne une image pour Apple 1290x2796 en préservant le ratio.
    Padding noir si nécessaire.
    Blur optionnel d'une zone (x1,y1,x2,y2) en fraction 0-1.
    """
    img = Image.open(src).convert("RGB")
    src_w, src_h = img.size

    # Apply blur BEFORE resize (on source coordinates)
    if blur_region:
        x1, y1, x2, y2 = blur_region
        bx1 = int(x1 * src_w); by1 = int(y1 * src_h)
        bx2 = int(x2 * src_w); by2 = int(y2 * src_h)
        area = img.crop((bx1, by1, bx2, by2))
        area_blurred = area.filter(ImageFilter.GaussianBlur(radius=18))
        img.paste(area_blurred, (bx1, by1))

    # Fit to Apple canvas
    src_ratio = src_w / src_h
    target_ratio = APPLE_W / APPLE_H
    if src_ratio > target_ratio:
        # Trop large - on scale sur largeur
        new_w = APPLE_W
        new_h = int(APPLE_W / src_ratio)
    else:
        # Trop haute ou même ratio - on scale sur hauteur
        new_h = APPLE_H
        new_w = int(APPLE_H * src_ratio)

    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (APPLE_W, APPLE_H), (0, 0, 0))
    px = (APPLE_W - new_w) // 2
    py = (APPLE_H - new_h) // 2
    canvas.paste(resized, (px, py))
    canvas.save(dst, "PNG", optimize=True)
    return canvas

print("=== STAGE 1: Resize 7 static screenshots to 1290x2796 ===")
static_files = [
    ("img1_faq.webp", "01_faq.png", None),
    ("img2_chantier_exports.webp", "02_chantier_exports.png", None),
    ("img3_selection.webp", "03_selection.png", None),
    ("img4_login.webp", "04_login.png", None),
    # ID "MICHEL-PEZZUTO-2FC737" blur coords validated visually
    ("img5_dashboard.webp", "05_dashboard.png", (0.03, 0.155, 0.55, 0.185)),
    ("img6_chantier_detail.webp", "06_chantier_detail.png", None),
    ("img7_ia_import.webp", "07_ia_import.png", None),
]
resized_dir = BASE / "resized"
resized_dir.mkdir(exist_ok=True)
for src_name, dst_name, blur in static_files:
    src = RAW / src_name
    dst = resized_dir / dst_name
    resize_for_apple(src, dst, blur)
    print(f"  ✓ {dst_name}")

# ============================================================
# STAGE 2 - Prepare animation frames (fit to 1290x2796)
# ============================================================
print("\n=== STAGE 2: Prepare animation frames ===")

def fit_frame(src_path):
    """Charge frame webp/png et l'adapte au format Apple 1290x2796."""
    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    ratio = w / h
    target = APPLE_W / APPLE_H
    if ratio > target:
        new_w = APPLE_W
        new_h = int(APPLE_W / ratio)
    else:
        new_h = APPLE_H
        new_w = int(APPLE_H * ratio)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (APPLE_W, APPLE_H), (10, 10, 10))
    px = (APPLE_W - new_w) // 2
    py = (APPLE_H - new_h) // 2
    canvas.paste(resized, (px, py))
    return canvas

frame_top = fit_frame(RAW / "frame_top.webp")
frame_mid = fit_frame(RAW / "frame_mid.webp")
frame_mid2 = fit_frame(RAW / "frame_mid2.webp")
frame_bot = fit_frame(RAW / "frame_bot.webp")
final_apple = fit_frame(RAW / "final_chantier.webp")
final_social = fit_frame(RAW / "endcard_qr.png")

# Preview all
frame_top.save(FRAMES / "_frame_top.png")
frame_mid.save(FRAMES / "_frame_mid.png")
frame_mid2.save(FRAMES / "_frame_mid2.png")
frame_bot.save(FRAMES / "_frame_bot.png")
final_apple.save(FRAMES / "_final_apple.png")
final_social.save(FRAMES / "_final_social.png")
print("  ✓ 6 frames préparées")

# ============================================================
# STAGE 3 - Generate video frames sequence
# ============================================================
print("\n=== STAGE 3: Generate video frame sequence ===")

FPS = 30
def easeInOut(t):
    """Cubic ease in-out for smooth animations."""
    return 3 * t * t - 2 * t * t * t

def crossfade(img_a, img_b, alpha):
    """Blend two PIL images. alpha=0 -> img_a, alpha=1 -> img_b."""
    return Image.blend(img_a, img_b, alpha)

def add_tap_effect(img, cx, cy, radius, color=(255, 140, 0), alpha=0.5):
    """Add a semi-transparent ripple circle at (cx, cy)."""
    out = img.copy()
    overlay = Image.new("RGBA", out.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    a = int(255 * alpha)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 outline=(*color, a), width=8)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=(*color, int(a*0.15)))
    out = Image.alpha_composite(out.convert("RGBA"), overlay).convert("RGB")
    return out

def render_sequence(final_frame, out_dir, name):
    """
    Génère la séquence complète:
    - 0.8s frame_top (pause initiale)
    - 1.5s crossfade top→mid (montre remplissage largeur/hauteur)
    - 1.0s pause mid (montre calcul diagonale VALIDÉ)
    - 1.5s crossfade mid→mid2 (feuillures)
    - 1.0s pause mid2
    - 1.5s crossfade mid2→bot (réserve sol)
    - 1.5s pause bot (montre 250mm calculé)
    - 1.0s tap ENREGISTRER (ripple sur bouton orange)
    - 0.5s fade to black
    - 3.0s final frame (chantier / endcard)
    Total: ~13.3s
    """
    out_dir.mkdir(exist_ok=True, parents=True)
    frame_idx = 0

    # Bouton ENREGISTRER position approximative (bas droite, orange)
    # Dans nos frames à 1290x2796, le bouton orange est autour de:
    tap_cx, tap_cy, tap_r = 920, 2510, 90

    def emit(img, n_frames):
        nonlocal frame_idx
        for _ in range(n_frames):
            img.save(out_dir / f"f_{frame_idx:05d}.png")
            frame_idx += 1

    def transition(a, b, seconds):
        n = int(seconds * FPS)
        for i in range(n):
            t = easeInOut(i / max(n - 1, 1))
            blended = crossfade(a, b, t)
            blended.save(out_dir / f"f_{frame_idx:05d}.png")
            nonlocal_incr()
        return

    # 1. Pause initiale sur frame_top (0.8s)
    emit(frame_top, int(0.8 * FPS))

    # 2. Crossfade top→mid (1.5s)
    n = int(1.5 * FPS)
    for i in range(n):
        t = easeInOut(i / max(n - 1, 1))
        blended = crossfade(frame_top, frame_mid, t)
        blended.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 3. Pause sur frame_mid (1.2s)
    emit(frame_mid, int(1.2 * FPS))

    # 4. Crossfade mid→mid2 (1.5s)
    n = int(1.5 * FPS)
    for i in range(n):
        t = easeInOut(i / max(n - 1, 1))
        blended = crossfade(frame_mid, frame_mid2, t)
        blended.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 5. Pause sur frame_mid2 (1.0s)
    emit(frame_mid2, int(1.0 * FPS))

    # 6. Crossfade mid2→bot (1.5s)
    n = int(1.5 * FPS)
    for i in range(n):
        t = easeInOut(i / max(n - 1, 1))
        blended = crossfade(frame_mid2, frame_bot, t)
        blended.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 7. Pause sur frame_bot (1.5s)
    emit(frame_bot, int(1.5 * FPS))

    # 8. Tap ENREGISTRER effect (1.0s) - ripple expanding
    n = int(1.0 * FPS)
    for i in range(n):
        # Expanding ring
        progress = i / max(n - 1, 1)
        r = int(tap_r + progress * 120)
        alpha = 0.7 * (1 - progress)
        frame = add_tap_effect(frame_bot, tap_cx, tap_cy, r, alpha=alpha)
        frame.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 9. Fade to black (0.4s)
    black = Image.new("RGB", (APPLE_W, APPLE_H), (0, 0, 0))
    n = int(0.4 * FPS)
    for i in range(n):
        t = i / max(n - 1, 1)
        blended = crossfade(frame_bot, black, t)
        blended.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 10. Fade in final (0.4s)
    n = int(0.4 * FPS)
    for i in range(n):
        t = i / max(n - 1, 1)
        blended = crossfade(black, final_frame, t)
        blended.save(out_dir / f"f_{frame_idx:05d}.png")
        frame_idx += 1

    # 11. Hold final frame (2.6s)
    emit(final_frame, int(2.6 * FPS))

    print(f"  ✓ {name}: {frame_idx} frames generated")
    return frame_idx


# Version APPLE (ends on chantier)
apple_frames_dir = FRAMES / "apple"
apple_count = render_sequence(final_apple, apple_frames_dir, "APPLE")

# Version SOCIAL (ends on QR endcard)
social_frames_dir = FRAMES / "social"
social_count = render_sequence(final_social, social_frames_dir, "SOCIAL")

# ============================================================
# STAGE 4 - Encode videos with ffmpeg
# ============================================================
print("\n=== STAGE 4: Encode MP4 videos ===")

def encode(frames_dir, out_file):
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(frames_dir / "f_%05d.png"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-vf", "scale=1080:2340,pad=1080:2340:0:0",  # Common vertical H.264 spec, well-supported
        str(out_file)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFMPEG ERROR:", result.stderr[-500:])
    return result.returncode == 0

apple_out = OUT / "MesureChassis-AppPreview-APPLE.mp4"
social_out = OUT / "MesureChassis-Video-SOCIAL.mp4"

encode(apple_frames_dir, apple_out)
print(f"  ✓ {apple_out.name}: {apple_out.stat().st_size // 1024} KB")

encode(social_frames_dir, social_out)
print(f"  ✓ {social_out.name}: {social_out.stat().st_size // 1024} KB")

# ============================================================
# STAGE 5 - Copy resized screenshots to output
# ============================================================
print("\n=== STAGE 5: Package final assets ===")

apple_pack_dir = OUT / "AppStore_Package"
apple_pack_dir.mkdir(exist_ok=True, parents=True)
(apple_pack_dir / "screenshots-iphone-6.9inch").mkdir(exist_ok=True)

# Suggested order (killer feature first)
order = [
    ("07_ia_import.png", "01_ia_import_killer.png"),
    ("03_selection.png", "02_selection_menuiseries.png"),
    ("02_chantier_exports.png", "03_exports_6_formats.png"),
    ("06_chantier_detail.png", "04_chantier_detail.png"),
    ("05_dashboard.png", "05_dashboard.png"),
    ("01_faq.png", "06_centre_aide.png"),
    ("04_login.png", "07_connexion.png"),
]
for src_name, dst_name in order:
    src = resized_dir / src_name
    dst = apple_pack_dir / "screenshots-iphone-6.9inch" / dst_name
    if src.exists():
        Image.open(src).save(dst, "PNG", optimize=True)
        print(f"  ✓ {dst_name}")

# Copy videos
import shutil
shutil.copy(apple_out, apple_pack_dir / "app-preview-video.mp4")
shutil.copy(social_out, apple_pack_dir / "social-media-video-with-QR.mp4")

# README
readme = """# MesureChâssis - Package Soumission App Store

## 📱 Captures d'écran iPhone 6.9" (1290×2796 px)

Ordre recommandé (ordre d'affichage sur la fiche App Store) :

1. **01_ia_import_killer.png** — 🔥 IA détecte les châssis (WOW factor)
2. **02_selection_menuiseries.png** — 7 formes de baies (largeur produit)
3. **03_exports_6_formats.png** — Exports PDF/Excel/CSV/JSON/ERP (pro)
4. **04_chantier_detail.png** — Détail chantier concret
5. **05_dashboard.png** — Vue d'ensemble (ID utilisateur flouté)
6. **06_centre_aide.png** — Support client
7. **07_connexion.png** — Login FR/NL/EN + Apple/Google

## 🎬 Vidéos

- **app-preview-video.mp4** — Pour App Store Connect (~14s)
  Conforme Apple Guidelines (sans logo Apple / sans "download")

- **social-media-video-with-QR.mp4** — Pour TikTok/LinkedIn/Instagram (~14s)
  Se termine sur endcard QR code avec logo Apple

## ⚠️ NE PAS uploader social-media-video-with-QR.mp4 sur App Store Connect
Elle contient le logo Apple + "sur l'App Store" = motif de rejet automatique.
"""
(apple_pack_dir / "README.md").write_text(readme)
print("  ✓ README.md")

# Zip final
zip_path = OUT / "MesureChassis-AppStore-Package.zip"
shutil.make_archive(str(zip_path).replace(".zip", ""), "zip", apple_pack_dir)
print(f"\n✅ ZIP créé: {zip_path} ({zip_path.stat().st_size // 1024} KB)")

# Copy zip to public downloads
public_dir = Path("/app/backend/public_downloads")
public_dir.mkdir(exist_ok=True, parents=True)
shutil.copy(zip_path, public_dir / "MesureChassis-AppStore-Package.zip")
shutil.copy(apple_out, public_dir / "MesureChassis-AppPreview-APPLE.mp4")
shutil.copy(social_out, public_dir / "MesureChassis-Video-SOCIAL.mp4")
print(f"✅ Copié dans /app/backend/public_downloads/")
