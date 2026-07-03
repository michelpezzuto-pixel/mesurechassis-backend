"""
📊 Webhook Resend — reçoit les événements de délivrance/ouverture/clic/bounce.

Configuration côté Resend Dashboard :
  1. Domains → mesurechassis.com → Configuration → activer :
      • Open tracking
      • Click tracking
  2. Webhooks → Add endpoint :
      URL: https://mesurechassis.com/api/webhooks/resend
      Events: email.delivered, email.opened, email.clicked, email.bounced,
              email.complained, email.delivery_delayed

Chaque prospect en DB (collection `prospects`) reçoit des timestamps :
  - delivered_at
  - opened_at (premier open)
  - open_count (nombre d'opens)
  - clicked_at (premier click)
  - click_count
  - bounced_at
  - bounce_reason
  - complained_at (spam complaint)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from db import db

logger = logging.getLogger("mesurechassis.webhook.resend")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_prospect_by_email(email: str, updates: dict[str, Any]) -> bool:
    """Met à jour un prospect via son email. Retourne True si trouvé."""
    if not email:
        return False
    result = await db.prospects.update_one(
        {"email": email.lower().strip()},
        {"$set": updates, "$inc": updates.pop("__inc__", {})} if updates.get("__inc__") else {"$set": updates},
    )
    return result.matched_count > 0


@router.post("/resend")
async def resend_webhook(
    request: Request,
    svix_id: str | None = Header(None, alias="svix-id"),
    svix_timestamp: str | None = Header(None, alias="svix-timestamp"),
    svix_signature: str | None = Header(None, alias="svix-signature"),
) -> dict:
    """Endpoint appelé par Resend à chaque événement email.

    Payload Resend v1 :
        {
          "type": "email.opened",
          "created_at": "2026-07-02T12:34:56Z",
          "data": {
            "email_id": "1c295716-...",
            "to": ["prospect@example.com"],
            "from": "MesureChâssis <info@mesurechassis.com>",
            "subject": "Question entre menuisiers"
          }
        }

    TODO : vérification signature Svix (webhook secret Resend) — pas
    critique en beta, mais à durcir avant prod si on utilise ces données
    pour un dashboard analytics.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    event_type = payload.get("type", "")
    data = payload.get("data", {})
    to_list = data.get("to") or []
    email = to_list[0] if to_list else data.get("email", "")

    logger.info("📊 Resend webhook: %s → %s", event_type, email)

    if not email:
        return {"ok": True, "skipped": "no email"}

    now = _now_iso()
    email_lc = email.lower().strip()

    if event_type == "email.delivered":
        await db.prospects.update_one(
            {"email": email_lc},
            {"$set": {"delivered_at": now}},
        )
    elif event_type == "email.opened":
        await db.prospects.update_one(
            {"email": email_lc},
            {
                "$set": {"last_opened_at": now},
                "$setOnInsert": {"first_opened_at": now},
                "$inc": {"open_count": 1},
            },
        )
        # Premier open : le setOnInsert ne marche que si upsert.
        # On force la première ouverture séparément.
        await db.prospects.update_one(
            {"email": email_lc, "first_opened_at": {"$exists": False}},
            {"$set": {"first_opened_at": now}},
        )
    elif event_type == "email.clicked":
        clicked_url = data.get("click", {}).get("link", "") or data.get("link", "")
        await db.prospects.update_one(
            {"email": email_lc},
            {
                "$set": {
                    "last_clicked_at": now,
                    "last_clicked_url": clicked_url,
                },
                "$inc": {"click_count": 1},
            },
        )
        await db.prospects.update_one(
            {"email": email_lc, "first_clicked_at": {"$exists": False}},
            {"$set": {"first_clicked_at": now}},
        )
    elif event_type == "email.bounced":
        reason = data.get("bounce", {}).get("message", "") or data.get("reason", "")
        await db.prospects.update_one(
            {"email": email_lc},
            {"$set": {
                "bounced_at": now,
                "bounce_reason": reason[:500],
                "status": "failed",  # marque comme échec définitif
            }},
        )
    elif event_type == "email.complained":
        await db.prospects.update_one(
            {"email": email_lc},
            {"$set": {
                "complained_at": now,
                "status": "unsubscribed",  # SPAM complaint = unsub automatique
            }},
        )
    elif event_type == "email.delivery_delayed":
        await db.prospects.update_one(
            {"email": email_lc},
            {"$set": {"delivery_delayed_at": now}},
        )

    return {"ok": True, "type": event_type, "email": email}


@router.get("/resend/health")
async def resend_health() -> dict:
    """Ping pour vérifier que l'endpoint est joignable par Resend."""
    return {"status": "ok", "endpoint": "resend"}
