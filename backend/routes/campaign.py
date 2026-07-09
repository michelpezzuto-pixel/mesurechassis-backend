"""Module Campagne — prospection testeurs à 1 bouton.

L'admin importe des prospects (email + entreprise + région) puis clique sur
« Envoyer le lot du jour » : le backend envoie jusqu'à 15 emails personnalisés
par jour via Resend (limite anti-spam), avec mention STOP (RGPD) et suivi des
statuts. Conçu pour pouvoir basculer sur Brevo plus tard (mêmes données).

🆕 RGPD (juin 2026) — Désinscription automatique :
    - Chaque email contient un lien public « Se désinscrire en 1 clic »
      signé avec JWT (token tamper-proof, durée illimitée).
    - L'admin peut aussi désinscrire manuellement depuis le dashboard.
    - Le CRON d'envoi skippe tous les prospects avec `unsubscribed=True`.
"""

import asyncio
import csv
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    _BRUSSELS_TZ = ZoneInfo("Europe/Brussels")
except ImportError:  # pragma: no cover — fallback offset fixe (UTC+1)
    _BRUSSELS_TZ = timezone(timedelta(hours=1))

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from db import JWT_SECRET, db
from deps import require_platform_owner
from email_service import send_email

logger = logging.getLogger("mesurechassis.campaign")

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DAILY_LIMIT = 40
PAUSE_BETWEEN_SENDS_S = 3
RELANCE_DELAY_DAYS = 3  # 1ère relance J+3 si pas répondu
SECOND_RELANCE_DELAY_DAYS = 7  # 2e relance J+7 (dernière chance)

# 🚫 Domaines email GÉNÉRIQUES — Si un import contient l'un de ces mots dans
# le champ « company » (typiquement un scraper qui a pris le domaine à la
# place du vrai nom d'entreprise), on vide le champ pour éviter d'afficher
# des noms comme « Mr Gmail » / « Mr Free ».
_GENERIC_EMAIL_DOMAINS = {
    "gmail", "googlemail",
    "yahoo", "yahoo.fr", "yahoo.com",
    "hotmail", "hotmail.fr", "hotmail.com",
    "outlook", "outlook.fr", "outlook.com",
    "live", "live.fr", "live.com",
    "orange", "orange.fr",
    "free", "free.fr",
    "wanadoo", "wanadoo.fr",
    "sfr", "sfr.fr",
    "laposte", "laposte.net",
    "bbox", "bouygtel",
    "aol", "aol.fr", "aol.com",
    "icloud", "me.com", "mac.com",
    "protonmail", "proton.me",
    "voila", "voila.fr",
    "numericable", "neuf.fr",
    "skynet", "skynet.be",
    "telenet", "telenet.be",
    "belgacom", "belgacom.be", "proximus.be",
    "gmx", "gmx.fr", "gmx.com",
    "mail", "mail.com", "mail.ru",
}


def _clean_company(raw: str | None) -> str:
    """Retourne le nom d'entreprise nettoyé — vide si c'est un domaine email générique."""
    c = (raw or "").strip()
    if not c:
        return ""
    if c.lower() in _GENERIC_EMAIL_DOMAINS:
        return ""
    return c


def _is_weekend_brussels() -> bool:
    """True si on est samedi ou dimanche en heure belge (Europe/Brussels).

    Évite d'envoyer des mails de prospection le week-end :
      • mauvais taux d'ouverture pro
      • risque accru de classement en spam
      • impression négative ("il bosse même le dimanche")
    """
    local_now = datetime.now(_BRUSSELS_TZ)
    # weekday() : lundi=0 … dimanche=6 → samedi=5, dimanche=6
    return local_now.weekday() >= 5

# === SUJETS (testés pour CTR optimal en B2B menuisiers) ============
# Refonte juillet 2026 — Lancement App Store : angle "enfin disponible".
SUBJECTS = {
    "be": "🎉 MesureChâssis est enfin sur l'Apple Store",
    "fr": "🎉 MesureChâssis est enfin sur l'Apple Store",
    "lu": "🎉 MesureChâssis est enfin sur l'Apple Store",
}
SUBJECT_RELANCE_1 = "📱 Vous l'avez essayée ? (30 sec)"
SUBJECT_RELANCE_2 = "🎁 Dernière chance — test 100 % gratuit"

