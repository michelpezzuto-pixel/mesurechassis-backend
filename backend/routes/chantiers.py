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
from email_service import (
    send_assignment_email,
    send_ready_for_verification_email,
)
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
    # 🆕 V3 — Validation stricte du nom client (cahier 10/06/2026).
    #    Empêche la création de chantiers "Sans nom" qui corrompaient
    #    l'affichage des listes côté frontend.
    last_clean = (payload.last_name or "").strip()
    client_name_clean = (payload.client_name or "").strip()
    if not last_clean and not client_name_clean:
        raise HTTPException(
            status_code=422,
            detail="Le nom du client (last_name) est obligatoire.",
        )
    addr_clean = (payload.address or "").strip()
    if not addr_clean:
        raise HTTPException(
            status_code=422,
            detail="L'adresse du chantier (address) est obligatoire.",
        )
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
    # ⚙️ Mode Artisan / Solo : le devis a été établi AVANT la prise de mesures
    # (étape commerciale hors-app). Le chantier est donc créé directement en
    # "À mesurer", sans étape intermédiaire "Devis à faire".
    initial_status = payload.status
    if user.get("artisan_mode", False) and initial_status == "devis_a_faire":
        initial_status = "a_mesurer"
    # ⚙️ Mode Entreprise + Admin avec assigned_to : la phase commerciale
    # est faite hors-app. On démarre directement en "À mesurer" pour que
    # le commercial assigné voie immédiatement le bouton "Clôturer la prise
    # de cotes". Pas d'étape "Devis à faire" intermédiaire qui bloque.
    if (
        initial_status == "devis_a_faire"
        and user.get("role") == "admin"
        and payload.assigned_to
    ):
        initial_status = "a_mesurer"
    # 🔒 RBAC Entreprise : l'Admin DOIT assigner le chantier à un Commercial
    # (ou Technicien) au moment de la création. Le mode Artisan est exempté.
    company_for_check = await db.companies.find_one(
        {"company_id": user.get("company_id", "default")}
    ) or {}
    is_artisan_mode_check = bool(
        company_for_check.get("artisan_mode")
        or company_for_check.get("account_type") == "artisan"
        or user.get("artisan_mode", False)
    )
    if (
        not is_artisan_mode_check
        and user.get("role") == "admin"
        and not payload.assigned_to
    ):
        # 🆕 Commercial optionnel pour l'admin SEUL : si l'entreprise n'a
        # aucun commercial/technicien (artisan travaillant seul en mode
        # Entreprise), on n'exige plus l'assignation → auto-attribution à
        # lui-même pour ne pas le bloquer. S'il a une équipe, l'assignation
        # reste obligatoire (workflow RBAC préservé).
        team_count = await db.users.count_documents(
            {
                "company_id": user.get("company_id", "default"),
                "role": {"$in": ["commercial", "technician"]},
            }
        )
        if team_count > 0:
            raise HTTPException(
                400,
                "En mode Entreprise, l'Admin doit assigner le chantier à un "
                "Commercial lors de la création (assigned_to obligatoire).",
            )
        # Solo → l'admin se voit attribuer son propre chantier.
        payload.assigned_to = user["id"]
    # Vérifie que le destinataire de l'assignation existe dans la même company
    if payload.assigned_to and not is_artisan_mode_check:
        assignee_check = await db.users.find_one(
            {
                "id": payload.assigned_to,
                "company_id": user.get("company_id", "default"),
            },
            {"_id": 0, "role": 1},
        )
        if not assignee_check:
            raise HTTPException(
                400, "Collaborateur introuvable dans votre entreprise."
            )
    doc = {
        "id": str(uuid.uuid4()),
        "client_name": client_name,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "address": payload.address,
        "postal_code": payload.postal_code,
        "city": payload.city,
        # 📞 (juin 2026) Coordonnées client — persistées à la création.
        "client_phone": (payload.client_phone or "").strip() or None,
        "client_email": (payload.client_email or "").strip() or None,
        "status": initial_status,
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
                ("a_mesurer", "a_verifier"): {"commercial"},
                ("technique_a_valider", "en_fabrication"): {"technician"},
                ("a_verifier", "en_fabrication"): {"technician"},
                # 🔄 RENVOI vers le commercial pour corrections
                ("a_verifier", "a_mesurer"): {"technician"},
                ("technique_a_valider", "a_mesurer"): {"technician"},
                ("en_fabrication", "a_verifier"): {"technician"},
                # 🏁 CLÔTURE DÉFINITIVE : réservée à l'Admin (et technicien
                #    en mode legacy pour ne pas casser les workflows existants)
                ("en_fabrication", "cloture"): {"admin", "technician"},
                ("en_commande", "cloture"): {"admin", "technician"},
                ("a_verifier", "cloture"): {"admin"},
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
    # 🔔 EMAIL CRITIQUE : prévenir Tech + Admin que la prise de cotes est
    #    terminée et qu'il faut maintenant vérifier les mesures.
    if (
        "status" in update
        and update.get("status") == "a_verifier"
        and existing.get("status") != "a_verifier"
        and user.get("role") == "commercial"
    ):
        # On compte les mesures pour info dans l'email
        try:
            nb_mesures = await db.mesures.count_documents(
                {"chantier_id": chantier_id, "company_id": company}
            )
        except Exception:
            nb_mesures = 0
        # Récupère tous les techniciens + admins de la même entreprise
        try:
            recipients = await db.users.find(
                {
                    "company_id": company,
                    "role": {"$in": ["technician", "admin"]},
                    "email": {"$exists": True, "$ne": None},
                },
                {"_id": 0, "email": 1, "name": 1, "role": 1},
            ).to_list(50)
            for r in recipients:
                try:
                    send_ready_for_verification_email(
                        to=r.get("email"),
                        recipient_name=r.get("name") or "",
                        chantier_name=doc.get("client_name", ""),
                        address=doc.get("address"),
                        commercial_name=user.get("name"),
                        nb_mesures=nb_mesures,
                    )
                except Exception as e:
                    import logging as _lg
                    _lg.getLogger("mesurechassis").warning(
                        "Email a_verifier ko pour %s: %s", r.get("email"), e
                    )
        except Exception:
            # Best effort — on ne bloque jamais la transition de statut
            pass
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



# ═════════════════════════════════════════════════════════════════════
# WORKFLOW DEMANDE DE MODIFICATION (Commercial → Technicien)
# ═════════════════════════════════════════════════════════════════════
# Le Commercial, une fois le chantier passé en "À vérifier", ne peut PLUS
# modifier les mesures directement. Pour récupérer la main, il doit
# demander l'autorisation au Technicien. Ce dernier peut approuver
# (statut → "à mesurer") ou refuser. Le flag est stocké directement
# dans le document chantier sous `mod_request`.

@router.post("/chantiers/{chantier_id}/mod-request")
async def request_modification(
    chantier_id: str,
    payload: dict,
    user=Depends(require_roles(["commercial"])),
):
    """Le Commercial demande au Technicien d'autoriser la modification."""
    company = user.get("company_id", "default")
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    # Une demande n'est possible que pour les chantiers verrouillés au commercial
    if doc.get("status") not in {"a_verifier", "technique_a_valider"}:
        raise HTTPException(
            400,
            "La demande de modification n'est possible que pour les chantiers"
            " en attente de vérification.",
        )
    reason = (payload or {}).get("reason", "").strip()[:500]
    now = datetime.now(timezone.utc).isoformat()
    mod_req = {
        "requested_at": now,
        "requested_by": user.get("id"),
        "requested_by_name": user.get("name"),
        "reason": reason,
        "status": "pending",
    }
    await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {"$set": {"mod_request": mod_req}},
    )
    # 🔔 Notifier les techniciens de la même entreprise
    tech_users = await db.users.find(
        {"company_id": company, "role": "technician"},
        {"_id": 0, "id": 1, "push_token": 1, "name": 1},
    ).to_list(50)
    for tech in tech_users:
        try:
            await send_push_to_user(
                tech.get("id"),
                "🔔 Demande de modification",
                f"{user.get('name')} demande à modifier le chantier "
                f"{doc.get('client_name', '')}",
                data={"chantier_id": chantier_id, "type": "mod_request"},
            )
        except Exception:
            pass
    return {"ok": True, "mod_request": mod_req}


