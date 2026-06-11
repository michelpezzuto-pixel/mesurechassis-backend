"""Module Campagne — prospection testeurs à 1 bouton.

L'admin importe des prospects (email + entreprise + région) puis clique sur
« Envoyer le lot du jour » : le backend envoie jusqu'à 15 emails personnalisés
par jour via Resend (limite anti-spam), avec mention STOP (RGPD) et suivi des
statuts. Conçu pour pouvoir basculer sur Brevo plus tard (mêmes données).
"""

import asyncio
import csv
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from db import db
from deps import require_admin
from email_service import send_email

logger = logging.getLogger("mesurechassis.campaign")

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DAILY_LIMIT = 15
PAUSE_BETWEEN_SENDS_S = 3

SUBJECTS = {
    "be": "Artisan menuisier ? Testez en avant-première l'app belge de prise de mesures",
    "fr": "Artisan menuisier ? Testez en avant-première l'app de prise de mesures pensée pour le métier",
    "lu": "Artisan menuisier ? Testez en avant-première l'app de prise de mesures pensée pour le métier",
}

# {origin} : phrase d'accroche adaptée au pays du prospect (option B du client —
# les belges voient "application mobile belge", FR/LU un texte neutre).
ORIGIN_PHRASES = {
    "be": "une application mobile belge",
    "fr": "une application mobile conçue par un menuisier",
    "lu": "une application mobile conçue par un menuisier",
}

BODY_TEMPLATE = """Bonjour,

Je me permets de contacter {company} car je lance un outil pensé pour notre métier. Je m'appelle Michel Pezzuto et, comme vous, je connais les réalités du terrain. C'est pourquoi j'ai créé MesureChâssis : {origin} qui en finit avec le carnet de notes et les erreurs de ressaisie sur les chantiers.

Concrètement, MesureChâssis vous permet de :

✅ Relever vos cotes avec un assistant guidé — 12 formes de baies, du rectangle au bow-window
✅ Organiser vos chantiers et vos équipes (commercial / technicien)
✅ Générer en un clic des fiches PDF techniques prêtes pour la production

Avant le lancement officiel sur Google Play, j'ouvre l'application à un groupe d'artisans — et j'aimerais vous compter parmi eux. L'accès est entièrement gratuit.

👉 Pour devenir testeur (30 secondes) :
https://mesurechassis.com/devenir-testeur.html

Il vous faut simplement un téléphone Android et une adresse Gmail. Vous recevrez ensuite le lien d'installation Google Play par email.

Votre regard de professionnel compte : chaque retour m'aide à construire l'outil dont notre métier a vraiment besoin.

Bien cordialement,
Michel Pezzuto — Fondateur de MesureChâssis
info@mesurechassis.com · https://mesurechassis.com

—
Vous recevez cet email car votre entreprise est active dans la menuiserie. Pour ne plus être contacté, répondez simplement STOP."""


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


PROSPECTS_CSV = Path(__file__).resolve().parent.parent / "static" / "liste_prospects_testeurs.csv"


async def seed_prospects_from_csv() -> None:
    """Importe au démarrage les prospects du CSV embarqué (idempotent).

    Format : EMAIL;ENTREPRISE;REGION (utf-8 avec BOM possible).
    Les emails déjà présents en base sont ignorés — on peut donc enrichir
    le CSV et redéployer sans créer de doublons.
    """
    if not PROSPECTS_CSV.exists():
        return
    added = 0
    with PROSPECTS_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            email = (row.get("EMAIL") or "").strip().lower()
            if not EMAIL_RE.match(email):
                continue
            if await db.prospects.find_one({"email": email}):
                continue
            await db.prospects.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "company": (row.get("ENTREPRISE") or "").strip(),
                    "region": (row.get("REGION") or "").strip(),
                    "country": (row.get("PAYS") or "be").strip().lower(),
                    "status": "pending",
                    "sent_at": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            added += 1
    if added:
        logger.info("Campagne : %s prospects importés depuis le CSV.", added)


