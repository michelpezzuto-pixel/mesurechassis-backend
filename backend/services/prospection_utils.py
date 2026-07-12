"""🛠️  Utilitaires centralisés pour toutes les campagnes de prospection.

Ce module offre une API unique pour :
    • Upserter un prospect dans la collection ``prospects`` (crée un id si absent)
    • Construire le footer HTML « Se désinscrire en 1 clic » avec token JWT signé
    • Vérifier si le prospect est déjà désinscrit / a déjà reçu ce message
    • Envoyer un email via Resend en respectant la fenêtre horaire (16h30)
    • Logger chaque tentative dans ``prospection_logs``

Il est utilisé par :
    - ``send_prospection_b2b.py``       (stations-service belges)
    - ``send_prospection_sponsors.py``  (fabricants menuiseries)
    - ``send_launch_appstore.py``       (annonce app dispo App Store — nouveau)
    - ``routes/campaign.py``            (via une adaptation directe)

⚠️  RGPD : Chaque email envoyé DOIT contenir le footer HTML retourné par
    ``build_unsubscribe_footer()``. Sans ce bouton, l'envoi est refusé
    (contrôle côté ``send_prospect_email``).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, time, timezone
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
import jwt

from db import JWT_SECRET, db

logger = logging.getLogger("mesurechassis.prospection")

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("MAIL_FROM", "MesureChâssis <info@mesurechassis.com>")
REPLY_TO = "info@mesurechassis.com"
# JWT — même clé que routes/campaign.py pour interopérabilité du token unsubscribe
JWT_ALG = "HS256"
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "https://www.mesurechassis.com")

# Fenêtre d'envoi préférée par Michel (retours ~2x supérieurs à 16h30).
# On accepte une fenêtre large 15h30 → 17h30 heure de Bruxelles pour laisser
# de la marge à l'exécution.
_SEND_TZ = ZoneInfo("Europe/Brussels")
_SEND_WINDOW_START = time(hour=15, minute=30)
_SEND_WINDOW_END = time(hour=17, minute=30)

# Réseaux de fabricants qui n'ont PAS de bouton unsubscribe individuel
# (adresses génériques `info@`, `service@`) — pour ces destinataires, on
# affiche quand même le bouton pour respecter le RGPD, mais on note qu'un
# `mailto:` de contact est présent en fallback.


# ═══════════════════════════════════════════════════════════════════════
# UPSERT PROSPECT
# ═══════════════════════════════════════════════════════════════════════
async def upsert_prospect(
    email: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    source: str = "generic",
) -> dict:
    """Insère ou récupère un prospect. Retourne le doc complet (avec ``id``).

    ``source`` est libre : ``"b2b_station"``, ``"sponsor"``, ``"launch_appstore"``,
    ``"testeur_form"``…  Permet de tracer d'où vient chaque contact.
    """
    email_norm = email.strip().lower()
    existing = await db.prospects.find_one({"email": email_norm})
    if existing:
        # Rafraîchit les métadonnées si on a plus d'infos qu'avant.
        updates: dict[str, Any] = {}
        if first_name and not existing.get("first_name"):
            updates["first_name"] = first_name
        if last_name and not existing.get("last_name"):
            updates["last_name"] = last_name
        if company and not existing.get("company"):
            updates["company"] = company
        if updates:
            await db.prospects.update_one({"id": existing["id"]}, {"$set": updates})
            existing.update(updates)
        return existing

    doc = {
        "id": str(uuid.uuid4()),
        "email": email_norm,
        "first_name": (first_name or "").strip() or None,
        "last_name": (last_name or "").strip() or None,
        "company": (company or "").strip() or None,
        "source": source,
        "unsubscribed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.prospects.insert_one(doc)
    return doc


# ═══════════════════════════════════════════════════════════════════════
# TOKEN + FOOTER UNSUBSCRIBE
# ═══════════════════════════════════════════════════════════════════════
def _make_unsubscribe_token(prospect_id: str, email: str) -> str:
    """JWT signé (HS256) — sans expiration, révocable côté DB si besoin."""
    payload = {
        "pid": prospect_id,
        "email": email,
        "purpose": "unsubscribe_campaign",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def build_unsubscribe_url(prospect_id: str, email: str) -> str:
    """URL complète cliquable — même endpoint que ``routes/campaign.py``."""
    token = _make_unsubscribe_token(prospect_id, email)
    return f"{PUBLIC_BACKEND_URL}/api/public/unsubscribe?token={quote(token)}"


def build_unsubscribe_footer(prospect_id: str, email: str) -> str:
    """Bloc HTML propre à insérer OBLIGATOIREMENT en bas de chaque email.

    Rend un CTA visible mais discret (respect du branding + accessibilité).
    """
    url = build_unsubscribe_url(prospect_id, email)
    return (
        '<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;'
        'font-size:11px;color:#9ca3af;text-align:center;line-height:1.7;'
        'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif">'
        'MesureChâssis SRL · Namur, Belgique · Prospection B2B légitime '
        '(RGPD Art. 21).<br>'
        f'<a href="{url}" style="color:#FF5A00;text-decoration:underline;'
        'font-weight:600;padding:6px 0;display:inline-block">'
        '🚫 Ne plus recevoir d\'emails de notre part (1 clic)'
        '</a>'
        '</div>'
    )


# ═══════════════════════════════════════════════════════════════════════
# FENÊTRE HORAIRE (16h30 Michel)
# ═══════════════════════════════════════════════════════════════════════
def is_send_window_open(*, now: datetime | None = None) -> tuple[bool, str]:
    """Retourne (ouvert, motif). Fenêtre : lun-ven 15h30–17h30 Europe/Brussels.

    Le week-end, la fenêtre est fermée (bonnes pratiques B2B).
    """
    now = (now or datetime.now(_SEND_TZ)).astimezone(_SEND_TZ)
    if now.weekday() >= 5:  # sam/dim
        return False, f"Weekend ({now.strftime('%A')}) — envois désactivés"
    t = now.time()
    if t < _SEND_WINDOW_START:
        return False, (
            f"Trop tôt (il est {t.strftime('%H:%M')} · fenêtre 15h30–17h30 "
            "Bruxelles)"
        )
    if t > _SEND_WINDOW_END:
        return False, (
            f"Trop tard (il est {t.strftime('%H:%M')} · fenêtre 15h30–17h30 "
            "Bruxelles). Prévois le batch pour demain."
        )
    return True, f"OK — dans la fenêtre ({t.strftime('%H:%M')} Bruxelles)"


# ═══════════════════════════════════════════════════════════════════════
# ENVOI EMAIL VIA RESEND
# ═══════════════════════════════════════════════════════════════════════
class ProspectionError(Exception):
    """Erreur métier au niveau de l'envoi (skip, refus, quota)."""


