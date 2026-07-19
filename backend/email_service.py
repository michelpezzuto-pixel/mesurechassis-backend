"""Service d'envoi d'email — Backend Resend HTTP API.

Resend permet d'envoyer des emails transactionnels via une simple requête HTTP
authentifiée. Si la clé n'est pas configurée OU si l'appel échoue, on
fallback en MOCK console (utile en local + non bloquant pour les tests).

Variables d'env :
    RESEND_API_KEY   : clé secrète Resend (`re_...`)
    MAIL_FROM        : expéditeur ("MesureChâssis <info@mesurechassis.com>")
    MAIL_SUPPORT     : adresse support utilisée pour les notifs internes
    FRONTEND_URL     : base URL pour construire les liens
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("mesurechassis.email")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"
FROM_EMAIL = os.getenv("MAIL_FROM", "MesureChâssis <info@mesurechassis.com>")
REPLY_TO_EMAIL = os.getenv("MAIL_REPLY_TO", "").strip()
MAIL_SUPPORT = os.getenv("MAIL_SUPPORT", "info@mesurechassis.com")
# 🔔 BCC founder — Michel veut "ressentir" chaque nouvel inscrit comme
# un ping émotionnel (comme les $$$ de Stripe). Set via variable env
# MAIL_FOUNDER_BCC. Support de plusieurs emails séparés par virgule.
# Utilisé UNIQUEMENT pour les mails de bienvenue / vérification / invitation
# (JAMAIS pour les mails de campagne ou notifications internes, sinon
# la boîte du founder serait saturée).
MAIL_FOUNDER_BCC = [
    e.strip() for e in os.getenv("MAIL_FOUNDER_BCC", "").split(",")
    if e.strip() and "@" in e.strip()
]
# ─────────────────────────────────────────────────────────────────────
# 🆕 Résolution robuste de l'URL de base pour les liens email
# ─────────────────────────────────────────────────────────────────────
# Ordre de priorité (du plus stable au plus volatile) :
#   1. PUBLIC_BACKEND_URL       → URL Railway prod stable (RECOMMANDÉ)
#   2. FRONTEND_URL             → URL preview / prod frontend
#   3. fallback : chaîne vide → lien relatif (marche pas dans mail).
FRONTEND_URL = os.getenv("FRONTEND_URL", "")  # ex. https://mesurechassis.com


def _link_base_url() -> str:
    """URL de base à utiliser pour les liens dans les emails.

    Priorité PUBLIC_BACKEND_URL car le backend Railway a une URL FIXE
    qui ne change pas quand on change de preview/fork. Les liens de
    vérification restent donc valides même après un redéploiement.
    """
    stable = os.getenv("PUBLIC_BACKEND_URL", "").rstrip("/")
    if stable:
        return stable
    return FRONTEND_URL.rstrip("/") if FRONTEND_URL else ""


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def _build_link(path: str, token: str) -> str:
    """Construit le lien public pour activation / invitation."""
    base = _link_base_url()
    if base:
        return f"{base}{path}?token={token}"
    return f"{path}?token={token}"


def build_verification_link(token: str) -> str:
    # 🆕 Endpoint GET côté backend qui renvoie une page HTML autonome de
    # succès. Fonctionne même si le frontend Expo est indisponible ou
    # que l'URL de preview a changé.
    return _build_link("/api/auth/verify-link", token)


def build_invitation_link(token: str) -> str:
    return _build_link("/invite", token)


def _body_to_html(body: str) -> str:
    """Convertit un texte brut en HTML simple (préserve les sauts de ligne)."""
    safe = (
        body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    paragraphs = "".join(
        f"<p style='margin:0 0 12px 0;line-height:1.55;font-size:14px;color:#1f2937;'>"
        f"{p.replace(chr(10), '<br/>')}</p>"
        for p in safe.split("\n\n")
        if p.strip()
    )
    return (
        "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
        "max-width:560px;margin:0 auto;padding:24px;background:#ffffff;'>"
        "<div style='border-bottom:2px solid #f59e0b;padding-bottom:12px;margin-bottom:16px;'>"
        "<h1 style='font-size:18px;margin:0;color:#111827;letter-spacing:0.4px;'>"
        "MesureChâssis</h1></div>"
        f"{paragraphs}"
        "<div style='margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;"
        "font-size:11px;color:#9ca3af;text-align:center;'>"
        "MesureChâssis — Prise de mesures pour menuiseries professionnelles"
        "</div></div>"
    )


# ─────────────────────────────────────────────────────────────────────
# Envoi générique
# ─────────────────────────────────────────────────────────────────────
def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    link: Optional[str] = None,
    html: Optional[str] = None,
    reply_to_override: Optional[str] = None,
    founder_bcc: bool = False,
) -> dict:
    """Envoie un email via Resend.

    Fallback MOCK en console si :
      - `RESEND_API_KEY` absent
      - appel Resend en échec (erreur réseau, 4xx/5xx)

    Le payload retourné contient `delivered: bool` pour signaler à
    l'appelant si l'envoi réel a réussi ou si on est resté en mock.

    `reply_to_override` permet de spécifier un Reply-To différent du défaut
    (utile pour les feedbacks où on veut que la réponse aille au client).

    `founder_bcc=True` ajoute automatiquement `MAIL_FOUNDER_BCC` en copie
    cachée. Utilisé pour les emails "moments-clés" (bienvenue, invitation)
    afin que le founder ressente chaque nouvel inscrit dans sa boîte.
    """
    payload_log = {"to": to, "subject": subject, "body": body, "link": link}

    if not RESEND_API_KEY:
        _mock_log(to, subject, body, link, reason="RESEND_API_KEY manquante")
        payload_log["delivered"] = False
        return payload_log

    html_content = html or _body_to_html(body)
    resend_payload = {
        "from": FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "text": body,
        "html": html_content,
    }
    # 🔔 BCC founder — filet émotionnel pour Michel (opt-in par email).
    if founder_bcc and MAIL_FOUNDER_BCC:
        # On évite le double-ping si le user est lui-même dans la liste BCC
        # (ex: Michel crée un compte de test avec son propre email).
        bcc_clean = [e for e in MAIL_FOUNDER_BCC if e.lower() != to.lower()]
        if bcc_clean:
            resend_payload["bcc"] = bcc_clean
    if REPLY_TO_EMAIL or reply_to_override:
        resend_payload["reply_to"] = reply_to_override or REPLY_TO_EMAIL
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(RESEND_API_URL, json=resend_payload, headers=headers)
        if r.status_code >= 400:
            logger.warning(
                "📧 Resend FAIL (%s) for %s — %s",
                r.status_code,
                to,
                r.text[:400],
            )
            _mock_log(to, subject, body, link, reason=f"Resend HTTP {r.status_code}")
            payload_log["delivered"] = False
            payload_log["error"] = r.text[:400]
            return payload_log
        data = r.json() if r.content else {}
        logger.info(
            "📧 Resend OK → %s (subject=%r, id=%s)",
            to,
            subject,
            data.get("id", "?"),
        )
        payload_log["delivered"] = True
        payload_log["resend_id"] = data.get("id")
        return payload_log
    except Exception as e:  # noqa: BLE001
        logger.exception("📧 Resend exception → fallback mock : %s", e)
        _mock_log(to, subject, body, link, reason=f"Exception: {e}")
        payload_log["delivered"] = False
        payload_log["error"] = str(e)
        return payload_log


def _mock_log(
    to: str, subject: str, body: str, link: Optional[str], reason: str
) -> None:
    """Log MOCK lorsque Resend n'a pas pu envoyer."""
    logger.warning(
        "─────────  📧 EMAIL (MOCK — %s)  ─────────", reason
    )
    logger.info(" From    : %s", FROM_EMAIL)
    logger.info(" To      : %s", to)
    logger.info(" Subject : %s", subject)
    if link:
        logger.info(" Link    : %s", link)
    logger.info(" Body    :")
    for line in body.splitlines():
        logger.info("   %s", line)
    logger.warning("──────────────────────────────────────────────")


