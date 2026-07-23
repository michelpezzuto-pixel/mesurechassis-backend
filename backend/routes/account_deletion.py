"""🗂️ Exit Survey + Grace Period (suppression de compte différée).

Nouveau flux (v1.1.4+) qui remplace `DELETE /auth/me` (conservé pour compat).

Workflow :
  1. Frontend appelle `POST /account/delete-with-survey` avec la raison,
     un éventuel texte libre et le mot de passe de confirmation.
  2. Backend :
     - Insère le questionnaire dans `account_deletion_surveys`
     - Passe le compte en `status = "pending_deletion"` +
       `pending_deletion_until = now + 30j`
     - Envoie un email à l'admin (Michel) avec la raison + contexte
     - Envoie un email à l'utilisateur avec un lien de restauration signé
     - Le mot de passe est conservé (pas mis à "" comme dans le legacy) pour
       autoriser une restauration transparente
  3. Login → 403 tant que `pending_deletion` avec code
     "account_pending_deletion" (le frontend redirige vers la page de
     restauration email).
  4. Cron toutes les 6h → hard-delete définitif après 30j.
  5. Endpoint public `GET /account/restore?token=...` → page HTML de
     confirmation + restore instantané.

Conforme Apple Guideline 5.1.1(v) (deletion available in-app) + RGPD (hard
delete 30j).
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from db import JWT_SECRET, db
from deps import auth_user, verify_password
from email_service import send_email, _link_base_url

logger = logging.getLogger("mesurechassis.account_deletion")

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────
GRACE_PERIOD_DAYS = 30
RESTORE_TOKEN_TTL_DAYS = 30
_RESTORE_JWT_SCOPE = "account_restore"

REASON_LABELS = {
    "too_expensive": "C'est trop cher",
    "too_complex": "L'application est trop compliquée à utiliser",
    "missing_features": "Je ne trouve pas les fonctionnalités dont j'ai besoin",
    "technical_issues": "Problèmes techniques ou bugs récurrents",
    "no_longer_needed": "Je n'ai plus besoin de l'outil pour mes chantiers",
    "other": "Autre",
}

ADMIN_NOTIFY_EMAIL = os.getenv(
    "SUPPRESSIONS_EMAIL", "suppressions@mesurechassis.com"
).strip()


# ─────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────
class DeleteWithSurveyRequest(BaseModel):
    reason: str = Field(..., description="Enum reason key")
    custom_text: Optional[str] = Field(
        default=None, max_length=1000, description="Requis si reason=other"
    )
    password: str = Field(..., description="Mot de passe actuel pour confirmer")


# ─────────────────────────────────────────────────────────────────────
# Token utils (JWT signé, expiration 30j)
# ─────────────────────────────────────────────────────────────────────
def _make_restore_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "scope": _RESTORE_JWT_SCOPE,
        "exp": int(
            (
                datetime.now(timezone.utc)
                + timedelta(days=RESTORE_TOKEN_TTL_DAYS)
            ).timestamp()
        ),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_restore_token(token: str) -> dict:
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Lien de restauration expiré (30 jours max).")
    except jwt.InvalidTokenError as e:
        raise HTTPException(400, f"Lien de restauration invalide : {e}")
    if claims.get("scope") != _RESTORE_JWT_SCOPE:
        raise HTTPException(400, "Lien de restauration invalide (scope).")
    if not claims.get("sub"):
        raise HTTPException(400, "Lien de restauration incomplet.")
    return claims


# ─────────────────────────────────────────────────────────────────────
# Emails
# ─────────────────────────────────────────────────────────────────────
def _build_restore_url(token: str) -> str:
    base = _link_base_url()
    if not base:
        base = os.getenv(
            "PUBLIC_BACKEND_URL", ""
        ).rstrip("/")
    if not base:
        return f"/api/account/restore?token={token}"
    return f"{base}/api/account/restore?token={token}"


def _send_admin_notification(
    *,
    email: str,
    reason: str,
    custom_text: Optional[str],
    plan: str,
    days_since_signup: int,
    chantier_count: int,
    role: Optional[str],
) -> None:
    reason_label = REASON_LABELS.get(reason, reason)
    subject = f"[MesureChâssis] Suppression compte — {reason_label}"
    body_lines = [
        "🚨 Un utilisateur vient de supprimer son compte MesureChâssis.",
        "",
        f"• Email       : {email}",
        f"• Rôle        : {role or '—'}",
        f"• Plan        : {plan}",
        f"• Ancienneté  : {days_since_signup} jour(s)",
        f"• Chantiers   : {chantier_count}",
        f"• Raison      : {reason_label}",
    ]
    if reason == "other" and custom_text:
        body_lines += ["", "📝 Message libre :", custom_text]
    body_lines += [
        "",
        "Le compte passe en pending_deletion pendant 30 jours "
        "(grace period RGPD) avant hard-delete définitif.",
    ]
    try:
        send_email(
            to=ADMIN_NOTIFY_EMAIL,
            subject=subject,
            body="\n".join(body_lines),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Notif admin exit-survey KO : %s", e)


def _send_user_restoration_email(
    *, email: str, name: str, restore_url: str
) -> None:
    body = (
        f"Bonjour {name or ''},\n\n"
        "Nous confirmons la suppression de votre compte MesureChâssis.\n\n"
        f"⏳ Grace Period : vous avez {GRACE_PERIOD_DAYS} jours pour changer "
        "d'avis. Après cette période, vos données seront définitivement "
        "supprimées (conformément au RGPD).\n\n"
        "Si vous souhaitez restaurer votre compte, cliquez sur le lien "
        "ci-dessous :\n\n"
        f"   {restore_url}\n\n"
        "Ce lien est unique et valable 30 jours.\n\n"
        "Merci d'avoir utilisé MesureChâssis. Vos retours nous aident à "
        "améliorer l'application pour les autres artisans.\n\n"
        "L'équipe MesureChâssis"
    )
    html = (
        "<div style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;"
        "max-width:560px;margin:0 auto;padding:24px;background:#ffffff;'>"
        "<div style='border-bottom:2px solid #f59e0b;padding-bottom:12px;margin-bottom:20px;'>"
        "<h1 style='font-size:18px;margin:0;color:#111827;letter-spacing:0.4px;'>"
        "MesureChâssis — Compte supprimé</h1></div>"
        f"<p style='font-size:14px;color:#1f2937;line-height:1.55;margin:0 0 16px;'>"
        f"Bonjour {name or ''},</p>"
        "<p style='font-size:14px;color:#1f2937;line-height:1.55;margin:0 0 16px;'>"
        "Nous confirmons la suppression de votre compte MesureChâssis.</p>"
        f"<div style='background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;"
        "padding:16px;margin:20px 0;'>"
        "<div style='font-size:12px;color:#92400e;font-weight:700;margin-bottom:6px;'>"
        f"⏳ GRACE PERIOD — {GRACE_PERIOD_DAYS} JOURS</div>"
        "<div style='font-size:13px;color:#78350f;line-height:1.5;'>"
        f"Vous avez {GRACE_PERIOD_DAYS} jours pour changer d'avis. Après cette "
        "période, vos données seront définitivement supprimées (RGPD).</div>"
        "</div>"
        "<div style='text-align:center;margin:24px 0;'>"
        f"<a href='{restore_url}' style='display:inline-block;background:#22c55e;"
        "color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;"
        "font-weight:700;font-size:14px;'>✅ Restaurer mon compte</a></div>"
        "<p style='font-size:12px;color:#6b7280;line-height:1.5;margin:16px 0 0;'>"
        "Ce lien est unique et valable 30 jours.</p>"
        "<div style='margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;"
        "font-size:11px;color:#9ca3af;text-align:center;'>"
        "MesureChâssis — Prise de mesures pour menuiseries professionnelles"
        "</div></div>"
    )
    try:
        send_email(
            to=email,
            subject=(
                "Compte MesureChâssis supprimé — vous avez 30 jours pour "
                "changer d'avis"
            ),
            body=body,
            html=html,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Email user restoration KO : %s", e)


# ─────────────────────────────────────────────────────────────────────
# Endpoint 1 — Delete with Survey
# ─────────────────────────────────────────────────────────────────────
@router.post("/account/delete-with-survey")
async def delete_with_survey(
    payload: DeleteWithSurveyRequest,
    user=Depends(auth_user),
):
    """Nouveau flux de suppression avec questionnaire + grace period 30j."""
    reason = (payload.reason or "").strip()
    if reason not in REASON_LABELS:
        raise HTTPException(400, "Raison invalide.")
    custom_text = (payload.custom_text or "").strip() or None
    if reason == "other" and not custom_text:
        raise HTTPException(
            400, "Veuillez préciser votre raison dans le champ texte."
        )

    user_doc = await db.users.find_one({"id": user["id"]})
    if not user_doc:
        raise HTTPException(404, "Utilisateur introuvable.")
    if not user_doc.get("hashed_password"):
        raise HTTPException(400, "Mot de passe incorrect.")
    if not verify_password(payload.password, user_doc["hashed_password"]):
        raise HTTPException(400, "Mot de passe incorrect.")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    hard_delete_at = now + timedelta(days=GRACE_PERIOD_DAYS)

    # Ancienneté du compte
    created_at_str = user_doc.get("created_at") or now_iso
    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        days_since_signup = max(0, int((now - created_at).total_seconds() // 86400))
    except Exception:
        days_since_signup = 0

    # Nb chantiers
    try:
        chantier_count = await db.chantiers.count_documents(
            {"created_by": user["id"]}
        )
    except Exception:
        chantier_count = 0

    # Plan actuel via company
    plan = "trial"
    try:
        company = await db.companies.find_one(
            {"company_id": user_doc.get("company_id", "default")},
            {"_id": 0, "plan": 1, "subscription_status": 1},
        )
        if company:
            plan = company.get("plan") or company.get("subscription_status") or "trial"
    except Exception:
        pass

    survey_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": user_doc.get("email"),
        "role": user_doc.get("role"),
        "reason": reason,
        "reason_label": REASON_LABELS[reason],
        "custom_text": custom_text,
        "plan_at_deletion": plan,
        "days_since_signup": days_since_signup,
        "chantier_count": chantier_count,
        "deletion_requested_at": now_iso,
        "hard_delete_scheduled_at": hard_delete_at.isoformat(),
        "restored_at": None,
        "hard_deleted_at": None,
    }
    await db.account_deletion_surveys.insert_one(survey_doc)

    # Mise à jour user → pending_deletion (on conserve le hash pour restore)
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "status": "pending_deletion",
                "pending_deletion_since": now_iso,
                "pending_deletion_until": hard_delete_at.isoformat(),
                "push_tokens": [],
            }
        },
    )

    # Email admin (Michel)
    _send_admin_notification(
        email=user_doc.get("email"),
        reason=reason,
        custom_text=custom_text,
        plan=plan,
        days_since_signup=days_since_signup,
        chantier_count=chantier_count,
        role=user_doc.get("role"),
    )

    # Email utilisateur avec lien de restauration
    token = _make_restore_token(user["id"], user_doc.get("email") or "")
    restore_url = _build_restore_url(token)
    _send_user_restoration_email(
        email=user_doc.get("email") or "",
        name=user_doc.get("name") or "",
        restore_url=restore_url,
    )

    return {
        "ok": True,
        "grace_period_days": GRACE_PERIOD_DAYS,
        "hard_delete_scheduled_at": hard_delete_at.isoformat(),
        "message": (
            "Compte supprimé. Vous avez 30 jours pour changer d'avis. "
            "Un email de restauration vient de vous être envoyé."
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# Endpoint 2 — Restore Account (public, via lien email)
# ─────────────────────────────────────────────────────────────────────
def _html_response(*, title: str, body: str, accent: str = "#22c55e") -> str:
    return f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — MesureChâssis</title>
<style>
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a; color: #f5f5f5;
    min-height: 100vh; display: flex; justify-content: center;
    padding: 32px 20px;
  }}
  .wrap {{ max-width: 480px; width: 100%; text-align: center; }}
  .card {{
    background: #171717; border: 2px solid {accent};
    border-radius: 20px; padding: 32px 24px; margin-top: 40px;
  }}
  .emoji {{ font-size: 56px; margin-bottom: 12px; }}
  h1 {{ font-size: 22px; margin: 0 0 16px; color: {accent}; }}
  p {{ font-size: 15px; line-height: 1.6; color: #d4d4d4; margin: 10px 0; }}
  .btn {{
    display: inline-block; margin-top: 24px; padding: 14px 26px;
    background: #FF5A00; color: #fff; text-decoration: none;
    border-radius: 26px; font-weight: 800; font-size: 14px;
    letter-spacing: 0.5px;
  }}
</style></head>
<body><div class="wrap"><div class="card">{body}</div></div></body></html>"""


