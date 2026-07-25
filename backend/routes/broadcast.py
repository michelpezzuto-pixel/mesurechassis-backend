"""
Endpoints admin pour envoyer des broadcasts email aux utilisateurs réels
(exclut les comptes techniques : pytest_*, @example.com, owners plateforme).

Cas d'usage :
1. Notifier la sortie d'une nouvelle version App Store/Play Store
   POST /api/admin/users/notify-new-version
2. Notifier les Google/Apple users existants d'une nouvelle exigence TVA
   POST /api/admin/users/notify-vat-requirement

Protégés par PLATFORM_ADMIN_TOKEN. Idempotent via tracking
(`broadcast_flags` sur user : ex. `notified_v_1_0_35`, `notified_vat_lock_2026_07`).

Cadence Resend : max 100 emails/heure (self-throttle via asyncio.sleep).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db import db
from email_service import send_email

log = logging.getLogger("mesurechassis.broadcast")

router = APIRouter(prefix="/admin/users", tags=["admin-broadcast"])


# ─────────────────────────────────────────────────────────────────
# Auth admin (identique à admin_tools.py — accepte token statique ou JWT)
# ─────────────────────────────────────────────────────────────────
def _check_admin_token(token: str) -> None:
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré")
    if token == expected:
        return
    try:
        import jwt as _jwt
        claims = _jwt.decode(token, expected, algorithms=["HS256"], leeway=10)
        if claims.get("scope") in ("admin_map", "admin_marketing"):
            return
    except Exception:
        pass
    raise HTTPException(401, "Token admin invalide")


# ─────────────────────────────────────────────────────────────────
# Détection comptes techniques (importé depuis admin_tools)
# ─────────────────────────────────────────────────────────────────
def _is_technical_account(email: str) -> bool:
    try:
        from routes.admin_tools import _is_technical_account as _fn
        return _fn(email)
    except Exception:
        # Fallback minimal
        el = (email or "").lower()
        return (
            not el
            or "@example.com" in el
            or el.startswith("pytest_")
            or el.startswith("test_")
        )


# ─────────────────────────────────────────────────────────────────
# 1. Notification nouvelle version app
# ─────────────────────────────────────────────────────────────────
class NotifyVersionIn(BaseModel):
    latest_version: str = Field(..., description="ex: 1.0.35")
    highlights: list[str] = Field(
        default_factory=list,
        description="Liste courte des nouveautés (max 5 bullets)",
    )
    app_store_url: str = Field(
        default="https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930",
    )
    play_store_url: Optional[str] = None
    dry_run: bool = False
    only_email_domain: Optional[str] = Field(
        default=None,
        description="Restreint à un domaine (ex: 'sambre-menuiserie.be')",
    )


def _tpl_new_version(email: str, name: str, ver: str, highlights: list[str],
                     ios_url: str, android_url: Optional[str]) -> tuple[str, str, str]:
    hi = highlights[:5]
    hi_html = "".join(
        f'<li style="margin:6px 0">✨ {h}</li>' for h in hi
    ) if hi else '<li style="margin:6px 0">✨ Améliorations & correctifs</li>'
    hi_text = "\n".join(f"- {h}" for h in hi) if hi else "- Améliorations & correctifs"

    android_line_html = (
        f'<p style="text-align:center;margin:6px 0;font-size:13px;color:#6c6c70;">'
        f'Android : <a href="{android_url}" style="color:#003580">Play Store</a></p>'
        if android_url else ""
    )
    android_line_txt = f"\nAndroid : {android_url}" if android_url else ""

    subject = f"🚀 MesureChâssis v{ver} disponible"
    text = (
        f"Salut {name} !\n\n"
        f"La version {ver} de MesureChâssis vient de sortir sur l'App Store.\n\n"
        f"Nouveautés :\n{hi_text}\n\n"
        f"Mets à jour depuis l'App Store en 1 tap :\n{ios_url}"
        f"{android_line_txt}\n\n"
        f"Michel — Fondateur"
    )
    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#f5f5f7;margin:0;padding:24px;color:#1c1c1e;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
              padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
              color:#00C853;font-weight:700;margin:0 0 10px;">
      MesureChâssis · Update
    </p>
    <h1 style="margin:0 0 12px;font-size:22px;line-height:1.25;">
      🚀 Version {ver} disponible
    </h1>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Salut {name}, la nouvelle version de MesureChâssis vient de sortir.
      Voici ce qu'elle apporte :
    </p>
    <ul style="font-size:14.5px;line-height:1.55;color:#2c2c2e;
               background:#F0FBF3;border-left:4px solid #00C853;
               padding:14px 18px 14px 34px;border-radius:6px;margin:0 0 20px;">
      {hi_html}
    </ul>
    <p style="text-align:center;margin:24px 0 8px;">
      <a href="{ios_url}"
         style="display:inline-block;background:#00C853;color:#001B44;
                text-decoration:none;padding:14px 28px;border-radius:10px;
                font-weight:700;font-size:15px;">
        Mettre à jour depuis l'App Store →
      </a>
    </p>
    {android_line_html}
    <hr style="border:none;border-top:1px solid #e5e5ea;margin:32px 0 16px;">
    <p style="font-size:12px;color:#8e8e93;margin:0;line-height:1.5;">
      Michel · Fondateur MesureChâssis<br>
      Réponds directement à ce mail si tu as la moindre question.
    </p>
  </div>
</body></html>"""
    return subject, text, html