# ─────────────────────────────────────────────────────────────────────
# Templates spécifiques (un par cas d'usage)
# ─────────────────────────────────────────────────────────────────────
def send_verification_email(*, to: str, name: str, link: str) -> dict:
    body = (
        f"Bonjour {name},\n\n"
        "✅ Votre inscription sur MesureChâssis a bien été enregistrée.\n\n"
        "Bienvenue ! Avant de pouvoir vous connecter, nous devons "
        "vérifier votre adresse email.\n\n"
        "Pour activer définitivement votre compte, cliquez sur le lien "
        "ci-dessous (valide 7 jours) :\n\n"
        f"   {link}\n\n"
        "─────────────────────────────────\n"
        "Une fois cette étape effectuée, vous pourrez vous connecter avec "
        "l'email et le mot de passe que vous venez de choisir.\n\n"
        "Si vous n'êtes pas à l'origine de cette inscription, ignorez ce message.\n\n"
        "À très bientôt,\n"
        "L'équipe MesureChâssis"
    )
    return send_email(
        to=to,
        subject="✅ Inscription enregistrée — Vérifiez votre email",
        body=body,
        link=link,
        founder_bcc=True,  # 🔔 Michel reçoit une copie de chaque bienvenue
    )


async def send_password_reset_email(email: str, code: str) -> dict:
    """Envoie le code de réinitialisation par email via Resend.

    Le bloc HTML met le code en gros caractères pour éviter les erreurs
    de saisie sur mobile.
    """
    body = (
        "Bonjour,\n\n"
        "Vous avez demandé la réinitialisation de votre mot de passe sur MesureChâssis.\n\n"
        f"Votre code de vérification : {code}\n\n"
        "Ce code est valable 30 minutes.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
        "L'équipe MesureChâssis"
    )
    # HTML enrichi avec code en évidence
    html = (
        "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
        "max-width:560px;margin:0 auto;padding:24px;background:#ffffff;'>"
        "<div style='border-bottom:2px solid #f59e0b;padding-bottom:12px;margin-bottom:20px;'>"
        "<h1 style='font-size:18px;margin:0;color:#111827;letter-spacing:0.4px;'>"
        "MesureChâssis</h1></div>"
        "<p style='font-size:14px;color:#1f2937;line-height:1.55;margin:0 0 16px;'>Bonjour,</p>"
        "<p style='font-size:14px;color:#1f2937;line-height:1.55;margin:0 0 16px;'>"
        "Vous avez demandé la réinitialisation de votre mot de passe.</p>"
        "<div style='background:#fffbeb;border:2px solid #f59e0b;border-radius:8px;"
        "padding:18px;text-align:center;margin:20px 0;'>"
        "<div style='font-size:11px;color:#92400e;letter-spacing:1px;font-weight:700;"
        "margin-bottom:8px;'>VOTRE CODE</div>"
        f"<div style='font-size:34px;font-weight:900;letter-spacing:8px;color:#111827;"
        f"font-family:monospace;'>{code}</div></div>"
        "<p style='font-size:13px;color:#6b7280;line-height:1.55;margin:0 0 8px;'>"
        "Ce code est valable <strong>30 minutes</strong>.</p>"
        "<p style='font-size:13px;color:#6b7280;line-height:1.55;margin:0 0 24px;'>"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message — "
        "votre mot de passe ne sera pas modifié.</p>"
        "<div style='margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;"
        "font-size:11px;color:#9ca3af;text-align:center;'>"
        "MesureChâssis — Prise de mesures pour menuiseries professionnelles"
        "</div></div>"
    )
    return send_email(
        to=email,
        subject="Réinitialisation de votre mot de passe — MesureChâssis",
        body=body,
        link=None,
        html=html,
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
        founder_bcc=True,  # 🔔 Michel voit chaque nouvelle invitation team
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


def send_ready_for_verification_email(
    *,
    to: str,
    recipient_name: str,
    chantier_name: str,
    address: Optional[str],
    commercial_name: Optional[str] = None,
    nb_mesures: int = 0,
) -> dict:
    """🔔 Notification quand le Commercial clôture la prise de cotes.

    Envoyée à TOUS les techniciens + admins de l'entreprise pour les avertir
    que le chantier est prêt à être vérifié.
    """
    addr_line = address if address else "Adresse non précisée"
    by_line = (
        f" par {commercial_name}" if commercial_name else " par le commercial"
    )
    nb_line = (
        f"   📐 {nb_mesures} ouverture(s) mesurée(s)\n"
        if nb_mesures > 0
        else ""
    )
    body = (
        f"Bonjour {recipient_name},\n\n"
        "📥 Une prise de cotes vient d'être terminée"
        f"{by_line} et attend votre vérification :\n\n"
        f"   📋 {chantier_name}\n"
        f"   📍 {addr_line}\n"
        f"{nb_line}\n"
        "Connectez-vous à MesureChâssis pour :\n"
        "  ✓ Vérifier les mesures saisies\n"
        "  ✓ Valider pour la mise en fabrication\n"
        "  ✓ OU renvoyer au commercial pour corrections\n\n"
        "L'équipe MesureChâssis"
    )
    return send_email(
        to=to,
        subject=f"📥 Prise de cotes à vérifier : {chantier_name}",
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
    """Notification interne : un utilisateur signale un bug ou suggère une amélioration.

    Envoie le mail avec `reply_to=<sender_email>` afin que cliquer sur "Répondre"
    dans la boîte mail destinataire pré-remplisse une réponse directement vers
    l'utilisateur qui a soumis le feedback. Le HTML inclut un bouton "RÉPONDRE
    AU CLIENT" en mailto: pour les clients mail qui n'exposeraient pas reply-to.
    """
    ctx_line = f"\n   Page : {page_context}" if page_context else ""
    body = (
        "Un nouveau feedback utilisateur a été soumis :\n\n"
        f"   De     : {sender_name} <{sender_email}>\n"
        f"   Société: {company_name}{ctx_line}\n\n"
        "─── MESSAGE ───\n"
        f"{user_comment}\n"
        "──────────────\n\n"
        f"Pour répondre directement : {sender_email}"
    )
    # HTML enrichi avec bouton de réponse cliquable (mailto)
    safe_comment = (
        (user_comment or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    safe_page = (page_context or "").replace("<", "&lt;").replace(">", "&gt;")
    reply_subject = (
        "Re%3A%20Feedback%20MesureCh%C3%A2ssis"  # URL-encoded "Re: Feedback MesureChâssis"
    )
    reply_body = (
        f"Bonjour%20{sender_name.split()[0] if sender_name else ''}%2C%0A%0A"
        f"Merci%20pour%20votre%20retour.%0A%0A"
    )
    html = (
        "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
        "max-width:600px;margin:0 auto;padding:24px;background:#ffffff;'>"
        "<div style='border-bottom:2px solid #f59e0b;padding-bottom:12px;margin-bottom:18px;'>"
        "<h1 style='font-size:18px;margin:0;color:#111827;letter-spacing:0.4px;'>"
        "💬 Nouveau feedback utilisateur</h1></div>"
        "<table style='width:100%;font-size:13px;color:#374151;margin-bottom:14px;border-collapse:collapse;'>"
        f"<tr><td style='padding:6px 0;color:#6b7280;width:90px;'>De</td>"
        f"<td style='padding:6px 0;'><strong>{sender_name}</strong> "
        f"&lt;<a href='mailto:{sender_email}' style='color:#ea580c;text-decoration:none;'>{sender_email}</a>&gt;</td></tr>"
        f"<tr><td style='padding:6px 0;color:#6b7280;'>Société</td>"
        f"<td style='padding:6px 0;'>{company_name}</td></tr>"
        + (
            f"<tr><td style='padding:6px 0;color:#6b7280;'>Page</td>"
            f"<td style='padding:6px 0;'><code style='background:#f3f4f6;padding:2px 6px;border-radius:4px;'>"
            f"{safe_page}</code></td></tr>"
            if safe_page
            else ""
        )
        + "</table>"
        "<div style='background:#fffbeb;border-left:3px solid #f59e0b;padding:14px 16px;border-radius:6px;margin-bottom:20px;'>"
        "<div style='font-size:11px;color:#92400e;letter-spacing:0.8px;font-weight:700;margin-bottom:8px;'>"
        "MESSAGE</div>"
        f"<div style='font-size:14px;color:#1f2937;line-height:1.55;'>{safe_comment}</div>"
        "</div>"
        # Bouton mailto: répondre au client
        "<div style='text-align:center;margin:24px 0 10px;'>"
        f"<a href='mailto:{sender_email}?subject={reply_subject}&body={reply_body}' "
        "style='display:inline-block;background:#ea580c;color:#ffffff;text-decoration:none;"
        "padding:12px 22px;border-radius:8px;font-weight:800;letter-spacing:0.6px;font-size:13px;'>"
        "📩 RÉPONDRE AU CLIENT</a></div>"
        f"<p style='text-align:center;font-size:11px;color:#9ca3af;margin:6px 0 0;'>"
        f"Ou répondez directement à ce mail — l'adresse de réponse est <strong>{sender_email}</strong>.</p>"
        "<div style='margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;"
        "font-size:11px;color:#9ca3af;text-align:center;'>"
        "MesureChâssis · Notification interne</div></div>"
    )
    return send_email(
        to=to,
        subject=f"[Feedback] {sender_name} — {company_name}",
        body=body,
        html=html,
        reply_to_override=sender_email,
    )
