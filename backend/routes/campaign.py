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
from datetime import datetime, timedelta, timezone
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
RELANCE_DELAY_DAYS = 5  # relance auto J+5 si pas inscrit comme testeur

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

RELANCE_TEMPLATE = """Bonjour,

Il y a quelques jours, je proposais à {company} de découvrir MesureChâssis en avant-première — l'application qui simplifie la prise de mesures sur chantier (12 formes de baies, fiches PDF prêtes pour la production).

Les places de testeurs se remplissent et je voulais m'assurer que mon premier message ne s'était pas perdu : l'accès reste entièrement gratuit, et il suffit d'un téléphone Android et d'une adresse Gmail.

👉 Inscription en 30 secondes :
https://mesurechassis.com/devenir-testeur.html

Votre regard de professionnel serait précieux pour construire un outil qui colle vraiment au terrain.

Bien cordialement,
Michel Pezzuto — Fondateur de MesureChâssis
info@mesurechassis.com · https://mesurechassis.com

—
Pour ne plus être contacté, répondez simplement STOP."""

RECAP_RECIPIENT = "info@mesurechassis.com"
RECAP_WEEKDAY = 0  # lundi
RECAP_HOUR_UTC = 7  # ≈ 9h heure belge (été)


async def send_weekly_recap() -> dict:
    """Construit et envoie le récap hebdo de la campagne à l'admin."""
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    sent_week = await db.prospects.count_documents({"sent_at": {"$gte": week_ago}})
    relances_week = await db.prospects.count_documents(
        {"relance_sent_at": {"$gte": week_ago}}
    )
    signups_week = await db.tester_signups.count_documents(
        {"created_at": {"$gte": week_ago}}
    )
    signups_total = await db.tester_signups.count_documents({})
    pending = await db.prospects.count_documents({"status": "pending"})
    sent_total = await db.prospects.count_documents({"status": "sent"})
    relance_due = len(await _relances_dues())

    objectif = f"{signups_total}/12 testeurs Google Play"
    body = f"""Bonjour Michel,

Voici le point hebdomadaire de votre campagne de recrutement de testeurs MesureChâssis :

📊 CETTE SEMAINE
✉️ Emails de prospection envoyés : {sent_week}
🔁 Relances J+5 envoyées : {relances_week}
🎉 Nouveaux testeurs inscrits : {signups_week}

📈 SITUATION GLOBALE
🎯 Objectif Google Play : {objectif}
📬 Prospects contactés au total : {sent_total}
⏳ Prospects restant à contacter : {pending}
🔔 Relances en attente d'envoi : {relance_due}

👉 Pensez à votre clic quotidien « Envoyer le lot du jour » dans l'app (Dashboard → Campagne).

Bonne semaine !
— Votre assistant MesureChâssis"""

    res = await asyncio.to_thread(
        send_email,
        to=RECAP_RECIPIENT,
        subject="📊 Récap hebdo campagne testeurs — MesureChâssis",
        body=body,
    )
    logger.info(
        "Récap hebdo envoyé à %s (delivered=%s)", RECAP_RECIPIENT, res.get("delivered")
    )
    return res