@router.post("/notify-new-version")
async def notify_new_version(
    payload: NotifyVersionIn,
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
):
    """
    Envoie un email Resend à TOUS les utilisateurs réels pour annoncer
    une nouvelle version. Idempotent via le flag
    `broadcast_flags.notified_v_<version>` posé sur chaque user.
    """
    _check_admin_token(token)

    ver_key = f"notified_v_{payload.latest_version.replace('.', '_')}"
    flag_key = f"broadcast_flags.{ver_key}"
    now = datetime.now(timezone.utc)

    query = {
        "email": {"$exists": True, "$ne": None},
        "status": {"$ne": "suspended"},
        flag_key: {"$ne": True},
    }
    if payload.only_email_domain:
        query["email"] = {"$regex": f"@{payload.only_email_domain}$", "$options": "i"}

    cursor = db.users.find(query, {"email": 1, "name": 1, "id": 1, "created_at": 1})

    sent, skipped_tech, skipped_err, dry_targets = 0, 0, 0, []

    async for u in cursor:
        email = (u.get("email") or "").strip()
        name = u.get("name") or "collègue"
        if not email or _is_technical_account(email):
            skipped_tech += 1
            continue

        if payload.dry_run:
            dry_targets.append(email)
            continue

        try:
            subject, text, html = _tpl_new_version(
                email, name, payload.latest_version, payload.highlights,
                payload.app_store_url, payload.play_store_url,
            )
            result = send_email(to=email, subject=subject, body=text, html=html)
            delivered = bool(result.get("delivered"))
            await db.users.update_one(
                {"id": u["id"]},
                {"$set": {
                    flag_key: True,
                    f"broadcast_flags.{ver_key}_at": now,
                    f"broadcast_flags.{ver_key}_delivered": delivered,
                }},
            )
            sent += 1
            # Self-throttle Resend : max 10/sec
            await asyncio.sleep(0.12)
        except Exception as exc:  # noqa: BLE001
            log.exception("notify_new_version failed for %s: %s", email, exc)
            skipped_err += 1

    return {
        "ok": True,
        "dry_run": payload.dry_run,
        "version": payload.latest_version,
        "sent": sent,
        "skipped_technical": skipped_tech,
        "skipped_errors": skipped_err,
        "dry_targets_preview": dry_targets[:20] if payload.dry_run else [],
        "dry_total": len(dry_targets) if payload.dry_run else None,
    }


# ─────────────────────────────────────────────────────────────────
# 2. Notification "nouvelle exigence TVA" (Google/Apple users grandfathered)
# ─────────────────────────────────────────────────────────────────
class NotifyVatIn(BaseModel):
    dry_run: bool = False