# Lien direct App Store (iOS) + version web pour Android / desktop
APP_STORE_URL = "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930"
APP_WEB_URL = "https://mesurechassis.com/telecharger.html"
# QR code pointant vers l'App Store (généré via api.qrserver.com, gratuit)
QR_IMG_URL = (
    "https://api.qrserver.com/v1/create-qr-code/"
    "?size=200x200"
    "&data=https%3A%2F%2Fapps.apple.com%2Ffr%2Fapp%2Fmesurech%25C3%25A2ssis%2Fid6776357930"
    "&color=121214&bgcolor=ffffff&qzone=1"
)

# {origin} : phrase d'accroche adaptée au pays du prospect (option B du client —
# les belges voient "application mobile belge", FR/LU un texte neutre).
ORIGIN_PHRASES = {
    "be": "une application mobile belge",
    "fr": "une application mobile conçue par un menuisier",
    "lu": "une application mobile conçue par un menuisier",
}

# ═════════════════════════════════════════════════════════════════════
# === MAIL #1 — Premier contact (COURT, ~80 mots, style Michel) ═════
# ═════════════════════════════════════════════════════════════════════
# Refonte juillet 2026 — Lancement App Store validé par Apple.
BODY_TEMPLATE = """Bonjour,

Je suis Michel, menuisier comme vous.

🎉 MesureChâssis est enfin disponible sur l'Apple Store — vous pouvez la télécharger et la tester **gratuitement** dès maintenant pour simplifier vos relevés de mesures sur chantier.

📲 Télécharger sur l'App Store :
👉 {app_store_url}

[QR_CODE_PLACEHOLDER]

Vous n'avez pas d'iPhone ? Version Android en route + version web dispo :
🌐 {app_web_url}

Si vous testez, dites-moi ce que vous en pensez — votre retour vaut de l'or.

Michel Pezzuto — Menuisier · Fondateur MesureChâssis
📧 info@mesurechassis.com

—
Vous recevez cet email car votre entreprise est active dans la menuiserie. Pour ne plus être contacté, répondez simplement STOP."""

# ═════════════════════════════════════════════════════════════════════
# === MAIL #2 — Relance J+3 (rappel test gratuit App Store) ═════════
# ═════════════════════════════════════════════════════════════════════
RELANCE_TEMPLATE = """Bonjour,

Je vous ai écrit il y a quelques jours à propos de MesureChâssis, notre app de prise de mesures pensée pour les menuisiers.

Rapide rappel : elle est disponible **gratuitement** sur l'Apple Store depuis peu.

En 30 secondes chrono :
📲 Scannez le QR code ou cliquez : {app_store_url}
📸 Photographiez un cahier des charges → l'IA liste toutes les ouvertures
✅ Vous validez les cotes sur place. Fini la double saisie.

[QR_CODE_PLACEHOLDER]

Test gratuit, pas de carte bancaire.

Si vous voulez une démo visio (10 min), répondez à ce mail — je m'adapte à votre planning.

Bien cordialement,
Michel Pezzuto — MesureChâssis
📧 info@mesurechassis.com

—
Pour ne plus être contacté, répondez simplement STOP."""

# ═════════════════════════════════════════════════════════════════════
# === MAIL #3 — Relance J+7 (dernière chance, angle usage concret) ═══
# ═════════════════════════════════════════════════════════════════════
RELANCE_2_TEMPLATE = """Bonjour,

Je vous écris une dernière fois (promis 🙏).

Imaginez ça :
📋 Votre client vous envoie un cahier des charges avec 12 fenêtres.
📸 Vous le prenez en photo dans MesureChâssis → en 10 secondes, les 12 ouvertures sont créées avec leurs dimensions.
🔍 Sur place, vous validez juste les cotes réelles. Voilà.

C'est ce que MesureChâssis fait **depuis votre iPhone** — et c'est gratuit à tester.

📲 App Store : {app_store_url}

[QR_CODE_PLACEHOLDER]

Un « oui » ou un « non », ça me va — je ne prends pas mal.

Bonne continuation,
Michel Pezzuto — Fondateur MesureChâssis
📧 info@mesurechassis.com

—
Pour ne plus être contacté, répondez simplement STOP."""