async def weekly_recap_loop() -> None:
    """Boucle de fond : envoie le récap chaque lundi ≈ 9h belge (1 fois max/semaine)."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            if now.weekday() == RECAP_WEEKDAY and now.hour >= RECAP_HOUR_UTC:
                monday = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ).isoformat()
                marker = await db.campaign_meta.find_one({"key": "weekly_recap"})
                if not marker or marker.get("last_sent", "") < monday:
                    await send_weekly_recap()
                    await db.campaign_meta.update_one(
                        {"key": "weekly_recap"},
                        {"$set": {"last_sent": now.isoformat()}},
                        upsert=True,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Récap hebdo en erreur (réessai dans 1h) : %s", exc)
        await asyncio.sleep(3600)


@router.post("/campaign/recap-now")
async def recap_now(user=Depends(require_admin)):
    """Envoi immédiat du récap (test / à la demande depuis l'app)."""
    res = await send_weekly_recap()
    return {
        "ok": True,
        "delivered": bool(res.get("delivered")),
        "message": f"Récap envoyé à {RECAP_RECIPIENT} ✉️",
    }


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
            # CONTACTE_LE rempli = prospect déjà contacté manuellement (Outlook)
            # avant la mise en place du module → seedé "sent" pour éviter le doublon.
            contacte_le = (row.get("CONTACTE_LE") or "").strip()
            await db.prospects.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "company": (row.get("ENTREPRISE") or "").strip(),
                    "region": (row.get("REGION") or "").strip(),
                    "country": (row.get("PAYS") or "be").strip().lower(),
                    "status": "sent" if contacte_le else "pending",
                    "sent_at": contacte_le or None,
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


async def _signup_emails() -> set:
    """Emails des testeurs inscrits — pour ne pas relancer les convertis."""
    return {
        d["email"] for d in await db.tester_signups.find({}, {"email": 1}).to_list(2000)
    }


async def _quota_used_today() -> int:
    """Quota anti-spam : premiers envois + relances comptent ensemble."""
    today = _today_start_iso()
    first_sends = await db.prospects.count_documents({"sent_at": {"$gte": today}})
    relances = await db.prospects.count_documents({"relance_sent_at": {"$gte": today}})
    return first_sends + relances


async def _relances_dues() -> list[dict]:
    """Prospects contactés il y a ≥ J+5, jamais relancés, pas encore inscrits."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=RELANCE_DELAY_DAYS)
    ).isoformat()
    docs = await db.prospects.find(
        {"status": "sent", "relance_sent_at": None, "sent_at": {"$lte": cutoff}},
        {"_id": 0, "id": 1, "email": 1},
    ).to_list(500)
    signups = await _signup_emails()
    return [d for d in docs if d["email"] not in signups]


@router.get("/campaign/stats")
async def campaign_stats(user=Depends(require_admin)):
    pending = await db.prospects.count_documents({"status": "pending"})
    sent = await db.prospects.count_documents({"status": "sent"})
    failed = await db.prospects.count_documents({"status": "failed"})
    sending = await db.prospects.count_documents({"status": "sending"})
    relances_sent = await db.prospects.count_documents(
        {"relance_sent_at": {"$ne": None}}
    )
    # Croisement : prospects contactés devenus testeurs inscrits
    signup_emails = await _signup_emails()
    contacted = await db.prospects.find(
        {"status": "sent"}, {"email": 1}
    ).to_list(2000)
    converted = sum(1 for c in contacted if c["email"] in signup_emails)
    return {
        "pending": pending,
        "sent": sent,
        "failed": failed,
        "sending": sending,
        "sent_today": await _quota_used_today(),
        "daily_limit": DAILY_LIMIT,
        "converted": converted,
        "relance_due": len(await _relances_dues()),
        "relances_sent": relances_sent,
    }


@router.get("/campaign/prospects")
async def list_prospects(user=Depends(require_admin)):
    docs = (
        await db.prospects.find({}, {"_id": 0})
        .sort([("status", 1), ("sent_at", -1)])
        .to_list(500)
    )
    return {"prospects": docs}


async def _send_batch_task(items: list[dict]) -> None:
    """Tâche de fond : envoie les emails un par un, espacés (anti-spam).

    `items` : [{"id": ..., "kind": "new" | "relance"}].
    """
    for item in items:
        pid, kind = item["id"], item["kind"]
        doc = await db.prospects.find_one({"id": pid})
        if not doc:
            continue
        if kind == "new" and doc.get("status") != "sending":
            continue
        company = doc.get("company") or "votre entreprise"
        country = (doc.get("country") or "be").lower()
        subject = SUBJECTS.get(country, SUBJECTS["fr"])
        if kind == "relance":
            subject = "Re: " + subject
            body = RELANCE_TEMPLATE.format(company=company)
        else:
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
            ok = bool(res.get("delivered"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Envoi campagne échoué pour %s : %s", doc["email"], exc)
            ok = False
        now_iso = datetime.now(timezone.utc).isoformat()
        if kind == "relance":
            update = {"relance_sent_at": now_iso, "relance_failed": not ok}
        else:
            update = {"status": "sent" if ok else "failed", "sent_at": now_iso}
        await db.prospects.update_one({"id": pid}, {"$set": update})
        logger.info(
            "Campagne (%s) → %s : %s", kind, doc["email"], "sent" if ok else "failed"
        )
        await asyncio.sleep(PAUSE_BETWEEN_SENDS_S)


@router.post("/campaign/send-batch")
async def send_batch(background_tasks: BackgroundTasks, user=Depends(require_admin)):
    """Envoie le lot du jour : relances J+5 en priorité, puis nouveaux prospects.

    Quota global de 15 emails/jour (premiers envois + relances confondus).
    """
    remaining = DAILY_LIMIT - await _quota_used_today()
    if remaining <= 0:
        raise HTTPException(
            429,
            f"Limite quotidienne atteinte ({DAILY_LIMIT} emails/jour). Revenez demain !",
        )
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1) Relances J+5 prioritaires (leads encore tièdes)
    relances = (await _relances_dues())[:remaining]
    if relances:
        # Horodatage immédiat = verrou anti double-clic
        await db.prospects.update_many(
            {"id": {"$in": [d["id"] for d in relances]}},
            {"$set": {"relance_sent_at": now_iso}},
        )
    items = [{"id": d["id"], "kind": "relance"} for d in relances]

    # 2) Nouveaux prospects sur les créneaux restants
    slots = remaining - len(items)
    if slots > 0:
        batch = (
            await db.prospects.find({"status": "pending"}, {"_id": 0, "id": 1})
            .limit(slots)
            .to_list(slots)
        )
        ids = [b["id"] for b in batch]
        if ids:
            # On marque "sending" immédiatement pour éviter tout double-clic
            await db.prospects.update_many(
                {"id": {"$in": ids}}, {"$set": {"status": "sending"}}
            )
        items += [{"id": i, "kind": "new"} for i in ids]

    if not items:
        raise HTTPException(404, "Aucun prospect en attente ni relance due 🎉")
    background_tasks.add_task(_send_batch_task, items)
    n_rel = len(relances)
    msg = f"Envoi de {len(items)} emails lancé"
    if n_rel:
        msg += f" (dont {n_rel} relance{'s' if n_rel > 1 else ''} J+5)"
    msg += f" — ≈{len(items) * PAUSE_BETWEEN_SENDS_S}s. Actualisez pour suivre."
    return {"ok": True, "scheduled": len(items), "relances": n_rel, "message": msg}