def _tpl_vat_requirement(email: str, name: str) -> tuple[str, str, str]:
    subject = "🍎 Nouvelle exigence Apple — 30 secondes pour continuer"
    text = (
        f"Salut {name},\n\n"
        "Une nouvelle règle Apple (3.1.3(c)) impose désormais à toutes les "
        "apps B2B de vérifier que chaque utilisateur est un pro UE.\n\n"
        "Concrètement, la prochaine fois que tu ouvres MesureChâssis, tu "
        "auras un écran te demandant :\n"
        "1. Ton identifiant pro (TVA, SIREN, SIRET ou BCE — au choix)\n"
        "2. Le nom de ta société\n\n"
        "Ça prend 30 secondes et c'est demandé UNE SEULE FOIS. Après tu "
        "n'y penses plus.\n\n"
        "Désolé pour la contrainte, elle vient d'Apple pas de nous. Si tu "
        "as un souci pour renseigner ces infos (auto-entrepreneur, "
        "franchise TVA…), réponds à ce mail et je t'aide directement.\n\n"
        "Michel — Fondateur"
    )
    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#f5f5f7;margin:0;padding:24px;color:#1c1c1e;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
              padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
              color:#00C853;font-weight:700;margin:0 0 10px;">
      MesureChâssis · Info importante
    </p>
    <h1 style="margin:0 0 12px;font-size:22px;line-height:1.25;">
      🍎 Nouvelle exigence Apple
    </h1>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Salut {name},
    </p>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Une <strong>nouvelle règle Apple (3.1.3(c))</strong> impose désormais
      à toutes les apps B2B de vérifier que chaque utilisateur est un
      professionnel UE.
    </p>
    <div style="background:#F0FBF3;border-left:4px solid #00C853;
                padding:14px 18px;border-radius:6px;margin:16px 0;
                font-size:14.5px;color:#2c2c2e;line-height:1.6;">
      Concrètement, à ta prochaine ouverture de MesureChâssis :<br>
      <strong>1.</strong> Ton identifiant pro (TVA, SIREN, SIRET ou BCE)<br>
      <strong>2.</strong> Le nom de ta société<br><br>
      <em style="color:#008C3A;">
        30 secondes, une seule fois, jamais redemandé ensuite.
      </em>
    </div>
    <p style="font-size:14px;line-height:1.55;margin:0 0 14px;color:#6c6c70;">
      Désolé pour la contrainte, elle vient d'Apple, pas de nous 🙏
      Si tu as un souci (auto-entrepreneur, franchise TVA…),
      <strong>réponds simplement à ce mail</strong> et je t'aide directement.
    </p>
    <hr style="border:none;border-top:1px solid #e5e5ea;margin:32px 0 16px;">
    <p style="font-size:12px;color:#8e8e93;margin:0;line-height:1.5;">
      Michel · Fondateur MesureChâssis
    </p>
  </div>
