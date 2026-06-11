"""Inscriptions des testeurs Google Play (pré-lancement).

Page publique `/devenir-testeur` → POST /api/testers/register (sans auth).
L'admin consulte la liste dans l'app (GET /api/testers) puis colle les
adresses dans Google Play Console (liste de testeurs du test fermé).
"""

import logging
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_admin

logger = logging.getLogger("mesurechassis.testers")

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/testers/register")
async def register_tester(payload: dict):
    """Inscription publique d'un candidat testeur (pas d'authentification)."""
    name = (payload.get("name") or "").strip()
    company = (payload.get("company") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    phone = (payload.get("phone") or "").strip()

    if not name:
        raise HTTPException(400, "Nom requis")
    if not email or not EMAIL_RE.match(email):
        raise HTTPException(400, "Adresse email valide requise")

    existing = await db.tester_signups.find_one({"email": email})
    if existing:
        # Idempotent : on ne crée pas de doublon mais on confirme au visiteur.
        return {"ok": True, "message": "Vous êtes déjà inscrit ! Vous recevrez le lien d'invitation très bientôt."}

    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "status": "new",  # new → invited (une fois ajouté dans Play Console)
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tester_signups.insert_one(doc)
    logger.info("Nouveau testeur inscrit : %s (%s)", email, company or "—")

    # Notification email à l'admin (best-effort, ne bloque jamais l'inscription)
    try:
        from email_service import send_email
        import os
        send_email(
            to=os.getenv("SUPPORT_EMAIL", "info@mesurechassis.com"),
            subject=f"🧪 Nouveau testeur : {name}",
            body="",
            html=(
                f"<p>Nouvelle inscription testeur Google Play :</p>"
                f"<ul><li><b>Nom :</b> {name}</li>"
                f"<li><b>Société :</b> {company or '—'}</li>"
                f"<li><b>Email :</b> {email}</li>"
                f"<li><b>Téléphone :</b> {phone or '—'}</li></ul>"
                f"<p>Ajoutez cette adresse à la liste de testeurs dans Google Play Console.</p>"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification email testeur non envoyée : %s", exc)

    return {
        "ok": True,
        "message": "Inscription enregistrée ! Vous recevrez le lien d'invitation Google Play très bientôt.",
    }


@router.get("/testers")
async def list_testers(user=Depends(require_admin)):
    """Liste des candidats testeurs (admin uniquement)."""
    docs = (
        await db.tester_signups.find({}, {"_id": 0})
        .sort("created_at", -1)
        .to_list(2000)
    )
    return {"total": len(docs), "testers": docs}


@router.patch("/testers/{tester_id}/invited")
async def mark_tester_invited(tester_id: str, user=Depends(require_admin)):
    """Marque un testeur comme ajouté dans Play Console (suivi visuel)."""
    res = await db.tester_signups.update_one(
        {"id": tester_id}, {"$set": {"status": "invited"}}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Testeur introuvable")
    return {"ok": True}


@router.delete("/testers/{tester_id}")
async def delete_tester(tester_id: str, user=Depends(require_admin)):
    """Supprime une inscription (admin uniquement)."""
    res = await db.tester_signups.delete_one({"id": tester_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Testeur introuvable")
    return {"ok": True}
