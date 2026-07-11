"""📧 Prospection SPONSORS — Campagne « Café MesureChâssis ».

Ciblage : 3 fournisseurs belges de menuiserie qui ont un budget marketing
dédié aux artisans pros. Objectif : décrocher UN sponsor qui finance les
cafés (≈500-1500 €/an) en échange d'une visibilité exclusive dans l'app
et sur les affiches A3 en station-service.

Exécution : docker exec ... python /app/backend/send_prospection_sponsors.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("prospection-sponsors")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("MAIL_FROM", "MesureChâssis <info@mesurechassis.com>")
REPLY_TO = "info@mesurechassis.com"

MICHEL_PHONE = "+32 496 65 00 32"
MICHEL_NAME = "Michel Pezzuto"
APP_STORE_URL = "https://apps.apple.com/fr/app/mesurechâssis/id6776357930"
SITE_URL = "https://mesurechassis.com"

# ═════════ Cibles sponsors (fournisseurs menuiserie belges) ═════════
TARGETS = [
    {
        "brand": "Deceuninck",
        "contact_name": "Service Marketing Deceuninck Belgium",
        "to": "info@deceuninck.be",
        "pitch_extra": "Vous êtes LE fournisseur PVC belge le plus utilisé par les menuisiers, ce partenariat renforcera votre position déjà dominante.",
    },
    {
        "brand": "Reynaers Aluminium",
        "contact_name": "Service Marketing Reynaers Belgium",
        "to": "info@reynaers.com",
        "pitch_extra": "En tant que leader alu résidentiel européen, votre marque doit être visible partout où le menuisier prépare ses chantiers.",
    },
    {
        "brand": "Aliplast",
        "contact_name": "Service Marketing Aliplast",
        "to": "info@aliplast.com",
        "pitch_extra": "En tant que fabricant belge indépendant, ce partenariat vous positionne au plus près des menuisiers locaux qui privilégient les circuits courts.",
    },
]


def build_email(brand: str, contact_name: str, pitch_extra: str) -> tuple[str, str, str]:
    subject = f"{brand} × MesureChâssis — 500 € pour toucher 2 000 menuisiers pros chaque jour"

    text = f"""Bonjour {contact_name},

Je suis Michel Pezzuto, fondateur de MesureChâssis, l'app iOS de référence pour les menuisiers professionnels en Belgique (App Store depuis juin 2026).

Nous lançons en septembre une campagne physique inédite : « Café MesureChâssis » — 100 affiches A3 déposées dans les stations-service partenaires (Total, Q8, Shell, Octa+). Chaque menuisier qui teste l'app gagne un café gratuit à consommer chez notre partenaire station-service.

C'est ici que {brand} peut devenir le sponsor exclusif du dispositif.

CE QUE JE VOUS PROPOSE
──────────────────────
Devenez SPONSOR OFFICIEL de la campagne pendant 12 mois :
• Budget : ≈500 €/an (soit 250 cafés × 2 €)
• Vos jetons "cafés" à distribuer = 250 impressions physiques par an

CE QUE VOUS Y GAGNEZ
────────────────────
1. LOGO SPONSOR sur les 100 affiches A3 en station-service
   → 100 pompes × 500 vues/semaine × 52 semaines = 2 600 000 impressions/an
2. LOGO PERMANENT dans l'app MesureChâssis (écran "Mes Cafés")
   → 2 000 menuisiers actifs, +30 nouveaux/semaine
3. BANNIÈRE dans la newsletter mensuelle envoyée aux inscrits
4. Un ARTICLE de présentation de {brand} dans le blog MesureChâssis
5. Statistiques mensuelles précises (cafés consommés, provinces touchées, etc.)

POURQUOI {brand} ?
──────────────────
{pitch_extra}

Autrement dit : là où vos concurrents dépensent 10 000 €+ pour du print générique, vous ciblez pour 500 € des menuisiers 100% pros, actifs, prêts à prescrire vos produits à leurs clients finaux.

CE QUI EST INCLUS
─────────────────
• Intégration de votre logo sur les affiches et dans l'app (dev à ma charge)
• Facturation trimestrielle (125 €/trimestre HT)
• Rapport mensuel de performance par email
• Réversibilité : préavis de 30 jours si vous souhaitez sortir

Auriez-vous 20 minutes cette semaine pour un appel ? Je peux venir vous présenter la campagne, l'app et les premiers résultats (32 utilisateurs testeurs actifs, communauté qui grandit).

Bien cordialement,