@router.get("/account/restore", response_class=HTMLResponse)
async def restore_account(token: str = Query(..., min_length=10)):
    """Restaure un compte en pending_deletion via lien email signé."""
    claims = _decode_restore_token(token)
    user_id = claims["sub"]

    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        return HTMLResponse(
            _html_response(
                title="Compte introuvable",
                accent="#ef4444",
                body=(
                    "<div class='emoji'>❌</div>"
                    "<h1>COMPTE INTROUVABLE</h1>"
                    "<p>Ce compte n'existe plus. Le hard-delete de 30 jours "
                    "est peut-être déjà passé.</p>"
                ),
            ),
            status_code=404,
        )

    status = user_doc.get("status") or "active"
    if status == "deleted":
        return HTMLResponse(
            _html_response(
                title="Compte définitivement supprimé",
                accent="#ef4444",
                body=(
                    "<div class='emoji'>🗑️</div>"
                    "<h1>DÉLAI DÉPASSÉ</h1>"
                    "<p>Ce compte a été définitivement supprimé et ne peut "
                    "plus être restauré. Vous pouvez créer un nouveau compte.</p>"
                ),
            ),
            status_code=410,
        )

    if status != "pending_deletion":
        # Déjà actif — idempotence
        return HTMLResponse(
            _html_response(
                title="Compte déjà actif",
                body=(
                    "<div class='emoji'>ℹ️</div>"
                    "<h1>COMPTE DÉJÀ ACTIF</h1>"
                    "<p>Votre compte est déjà actif. Vous pouvez vous "
                    "connecter normalement depuis l'application.</p>"
                ),
            )
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {"status": "active", "restored_at": now_iso},
            "$unset": {
                "pending_deletion_since": "",
                "pending_deletion_until": "",
            },
        },
    )
    # Log dans l'exit survey
    await db.account_deletion_surveys.update_one(
        {"user_id": user_id, "restored_at": None, "hard_deleted_at": None},
        {"$set": {"restored_at": now_iso}},
    )

    return HTMLResponse(
        _html_response(
            title="Compte restauré",
            body=(
                "<div class='emoji'>✅</div>"
                "<h1>COMPTE RESTAURÉ</h1>"
                "<p>Excellent ! Votre compte a été restauré avec succès. "
                "Vous pouvez à nouveau vous connecter dans l'application "
                "MesureChâssis.</p>"
                "<p style='color:#9E9EA5;font-size:12px;margin-top:16px;'>"
                "Toutes vos données (chantiers, mesures, documents) sont "
                "intactes.</p>"
            ),
        )
    )


