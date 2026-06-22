"""Routes d'import de cahier des charges (PDF/Excel/Image) — Build 11+ (juin 2026).

Workflow utilisateur :
    1. L'artisan ouvre un chantier → clique "Importer cahier des charges"
    2. Il sélectionne un PDF, un Excel (.xlsx) ou une photo (JPG/PNG)
    3. Le backend stocke le fichier puis lance l'analyse Gemini 2.5 Flash
       EN BACKGROUND (sinon Cloudflare timeout à ~100s sur les gros PDF).
    4. La requête POST retourne immédiatement un draft en status="processing".
    5. Le frontend poll GET /spec-drafts/{id} toutes les 3s jusqu'à ce
       que status passe à "pending" (succès) ou "failed" (erreur).
    6. L'artisan voit la prévisualisation, ajuste, supprime, puis valide
    7. Validation → création des mesures correspondantes en base avec
       les dimensions théoriques pré-remplies (flag `imported_from_spec`)
    8. Sur le chantier : l'artisan voit les mesures importées avec un
       badge spécial et peut les ouvrir pour confirmer/ajuster les
       mesures réelles relevées sur place.

🆕 Chunked Upload (juin 2026, anti-502) :
    Pour les gros PDF (>2 Mo) en 5G/Wi-Fi lent, Cloudflare coupe la
    connexion après 100 sec → erreur 502. Solution : découper le fichier
    côté mobile en chunks de 1 Mo, uploader chaque chunk dans sa propre
    requête HTTP courte (<10 sec), puis demander au backend d'assembler
    et de lancer l'analyse IA en arrière-plan.

    Routes :
      POST /chantiers/{id}/import-spec/chunked/init        → crée upload_id
      POST /chantiers/{id}/import-spec/chunked/{id}/chunk  → upload 1 chunk
      POST /chantiers/{id}/import-spec/chunked/{id}/complete → assemble + lance IA

Paywall :
    En BETA_MODE, accessible à tous. Hors beta : nécessite un
    abonnement actif (standard / team / pro) — exclut le freemium.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from db import BETA_MODE, VALID_BLOCK_TYPES, db
from deps import require_roles
from services.spec_parser import parse_excel, parse_image, parse_pdf
from utils import check_chantier_access

logger = logging.getLogger("mesurechassis.spec_import")
router = APIRouter()

# Mêmes rôles que les mesures : tout sauf "lecture seule"
EDIT_ROLES = ["admin", "commercial", "technician"]

# Taille max d'un upload : 15 Mo (suffisant pour un PDF de plan).
MAX_UPLOAD_SIZE = 15 * 1024 * 1024

# Mime-types supportés
PDF_MIMES = {"application/pdf"}
IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
EXCEL_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",  # certains navigateurs envoient ce mime
}


# ════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ════════════════════════════════════════════════════════════════════════
class SpecItem(BaseModel):
    label: str
    block_type: str
    width_mm: int = 0
    height_mm: int = 0
    quantity: int = 1
    notes: str = ""


class SpecDraft(BaseModel):
    id: str
    chantier_id: str
    filename: str
    source: str  # pdf | excel | image
    summary: str = ""
    items: List[SpecItem] = Field(default_factory=list)
    status: str = "pending"  # processing | pending | imported | rejected | failed
    created_at: str
    created_by: str
    error_message: Optional[str] = None  # rempli si status == "failed"


class ConfirmImportPayload(BaseModel):
    """Items finaux validés par l'utilisateur (après édition manuelle)."""

    items: List[SpecItem]


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════
def _ensure_subscription_allows_import(user: dict, company_doc: Optional[dict] = None) -> None:
    """Vérifie l'éligibilité paywall.

    Règle métier (juin 2026) :
        - BETA_MODE actif → accessible à tous.
        - Hors beta : nécessite un abonnement payant actif (standard,
          team, pro). Le freemium en est EXCLU (incite à upgrader).
    """
    if BETA_MODE:
        return
    sub_status = (user.get("subscription_status") or "").lower()
    plan = (user.get("plan") or "").lower()
    # trial = OK pendant la période d'essai (sinon l'utilisateur ne peut
    # pas tester la feature avant d'acheter).
    if sub_status == "trial" or plan in {"standard", "team", "pro"}:
        return
    raise HTTPException(
        402,
        detail={
            "code": "import_spec_paywall",
            "message": (
                "L'import de cahier des charges est inclus dans tous les "
                "abonnements payants (à partir de 19,99 €/mois). Profitez "
                "de votre essai gratuit de 14 jours pour le tester."
            ),
        },
    )


