"""📧 Prospection B2B — Campagne « Café MesureChâssis ».

Envoie 5 mails personnalisés aux marques station-service belges :
    ► IMMÉDIATS (aujourd'hui, ~staggered 5 min) : Total, Q8, Octa+
    ► DIFFÉRÉS (demain 10h00 UTC via Resend scheduled_at) : Shell, Esso

Chaque envoi est loggé dans la collection `prospection_logs`.

Exécution : docker exec ... python /app/backend/send_prospection_b2b.py
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

import sys
sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("prospection")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("MAIL_FROM", "MesureChâssis <info@mesurechassis.com>")
REPLY_TO = "info@mesurechassis.com"

MICHEL_PHONE = "+32 496 65 00 32"
MICHEL_NAME = "Michel Pezzuto"
APP_STORE_URL = "https://apps.apple.com/fr/app/mesurechâssis/id6776357930"
SITE_URL = "https://mesurechassis.com"

# ═════════ Cibles ═════════
TARGETS = [
    {
        "brand": "TotalEnergies",
        "contact_name": "Service Partenariats",
        "to": "service.communication@totalenergies.com",
        "batch": 1,  # aujourd'hui
    },
    {
        "brand": "Q8 Belgium",
        "contact_name": "Service Partenariats Q8",
        "to": "info@q8.be",
        "batch": 1,
    },
    {
        "brand": "Octa+",
        "contact_name": "Équipe Octa+",
        "to": "info@octaplus.be",
        "batch": 1,
    },
    {
        "brand": "Shell Belgium",
        "contact_name": "Retail Communication Shell",
        "to": "be-communication@shell.com",
        "batch": 2,  # demain
    },
    {
        "brand": "Esso Belgium",
        "contact_name": "Service Partenariats Esso",
        "to": "customer.service.be@exxonmobil.com",
        "batch": 2,
    },
]


def build_email(brand: str, contact_name: str) -> tuple[str, str, str]:
    """Retourne (subject, text, html) personnalisé."""
    subject = f"Partenariat gratuit — Ramener 400+ menuisiers pros dans les stations {brand} chaque mois"

    text = f"""Bonjour {contact_name},

Je suis Michel Pezzuto, fondateur de MesureChâssis, l'app iOS de référence pour les menuisiers professionnels en Belgique (disponible sur l'App Store depuis juin 2026).

Je vous contacte pour vous proposer un partenariat 100% gratuit qui va ramener physiquement les artisans de la menuiserie dans vos stations {brand}, plusieurs fois par mois.

LE PRINCIPE EN 30 SECONDES
──────────────────────────
À chaque prise de mesures dans l'app (~5 fois par jour), le menuisier gagne 1 jeton café à consommer dans une station-service {brand} participante. Il présente son écran, votre pompiste tape un code PIN à 4 chiffres → café offert au menuisier.

CE QUE VOUS Y GAGNEZ
────────────────────
• Flux garanti de professionnels du bâtiment dans vos stations
  (les menuisiers = gros rouleurs de camionnettes, plusieurs pleins/mois)
• Visibilité EXCLUSIVE de la marque {brand} dans mon app
  (~2 000 menuisiers pros actifs, +30 nouveaux/semaine)
• Panneaux d'affichage A3 fournis, imprimés à mes frais
• Zéro développement, zéro contrat contraignant
  → on démarre avec 1 station pilote

CE QUE JE VOUS DEMANDE
──────────────────────
• Le café offert au menuisier (~2 € TTC), refacturé mensuellement par mes soins
• Un pompiste formé (2 min de démo suffisent) qui tape le PIN sur l'écran du menuisier
• 1 seule station en test pour démarrer — on scale seulement si ça marche

OBJECTIF DU PILOTE
──────────────────
• 20 cafés/mois maximum par station (plafond que vous validez)
• Pilote de 3 mois → bilan chiffré ensemble
• Si concluant → extension à 10, 50, 100 stations Belgique + France

Auriez-vous 15 minutes cette semaine pour un appel ? Je peux venir vous présenter l'app en 5 min chrono, où vous voulez.

Bien cordialement,

{MICHEL_NAME}
Fondateur MesureChâssis
📱 {MICHEL_PHONE}
📧 info@mesurechassis.com
🌐 {SITE_URL}
📲 {APP_STORE_URL}