RECAP_RECIPIENT = "info@mesurechassis.com"
RECAP_WEEKDAY = 0  # lundi
RECAP_HOUR_UTC = 7  # ≈ 9h heure belge (été)


# ════════════════════════════════════════════════════════════════════
# 🆕 RGPD — Système de désinscription publique (1 clic, sans login)
# ════════════════════════════════════════════════════════════════════
#
# Chaque email de campagne contient un lien unique signé JWT :
#   https://www.mesurechassis.com/api/public/unsubscribe?token=...
#
# Le token contient {prospect_id, email} et est signé avec JWT_SECRET.
# Le lien est valable indéfiniment (pas d'expiration : on veut que le
# prospect puisse cliquer même 6 mois après).
#
# Quand le prospect clique :
#   1. Backend vérifie la signature du token
#   2. Marque le prospect comme `unsubscribed=True`
#   3. Affiche une page HTML de confirmation
#   4. Le CRON suivant skippe automatiquement ce prospect.
# ════════════════════════════════════════════════════════════════════

# URL publique du backend (utilisée pour générer le lien unsubscribe)
# En prod = Railway, en dev local = relatif. Configurable via env.
import os as _os
PUBLIC_BACKEND_URL = _os.environ.get(
    "PUBLIC_BACKEND_URL",
    "https://capable-gratitude-production-db51.up.railway.app",
).rstrip("/")


def _make_unsubscribe_token(prospect_id: str, email: str) -> str:
    """Génère un token JWT signé pour désinscription 1-clic (sans expiration)."""
    payload = {
        "pid": prospect_id,
        "email": email.lower().strip(),
        "purpose": "unsubscribe_campaign",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_unsubscribe_token(token: str) -> dict:
    """Décode et vérifie un token JWT d'unsubscribe. Raise HTTPException si invalide."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError as e:
        raise HTTPException(400, f"Lien invalide ou expiré : {e}")
    if payload.get("purpose") != "unsubscribe_campaign":
        raise HTTPException(400, "Lien invalide (mauvais usage)")
    if not payload.get("pid") or not payload.get("email"):
        raise HTTPException(400, "Lien incomplet")
    return payload


def _build_unsubscribe_url(prospect_id: str, email: str) -> str:
    """URL complète d'unsubscribe pour insertion dans un email de campagne."""
    token = _make_unsubscribe_token(prospect_id, email)
    return f"{PUBLIC_BACKEND_URL}/api/public/unsubscribe?token={quote(token)}"


def _build_unsubscribe_footer_html(prospect_id: str, email: str) -> str:
    """Bloc HTML à insérer en bas d'email (CTA visible + style discret)."""
    url = _build_unsubscribe_url(prospect_id, email)
    return (
        f'<div style="margin-top:30px;padding-top:14px;border-top:1px solid #e5e7eb;'
        f'font-size:11px;color:#9ca3af;text-align:center;line-height:1.6">'
        f'MesureChâssis — Outil pro pour menuisiers · '
        f'<a href="{url}" style="color:#9ca3af;text-decoration:underline">'
        f'Se désinscrire en 1 clic'
        f'</a>'
        f'</div>'
    )


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
async def recap_now(user=Depends(require_platform_owner)):
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
                    "company": _clean_company(row.get("ENTREPRISE")),
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
async def import_prospects(payload: dict, user=Depends(require_platform_owner)):
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
                "company": _clean_company(it.get("company")),
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
    """Prospects à relancer J+3 — `status=sent`, pas encore relancés, déjà patientés."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=RELANCE_DELAY_DAYS)
    ).isoformat()
    docs = await db.prospects.find(
        {
            "status": "sent",
            "relance_sent_at": None,
            "sent_at": {"$lte": cutoff},
            # 🆕 RGPD — Skip les désinscrits
            "$or": [
                {"unsubscribed": {"$exists": False}},
                {"unsubscribed": False},
            ],
        },
        {"_id": 0, "id": 1, "email": 1},
    ).to_list(500)
    signups = await _signup_emails()
    return [d for d in docs if d["email"] not in signups]


async def _second_relances_dues() -> list[dict]:
    """Prospects à relancer J+7 (2e relance, dernière) — déjà relancés une fois."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=SECOND_RELANCE_DELAY_DAYS)
    ).isoformat()
    docs = await db.prospects.find(
        {
            "status": "sent",
            "relance_sent_at": {"$ne": None, "$lte": cutoff},
            "relance_2_sent_at": None,
            # 🆕 RGPD — Skip les désinscrits
            "$or": [
                {"unsubscribed": {"$exists": False}},
                {"unsubscribed": False},
            ],
        },
        {"_id": 0, "id": 1, "email": 1},
    ).to_list(500)
    signups = await _signup_emails()
    return [d for d in docs if d["email"] not in signups]