@router.post("/chantiers/{chantier_id}/mod-request/respond")
async def respond_modification(
    chantier_id: str,
    payload: dict,
    user=Depends(require_roles(["technician", "admin"])),
):
    """Le Technicien approuve ou refuse la demande du Commercial.

    payload: { "approve": bool, "comment": str (optional) }
    """
    company = user.get("company_id", "default")
    doc = await db.chantiers.find_one(
        {"id": chantier_id, "company_id": company}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Chantier introuvable")
    mod_req = doc.get("mod_request") or {}
    if mod_req.get("status") != "pending":
        raise HTTPException(
            400, "Aucune demande de modification en attente."
        )
    approve = bool((payload or {}).get("approve", False))
    comment = (payload or {}).get("comment", "").strip()[:500]
    now = datetime.now(timezone.utc).isoformat()
    updates: dict = {
        "mod_request.status": "approved" if approve else "refused",
        "mod_request.responded_at": now,
        "mod_request.responded_by": user.get("id"),
        "mod_request.responded_by_name": user.get("name"),
        "mod_request.response_comment": comment,
    }
    if approve:
        # Repasse le chantier en "à mesurer" pour que le commercial corrige
        updates["status"] = "a_mesurer"
    await db.chantiers.update_one(
        {"id": chantier_id, "company_id": company},
        {"$set": updates},
    )
    # 🔔 Notifier le commercial qui a fait la demande
    requester_id = mod_req.get("requested_by")
    if requester_id:
        try:
            title = (
                "✅ Demande acceptée"
                if approve
                else "❌ Demande refusée"
            )
            body = (
                f"Vous pouvez reprendre les mesures du chantier "
                f"{doc.get('client_name', '')}"
                if approve
                else "Le technicien a refusé votre demande de modification."
            )
            await send_push_to_user(
                requester_id,
                title,
                body,
                data={
                    "chantier_id": chantier_id,
                    "type": "mod_request_response",
                    "approved": approve,
                },
            )
        except Exception:
            pass
    return {"ok": True, "approved": approve}