─────────────────────────────────────
Si vous ne souhaitez plus recevoir ce type de messages, répondez simplement STOP à ce mail. RGPD Art. 21 — Prospection B2B légitime.
"""

    html = _build_html(brand, contact_name)
    return subject, text, html


def _build_html(brand: str, contact_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Partenariat MesureChâssis × {brand}</title></head>
<body style="margin:0;padding:24px;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1a1a1e;">
<div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06);">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#FF5A00 0%,#FF7733 100%);padding:28px 32px;color:#fff;">
    <table style="width:100%;border-collapse:collapse;"><tr>
      <td style="vertical-align:middle;">
        <div style="font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;opacity:0.85;">Partenariat B2B</div>
        <h1 style="font-size:24px;font-weight:800;margin:6px 0 0;line-height:1.15;">MesureChâssis × {brand}</h1>
      </td>
      <td style="width:64px;vertical-align:middle;text-align:right;">
        <img src="https://customer-assets.emergentagent.com/job_window-field-app/artifacts/buk4dyh1_emergent-image-1783632378031.png" alt="MesureChâssis" width="56" height="56" style="border-radius:12px;display:block;margin-left:auto;">
      </td>
    </tr></table>
  </div>

  <!-- BODY -->
  <div style="padding:32px;">
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;">Bonjour <strong>{contact_name}</strong>,</p>

    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;">Je suis <strong>Michel Pezzuto</strong>, fondateur de <strong>MesureChâssis</strong>, l'app iOS de référence pour les menuisiers professionnels en Belgique (disponible sur l'App Store depuis juin 2026).</p>

    <p style="font-size:15px;line-height:1.55;margin:0 0 22px;">Je vous propose un <strong style="color:#FF5A00;">partenariat 100% gratuit</strong> qui va ramener physiquement les artisans de la menuiserie dans vos stations <strong>{brand}</strong>, plusieurs fois par mois.</p>

    <!-- PRINCIPE -->
    <div style="background:#fff7f0;border-left:4px solid #FF5A00;padding:18px 20px;border-radius:6px;margin:0 0 24px;">
      <div style="font-size:11px;font-weight:800;color:#FF5A00;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">Le principe en 30 sec</div>
      <p style="font-size:14px;line-height:1.55;margin:0;">À chaque prise de mesures dans l'app (~5 fois/jour), le menuisier <strong>gagne 1 jeton café</strong> à consommer dans une station {brand} participante. Il présente son écran, votre pompiste tape un <strong>code PIN à 4 chiffres</strong> → café offert. ☕</p>
    </div>

    <!-- CE QUE VOUS GAGNEZ -->
    <h2 style="font-size:15px;font-weight:800;color:#1a1a1e;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">Ce que vous y gagnez</h2>
    <ul style="font-size:14px;line-height:1.6;color:#333;padding:0 0 0 20px;margin:0 0 24px;">
      <li><strong>Flux garanti</strong> de professionnels du bâtiment dans vos stations</li>
      <li><strong>Visibilité EXCLUSIVE</strong> de la marque {brand} dans l'app (~2 000 menuisiers pros actifs)</li>
      <li>Panneaux d'affichage A3 fournis, <strong>imprimés à mes frais</strong></li>
      <li><strong>Zéro développement</strong>, zéro contrat contraignant</li>
    </ul>

    <!-- CE QUE JE DEMANDE -->
    <h2 style="font-size:15px;font-weight:800;color:#1a1a1e;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">Ce que je vous demande</h2>
    <ul style="font-size:14px;line-height:1.6;color:#333;padding:0 0 0 20px;margin:0 0 24px;">
      <li>Le café offert au menuisier (~2 € TTC), refacturé mensuellement</li>
      <li>Un pompiste formé (2 min de démo) pour taper le PIN</li>
      <li><strong>1 seule station en test</strong> pour démarrer</li>
    </ul>

    <!-- OBJECTIF -->
    <div style="background:#f8fafc;border-radius:8px;padding:16px 20px;margin:0 0 28px;">
      <div style="font-size:11px;font-weight:800;color:#0f766e;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;">🎯 Objectif du pilote</div>
      <ul style="font-size:14px;line-height:1.55;margin:0;padding:0 0 0 20px;color:#333;">
        <li>20 cafés/mois max/station (plafond que vous validez)</li>
        <li>Pilote de 3 mois → bilan chiffré ensemble</li>
        <li>Si concluant → extension à 10, 50, 100 stations Belgique + France</li>
      </ul>
    </div>

    <!-- CTA -->
    <div style="text-align:center;margin:28px 0;">
      <a href="tel:{MICHEL_PHONE.replace(' ','')}" style="display:inline-block;background:#FF5A00;color:#fff;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;box-shadow:0 4px 14px rgba(255,90,0,0.35);">
        📞 M'appeler pour 15 min de démo
      </a>
    </div>

    <p style="font-size:14px;line-height:1.55;margin:0 0 8px;text-align:center;color:#555;">Ou répondez simplement à ce mail — je m'adapte à vos horaires.</p>
  </div>

  <!-- SIGNATURE -->
  <div style="background:#1a1a1e;color:#fff;padding:24px 32px;">
    <table style="width:100%;border-collapse:collapse;"><tr>
      <td style="vertical-align:top;">
        <div style="font-size:16px;font-weight:800;color:#fff;">{MICHEL_NAME}</div>
        <div style="font-size:12px;color:#a8a8b0;margin-top:2px;">Fondateur MesureChâssis</div>
        <div style="margin-top:14px;font-size:13px;line-height:1.7;color:#e5e5e9;">
          📱 <a href="tel:{MICHEL_PHONE.replace(' ','')}" style="color:#FF7733;text-decoration:none;">{MICHEL_PHONE}</a><br/>
          📧 <a href="mailto:info@mesurechassis.com" style="color:#FF7733;text-decoration:none;">info@mesurechassis.com</a><br/>
          🌐 <a href="{SITE_URL}" style="color:#FF7733;text-decoration:none;">{SITE_URL}</a><br/>
          📲 <a href="{APP_STORE_URL}" style="color:#FF7733;text-decoration:none;">Télécharger sur l'App Store</a>
        </div>
      </td>
      <td style="width:120px;vertical-align:top;text-align:right;">
        <img src="https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={APP_STORE_URL.replace(':','%3A').replace('/','%2F')}&bgcolor=1a1a1e&color=ffffff" alt="QR App Store" width="100" height="100" style="border-radius:8px;background:#1a1a1e;padding:6px;">
      </td>
    </tr></table>
  </div>

  <!-- LEGAL -->
  <div style="padding:14px 32px;background:#0f0f12;color:#5a5a62;font-size:11px;line-height:1.5;text-align:center;">
    Prospection B2B légitime — RGPD Art. 21. Répondez STOP pour ne plus recevoir ce type de message. MesureChâssis SRL, Belgique.
  </div>
</div>
</body></html>
"""