</body></html>"""
    return subject, text, html


@router.post("/notify-vat-requirement")
async def notify_vat_requirement(
    payload: NotifyVatIn,
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
):
    """
    Cible les users existants (créés avant 15 juillet 2026) dont la
    company n'a PAS encore de vat_number ni de business_id_value.
    Envoie un email préventif "nouvelle exigence Apple".
    """
    _check_admin_token(token)

    _CUTOFF = datetime.fromisoformat("2026-07-15T00:00:00+00:00")
    flag_key = "broadcast_flags.notified_vat_lock_2026_07"
    now = datetime.now(timezone.utc)

    # 1. Récupère les company_id sans vat_number ni business_id
    company_ids_no_vat = set()
    async for c in db.companies.find(
        {},
        {"company_id": 1, "vat_number": 1, "business_id_value": 1},
    ):
        vat = (c.get("vat_number") or "").strip()
        biz = (c.get("business_id_value") or "").strip()
        if not vat and not biz:
            company_ids_no_vat.add(c.get("company_id"))

    if not company_ids_no_vat:
        return {"ok": True, "sent": 0, "message": "Toutes les sociétés ont un ID pro."}

    # 2. Users éligibles
    query = {
        "company_id": {"$in": list(company_ids_no_vat)},
        "status": {"$ne": "suspended"},
        flag_key: {"$ne": True},
    }

    cursor = db.users.find(query, {"email": 1, "name": 1, "id": 1, "created_at": 1})

    sent, skipped_tech, skipped_recent, skipped_err = 0, 0, 0, 0
    dry_targets: list[str] = []

    async for u in cursor:
        email = (u.get("email") or "").strip()
        name = u.get("name") or "collègue"
        if not email or _is_technical_account(email):
            skipped_tech += 1
            continue

        # Grandfathered uniquement (créé avant cutoff)
        ca = u.get("created_at")
        if isinstance(ca, str):
            try:
                ca = datetime.fromisoformat(ca.replace("Z", "+00:00"))
            except Exception:
                ca = None
        if not ca or ca >= _CUTOFF:
            skipped_recent += 1
            continue

        if payload.dry_run:
            dry_targets.append(email)
            continue

        try:
            subject, text, html = _tpl_vat_requirement(email, name)
            result = send_email(to=email, subject=subject, body=text, html=html)
            delivered = bool(result.get("delivered"))
            await db.users.update_one(
                {"id": u["id"]},
                {"$set": {
                    flag_key: True,
                    "broadcast_flags.notified_vat_lock_2026_07_at": now,
                    "broadcast_flags.notified_vat_lock_2026_07_delivered": delivered,
                }},
            )
            sent += 1
            await asyncio.sleep(0.12)
        except Exception as exc:  # noqa: BLE001
            log.exception("notify_vat_requirement failed for %s: %s", email, exc)
            skipped_err += 1

    return {
        "ok": True,
        "dry_run": payload.dry_run,
        "sent": sent,
        "skipped_technical": skipped_tech,
        "skipped_recent_accounts": skipped_recent,
        "skipped_errors": skipped_err,
        "dry_targets_preview": dry_targets[:20] if payload.dry_run else [],
        "dry_total": len(dry_targets) if payload.dry_run else None,
    }


# ─────────────────────────────────────────────────────────────────
# 3. Preview des templates (aperçu HTML)
# ─────────────────────────────────────────────────────────────────
@router.get("/broadcast-preview/{kind}")
async def broadcast_preview(
    kind: str,
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    version: str = Query("1.0.35"),
    highlights: str = Query(
        "Correction de bugs mineurs|Amélioration des exports PDF|Formulaire TVA plus rapide",
        description="Pipe-separated highlights (uniquement pour kind=new-version)",
    ),
    email: str = Query("demo@mesurechassis.com"),
    name: str = Query("Loïc"),
):
    """Aperçu HTML des templates broadcast."""
    _check_admin_token(token)
    from fastapi.responses import HTMLResponse
    if kind == "new-version":
        hl = [h.strip() for h in highlights.split("|") if h.strip()]
        subject, _, html = _tpl_new_version(
            email, name, version, hl,
            "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930",
            None,
        )
    elif kind == "vat-requirement":
        subject, _, html = _tpl_vat_requirement(email, name)
    else:
        raise HTTPException(400, "kind doit être 'new-version' ou 'vat-requirement'")
    return HTMLResponse(f"<!-- Subject: {subject} -->\n{html}")


# ─────────────────────────────────────────────────────────────────
# 4. Statistiques broadcast
# ─────────────────────────────────────────────────────────────────
@router.get("/broadcast-stats")
async def broadcast_stats(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
):
    """Statistiques des broadcasts effectués."""
    _check_admin_token(token)

    # Compte par flag
    pipeline = [
        {"$match": {"broadcast_flags": {"$exists": True}}},
        {"$project": {"broadcast_flags": 1, "_id": 0}},
    ]
    flag_counts: dict[str, int] = {}
    async for doc in db.users.aggregate(pipeline):
        flags = doc.get("broadcast_flags", {}) or {}
        for k, v in flags.items():
            if v is True:
                flag_counts[k] = flag_counts.get(k, 0) + 1

    # Users réels totaux (approximation via _is_technical_account)
    real_users = 0
    async for u in db.users.find({}, {"email": 1}):
        if not _is_technical_account(u.get("email", "")):
            real_users += 1

    return {
        "real_users_total": real_users,
        "broadcast_counts": flag_counts,
    }