@router.post("/campaign/prospects/import")
async def import_prospects(payload: dict, user=Depends(require_admin)):
    """Importe/complète la liste de prospects. Dédoublonne par email."""
    items = payload.get("prospects") or []
    added, skipped = 0, 0
    for it in items:
        email = (it.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            skipped += 1
            continue
        if await db.prospects.find_one({"email": email}):
            skipped += 1
            continue
        await db.prospects.insert_one(
            {
                "id": str(uuid.uuid4()),
                "email": email,
                "company": (it.get("company") or "").strip(),
                "region": (it.get("region") or "").strip(),
                "country": (it.get("country") or "be").strip().lower(),
                "status": "pending",  # pending → sent | failed
                "sent_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        added += 1
    return {"ok": True, "added": added, "skipped": skipped}


@router.get("/campaign/stats")
async def campaign_stats(user=Depends(require_admin)):
    pending = await db.prospects.count_documents({"status": "pending"})
    sent = await db.prospects.count_documents({"status": "sent"})
    failed = await db.prospects.count_documents({"status": "failed"})
    sent_today = await db.prospects.count_documents(
        {"status": "sent", "sent_at": {"$gte": _today_start_iso()}}
    )
    sending = await db.prospects.count_documents({"status": "sending"})
    # Croisement : prospects contactés devenus testeurs inscrits
    signup_emails = {
        d["email"] for d in await db.tester_signups.find({}, {"email": 1}).to_list(2000)
    }
    contacted = await db.prospects.find(
        {"status": "sent"}, {"email": 1}
    ).to_list(2000)
    converted = sum(1 for c in contacted if c["email"] in signup_emails)
    return {
        "pending": pending,
        "sent": sent,
        "failed": failed,
        "sending": sending,
        "sent_today": sent_today,
        "daily_limit": DAILY_LIMIT,
        "converted": converted,
    }


@router.get("/campaign/prospects")
async def list_prospects(user=Depends(require_admin)):
    docs = (
        await db.prospects.find({}, {"_id": 0})
        .sort([("status", 1), ("sent_at", -1)])
        .to_list(500)
    )
    return {"prospects": docs}


async def _send_batch_task(prospect_ids: list[str]) -> None:
    """Tâche de fond : envoie les emails un par un, espacés (anti-spam)."""
    for pid in prospect_ids:
        doc = await db.prospects.find_one({"id": pid})
        if not doc or doc.get("status") not in ("sending",):
            continue
        company = doc.get("company") or "votre entreprise"
        country = (doc.get("country") or "be").lower()
        subject = SUBJECTS.get(country, SUBJECTS["fr"])
        body = BODY_TEMPLATE.format(
            company=company,
            origin=ORIGIN_PHRASES.get(country, ORIGIN_PHRASES["fr"]),
        )
        try:
            # send_email est synchrone (appel HTTP Resend) → thread séparé
            # pour ne pas bloquer l'event loop pendant le lot.
            res = await asyncio.to_thread(
                send_email, to=doc["email"], subject=subject, body=body
            )
            status = "sent" if res.get("delivered") else "failed"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Envoi campagne échoué pour %s : %s", doc["email"], exc)
            status = "failed"
        await db.prospects.update_one(
            {"id": pid},
            {"$set": {"status": status, "sent_at": datetime.now(timezone.utc).isoformat()}},
        )
        logger.info("Campagne → %s : %s", doc["email"], status)
        await asyncio.sleep(PAUSE_BETWEEN_SENDS_S)


@router.post("/campaign/send-batch")
async def send_batch(background_tasks: BackgroundTasks, user=Depends(require_admin)):
    """Envoie le lot du jour (max 15/jour, espacés de quelques secondes)."""
    sent_today = await db.prospects.count_documents(
        {"status": "sent", "sent_at": {"$gte": _today_start_iso()}}
    )
    remaining = DAILY_LIMIT - sent_today
    if remaining <= 0:
        raise HTTPException(
            429,
            f"Limite quotidienne atteinte ({DAILY_LIMIT} emails/jour). Revenez demain !",
        )
    batch = (
        await db.prospects.find({"status": "pending"}, {"_id": 0, "id": 1})
        .limit(remaining)
        .to_list(remaining)
    )
    if not batch:
        raise HTTPException(404, "Aucun prospect en attente — la liste est épuisée 🎉")
    ids = [b["id"] for b in batch]
    # On marque "sending" immédiatement pour éviter tout double-clic
    await db.prospects.update_many(
        {"id": {"$in": ids}}, {"$set": {"status": "sending"}}
    )
    background_tasks.add_task(_send_batch_task, ids)
    return {
        "ok": True,
        "scheduled": len(ids),
        "message": f"Envoi de {len(ids)} emails lancé (≈{len(ids) * PAUSE_BETWEEN_SENDS_S}s). Actualisez pour suivre.",
    }
