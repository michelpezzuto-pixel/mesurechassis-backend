"""Endpoint public — sert les ressources du POC ArUco (sans auth).

Permet à l'utilisateur de télécharger directement le PDF, les SVG et le DXF
depuis n'importe quel navigateur, sans avoir à pousser sur GitHub.

Routes :
    GET /api/poc/markers.pdf          → planche A4 12 markers ArUco 50 mm
    GET /api/poc/markers/{file}       → fichier individuel du dossier markers/
    GET /api/poc/results.md           → rapport markdown précision
    GET /api/poc/dxf/{file}.dxf       → fichiers DXF
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path

router = APIRouter(prefix="/poc", tags=["poc"])

POC_DIR = Path("/app/mesure-chassis/poc-aruco")


@router.get("/markers.pdf")
async def markers_pdf():
    """Planche A4 prête à imprimer : 12 ArUco 4x4_50 taille 50 mm."""
    pdf_path = POC_DIR / "markers" / "markers_A4_50mm.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "PDF non généré. Lancez generate_markers.py")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="markers_A4_50mm.pdf",
    )


@router.get("/markers/{file_name}")
async def marker_file(file_name: str):
    """Fichier individuel : ArUco_XX.svg ou ArUco_XX.png."""
    if "/" in file_name or ".." in file_name:
        raise HTTPException(400, "Chemin invalide")
    for sub in ("svg", "png"):
        candidate = POC_DIR / "markers" / sub / file_name
        if candidate.exists():
            media = "image/svg+xml" if sub == "svg" else "image/png"
            return FileResponse(path=str(candidate), media_type=media, filename=file_name)
    raise HTTPException(404, "Fichier introuvable")


@router.get("/dxf/{file_name}")
async def dxf_file(file_name: str):
    """Fichier DXF (vérité terrain ou bruité)."""
    if "/" in file_name or ".." in file_name or not file_name.endswith(".dxf"):
        raise HTTPException(400, "Chemin invalide")
    candidate = POC_DIR / file_name
    if not candidate.exists():
        raise HTTPException(404, "DXF introuvable")
    return FileResponse(
        path=str(candidate),
        media_type="application/dxf",
        filename=file_name,
    )


@router.get("/results.md", response_class=PlainTextResponse)
async def results_md():
    """Rapport markdown précision Monte-Carlo."""
    md = POC_DIR / "RESULTS.md"
    if not md.exists():
        raise HTTPException(404, "Rapport non généré")
    return md.read_text(encoding="utf-8")


@router.get("/icon.png")
async def app_icon():
    """Icône d'app verte 1024x1024 PNG, prête pour l'upload du build iOS."""
    icon_path = POC_DIR / "icon_green_1024.png"
    if not icon_path.exists():
        raise HTTPException(404, "Icône non générée. Lancez generate_icon.py")
    return FileResponse(
        path=str(icon_path),
        media_type="image/png",
        filename="icon_green_1024.png",
    )


@router.get("/protocol.md", response_class=PlainTextResponse)
async def protocol_md():
    """Protocole de test physique."""
    md = POC_DIR / "PROTOCOLE_TEST_PHYSIQUE.md"
    if not md.exists():
        raise HTTPException(404, "Protocole introuvable")
    return md.read_text(encoding="utf-8")
