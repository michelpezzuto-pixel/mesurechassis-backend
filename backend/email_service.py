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


async def send_password_reset_email(email: str, code: str) -> dict:
    """Envoie le code de réinitialisation par email.

    Pour l'instant : mock console (le code est aussi retourné dans
    la réponse HTTP en mode BETA pour ne pas bloquer l'utilisateur).
    Quand Resend sera branché, on basculera ici sur un envoi réel.
    """
    body = (
        f"Bonjour,\n\n"
        f"Vous avez demandé la réinitialisation de votre mot de passe sur MesureChâssis.\n\n"
        f"Votre code de vérification :\n\n"
        f"   ▶  {code}  ◀\n\n"
        f"Ce code est valable 30 minutes.\n"
        f"Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
        f"L'équipe MesureChâssis"
    )
    return send_email(
        to=email,
        subject="Réinitialisation de votre mot de passe — MesureChâssis",
        body=body,
        link=None,
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


def send_assignment_email(
    *,
    to: str,
    assignee_name: str,
    chantier_name: str,
    address: Optional[str],
    created_by_name: Optional[str] = None,
) -> dict:
    """Notification quand un chantier est attribué à un membre de l'équipe."""
    addr_line = address if address else "Adresse non précisée"
    by_line = f" (créé par {created_by_name})" if created_by_name else ""
    body = (
        f"Bonjour {assignee_name},\n\n"
        f"Un nouveau chantier vous a été attribué{by_line} :\n\n"
        f"   📋 {chantier_name}\n"
        f"   📍 {addr_line}\n\n"
        "Connectez-vous à MesureChâssis pour consulter les détails et "
        "planifier votre intervention.\n\n"
        "L'équipe MesureChâssis"
    )
    return send_email(
        to=to,
        subject=f"Nouveau chantier attribué : {chantier_name}",
        body=body,
    )


def send_feedback_email(
    *,
    to: str,
    sender_email: str,
    sender_name: str,
    company_name: str,
    user_comment: str,
    page_context: Optional[str] = None,
) -> dict:
    """Notification interne : un utilisateur signale un bug ou suggère une amélioration."""
    ctx_line = f"\n   Page : {page_context}" if page_context else ""
    body = (
        "Un nouveau feedback utilisateur a été soumis :\n\n"
        f"   De     : {sender_name} <{sender_email}>\n"
        f"   Société: {company_name}{ctx_line}\n\n"
        "─── MESSAGE ───\n"
        f"{user_comment}\n"
        "──────────────\n\n"
        "Connectez-vous à l'espace admin pour traiter ce feedback."
    )
    return send_email(
        to=to,
        subject=f"[Feedback] {sender_name} — {company_name}",
        body=body,
    )