def _detect_source(filename: str, content_type: Optional[str]) -> Optional[str]:
    """Détecte la nature du fichier (pdf / excel / image / None)."""
    name = (filename or "").lower()
    ct = (content_type or "").lower()
    if ct in PDF_MIMES or name.endswith(".pdf"):
        return "pdf"
    if ct in EXCEL_MIMES or name.endswith(".xlsx") or name.endswith(".xls"):
        return "excel"
    if ct in IMAGE_MIMES or any(name.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
        return "image"
    return None


def _expand_items_for_mesures(items: List[dict]) -> List[dict]:
    """Convertit la liste validée en payloads MesureCreate.

    - Réplique l'item N fois selon `quantity` (ex: 3 fenêtres identiques
      → 3 mesures distinctes, label suffixé « (1/3) », « (2/3) », « (3/3) »).
    - Pré-remplit width_top/middle/bottom = width_mm (toutes égales).
    - Pré-remplit height_left/middle/right = height_mm (toutes égales).
    - Ajoute un flag `imported_from_spec=True` dans `options` pour
      l'affichage frontend (badge spécial).
    """
    payloads: List[dict] = []
    for item in items:
        block_type = str(item.get("block_type") or "standard").lower()
        if block_type not in VALID_BLOCK_TYPES:
            block_type = "standard"
        width = float(item.get("width_mm") or 0)
        height = float(item.get("height_mm") or 0)
        qty = max(1, int(item.get("quantity") or 1))
        base_label = str(item.get("label") or "Ouverture").strip()[:80]
        notes = str(item.get("notes") or "").strip()
        for n in range(qty):
            label = base_label if qty == 1 else f"{base_label} ({n + 1}/{qty})"
            payloads.append(
                {
                    "block_type": block_type,
                    "label": label,
                    # 🆕 bay_width/bay_height — Permet au wizard d'hydrater les
                    #    champs Largeur / Hauteur en édition (mode validation).
                    "bay_width": width or None,
                    "bay_height": height or None,
                    "width_top": width or None,
                    "width_middle": width or None,
                    "width_bottom": width or None,
                    "height_left": height or None,
                    "height_middle": height or None,
                    "height_right": height or None,
                    "options": {
                        "imported_from_spec": True,
                        "validated_on_site": False,  # Sera basculé à True lors de la validation sur place
                        "spec_notes": notes,
                        "theoretical_width_mm": int(width),
                        "theoretical_height_mm": int(height),
                    },
                }
            )
    return payloads


# ════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════
@router.post("/chantiers/{chantier_id}/import-spec", response_model=SpecDraft)
async def import_spec(
    chantier_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Upload un cahier des charges + lance l'analyse IA EN BACKGROUND.

    ⚡ Ne bloque PAS la requête HTTP pendant l'analyse IA (qui peut
    prendre 30-90 secondes sur un gros PDF) — sinon Cloudflare timeout.

    Le draft est créé en `status="processing"`. Le frontend doit poller
    GET /spec-drafts/{id} pour récupérer le résultat final.
    """
    # 1) Accès au chantier
    chantier = await check_chantier_access(db, chantier_id, user)

    # 2) Paywall
    _ensure_subscription_allows_import(user)

    # 3) Lecture du fichier (avec garde-fou taille)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(400, "Fichier vide")
    if len(raw_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            413,
            f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE // (1024 * 1024)} Mo)",
        )

    # 4) Détection du type
    source = _detect_source(file.filename or "", file.content_type)
    if source is None:
        raise HTTPException(
            400,
            "Format non supporté. Utilisez PDF, Excel (.xlsx) ou image (JPG/PNG).",
        )

    # 5) Crée immédiatement un brouillon "processing" en base
    draft_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    draft_doc = {
        "id": draft_id,
        "chantier_id": chantier_id,
        "company_id": chantier.get("company_id", "default"),
        "filename": file.filename or "document",
        "source": source,
        "summary": "",
        "items": [],
        "status": "processing",  # 🆕 nouveau status : analyse en cours
        "created_at": now,
        "created_by": user.get("user_id") or user.get("id") or "",
        "raw_response": "",
    }
    await db.spec_drafts.insert_one(draft_doc)

    # 6) Lance l'analyse IA EN BACKGROUND (non bloquant)
    mime = file.content_type or "image/jpeg"
    background_tasks.add_task(
        _run_ai_analysis_bg,
        draft_id=draft_id,
        raw_bytes=raw_bytes,
        source=source,
        mime=mime,
    )

    # 7) Retourne immédiatement le brouillon (le frontend va poller)
    draft_doc.pop("_id", None)
    draft_doc.pop("raw_response", None)
    return SpecDraft(**draft_doc)


async def _run_ai_analysis_bg(
    draft_id: str,
    raw_bytes: bytes,
    source: str,
    mime: str,
) -> None:
    """Tâche d'arrière-plan : appelle Gemini puis met à jour le draft.

    🆕 Build 11.2 : APRÈS analyse IA réussie, on crée AUTOMATIQUEMENT
    les mesures correspondantes dans le chantier (avec flag imported_from_spec
    et statut "à valider"). Plus de preview intermédiaire — Michel
    arrive directement sur la liste de châssis pré-remplis.

    Toutes les exceptions sont catchées : on marque le draft en status
    "failed" pour que le frontend puisse afficher un message d'erreur
    propre à l'utilisateur.
    """
    session_id = f"spec_bg_{draft_id[:8]}"
    try:
        if source == "pdf":
            ai_result = await parse_pdf(raw_bytes, session_id)
        elif source == "excel":
            ai_result = await parse_excel(raw_bytes, session_id)
        else:  # image
            ai_result = await parse_image(raw_bytes, mime, session_id)
        items = ai_result.get("items", [])

        # 🆕 Conversion automatique en mesures
        draft = await db.spec_drafts.find_one({"id": draft_id})
        chantier_id = draft["chantier_id"] if draft else None
        mesures_created = 0
        if items and chantier_id:
            mesure_payloads = _expand_items_for_mesures(items)
            now_iso = datetime.now(timezone.utc).isoformat()
            for p in mesure_payloads:
                doc = {
                    **p,
                    "id": str(uuid.uuid4()),
                    "chantier_id": chantier_id,
                    "created_at": now_iso,
                    "alerts": [],
                    "slope_angle_deg": None,
                }
                await db.mesures.insert_one(doc)
                mesures_created += 1

        # Marque le draft comme directement "imported" (plus de pending)
        await db.spec_drafts.update_one(
            {"id": draft_id},
            {
                "$set": {
                    "status": "imported" if items else "failed",
                    "items": items,
                    "summary": ai_result.get("summary", ""),
                    "raw_response": ai_result.get("raw_response", ""),
                    "mesures_created": mesures_created,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": (
                        ""
                        if items
                        else "Aucun châssis n'a pu être détecté dans ce document."
                    ),
                }
            },
        )
        logger.info(
            "✅ Spec import OK draft=%s source=%s items=%d mesures=%d",
            draft_id,
            source,
            len(items),
            mesures_created,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("❌ Spec import KO draft=%s", draft_id)
        await db.spec_drafts.update_one(
            {"id": draft_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": f"{type(e).__name__}: {str(e)[:300]}",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )


@router.get("/chantiers/{chantier_id}/spec-drafts", response_model=List[SpecDraft])
async def list_drafts(chantier_id: str, user=Depends(require_roles(EDIT_ROLES))):
    """Liste les brouillons d'import en attente pour ce chantier."""
    await check_chantier_access(db, chantier_id, user)
    docs = (
        await db.spec_drafts.find(
            {"chantier_id": chantier_id, "status": "pending"},
            {"_id": 0, "raw_response": 0},
        )
        .sort("created_at", -1)
        .to_list(50)
    )
    return [SpecDraft(**d) for d in docs]


@router.get("/spec-drafts/{draft_id}", response_model=SpecDraft)
async def get_draft(draft_id: str, user=Depends(require_roles(EDIT_ROLES))):
    """Détail d'un brouillon (preview avant validation)."""
    doc = await db.spec_drafts.find_one(
        {"id": draft_id}, {"_id": 0, "raw_response": 0}
    )
    if not doc:
        raise HTTPException(404, "Brouillon introuvable")
    await check_chantier_access(db, doc["chantier_id"], user)
    return SpecDraft(**doc)


@router.post("/spec-drafts/{draft_id}/confirm")
async def confirm_import(
    draft_id: str,
    payload: ConfirmImportPayload,
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Valide l'import : convertit les items en mesures pré-remplies."""
    draft = await db.spec_drafts.find_one({"id": draft_id})
    if not draft:
        raise HTTPException(404, "Brouillon introuvable")
    if draft.get("status") != "pending":
        raise HTTPException(400, "Brouillon déjà traité")
    chantier_id = draft["chantier_id"]
    await check_chantier_access(db, chantier_id, user)

    # Convertit en payloads MesureCreate (avec expansion quantity)
    items_dicts = [item.model_dump() for item in payload.items]
    mesure_payloads = _expand_items_for_mesures(items_dicts)
    if not mesure_payloads:
        raise HTTPException(400, "Aucun châssis valide à importer")

    created: List[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for p in mesure_payloads:
        doc = {
            **p,
            "id": str(uuid.uuid4()),
            "chantier_id": chantier_id,
            "created_at": now,
            "alerts": [],
            "slope_angle_deg": None,
        }
        await db.mesures.insert_one(doc)
        doc.pop("_id", None)
        created.append(doc)

    # Marque le brouillon comme importé
    await db.spec_drafts.update_one(
        {"id": draft_id},
        {
            "$set": {
                "status": "imported",
                "imported_at": now,
                "imported_count": len(created),
            }
        },
    )

    return {
        "ok": True,
        "draft_id": draft_id,
        "mesures_created": len(created),
        "chantier_id": chantier_id,
    }


@router.post("/spec-drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, user=Depends(require_roles(EDIT_ROLES))):
    """Rejette un brouillon (l'artisan annule l'import après preview)."""
    draft = await db.spec_drafts.find_one({"id": draft_id})
    if not draft:
        raise HTTPException(404, "Brouillon introuvable")
    await check_chantier_access(db, draft["chantier_id"], user)
    await db.spec_drafts.update_one(
        {"id": draft_id},
        {
            "$set": {
                "status": "rejected",
                "rejected_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    return {"ok": True}



# ════════════════════════════════════════════════════════════════════════
# 🆕 CHUNKED UPLOAD — Anti-502 sur gros PDF en réseau lent (juin 2026)
# ════════════════════════════════════════════════════════════════════════
# Stratégie : le frontend découpe le fichier en chunks de 1 Mo, chaque chunk
# est uploadé dans une requête courte (<10 sec) qui ne risque pas un timeout
# Cloudflare. Puis le frontend appelle /complete qui réassemble les chunks
# sur disque (/tmp) et lance l'analyse IA en background.
#
# Stockage temporaire : /tmp/spec_chunked_uploads/{upload_id}/
#   - chunk_0000, chunk_0001, … (1 fichier par chunk)
#   - meta.json (filename, mime, total_chunks, total_size, chantier_id, user_id)
#
# Cleanup auto au /complete (succès) et après 1h (failsafe via task background).
# ════════════════════════════════════════════════════════════════════════

# Taille max d'un chunk individuel : 2 Mo (marge de manœuvre, frontend = 1 Mo)
MAX_CHUNK_SIZE = 2 * 1024 * 1024
# TTL max d'un upload incomplet (1h)
UPLOAD_TTL_SECONDS = 3600

CHUNKED_UPLOAD_DIR = Path(tempfile.gettempdir()) / "spec_chunked_uploads"
CHUNKED_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ChunkedInitPayload(BaseModel):
    filename: str
    mime_type: str = ""
    total_size: int
    total_chunks: int


class ChunkedInitResponse(BaseModel):
    upload_id: str
    chunk_size: int = 1024 * 1024  # 1 Mo recommandé côté client


async def _cleanup_upload_dir(upload_id: str) -> None:
    """Supprime le dossier d'upload (best-effort)."""
    try:
        d = CHUNKED_UPLOAD_DIR / upload_id
        if d.exists() and d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    except Exception:
        logger.warning("Failed to cleanup chunked upload dir %s", upload_id)


@router.post(
    "/chantiers/{chantier_id}/import-spec/chunked/init",
    response_model=ChunkedInitResponse,
)
async def chunked_init(
    chantier_id: str,
    payload: ChunkedInitPayload,
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Initialise un upload chunké pour un cahier des charges."""
    # Accès chantier + paywall (mêmes règles que l'upload classique)
    await check_chantier_access(db, chantier_id, user)
    _ensure_subscription_allows_import(user)

    if payload.total_size <= 0:
        raise HTTPException(400, "Taille totale invalide")
    if payload.total_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            413,
            f"Fichier trop volumineux (max {MAX_UPLOAD_SIZE // (1024 * 1024)} Mo)",
        )
    if payload.total_chunks <= 0 or payload.total_chunks > 64:
        raise HTTPException(400, "Nombre de chunks invalide (max 64)")

    source = _detect_source(payload.filename, payload.mime_type)
    if source is None:
        raise HTTPException(
            400,
            "Format non supporté. Utilisez PDF, Excel (.xlsx) ou image (JPG/PNG).",
        )

    upload_id = str(uuid.uuid4())
    upload_dir = CHUNKED_UPLOAD_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Stocke les métadonnées en DB pour gestion server-restart
    await db.spec_chunked_uploads.insert_one(
        {
            "id": upload_id,
            "chantier_id": chantier_id,
            "filename": payload.filename,
            "mime_type": payload.mime_type,
            "total_size": payload.total_size,
            "total_chunks": payload.total_chunks,
            "received_chunks": 0,
            "source": source,
            "status": "uploading",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": user.get("user_id") or user.get("id") or "",
        }
    )
    logger.info(
        "📦 Chunked upload init: id=%s, file=%s, size=%d, chunks=%d",
        upload_id,
        payload.filename,
        payload.total_size,
        payload.total_chunks,
    )
    return ChunkedInitResponse(upload_id=upload_id)


@router.post("/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk")
async def chunked_upload(
    chantier_id: str,
    upload_id: str,
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Upload d'un chunk individuel."""
    await check_chantier_access(db, chantier_id, user)
    meta = await db.spec_chunked_uploads.find_one({"id": upload_id})
    if not meta:
        raise HTTPException(404, "Upload session introuvable ou expirée")
    if meta.get("status") != "uploading":
        raise HTTPException(400, "Cette session n'accepte plus de chunks")
    if meta.get("chantier_id") != chantier_id:
        raise HTTPException(403, "Chantier non autorisé pour cette session")
    if chunk_index < 0 or chunk_index >= meta["total_chunks"]:
        raise HTTPException(400, f"chunk_index hors limites (0..{meta['total_chunks']-1})")

    # Lit + valide la taille du chunk
    chunk_bytes = await file.read()
    if not chunk_bytes:
        raise HTTPException(400, "Chunk vide")
    if len(chunk_bytes) > MAX_CHUNK_SIZE:
        raise HTTPException(413, f"Chunk trop gros (max {MAX_CHUNK_SIZE // (1024*1024)} Mo)")

    # Écrit le chunk sur disque (overwrite si retry du même index — idempotent)
    upload_dir = CHUNKED_UPLOAD_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    chunk_path = upload_dir / f"chunk_{chunk_index:04d}"
    with open(chunk_path, "wb") as f:
        f.write(chunk_bytes)

    # Recompte les chunks effectivement présents (pour idempotence)
    received_count = sum(
        1 for p in upload_dir.iterdir() if p.name.startswith("chunk_")
    )
    await db.spec_chunked_uploads.update_one(
        {"id": upload_id},
        {"$set": {"received_chunks": received_count}},
    )
    return {
        "ok": True,
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "received_chunks": received_count,
        "total_chunks": meta["total_chunks"],
    }


@router.post(
    "/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/complete",
    response_model=SpecDraft,
)
async def chunked_complete(
    chantier_id: str,
    upload_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Assemble les chunks et lance l'analyse IA en background."""
    chantier = await check_chantier_access(db, chantier_id, user)
    meta = await db.spec_chunked_uploads.find_one({"id": upload_id})
    if not meta:
        raise HTTPException(404, "Upload session introuvable")
    if meta.get("chantier_id") != chantier_id:
        raise HTTPException(403, "Chantier non autorisé pour cette session")

    upload_dir = CHUNKED_UPLOAD_DIR / upload_id
    if not upload_dir.exists():
        raise HTTPException(404, "Chunks introuvables sur disque (session expirée ?)")

    # Vérifie que tous les chunks attendus sont présents
    missing = []
    for i in range(meta["total_chunks"]):
        if not (upload_dir / f"chunk_{i:04d}").exists():
            missing.append(i)
    if missing:
        raise HTTPException(
            400,
            f"Chunks manquants : {missing[:5]}{'…' if len(missing) > 5 else ''} ({len(missing)} au total)",
        )

    # Assemble tous les chunks dans un buffer en mémoire (max 15 Mo, OK)
    buffer = bytearray()
    for i in range(meta["total_chunks"]):
        with open(upload_dir / f"chunk_{i:04d}", "rb") as f:
            buffer.extend(f.read())
    raw_bytes = bytes(buffer)

    if len(raw_bytes) != meta["total_size"]:
        logger.warning(
            "⚠️ Chunked assembly size mismatch: expected=%d, got=%d",
            meta["total_size"],
            len(raw_bytes),
        )
        # On continue quand même — peut-être un base64 ou compression. Mais on log.

    # Crée le draft "processing" et lance l'IA en background
    source = meta["source"]
    draft_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    draft_doc = {
        "id": draft_id,
        "chantier_id": chantier_id,
        "company_id": chantier.get("company_id", "default"),
        "filename": meta["filename"],
        "source": source,
        "summary": "",
        "items": [],
        "status": "processing",
        "created_at": now,
        "created_by": user.get("user_id") or user.get("id") or "",
        "raw_response": "",
        "via_chunked": True,
    }
    await db.spec_drafts.insert_one(draft_doc)

    mime = meta.get("mime_type") or "application/octet-stream"
    background_tasks.add_task(
        _run_ai_analysis_bg,
        draft_id=draft_id,
        raw_bytes=raw_bytes,
        source=source,
        mime=mime,
    )

    # Marque la session comme terminée
    await db.spec_chunked_uploads.update_one(
        {"id": upload_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now,
                "draft_id": draft_id,
            }
        },
    )

    # Cleanup disque (best-effort, en background)
    background_tasks.add_task(_cleanup_upload_dir, upload_id)

    logger.info(
        "✅ Chunked upload complete: upload_id=%s → draft_id=%s, size=%d bytes",
        upload_id,
        draft_id,
        len(raw_bytes),
    )
    draft_doc.pop("_id", None)
    draft_doc.pop("raw_response", None)
    return SpecDraft(**draft_doc)


@router.post("/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/abort")
async def chunked_abort(
    chantier_id: str,
    upload_id: str,
    user=Depends(require_roles(EDIT_ROLES)),
):
    """Annule un upload chunked en cours (cleanup disque + DB)."""
    await check_chantier_access(db, chantier_id, user)
    await db.spec_chunked_uploads.update_one(
        {"id": upload_id, "chantier_id": chantier_id},
        {"$set": {"status": "aborted"}},
    )
    await _cleanup_upload_dir(upload_id)
    return {"ok": True}