async def _has_already_received(prospect_id: str, campaign_slug: str) -> bool:
    """True si le prospect a déjà été touché sur cette campagne."""
    doc = await db.prospection_logs.find_one({
        "prospect_id": prospect_id,
        "campaign": campaign_slug,
        "status": "delivered",
    })
    return doc is not None


async def send_prospect_email(
    prospect: dict,
    *,
    subject: str,
    body_html: str,
    campaign_slug: str,
    dry_run: bool = False,
    force_send_outside_window: bool = False,
) -> dict:
    """Envoie un email à un prospect, tout en respectant les garde-fous RGPD.

    Retourne un dict de status :  {"status": "sent|skipped|error", "reason": ..., ...}

    Contrôles automatiques (dans l'ordre) :
        1. Prospect a-t-il `unsubscribed=True` ? → skip
        2. Prospect a-t-il déjà reçu ``campaign_slug`` ? → skip (dedup)
        3. Fenêtre horaire (16h30) ouverte ? → skip (sauf ``force_send_outside_window``)
        4. Le body contient-il bien le footer d'unsubscribe ? → refus
        5. Envoi via Resend HTTP API
        6. Log en base (``prospection_logs``)

    ``dry_run=True`` écrit l'email dans ``/tmp/prospection_preview/`` au lieu
    de l'envoyer via Resend. Idéal pour prévisualisation avant validation.
    """
    email = prospect["email"]
    pid = prospect["id"]

    # 1. Désabonné ?
    fresh = await db.prospects.find_one({"id": pid})
    if fresh and fresh.get("unsubscribed"):
        return {"status": "skipped", "reason": "unsubscribed", "email": email}

    # 2. Déjà touché sur cette campagne ?
    if await _has_already_received(pid, campaign_slug):
        return {"status": "skipped", "reason": "already_delivered", "email": email}

    # 3. Fenêtre horaire
    if not force_send_outside_window and not dry_run:
        open_, motif = is_send_window_open()
        if not open_:
            return {"status": "skipped", "reason": "outside_window", "detail": motif}

    # 4. Footer présent ?
    if 'href="' + PUBLIC_BACKEND_URL + '/api/public/unsubscribe' not in body_html:
        raise ProspectionError(
            f"Footer d'unsubscribe absent du body pour {email} — refus RGPD."
        )

    # 5. Dry-run → écrit sur disque, sort avant Resend
    if dry_run:
        out_dir = "/tmp/prospection_preview"
        os.makedirs(out_dir, exist_ok=True)
        # Sanitize filename
        safe = hashlib.sha1(email.encode()).hexdigest()[:12]
        path = f"{out_dir}/{campaign_slug}__{safe}.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"<!--\n"
                f"TO: {email}\n"
                f"SUBJECT: {subject}\n"
                f"CAMPAIGN: {campaign_slug}\n"
                f"PROSPECT_ID: {pid}\n"
                f"-->\n" + body_html
            )
        return {"status": "dry_run", "path": path, "email": email}

    # 6. Envoi via Resend
    if not RESEND_API_KEY:
        raise ProspectionError("RESEND_API_KEY absent de l'env")

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_EMAIL,
                "to": [email],
                "reply_to": REPLY_TO,
                "subject": subject,
                "html": body_html,
                "tags": [{"name": "campaign", "value": campaign_slug}],
            },
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    if r.status_code >= 400:
        await db.prospection_logs.insert_one({
            "id": str(uuid.uuid4()),
            "prospect_id": pid,
            "email": email,
            "campaign": campaign_slug,
            "subject": subject,
            "status": "error",
            "http_code": r.status_code,
            "error": r.text[:500],
            "sent_at": now_iso,
        })
        return {"status": "error", "email": email, "http_code": r.status_code,
                "detail": r.text[:200]}

    resend_data = r.json()
    await db.prospection_logs.insert_one({
        "id": str(uuid.uuid4()),
        "prospect_id": pid,
        "email": email,
        "campaign": campaign_slug,
        "subject": subject,
        "status": "delivered",
        "resend_id": resend_data.get("id"),
        "sent_at": now_iso,
    })
    return {"status": "sent", "email": email, "resend_id": resend_data.get("id")}


# ═══════════════════════════════════════════════════════════════════════
# UTILITAIRES DE REPORTING
# ═══════════════════════════════════════════════════════════════════════
async def campaign_stats(campaign_slug: str) -> dict:
    """Compte les envois par statut sur une campagne."""
    stats: dict[str, int] = {}
    cursor = db.prospection_logs.aggregate([
        {"$match": {"campaign": campaign_slug}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ])
    async for row in cursor:
        stats[row["_id"]] = row["n"]
    return stats


async def list_never_contacted(campaign_slug: str) -> list[dict]:
    """Liste les prospects jamais touchés par ``campaign_slug`` (utile pour relance)."""
    already = set()
    async for log in db.prospection_logs.find(
        {"campaign": campaign_slug, "status": "delivered"},
        {"prospect_id": 1, "_id": 0},
    ):
        already.add(log["prospect_id"])

    result = []
    async for p in db.prospects.find({
        "unsubscribed": {"$ne": True},
    }, {"_id": 0, "id": 1, "email": 1, "first_name": 1, "company": 1}):
        if p["id"] not in already:
            result.append(p)
    return result
