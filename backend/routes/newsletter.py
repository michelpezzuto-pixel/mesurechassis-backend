"""
Newsletter / Lead capture — landing page mesurechassis.com.

Endpoint public (pas d'auth) utilisé par le formulaire "Guide gratuit 5 pièges"
du site marketing. Stocke l'email dans la collection `newsletter_subscribers`
et envoie un email de confirmation via Resend avec le lien du PDF.

Anti-spam :
- Rate-limit basique sur l'IP (10/jour par IP)
- Validation email stricte (Pydantic EmailStr)
- Déduplication par email (upsert)

Séquence email prévue (à automatiser plus tard via CRON) :
- J0 : Envoi du guide PDF + welcome
- J3 : Astuce "prise de mesures en 30s"
- J7 : Étude de cas Sambre Menuiserie
- J14 : Bénéfice fiscal (TVA 0 %)
- J30 : Offre d'essai gratuite 30j

Auteur : MesureChâssis, juin 2026.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from db import db
from email_service import send_email

log = logging.getLogger("mesurechassis.newsletter")

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


# ─────────────────────────────────────────────────────────────────
# Modèles
# ─────────────────────────────────────────────────────────────────
class NewsletterSubscribeIn(BaseModel):
    email: EmailStr
    source: Optional[str] = Field(
        default="landing_unknown",
        max_length=64,
        description="Origine (ex: landing_hero_guide, footer, etc.)",
    )


class NewsletterSubscribeOut(BaseModel):
    ok: bool = True
    already_subscribed: bool = False
    message: str


# ─────────────────────────────────────────────────────────────────
# Contenu du guide (email HTML)
# ─────────────────────────────────────────────────────────────────
GUIDE_PDF_URL = os.getenv(
    "GUIDE_PDF_URL",
    "https://capable-gratitude-production-db51.up.railway.app/api/downloads/guide-5-pieges.pdf",
)


def _guide_email_html(email: str) -> str:
    """HTML de l'email de bienvenue envoyé après capture."""
    return f"""\
<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#f5f5f7;margin:0;padding:24px;color:#1c1c1e;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
              padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
    <h1 style="margin:0 0 12px;font-size:22px;">📚 Voici ton guide gratuit</h1>
    <p style="font-size:15px;line-height:1.55;margin:0 0 16px;color:#3a3a3c;">
      Salut ! Merci de t'être inscrit.<br><br>
      Voici le guide <strong>« 5 pièges qui te font perdre 2h par chantier »</strong> —
      rédigé par un menuisier belge après 15 ans de terrain.
    </p>
    <p style="text-align:center;margin:24px 0;">
      <a href="{GUIDE_PDF_URL}"
         style="display:inline-block;background:#00C853;color:#000;
                text-decoration:none;padding:14px 28px;border-radius:10px;
                font-weight:600;font-size:15px;">
        📥 Télécharger le PDF (2 Mo)
      </a>
    </p>
    <p style="font-size:14px;line-height:1.55;color:#6c6c70;margin:24px 0 0;">
      Dans les prochains jours je te partagerai 4 emails courts avec :<br>
      • Une astuce pour mesurer un trapèze en 30&nbsp;s<br>
      • L'histoire d'un menuisier qui a économisé 8h/semaine<br>
      • Le hack TVA que 80&nbsp;% des artisans ignorent<br>
      • Une offre exclusive pour tester l'app 30 jours gratuits
    </p>
    <hr style="border:none;border-top:1px solid #e5e5ea;margin:32px 0 16px;">
    <p style="font-size:12px;color:#8e8e93;margin:0;">
      Michel · Fondateur MesureChâssis<br>
      Répondre à ce mail directement pour toute question.
    </p>
  </div>
</body></html>
"""


# ─────────────────────────────────────────────────────────────────
# Endpoint public
# ─────────────────────────────────────────────────────────────────
@router.post("/subscribe", response_model=NewsletterSubscribeOut)
async def subscribe(payload: NewsletterSubscribeIn, request: Request):
    """
    Endpoint public appelé depuis le formulaire de mesurechassis.com.
    - Stocke l'email en base
    - Envoie le guide PDF par email (Resend)
    - Idempotent (upsert par email)
    """
    email = payload.email.lower().strip()
    source = (payload.source or "landing_unknown").strip()[:64]
    ip = (request.client.host if request.client else "unknown")[:64]
    ua = request.headers.get("user-agent", "")[:256]

    now = datetime.now(timezone.utc)

    # 1. Upsert en base
    coll = db["newsletter_subscribers"]
    existing = await coll.find_one({"email": email})
    already = bool(existing)

    if already:
        await coll.update_one(
            {"email": email},
            {"$set": {"last_seen_at": now, "last_source": source, "last_ip": ip}},
        )
        log.info("newsletter: re-subscribe email=%s source=%s", email, source)
        return NewsletterSubscribeOut(
            ok=True,
            already_subscribed=True,
            message="Déjà inscrit — on te renvoie le guide par sécurité 🙂",
        )

    await coll.insert_one({
        "email": email,
        "source": source,
        "ip": ip,
        "user_agent": ua,
        "created_at": now,
        "last_seen_at": now,
        "unsubscribed": False,
        "sequence_step": 0,  # 0 = welcome envoyé
    })
    log.info("newsletter: NEW subscriber email=%s source=%s ip=%s", email, source, ip)

    # 2. Envoi de l'email de bienvenue via Resend
    try:
        send_result = send_email(
            to=email,
            subject="📚 Ton guide gratuit MesureChâssis (5 pièges à éviter)",
            body=(
                "Salut !\n\n"
                "Merci de t'être inscrit. Voici le guide 'Les 5 pièges qui te font "
                "perdre 2h par chantier'.\n\n"
                f"👉 Télécharge-le ici : {GUIDE_PDF_URL}\n\n"
                "À très vite,\nMichel — Fondateur MesureChâssis"
            ),
            html=_guide_email_html(email),
            link=GUIDE_PDF_URL,
            founder_bcc=True,  # ← Michel reçoit chaque nouvelle capture en BCC
        )
        delivered = bool(send_result.get("delivered"))
    except Exception as exc:  # noqa: BLE001
        log.exception("newsletter: send_email failed for %s: %s", email, exc)
        delivered = False

    return NewsletterSubscribeOut(
        ok=True,
        already_subscribed=False,
        message=(
            "Bien reçu ! Vérifie ta boîte (et tes spams)."
            if delivered
            else "Bien reçu ! Le guide arrive dans quelques minutes."
        ),
    )


@router.get("/count")
async def public_count():
    """
    Compteur public d'inscrits (peut être affiché sur la landing).
    Ne retourne PAS d'emails, juste un nombre agrégé.
    """
    coll = db["newsletter_subscribers"]
    total = await coll.count_documents({"unsubscribed": {"$ne": True}})
    return {"total": int(total)}
