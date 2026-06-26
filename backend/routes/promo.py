"""Routes pour servir les vidéos promotionnelles MesureChâssis.

Les vidéos générées via Sora 2 sont stockées dans /app/backend/static/promo/
et exposées via /api/promo/{filename}.mp4 (accessibles publiquement, sans auth)
pour intégration sur le site web mesurechassis.com et réseaux sociaux.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/promo", tags=["promo"])

PROMO_DIR = Path("/app/backend/static/promo")

# Whitelist pour éviter l'accès à d'autres fichiers
ALLOWED_FILES = {
    "video1_galere.mp4",
    "video2_magie.mp4",
    "video1_galere_v2.mp4",
    "video1_galere_v3.mp4",
    "video2_magie_v2.mp4",
    "video_complete_v2.mp4",
    "video_complete_v3.mp4",
    "video_complete_v4.mp4",
    "video_motion_v1.mp4",
    "video_motion_v2.mp4",
    "video_motion_v3.mp4",
    "video_motion_v4_music.mp4",
    "hero_video_faststart.mp4",
    "site_mesurechassis_simplifie.zip",
}


@router.get("/{filename}")
def serve_promo_video(filename: str):
    """Sert une vidéo promo MP4 (public, no auth, cacheable)."""
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="File not found")
    path = PROMO_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    # Détecter le media-type selon l'extension
    if filename.endswith(".zip"):
        media_type = "application/zip"
    else:
        media_type = "video/mp4"
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        headers={
            "Cache-Control": "public, max-age=60",
            "Accept-Ranges": "bytes",
        },
    )


@router.get("")
def list_promo_videos():
    """Liste les vidéos promo disponibles."""
    videos = []
    for name in ALLOWED_FILES:
        path = PROMO_DIR / name
        if path.exists():
            videos.append({
                "name": name,
                "url": f"/api/promo/{name}",
                "size_kb": path.stat().st_size // 1024,
            })
    return {"videos": videos}
