"""Service d'envoi d'email — MOCK MVP.

Pour la production, remplacer le corps de `send_email` par une intégration
SendGrid / Resend / SMTP. Le présent module enregistre l'email dans les logs
et retourne le payload sous forme de dict (consommé par les routes pour
exposer le lien de vérification dans la réponse API, utile en démo).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("mesurechassis.email")

FROM_EMAIL = os.getenv("MAIL_FROM", "noreply@mesurechassis.fr")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")  # ex. https://app.mesurechassis.fr


def _build_link(path: str, token: str) -> str:
    """Construit le lien public pour activation / invitation.

    Pour le preview Expo, on retourne un chemin relatif. Le front-end
    expo-router gère `/verify?token=...` et `/invite?token=...`.
    """
    base = FRONTEND_URL.rstrip("/") if FRONTEND_URL else ""
    if base:
        return f"{base}{path}?token={token}"
    return f"{path}?token={token}"


def build_verification_link(token: str) -> str:
    return _build_link("/verify", token)


def build_invitation_link(token: str) -> str:
    return _build_link("/invite", token)


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    link: Optional[str] = None,
) -> dict:
    """Mock d'envoi. Log dans la console + retourne le payload."""
    logger.info(
        "─────────────────  📧 EMAIL (MOCK)  ─────────────────"
    )
    logger.info(" From    : %s", FROM_EMAIL)
    logger.info(" To      : %s", to)
    logger.info(" Subject : %s", subject)
    if link:
        logger.info(" Link    : %s", link)
    logger.info(" Body    :")
    for line in body.splitlines():
        logger.info("   %s", line)
    logger.info(
        "─────────────────────────────────────────────────────"
    )
    return {"to": to, "subject": subject, "body": body, "link": link}


def send_verification_email(*, to: str, name: str, link: str) -> dict:
    body = (
        f"Bonjour {name},\n\n"
        "Bienvenue sur MesureChâssis !\n\n"
        "Pour activer votre compte, cliquez sur le lien ci-dessous "
        "(valide 7 jours) :\n\n"
        f"   {link}\n\n"
        "Si vous n'êtes pas à l'origine de cette inscription, ignorez ce message.\n\n"
        "L'équipe MesureChâssis"
    )
    return send_email(
        to=to,
        subject="Vérifiez votre adresse email — MesureChâssis",
        body=body,
        link=link,
    )


def send_invitation_email(
    *, to: str, name: str, role: str, company_name: str, link: str
) -> dict:
    role_fr = {"commercial": "Commercial", "technician": "Technicien"}.get(role, role)
    body = (
        f"Bonjour {name},\n\n"
        f"Vous avez été invité(e) à rejoindre la société « {company_name} » "
        f"sur MesureChâssis en tant que {role_fr}.\n\n"
        "Cliquez sur le lien ci-dessous (valide 7 jours) pour définir votre "
        "mot de passe et activer votre compte :\n\n"
        f"   {link}\n\n"
        "L'équipe MesureChâssis"
    )
    return send_email(
        to=to,
        subject=f"Invitation à rejoindre {company_name} — MesureChâssis",
        body=body,
        link=link,
    )