async def send_resend(
    to: str,
    subject: str,
    text: str,
    html: str,
    scheduled_at: Optional[str] = None,
) -> dict:
    """Envoi via API Resend, avec support scheduled_at natif."""
    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY absente → MOCK")
        return {"delivered": False, "reason": "no_api_key"}
    payload: dict = {
        "from": FROM_EMAIL,
        "to": [to],
        "reply_to": REPLY_TO,
        "subject": subject,
        "text": text,
        "html": html,
    }
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(RESEND_API_URL, json=payload, headers=headers)
    if r.status_code >= 400:
        log.error("❌ Resend HTTP %s → %s", r.status_code, r.text[:300])
        return {"delivered": False, "http": r.status_code, "error": r.text[:400]}
    data = r.json() if r.content else {}
    log.info("✅ %s → Resend id=%s scheduled=%s", to, data.get("id"), scheduled_at or "now")
    return {"delivered": True, "resend_id": data.get("id"), "scheduled_at": scheduled_at}


async def main() -> None:
    now = datetime.now(timezone.utc)
    tomorrow_10h = (now + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    tomorrow_iso = tomorrow_10h.isoformat().replace("+00:00", "Z")

    log.info("═══ Prospection B2B — %d cibles ═══", len(TARGETS))

    # BATCH 1 : envois immédiats, espacés de 30 secondes pour éviter la
    # détection anti-spam par les gros MTA (staggered send)
    batch1 = [t for t in TARGETS if t["batch"] == 1]
    batch2 = [t for t in TARGETS if t["batch"] == 2]

    log.info("📨 BATCH 1 — %d envois immédiats (staggered 30s)", len(batch1))
    for i, target in enumerate(batch1):
        subject, text, html = build_email(target["brand"], target["contact_name"])
        result = await send_resend(target["to"], subject, text, html)
        await db.prospection_logs.insert_one(
            {
                "brand": target["brand"],
                "to": target["to"],
                "subject": subject,
                "sent_at": now.isoformat(),
                "batch": 1,
                "resend_id": result.get("resend_id"),
                "delivered": result.get("delivered", False),
                "error": result.get("error"),
            }
        )
        if i < len(batch1) - 1:
            log.info("⏸  Attente 30s avant prochain envoi…")
            await asyncio.sleep(30)

    log.info("📅 BATCH 2 — %d envois différés (planifiés %s)", len(batch2), tomorrow_iso)
    for target in batch2:
        subject, text, html = build_email(target["brand"], target["contact_name"])
        result = await send_resend(
            target["to"], subject, text, html, scheduled_at=tomorrow_iso
        )
        await db.prospection_logs.insert_one(
            {
                "brand": target["brand"],
                "to": target["to"],
                "subject": subject,
                "sent_at": now.isoformat(),
                "scheduled_for": tomorrow_iso,
                "batch": 2,
                "resend_id": result.get("resend_id"),
                "delivered": result.get("delivered", False),
                "error": result.get("error"),
            }
        )

    # RÉCAP
    delivered = await db.prospection_logs.count_documents(
        {"delivered": True, "sent_at": {"$gte": now.isoformat()[:19]}}
    )
    log.info("═══ Récap : %d/%d envois OK ═══", delivered, len(TARGETS))
    log.info("Vérifie tes stats Resend : https://resend.com/emails")


if __name__ == "__main__":
    asyncio.run(main())
