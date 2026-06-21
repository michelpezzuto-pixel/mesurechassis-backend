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

Paywall :
    En BETA_MODE, accessible à tous. Hors beta : nécessite un
    abonnement actif (standard / team / pro) — exclut le freemium.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
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
                    "width_top": width or None,
                    "width_middle": width or None,
                    "width_bottom": width or None,
                    "height_left": height or None,
                    "height_middle": height or None,
                    "height_right": height or None,
                    "options": {
                        "imported_from_spec": True,
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