@router.get("/campaign/stats")
async def campaign_stats(user=Depends(require_platform_owner)):
    pending = await db.prospects.count_documents({"status": "pending"})
    sent = await db.prospects.count_documents({"status": "sent"})
    failed = await db.prospects.count_documents({"status": "failed"})
    sending = await db.prospects.count_documents({"status": "sending"})
    relances_sent = await db.prospects.count_documents(
        {"relance_sent_at": {"$ne": None}}
    )
    unsubscribed = await db.prospects.count_documents({"unsubscribed": True})
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
        "unsubscribed": unsubscribed,
    }


@router.get("/campaign/prospects")
async def list_prospects(user=Depends(require_platform_owner)):
    docs = (
        await db.prospects.find({}, {"_id": 0})
        .sort([("status", 1), ("sent_at", -1)])
        .to_list(500)
    )
    return {"prospects": docs}


async def _send_batch_task(items: list[dict]) -> None:
    """Tâche de fond : envoie les emails un par un, espacés (anti-spam).

    `items` : [{"id": ..., "kind": "new" | "relance" | "relance2"}].
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
        if kind == "relance":
            subject = SUBJECT_RELANCE_1
            body = RELANCE_TEMPLATE.format(
                company=company,
                app_web_url=APP_WEB_URL,
                app_store_url=APP_STORE_URL,
            )
        elif kind == "relance2":
            subject = SUBJECT_RELANCE_2
            body = RELANCE_2_TEMPLATE.format(
                company=company,
                app_web_url=APP_WEB_URL,
                app_store_url=APP_STORE_URL,
            )
        else:
            subject = SUBJECTS.get(country, SUBJECTS["fr"])
            body = BODY_TEMPLATE.format(
                company=company,
                origin=ORIGIN_PHRASES.get(country, ORIGIN_PHRASES["fr"]),
                app_web_url=APP_WEB_URL,
                app_store_url=APP_STORE_URL,
            )
        # Insertion du QR code (image HTML inline) à la place du placeholder
        # send_email rend automatiquement le body en HTML — le tag <img> sera
        # préservé. On marque clairement la ligne pour les clients texte aussi.
        # QR pointe désormais vers l'App Store (lien direct pour iPhone/iPad).
        qr_html_block = (
            f'<div style="text-align:center;margin:20px 0">'
            f'<img src="{QR_IMG_URL}" alt="QR code App Store MesureChassis" '
            f'width="200" height="200" '
            f'style="border:1px solid #ddd;border-radius:8px;padding:8px;background:#fff" />'
            f'<br><span style="font-size:12px;color:#666">'
            f'(scannez avec l\'appareil photo de votre iPhone pour ouvrir l\'App Store)</span></div>'
        )
        body = body.replace("[QR_CODE_PLACEHOLDER]", qr_html_block)

        # 🆕 RGPD — Ajout du lien public unsubscribe en bas d'email
        unsubscribe_footer = _build_unsubscribe_footer_html(pid, doc["email"])
        body = body + "\n\n" + unsubscribe_footer
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
        elif kind == "relance2":
            update = {"relance_2_sent_at": now_iso, "relance_2_failed": not ok}
        else:
            update = {"status": "sent" if ok else "failed", "sent_at": now_iso}
        await db.prospects.update_one({"id": pid}, {"$set": update})
        logger.info(
            "Campagne (%s) → %s : %s", kind, doc["email"], "sent" if ok else "failed"
        )
        await asyncio.sleep(PAUSE_BETWEEN_SENDS_S)


@router.post("/campaign/send-batch")
async def send_batch(
    background_tasks: BackgroundTasks,
    force_weekend: bool = False,
    user=Depends(require_platform_owner),
):
    """Envoie le lot du jour, dans cet ordre de priorité :
      1. Relances J+7 (dernière chance, leads les plus tièdes)
      2. Relances J+3 (rappel soft)
      3. Nouveaux prospects (premier contact)

    Quota global : 40 emails/jour (toutes catégories confondues).
    Le mix relances / nouveaux est automatique : le système consomme
    d'abord les relances dues, puis remplit les slots restants avec des
    premiers contacts — la campagne ne stagne jamais.

    🗓️ FILTRE WEEK-END (Europe/Brussels) :
       Par défaut, l'envoi est BLOQUÉ le samedi et le dimanche. Les emails
       B2B ont un meilleur taux d'ouverture en semaine et envoyer le
       week-end donne l'impression d'être désorganisé. Pour passer outre
       (cas exceptionnel : campagne urgente), passer `?force_weekend=true`.
    """
    if _is_weekend_brussels() and not force_weekend:
        raise HTTPException(
            423,  # Locked
            "Envoi désactivé le week-end (samedi/dimanche, heure belge). "
            "Le quota d'aujourd'hui sera disponible lundi matin. "
            "Pour forcer un envoi exceptionnel, ajoutez ?force_weekend=true.",
        )
    remaining = DAILY_LIMIT - await _quota_used_today()
    if remaining <= 0:
        raise HTTPException(
            429,
            f"Limite quotidienne atteinte ({DAILY_LIMIT} emails/jour). Revenez demain !",
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    items: list[dict] = []

    # 1) Relances J+7 (priorité max — dernière chance)
    second_relances = (await _second_relances_dues())[:remaining]
    if second_relances:
        await db.prospects.update_many(
            {"id": {"$in": [d["id"] for d in second_relances]}},
            {"$set": {"relance_2_sent_at": now_iso}},
        )
        items += [{"id": d["id"], "kind": "relance2"} for d in second_relances]

    # 2) Relances J+3
    slots = remaining - len(items)
    if slots > 0:
        relances = (await _relances_dues())[:slots]
        if relances:
            await db.prospects.update_many(
                {"id": {"$in": [d["id"] for d in relances]}},
                {"$set": {"relance_sent_at": now_iso}},
            )
            items += [{"id": d["id"], "kind": "relance"} for d in relances]

    # 3) Nouveaux prospects sur les créneaux restants (excluant désinscrits)
    slots = remaining - len(items)
    if slots > 0:
        batch = (
            await db.prospects.find(
                {
                    "status": "pending",
                    "$or": [
                        {"unsubscribed": {"$exists": False}},
                        {"unsubscribed": False},
                    ],
                },
                {"_id": 0, "id": 1},
            )
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
    n_rel = sum(1 for x in items if x["kind"] == "relance")
    n_rel2 = sum(1 for x in items if x["kind"] == "relance2")
    n_new = sum(1 for x in items if x["kind"] == "new")
    parts = []
    if n_new:
        parts.append(f"{n_new} nouveau{'x' if n_new > 1 else ''}")
    if n_rel:
        parts.append(f"{n_rel} relance{'s' if n_rel > 1 else ''} J+3")
    if n_rel2:
        parts.append(f"{n_rel2} relance{'s' if n_rel2 > 1 else ''} J+7")
    msg = f"Envoi de {len(items)} emails lancé ({' · '.join(parts)})"
    msg += f" — ≈{len(items) * PAUSE_BETWEEN_SENDS_S}s. Actualisez pour suivre."
    return {
        "ok": True,
        "scheduled": len(items),
        "new": n_new,
        "relances": n_rel,
        "relances_2": n_rel2,
        "message": msg,
    }


# ════════════════════════════════════════════════════════════════════
# === RESET / TABULA RASA — pour relancer une campagne depuis zéro ═══
# ════════════════════════════════════════════════════════════════════
@router.post("/campaign/prospects/reset")
async def reset_prospects(payload: dict, user=Depends(require_platform_owner)):
    """Remet tous les prospects (ou un sous-ensemble) en statut "pending".

    Utilisation : Michel veut redémarrer une campagne depuis zéro après
    refonte des templates → on remet tout en pending et le bouton
    « Envoyer le lot du jour » repart de zéro avec les nouveaux mails.

    Body : { "scope": "all" | "sent" }
      - "all"  : remet TOUT en pending (y compris failed)
      - "sent" : ne remet que ceux qui ont déjà reçu un mail (utile pour
                 ré-envoyer un mail #2 modernisé à tous les anciens contactés)
    """
    scope = (payload or {}).get("scope", "sent")
    if scope == "all":
        flt = {}
    elif scope == "sent":
        flt = {"status": {"$in": ["sent", "failed"]}}
    else:
        raise HTTPException(400, "scope invalide (all | sent)")
    res = await db.prospects.update_many(
        flt,
        {
            "$set": {
                "status": "pending",
                "sent_at": None,
                "relance_sent_at": None,
                "relance_2_sent_at": None,
                "relance_failed": False,
                "relance_2_failed": False,
            }
        },
    )
    logger.info(
        "Campagne RESET (scope=%s) — %s prospects remis en pending",
        scope, res.modified_count,
    )
    return {
        "ok": True,
        "scope": scope,
        "reset": res.modified_count,
        "message": f"{res.modified_count} prospect(s) remis en file d'envoi.",
    }



# ════════════════════════════════════════════════════════════════════
# 🆕 RGPD — Routes désinscription (admin manuelle + public 1-clic)
# ════════════════════════════════════════════════════════════════════

@router.post("/campaign/prospects/{prospect_id}/unsubscribe")
async def admin_unsubscribe_prospect(
    prospect_id: str,
    user=Depends(require_platform_owner),
):
    """🚫 Désinscription manuelle d'un prospect par l'admin.

    Utilisé quand l'admin reçoit une réponse « STOP » par email et doit
    désinscrire manuellement. Idempotent : peut être appelé plusieurs fois.
    """
    doc = await db.prospects.find_one({"id": prospect_id})
    if not doc:
        raise HTTPException(404, "Prospect introuvable")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.prospects.update_one(
        {"id": prospect_id},
        {
            "$set": {
                "unsubscribed": True,
                "unsubscribed_at": now_iso,
                "unsubscribed_via": "admin_manual",
            }
        },
    )
    logger.info(
        "🚫 Prospect désinscrit (admin manuel) : %s (%s)",
        doc.get("email"), prospect_id,
    )
    return {
        "ok": True,
        "prospect_id": prospect_id,
        "email": doc.get("email"),
        "unsubscribed_at": now_iso,
    }


@router.post("/campaign/prospects/{prospect_id}/resubscribe")
async def admin_resubscribe_prospect(
    prospect_id: str,
    user=Depends(require_platform_owner),
):
    """🔄 Réinscription manuelle (cas exceptionnel : erreur de manip).

    À utiliser avec PRUDENCE et seulement avec accord exprès du prospect.
    """
    doc = await db.prospects.find_one({"id": prospect_id})
    if not doc:
        raise HTTPException(404, "Prospect introuvable")
    await db.prospects.update_one(
        {"id": prospect_id},
        {
            "$set": {"unsubscribed": False},
            "$unset": {"unsubscribed_at": "", "unsubscribed_via": ""},
        },
    )
    logger.info("🔄 Prospect ré-inscrit : %s", doc.get("email"))
    return {"ok": True, "prospect_id": prospect_id, "email": doc.get("email")}


# ────────────────────────────────────────────────────────────────────
# Route PUBLIQUE — Pas de require_admin. Accessible via lien JWT signé.
# ────────────────────────────────────────────────────────────────────
public_router = APIRouter()


@public_router.get("/public/unsubscribe", response_class=HTMLResponse)
async def public_unsubscribe_page(token: str = Query(...)):
    """🌐 Page HTML publique de confirmation de désinscription.

    1. Décode le token (vérifie la signature JWT)
    2. Marque le prospect comme `unsubscribed=True`
    3. Affiche une confirmation visuelle (sans JavaScript, pour les
       webmails qui désactivent le JS)
    """
    payload = _decode_unsubscribe_token(token)
    pid = payload["pid"]
    email = payload["email"]

    doc = await db.prospects.find_one({"id": pid})
    # On accepte même si le prospect n'existe plus en DB (ex: nettoyage),
    # pour rassurer l'utilisateur que sa demande est prise en compte.
    if doc:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.prospects.update_one(
            {"id": pid},
            {
                "$set": {
                    "unsubscribed": True,
                    "unsubscribed_at": now_iso,
                    "unsubscribed_via": "public_link",
                }
            },
        )
        logger.info(
            "🚫 Désinscription publique 1-clic : %s (%s)",
            email, pid,
        )

    # Page HTML de confirmation propre, mobile-friendly, sans JS
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Désinscription confirmée — MesureChâssis</title>
<style>
  body {{ margin:0; padding:24px; font-family:-apple-system,Segoe UI,Roboto,sans-serif;
         background:#0C0C0E; color:#fff; min-height:100vh;
         display:flex; align-items:center; justify-content:center; }}
  .card {{ max-width:480px; width:100%; background:#18181B; border-radius:16px;
          padding:32px 24px; text-align:center; border:1px solid #3F3F46; }}
  .icon {{ width:72px; height:72px; border-radius:36px; background:#32D74B22;
          display:flex; align-items:center; justify-content:center;
          margin:0 auto 16px; font-size:36px; }}
  h1 {{ font-size:22px; margin:0 0 8px; color:#fff; }}
  p {{ font-size:15px; line-height:1.5; color:#A1A1AA; margin:8px 0; }}
  .email {{ background:#27272A; padding:8px 12px; border-radius:8px;
           display:inline-block; font-family:monospace; color:#fff;
           margin:8px 0; }}
  .footer {{ font-size:12px; color:#52525B; margin-top:24px;
            padding-top:16px; border-top:1px solid #27272A; }}
  .footer a {{ color:#FF5A00; text-decoration:none; }}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h1>Vous êtes désinscrit·e</h1>
    <p>L'adresse suivante ne recevra plus aucun email de notre part&nbsp;:</p>
    <div class="email">{email}</div>
    <p>Aucune action supplémentaire n'est requise de votre part.</p>
    <p>Nous sommes désolés de vous voir partir. Si c'est une erreur,
       écrivez-nous à
       <a href="mailto:info@mesurechassis.com" style="color:#FF5A00">
       info@mesurechassis.com</a>.</p>
    <div class="footer">
      MesureChâssis — Outil pro pour menuisiers professionnels<br>
      <a href="https://www.mesurechassis.com">www.mesurechassis.com</a>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


# Petit alias POST → même comportement (certains clients mail "click-tracking"
# transforment les GET en POST). On accepte les deux pour robustesse.
@public_router.post("/public/unsubscribe", response_class=HTMLResponse)
async def public_unsubscribe_page_post(token: str = Query(...)):
    return await public_unsubscribe_page(token)
