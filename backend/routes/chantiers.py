"""Routes CRUD chantiers (métier de base + signatures)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from db import BETA_MODE, FREE_PLAN_MAX_CHANTIERS, VALID_STATUSES, db
from deps import (
    require_active_subscription,
    require_roles,
    send_push_to_user,
)
from email_service import send_assignment_email
from models import (
    Chantier,
    ChantierCreate,
    ChantierUpdate,
    SignatureIn,
)
router = APIRouter()


@router.post("/chantiers", response_model=Chantier)
async def create_chantier(
    payload: ChantierCreate,
    user=Depends(require_roles(["admin", "commercial"])),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    # --- Anti-fraud Freemium lifetime limit -------------------------------
    # 🚧 BETA GRATUITE : limite désactivée (BETA_MODE=True). Le bloc reste
    # en place pour réactivation simple une fois Stripe en ligne.
    if (
        not BETA_MODE
        and (user.get("plan") == "free")
        and not user.get("artisan_mode", False)
    ):
        used = int(user.get("chantiers_lifetime_count", 0))
        if used >= FREE_PLAN_MAX_CHANTIERS:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "free_plan_limit",
                    "message": (
                        f"Limite Freemium atteinte ({FREE_PLAN_MAX_CHANTIERS} "
                        "chantiers maximum sur la durée de vie du compte). "
                        "Passez en Pro pour créer des chantiers illimités."
                    ),
                    "limit": FREE_PLAN_MAX_CHANTIERS,
                    "used": used,
                },
            )
    client_name = payload.client_name
    if not client_name:
        parts = [p for p in [payload.last_name, payload.first_name] if p]
        client_name = " ".join(parts).strip() or "Sans nom"
    doc = {
        "id": str(uuid.uuid4()),
        "client_name": client_name,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "address": payload.address,
        "postal_code": payload.postal_code,
        "city": payload.city,
        "status": payload.status,
        "created_by": user["id"],
        "assigned_to": payload.assigned_to,
        "appointment_at": payload.appointment_at,
        "notes": payload.notes,
        "company_id": user.get("company_id", "default"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "site_photos": payload.site_photos or [],
    }
    await db.chantiers.insert_one(doc)
    doc.pop("_id", None)
    # Incrément lifetime — quel que soit le plan (utile pour bascules ultérieures).
    await db.companies.update_one(
        {"company_id": user.get("company_id", "default")},
        {"$inc": {"chantiers_lifetime_count": 1}},
        upsert=True,
    )
    if payload.assigned_to:
        await send_push_to_user(
            payload.assigned_to,
            "📌 Nouveau chantier assigné",
            f"{client_name} — Prise de rendez-vous à faire",
            {"type": "chantier_assigned", "chantier_id": doc["id"]},
        )
        # Notification email interne (anti-double : skip si auto-attribution)
        if payload.assigned_to != user["id"]:
            try:
                assignee = await db.users.find_one(
                    {"id": payload.assigned_to, "company_id": user.get("company_id", "default")},
                    {"_id": 0, "email": 1, "name": 1},
                )
                if assignee and assignee.get("email"):
                    address_parts = [
                        p for p in [
                            payload.address, payload.postal_code, payload.city
                        ] if p
                    ]
                    send_assignment_email(
                        to=assignee["email"],
                        assignee_name=assignee.get("name") or "",
                        chantier_name=client_name,
                        address=", ".join(address_parts) if address_parts else None,
                        created_by_name=user.get("name"),
                    )
            except Exception:
                # L'email ne doit jamais bloquer la création
                pass
    return Chantier(**doc)


@router.get("/chantiers", response_model=List[Chantier])
async def list_chantiers(
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    user=Depends(require_active_subscription),
):
    query: dict = {"company_id": user.get("company_id", "default")}
    if status_filter and status_filter in VALID_STATUSES:
        query["status"] = status_filter
    if q:
        import re as _re
        safe = _re.escape(q.strip())
        query["$or"] = [
            {"client_name": {"$regex": safe, "$options": "i"}},
            {"address": {"$regex": safe, "$options": "i"}},
        ]
    docs = (
        await db.chantiers.find(query, {"_id": 0})
        .sort("created_at", -1)
        .to_list(500)
    )
    return [Chantier(**d) for d in docs]


@router.get("/chantiers/{chantier_id}", response_model=Chantier)
async def get_chantier(
    chantier_id: str, user=Depends(require_active_subscription)
):
    doc = await db.chantiers.find_one(
        {
            "id": chantier_id,
            "company_id": user.get("company_id", "default"),
        },
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    return Chantier(**doc)


@router.patch("/chantiers/{chantier_id}", response_model=Chantier)
async def update_chantier(
    chantier_id: str,
    payload: ChantierUpdate,
    user=Depends(require_roles(["admin", "commercial", "technician"])),
):
    # NB : Le technicien peut PATCH ce endpoint pour faire avancer le
    # pipeline (status: technique_a_valider → en_fabrication → cloture),
    # ce qui est sa responsabilité métier. Les champs sensibles (client,
    # assignations) sont protégés ci-dessous pour les techniciens.
    if user.get("role") == "technician":
        # Filtre les champs autorisés pour le technician : uniquement le
        # statut peut être modifié (clôture / validation fabrication).
        allowed = {"status"}
        payload_dict = {
            k: v for k, v in payload.model_dump().items() if v is not None
        }
        forbidden = set(payload_dict.keys()) - allowed
        if forbidden:
            raise HTTPException(
                403,
                f"Technicien : modification limitée au statut "
                f"(refusé : {', '.join(sorted(forbidden))}).",
            )
    company = user.get("company_id", "default")
    existing = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}
    )
    if not existing:
        raise HTTPException(404, "Chantier introuvable")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if "status" in update and update["status"] not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")
    # --- RBAC par transition de statut --------------------------------------
    # Workflow strict (sauf mode Artisan où l'Admin a tous les droits) :
    #   devis_a_faire        → a_mesurer            : Admin/Commercial
    #   a_mesurer            → technique_a_valider  : Commercial/Admin
    #   technique_a_valider  → en_fabrication       : Technicien
    #   en_fabrication       → cloture              : Technicien
    if "status" in update:
        old_status = existing.get("status")
        new_status = update["status"]
        role = user.get("role")
        company_doc = await db.companies.find_one({"company_id": company}) or {}
        is_artisan_mode = bool(
            company_doc.get("artisan_mode")
            or company_doc.get("account_type") == "artisan"
        )
        if not is_artisan_mode and old_status != new_status:
            allowed_transitions: dict[tuple[str, str], set[str]] = {
                ("devis_a_faire", "a_mesurer"): {"admin"},
                ("a_mesurer", "technique_a_valider"): {"commercial"},
                ("technique_a_valider", "en_fabrication"): {"technician"},
                ("a_verifier", "en_fabrication"): {"technician"},
                ("en_fabrication", "cloture"): {"technician"},
                ("en_commande", "cloture"): {"technician"},
            }
            key = (old_status, new_status)
            if key in allowed_transitions and role not in allowed_transitions[key]:
                raise HTTPException(
                    403,
                    f"Cette transition ({old_status} → {new_status}) est "
                    f"réservée aux rôles : "
                    f"{', '.join(sorted(allowed_transitions[key]))}.",
                )
    if update:
        await db.chantiers.update_one(
            {"id": chantier_id, "company_id": company}, {"$set": update}
        )
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    new_assignee = update.get("assigned_to")
    if new_assignee and new_assignee != existing.get("assigned_to"):
        await send_push_to_user(
            new_assignee,
            "Nouveau chantier affecté",
            f"{doc['client_name']} — {doc['address']}",
            {"type": "chantier_assigned", "chantier_id": chantier_id},
        )
    return Chantier(**doc)


# ──────────────────────────────────────────────────────────────────────
# Configuration du Mur (Étape 1 du wizard) — accessible aussi aux
# techniciens car le terrain peut être configuré par le technicien lors
# de la première visite. Endpoint dédié pour ne pas ouvrir tout PATCH.
# ──────────────────────────────────────────────────────────────────────
@router.patch("/chantiers/{chantier_id}/wall-config", response_model=Chantier)
async def update_wall_config(
    chantier_id: str,
    payload: dict,
    user=Depends(require_roles(["admin", "commercial", "technician"])),
):
    company = user.get("company_id", "default")
    existing = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}
    )
    if not existing:
        raise HTTPException(404, "Chantier introuvable")
    # On accepte un dict free-form (project_type, masonry_type,
    # gros_oeuvre_mm, insulation_mode, parement_type, etc.)
    if not isinstance(payload, dict):
        raise HTTPException(400, "Payload doit être un objet JSON")

    # 🛡️ Garde anti-corruption : on plafonne les épaisseurs à 2000mm (mur
    # de 2m max) pour bloquer les valeurs aberrantes type 30050 (bug iOS
    # autocomplete observé). Si une valeur dépasse → on tronque à 2000 et
    # on log un warning. Le frontend a déjà un cap à 9999 dans CotField.
    SUSPECT_FIELDS = (
        "gros_oeuvre_mm",
        "iti_thickness_mm",
        "ite_insul_thickness_mm",
        "crepi_thickness_mm",
        "coulisse_thickness_mm",
        "brique_pierre_thickness_mm",
        "structure_lame_air_mm",
        "sill_thickness_mm",
    )
    import logging as _lg
    _logger = _lg.getLogger("mesurechassis")
    for k in SUSPECT_FIELDS:
        v = payload.get(k)
        if v is None:
            continue
        try:
            num = float(v)
        except (TypeError, ValueError):
            continue
        if num > 2000:
            _logger.warning(
                "wall_config: valeur suspecte %s=%s (chantier=%s) — refusée",
                k,
                num,
                chantier_id,
            )
            raise HTTPException(
                400,
                detail=(
                    f"Cote « {k} » = {num:g} mm aberrante "
                    "(épaisseur de mur > 2000 mm impossible). "
                    "Vérifiez votre saisie."
                ),
            )

    await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {"$set": {"wall_config": payload}},
    )
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    return Chantier(**doc)


@router.delete("/chantiers/{chantier_id}")
async def delete_chantier(
    chantier_id: str,
    user=Depends(require_roles(["admin", "commercial"])),
):
    company = user.get("company_id", "default")
    res = await db.chantiers.delete_one(
        {"id": chantier_id, "company_id": company}
    )
    if res.deleted_count:
        await db.mesures.delete_many({"chantier_id": chantier_id})
    return {"ok": True}


# --- Signatures ----------------------------------------------------------
@router.post("/chantiers/{chantier_id}/signature", response_model=Chantier)
async def save_signature(
    chantier_id: str,
    payload: SignatureIn,
    user=Depends(require_active_subscription),
):
    company = user.get("company_id", "default")
    if not payload.signature.strip():
        raise HTTPException(400, "Signature vide")
    res = await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {
            "$set": {
                "client_signature": payload.signature,
                "signed_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Chantier introuvable")
    doc = await db.chantiers.find_one({"id": chantier_id}, {"_id": 0})
    return Chantier(**doc)


@router.delete("/chantiers/{chantier_id}/signature", response_model=Chantier)
async def delete_signature(
    chantier_id: str, user=Depends(require_active_subscription)
):
    company = user.get("company_id", "default")
    await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {"$set": {"client_signature": None, "signed_at": None}},
    )
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    return Chantier(**doc)