# ─────────────────────────────────────────────────────────────────────
# Cron — Hard delete after grace period
# ─────────────────────────────────────────────────────────────────────
async def hard_delete_expired_pending_accounts() -> dict:
    """Exécute un hard-delete définitif des comptes en pending_deletion
    dont le délai de 30 jours est écoulé.
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    # Trouve les users à hard-delete
    cursor = db.users.find(
        {
            "status": "pending_deletion",
            "pending_deletion_until": {"$lte": now_iso},
        },
        {"_id": 0, "id": 1, "email": 1, "company_id": 1},
    )
    users_to_delete = await cursor.to_list(length=1000)
    processed = 0
    for u in users_to_delete:
        user_id = u.get("id")
        if not user_id:
            continue
        original_email = u.get("email") or ""
        try:
            # Anonymisation
            new_email = f"deleted_{uuid.uuid4().hex[:12]}@deleted.invalid"
            original_email_hash = hashlib.sha256(
                original_email.strip().lower().encode("utf-8")
            ).hexdigest()
            await db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "status": "deleted",
                        "deleted_at": now_iso,
                        "email": new_email,
                        "hashed_password": "",
                        "push_tokens": [],
                        "original_email_hash": original_email_hash,
                    },
                    "$unset": {
                        "pending_deletion_since": "",
                        "pending_deletion_until": "",
                    },
                },
            )
            await db.account_deletion_surveys.update_one(
                {
                    "user_id": user_id,
                    "restored_at": None,
                    "hard_deleted_at": None,
                },
                {"$set": {"hard_deleted_at": now_iso}},
            )
            processed += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Hard-delete KO user_id=%s : %s", user_id, e
            )
    return {"processed": processed, "checked": len(users_to_delete)}


# ─────────────────────────────────────────────────────────────────────
# Cron loop — s'exécute toutes les 6h
# ─────────────────────────────────────────────────────────────────────
async def hard_delete_loop() -> None:
    """Boucle background : purge des comptes en pending_deletion expirés."""
    import asyncio

    logger.info("🗑️ hard_delete_loop démarré (check toutes les 6h)")
    while True:
        try:
            res = await hard_delete_expired_pending_accounts()
            if res.get("processed", 0) > 0:
                logger.info(
                    "hard_delete: %d comptes purgés (checked=%d)",
                    res["processed"], res["checked"],
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("hard_delete_loop erreur : %s", e)
        await asyncio.sleep(6 * 3600)  # 6h


# ─────────────────────────────────────────────────────────────────────
# Admin — Dashboard HTML des exit surveys
# ─────────────────────────────────────────────────────────────────────
def _check_admin_token(token: str) -> None:
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré")
    if token != expected:
        raise HTTPException(401, "Token admin invalide")


@router.get("/admin/exit-surveys", response_class=HTMLResponse)
async def admin_exit_surveys(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    limit: int = Query(100, ge=1, le=500),
):
    """Dashboard admin HTML pour consulter les exit surveys."""
    _check_admin_token(token)

    cursor = (
        db.account_deletion_surveys.find({})
        .sort("deletion_requested_at", -1)
        .limit(limit)
    )
    surveys = await cursor.to_list(length=limit)
    total = await db.account_deletion_surveys.count_documents({})
    pending_delete = await db.users.count_documents(
        {"status": "pending_deletion"}
    )
    hard_deleted = await db.account_deletion_surveys.count_documents(
        {"hard_deleted_at": {"$ne": None}}
    )
    restored = await db.account_deletion_surveys.count_documents(
        {"restored_at": {"$ne": None}}
    )

    # Répartition par raison
    reason_counts = {}
    for s in surveys:
        r = s.get("reason_label") or s.get("reason") or "?"
        reason_counts[r] = reason_counts.get(r, 0) + 1

    reason_rows = "".join(
        f'<div class="reason-row">'
        f'<span class="reason-label">{r}</span>'
        f'<span class="reason-count">{c}</span></div>'
        for r, c in sorted(reason_counts.items(), key=lambda x: -x[1])
    )

    def _fmt_date(iso: Optional[str]) -> str:
        if not iso:
            return "—"
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return iso

    def _status_badge(s: dict) -> str:
        if s.get("hard_deleted_at"):
            return '<span class="badge badge-hard">🗑️ Hard-deleted</span>'
        if s.get("restored_at"):
            return '<span class="badge badge-restored">✅ Restauré</span>'
        return '<span class="badge badge-pending">⏳ Pending 30j</span>'

    rows = "".join(
        f'<tr>'
        f'<td>{_fmt_date(s.get("deletion_requested_at"))}</td>'
        f'<td>{s.get("email") or "—"}</td>'
        f'<td>{s.get("role") or "—"}</td>'
        f'<td>{s.get("plan_at_deletion") or "—"}</td>'
        f'<td class="reason-cell">{s.get("reason_label") or s.get("reason") or "?"}'
        f'{"<div class=custom>" + (s.get("custom_text") or "") + "</div>" if s.get("custom_text") else ""}'
        f'</td>'
        f'<td class="tc">{s.get("days_since_signup", 0)}j</td>'
        f'<td class="tc">{s.get("chantier_count", 0)}</td>'
        f'<td>{_status_badge(s)}</td>'
        f'</tr>'
        for s in surveys
    )

    html = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exit Surveys — Admin MesureChâssis</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0a0a0a; color: #f5f5f5; padding: 20px 16px;
  }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 20px; color: #FF5A00; letter-spacing: 0.3px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin-bottom: 24px; }}
  .stat {{ background: #171717; border: 1px solid #2a2a30; border-radius: 12px;
    padding: 16px; }}
  .stat-value {{ font-size: 28px; font-weight: 900; color: #FF5A00; }}
  .stat-label {{ font-size: 11px; color: #9E9EA5; text-transform: uppercase;
    letter-spacing: 0.5px; margin-top: 4px; }}
  .section {{ background: #171717; border: 1px solid #2a2a30; border-radius: 14px;
    padding: 20px; margin-bottom: 20px; }}
  .section h2 {{ font-size: 15px; margin: 0 0 14px; color: #d4d4d4;
    text-transform: uppercase; letter-spacing: 0.6px; }}
  .reason-row {{ display: flex; justify-content: space-between; padding: 8px 0;
    border-bottom: 1px solid #262626; font-size: 13.5px; }}
  .reason-row:last-child {{ border: none; }}
  .reason-count {{ color: #FF5A00; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #262626;
    vertical-align: top; }}
  th {{ background: #0e0e0e; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.5px; color: #9E9EA5; }}
  .tc {{ text-align: center; }}
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 8px;
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.3px; }}
  .badge-hard {{ background: #4a1d1d; color: #fca5a5; }}
  .badge-restored {{ background: #164e35; color: #86efac; }}
  .badge-pending {{ background: #451a03; color: #fbbf24; }}
  .reason-cell {{ max-width: 300px; }}
  .custom {{ font-size: 11.5px; color: #9E9EA5; margin-top: 4px; font-style: italic;
    padding: 6px 8px; background: #0e0e0e; border-left: 2px solid #FF5A00;
    border-radius: 4px; }}
  .empty {{ text-align: center; color: #9E9EA5; padding: 40px 0; }}
</style></head>
<body><div class="wrap">
  <h1>📊 EXIT SURVEYS — MesureChâssis</h1>
  <div class="stats">
    <div class="stat">
      <div class="stat-value">{total}</div>
      <div class="stat-label">Total suppressions</div>
    </div>
    <div class="stat">
      <div class="stat-value">{pending_delete}</div>
      <div class="stat-label">En grâce (30j)</div>
    </div>
    <div class="stat">
      <div class="stat-value">{restored}</div>
      <div class="stat-label">Restaurés ✅</div>
    </div>
    <div class="stat">
      <div class="stat-value">{hard_deleted}</div>
      <div class="stat-label">Hard-deleted 🗑️</div>
    </div>
  </div>

  <div class="section">
    <h2>📈 Répartition par raison</h2>
    {reason_rows or '<div class="empty">Aucune suppression enregistrée</div>'}
  </div>

  <div class="section">
    <h2>📋 Détails ({len(surveys)} sur {total})</h2>
    <table>
      <thead><tr>
        <th>Date</th><th>Email</th><th>Rôle</th><th>Plan</th>
        <th>Raison</th><th>Âge</th><th>Chantiers</th><th>Statut</th>
      </tr></thead>
      <tbody>{rows or '<tr><td colspan="8" class="empty">Aucune suppression</td></tr>'}</tbody>
    </table>
  </div>
</div></body></html>"""
    return HTMLResponse(html)