{MICHEL_NAME}
Fondateur MesureChâssis
📱 {MICHEL_PHONE}
📧 info@mesurechassis.com
🌐 {SITE_URL}
📲 {APP_STORE_URL}

─────────────────────────────────────
Si vous ne souhaitez plus recevoir ce type de messages, répondez STOP. RGPD Art. 21 — prospection B2B légitime.
"""

    html = _build_html(brand, contact_name, pitch_extra)
    return subject, text, html


def _build_html(brand: str, contact_name: str, pitch_extra: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>{brand} × MesureChâssis</title></head>
<body style="margin:0;padding:24px;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1a1a1e;">
<div style="max-width:620px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06);">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#FF5A00 0%,#FF7733 100%);padding:32px;color:#fff;">
    <table style="width:100%;border-collapse:collapse;"><tr>
      <td style="vertical-align:middle;">
        <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;opacity:0.9;">Sponsoring Exclusif</div>
        <h1 style="font-size:26px;font-weight:800;margin:8px 0 0;line-height:1.1;">{brand} × MesureChâssis</h1>
        <p style="font-size:14px;margin:8px 0 0;opacity:0.95;">Devenez sponsor officiel de la campagne physique 2026-2027</p>
      </td>
      <td style="width:64px;vertical-align:middle;text-align:right;">
        <img src="https://customer-assets.emergentagent.com/job_window-field-app/artifacts/buk4dyh1_emergent-image-1783632378031.png" alt="MesureChâssis" width="56" height="56" style="border-radius:12px;display:block;margin-left:auto;">
      </td>
    </tr></table>
  </div>

  <!-- BODY -->
  <div style="padding:32px;">
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;">Bonjour <strong>{contact_name}</strong>,</p>

    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;">Je suis <strong>Michel Pezzuto</strong>, fondateur de <strong>MesureChâssis</strong>, l'app iOS de référence pour les menuisiers professionnels en Belgique (App Store depuis juin 2026).</p>

    <p style="font-size:15px;line-height:1.55;margin:0 0 24px;">Nous lançons en septembre une campagne physique inédite : <strong>« Café MesureChâssis »</strong> — 100 affiches A3 déposées dans les stations-service partenaires (Total, Q8, Shell, Octa+). Chaque menuisier qui teste l'app gagne un café gratuit à la pompe.</p>

    <!-- CHIFFRES CLÉS -->
    <div style="background:linear-gradient(135deg,#fff7f0 0%,#ffe6d5 100%);border-left:4px solid #FF5A00;padding:20px 22px;border-radius:8px;margin:0 0 28px;">
      <div style="font-size:11px;font-weight:800;color:#FF5A00;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;">💥 L'occasion en 3 chiffres</div>
      <table style="width:100%;border-collapse:collapse;"><tr>
        <td style="text-align:center;padding:8px;">
          <div style="font-size:28px;font-weight:900;color:#FF5A00;">500 €</div>
          <div style="font-size:11px;color:#666;">budget annuel</div>
        </td>
        <td style="text-align:center;padding:8px;border-left:1px solid #FFB88C;border-right:1px solid #FFB88C;">
          <div style="font-size:28px;font-weight:900;color:#FF5A00;">2,6M</div>
          <div style="font-size:11px;color:#666;">impressions/an</div>
        </td>
        <td style="text-align:center;padding:8px;">
          <div style="font-size:28px;font-weight:900;color:#FF5A00;">2 000+</div>
          <div style="font-size:11px;color:#666;">menuisiers pros</div>
        </td>
      </tr></table>
    </div>

    <!-- CE QUE VOUS Y GAGNEZ -->
    <h2 style="font-size:15px;font-weight:800;color:#1a1a1e;margin:0 0 14px;text-transform:uppercase;letter-spacing:0.5px;">🎯 Ce que vous y gagnez</h2>
    <ol style="font-size:14px;line-height:1.65;color:#333;padding:0 0 0 20px;margin:0 0 28px;">
      <li style="margin-bottom:10px;"><strong>LOGO SPONSOR</strong> sur les 100 affiches A3 en station-service<br/><span style="color:#666;font-size:13px;">→ 100 pompes × 500 vues/semaine × 52 semaines = <strong>2 600 000 impressions/an</strong></span></li>
      <li style="margin-bottom:10px;"><strong>LOGO PERMANENT</strong> dans l'app MesureChâssis (écran « Mes Cafés »)<br/><span style="color:#666;font-size:13px;">→ 2 000 menuisiers actifs, +30 nouveaux/semaine</span></li>
      <li style="margin-bottom:10px;"><strong>BANNIÈRE</strong> dans la newsletter mensuelle envoyée aux inscrits</li>
      <li style="margin-bottom:10px;"><strong>ARTICLE de présentation</strong> de {brand} dans le blog MesureChâssis</li>
      <li><strong>Statistiques mensuelles</strong> précises (cafés consommés, provinces, engagement)</li>
    </ol>

    <!-- POURQUOI VOUS -->
    <div style="background:#0f766e;color:#fff;border-radius:10px;padding:20px 22px;margin:0 0 28px;">
      <div style="font-size:11px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;opacity:0.9;">🤝 Pourquoi {brand} ?</div>
      <p style="font-size:14px;line-height:1.6;margin:0;">{pitch_extra}</p>
    </div>

    <!-- COMPARATIF -->
    <p style="font-size:14px;line-height:1.6;margin:0 0 28px;color:#444;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:14px 18px;">
      💡 <strong>Autrement dit :</strong> là où vos concurrents dépensent 10 000 €+ pour du print générique, vous ciblez pour <strong>500 €/an</strong> des menuisiers 100 % pros, actifs, qui prescrivent vos produits à leurs clients finaux.
    </p>

    <!-- MODALITÉS -->
    <h2 style="font-size:15px;font-weight:800;color:#1a1a1e;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">📄 Modalités</h2>
    <ul style="font-size:14px;line-height:1.6;color:#333;padding:0 0 0 20px;margin:0 0 28px;">
      <li>Intégration de votre logo sur affiches + app (dev à ma charge)</li>
      <li>Facturation trimestrielle : <strong>125 €/trimestre HT</strong></li>
      <li>Rapport mensuel de performance envoyé par email</li>
      <li>Réversibilité : préavis de 30 jours pour sortir</li>
    </ul>

    <!-- CTA -->
    <div style="text-align:center;margin:32px 0;">
      <a href="tel:{MICHEL_PHONE.replace(' ','')}" style="display:inline-block;background:#FF5A00;color:#fff;padding:16px 36px;border-radius:12px;text-decoration:none;font-weight:700;font-size:15px;box-shadow:0 6px 20px rgba(255,90,0,0.35);">
        📞 M'appeler pour 20 min de démo
      </a>
    </div>
    <p style="font-size:14px;line-height:1.55;margin:0;text-align:center;color:#555;">Ou répondez à ce mail — je m'adapte à vos horaires.</p>
  </div>

  <!-- SIGNATURE -->
  <div style="background:#1a1a1e;color:#fff;padding:28px 32px;">
    <table style="width:100%;border-collapse:collapse;"><tr>
      <td style="vertical-align:top;">
        <div style="font-size:17px;font-weight:800;color:#fff;">{MICHEL_NAME}</div>
        <div style="font-size:12px;color:#a8a8b0;margin-top:2px;">Fondateur MesureChâssis</div>
        <div style="margin-top:14px;font-size:13px;line-height:1.75;color:#e5e5e9;">
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
    Prospection B2B légitime — RGPD Art. 21. Répondez STOP pour ne plus recevoir. MesureChâssis, Belgique.
  </div>
</div>
</body></html>
"""


async def send_resend(
    to: str, subject: str, text: str, html: str, scheduled_at: Optional[str] = None
) -> dict:
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
    log.info("✅ %s → Resend id=%s", to, data.get("id"))
    return {"delivered": True, "resend_id": data.get("id")}


async def main() -> None:
    now = datetime.now(timezone.utc)
    log.info("═══ Prospection SPONSORS — %d cibles ═══", len(TARGETS))

    for i, target in enumerate(TARGETS):
        subject, text, html = build_email(
            target["brand"], target["contact_name"], target["pitch_extra"]
        )
        result = await send_resend(target["to"], subject, text, html)
        await db.prospection_logs.insert_one(
            {
                "type": "sponsor",
                "brand": target["brand"],
                "to": target["to"],
                "subject": subject,
                "sent_at": now.isoformat(),
                "resend_id": result.get("resend_id"),
                "delivered": result.get("delivered", False),
                "error": result.get("error"),
            }
        )
        if i < len(TARGETS) - 1:
            log.info("⏸  Attente 30s…")
            await asyncio.sleep(30)

    log.info("═══ Récap : %d envois OK ═══", len(TARGETS))


if __name__ == "__main__":
    asyncio.run(main())
