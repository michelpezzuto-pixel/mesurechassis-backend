"""
Séquence email automatisée pour les inscrits newsletter mesurechassis.com.

5 emails progressifs :
  J0  → Welcome + guide PDF (envoyé instantanément par /newsletter/subscribe)
  J3  → Astuce "mesurer un trapèze en 30 s" (quick win)
  J7  → Étude de cas Sambre Menuiserie (preuve sociale)
  J14 → Le hack TVA que 80 % des artisans ignorent (curiosité)
  J30 → Offre exclusive : 30 jours d'essai gratuits (conversion)

Déclenchement CRON :
  L'endpoint POST /api/admin/newsletter/run-sequence est protégé par
  PLATFORM_ADMIN_TOKEN et doit être appelé 1× par jour (via Railway Cron
  ou GitHub Action). Idempotent (basé sur `sequence_step`).

Format de la collection `newsletter_subscribers` :
  {
    "email": "artisan@example.com",
    "created_at": <datetime>,
    "sequence_step": 0..4,
    "unsubscribed": bool,
    "source": "landing_hero_guide",
  }
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Callable

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import db
from email_service import send_email

log = logging.getLogger("mesurechassis.newsletter_sequence")

router = APIRouter(prefix="/admin/newsletter", tags=["admin-newsletter"])


# ─────────────────────────────────────────────────────────────────
# Templates HTML — un par jalon
# ─────────────────────────────────────────────────────────────────
def _shell(title: str, inner_html: str, cta_text: str, cta_url: str) -> str:
    """Enveloppe commune : header + contenu + CTA + footer."""
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#f5f5f7;margin:0;padding:24px;color:#1c1c1e;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;
              padding:32px;box-shadow:0 2px 12px rgba(0,0,0,.06);">
    <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
              color:#00C853;font-weight:700;margin:0 0 10px;">
      MesureChâssis · Le guide terrain
    </p>
    <h1 style="margin:0 0 16px;font-size:22px;line-height:1.25;">{title}</h1>
    {inner_html}
    <p style="text-align:center;margin:28px 0 8px;">
      <a href="{cta_url}"
         style="display:inline-block;background:#00C853;color:#001B44;
                text-decoration:none;padding:14px 28px;border-radius:10px;
                font-weight:700;font-size:15px;">{cta_text}</a>
    </p>
    <hr style="border:none;border-top:1px solid #e5e5ea;margin:32px 0 16px;">
    <p style="font-size:12px;color:#8e8e93;margin:0;line-height:1.5;">
      Michel · Fondateur MesureChâssis<br>
      Réponds à ce mail directement pour toute question.<br>
      <a href="https://www.mesurechassis.com/unsubscribe?email={{unsub_email}}"
         style="color:#8e8e93;">Se désinscrire</a>
    </p>
  </div>
</body></html>
"""


# ─── J3 : Quick win technique ─────────────────────────────────────
def _tpl_j3(email: str) -> tuple[str, str, str]:
    subject = "📐 Mesurer un trapèze en 30 s (astuce terrain)"
    body_text = (
        "Salut !\n\n"
        "Petit tip terrain : sur un trapèze, la plupart des artisans "
        "prennent 4 mesures (côté gauche, côté droit, base, sommet). "
        "En vrai, il en faut 6 pour éviter les mauvaises surprises.\n\n"
        "Les 2 mesures qu'on oublie tout le temps :\n"
        "1. La diagonale (elle révèle si le tableau est \"foireux\")\n"
        "2. L'angle du côté incliné (avec le rapporteur du téléphone)\n\n"
        "Dans l'app, ces 2 mesures sont demandées automatiquement quand "
        "tu choisis \"Trapèze\" — impossible de les zapper.\n\n"
        "À demain,\nMichel"
    )
    inner = """
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Salut ! Petit tip terrain aujourd'hui.
    </p>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Sur un trapèze, la plupart des artisans prennent
      <strong>4 mesures</strong> (côté G, côté D, base, sommet).
      <strong>En vrai il en faut 6</strong>. Les 2 oubliées :
    </p>
    <div style="background:#F0FBF3;border-left:4px solid #00C853;
                padding:14px 18px;border-radius:6px;margin:16px 0;
                font-size:14.5px;color:#2c2c2e;line-height:1.55;">
      <strong>1. La diagonale</strong> → révèle si le tableau est \"foireux\"<br>
      <strong>2. L'angle du côté incliné</strong> → avec le rapporteur du téléphone
    </div>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Dans l'app, ces 2 mesures sont demandées <strong>automatiquement</strong>
      quand tu sélectionnes \"Trapèze\" — impossible de les zapper.
      Résultat : zéro re-commande pour cause de trapèze mal dimensionné.
    </p>
    """
    html = _shell(
        title="📐 Le piège du trapèze (et comment le déjouer)",
        inner_html=inner,
        cta_text="Voir l'app en 60 s →",
        cta_url="https://www.mesurechassis.com",
    ).replace("{unsub_email}", email)
    return subject, body_text, html


# ─── J7 : Preuve sociale ──────────────────────────────────────────
def _tpl_j7(email: str) -> tuple[str, str, str]:
    subject = "🏗️ Comment Sambre Menuiserie économise 8 h/semaine"
    body_text = (
        "Salut !\n\n"
        "Loïc gère Sambre Menuiserie près de Charleroi (6 gars sur le terrain, "
        "40+ chantiers/an). Il utilise MesureChâssis depuis 4 mois.\n\n"
        "Avant : 3h par chantier pour prise de cotes + devis + PDF client.\n"
        "Après : 45 min. Soit 8h économisées par semaine sur 4 chantiers.\n\n"
        "Ce qu'il m'a dit précisément :\n"
        "\"Le PDF client sortait en 30s avec mon logo. Le client signait sur "
        "place au lieu d'attendre 3 jours mon devis. Ça a changé mon closing.\"\n\n"
        "Si tu veux tester : 30 jours gratuits, sans CB.\n\n"
        "À bientôt,\nMichel"
    )
    inner = """
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Loïc gère <strong>Sambre Menuiserie</strong> près de Charleroi
      (6 gars sur le terrain, 40+ chantiers/an).
      Il utilise MesureChâssis depuis 4 mois.
    </p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:18px 0;">
      <div style="background:#FDF2F2;border-radius:8px;padding:14px;text-align:center;">
        <div style="font-size:11px;color:#A00013;font-weight:700;text-transform:uppercase;">Avant</div>
        <div style="font-size:22px;font-weight:800;color:#1c1c1e;margin-top:4px;">3 h</div>
        <div style="font-size:12px;color:#6c6c70;">par chantier</div>
      </div>
      <div style="background:#F0FBF3;border-radius:8px;padding:14px;text-align:center;">
        <div style="font-size:11px;color:#008C3A;font-weight:700;text-transform:uppercase;">Après</div>
        <div style="font-size:22px;font-weight:800;color:#1c1c1e;margin-top:4px;">45 min</div>
        <div style="font-size:12px;color:#6c6c70;">par chantier</div>
      </div>
    </div>
    <blockquote style="border-left:4px solid #003580;padding:12px 18px;
                      margin:16px 0;background:#F5F7FA;border-radius:0 6px 6px 0;
                      font-size:14.5px;line-height:1.55;color:#3a3a3c;font-style:italic;">
      « Le PDF client sortait en 30 s avec mon logo. Le client signait sur place
      au lieu d'attendre 3 jours mon devis. Ça a changé mon closing. »<br>
      <strong style="font-style:normal;font-size:13px;color:#003580;">
        — Loïc, Sambre Menuiserie
      </strong>
    </blockquote>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      <strong>8 h économisées par semaine</strong> sur 4 chantiers.
      Sur un an, ça fait ~400 h — soit 2 mois de travail récupérés.
    </p>
    """
    html = _shell(
        title="🏗️ 8 h/semaine récupérées (étude de cas)",
        inner_html=inner,
        cta_text="Tester 30 jours gratuits →",
        cta_url="https://www.mesurechassis.com",
    ).replace("{unsub_email}", email)
    return subject, body_text, html


# ─── J14 : Curiosity gap (TVA) ────────────────────────────────────
def _tpl_j14(email: str) -> tuple[str, str, str]:
    subject = "💰 Le hack TVA que 80 % des menuisiers ignorent"
    body_text = (
        "Salut !\n\n"
        "Petite question : sur tes devis rénovation, tu factures à 21 % ou à 6 % ?\n\n"
        "En Belgique, la rénovation de logements > 10 ans peut passer à 6 % "
        "de TVA — mais uniquement si le devis mentionne la déclaration client.\n\n"
        "80 % des artisans que je croise ne le savent pas ou oublient de "
        "cocher la case dans leur devis. Résultat : ils facturent à 21 % et "
        "le client paie plus cher pour rien (ou pire, refuse le devis).\n\n"
        "Dans l'app, cette case est proposée AUTOMATIQUEMENT dès que tu marques "
        "un chantier comme \"rénovation\". Fini les oublis.\n\n"
        "Économie moyenne pour ton client : 15 % du HT. Ton devis devient "
        "hyper compétitif.\n\n"
        "À bientôt,\nMichel"
    )
    inner = """
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Petite question rapide : sur tes devis rénovation en Belgique,
      tu factures à <strong>21 %</strong> ou à <strong>6 %</strong> ?
    </p>
    <div style="background:#FFF3CD;border-left:4px solid #F5A623;
                padding:14px 18px;border-radius:6px;margin:16px 0;
                font-size:14.5px;color:#7A5C00;line-height:1.55;">
      ⚠️ <strong>La rénovation de logements de +10 ans peut passer à 6 % de TVA</strong>
      — mais uniquement si le devis mentionne la déclaration client.
    </div>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      <strong>80 % des artisans</strong> oublient de cocher la case dans leur devis.
      Résultat : ils facturent à 21 % et le client paie plus cher pour rien
      (ou pire, refuse le devis).
    </p>
    <div style="background:#F0FBF3;border-radius:8px;padding:14px 18px;
                margin:16px 0;font-size:14.5px;color:#2c2c2e;line-height:1.55;">
      💡 Dans l'app, cette case est proposée <strong>automatiquement</strong>
      dès que tu marques un chantier comme "rénovation".
      Économie moyenne pour ton client : <strong>15 % du HT</strong>.
      Ton devis devient hyper compétitif.
    </div>
    """
    html = _shell(
        title="💰 Le hack TVA que 80 % ignorent",
        inner_html=inner,
        cta_text="Voir l'app →",
        cta_url="https://www.mesurechassis.com",
    ).replace("{unsub_email}", email)
    return subject, body_text, html


# ─── J30 : Offre conversion ───────────────────────────────────────
def _tpl_j30(email: str) -> tuple[str, str, str]:
    subject = "🎁 30 jours gratuits (offre perso pour toi)"
    body_text = (
        "Salut !\n\n"
        "Ça fait un mois que tu es sur ma newsletter. Merci d'avoir tenu !\n\n"
        "Petit deal : je t'offre 30 jours d'essai complet de MesureChâssis, "
        "sans CB, sans engagement. Toutes les fonctionnalités, aucune limite.\n\n"
        "Ce que tu peux faire en 30 min chrono :\n"
        "→ Créer ton compte (Google ou email)\n"
        "→ Personnaliser ton PDF client (logo + couleurs)\n"
        "→ Faire ton premier chantier de test\n"
        "→ Générer un devis PRO en 30 s\n\n"
        "Après 30 jours, si tu veux continuer : 19 €/mois HT (moins qu'un café "
        "par jour). Sinon, tu ne fais rien, ton compte reste gratuit avec les "
        "chantiers déjà créés.\n\n"
        "Lien direct : https://www.mesurechassis.com\n\n"
        "À très vite,\nMichel"
    )
    inner = """
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Ça fait un mois que tu es sur ma newsletter. <strong>Merci d'avoir tenu !</strong>
    </p>
    <p style="font-size:15px;line-height:1.55;margin:0 0 14px;color:#3a3a3c;">
      Petit deal : je t'offre <strong>30 jours d'essai complet</strong> de
      MesureChâssis. Sans CB, sans engagement. Toutes les fonctionnalités,
      aucune limite.
    </p>
    <div style="background:#F0FBF3;border-radius:8px;padding:16px 20px;
                margin:18px 0;font-size:14.5px;color:#2c2c2e;line-height:1.7;">
      <strong style="color:#003580;font-size:15px;">Ce que tu peux faire en 30 min :</strong><br>
      → Créer ton compte (Google ou email)<br>
      → Personnaliser ton PDF client (logo + couleurs)<br>
      → Faire ton premier chantier de test<br>
      → Générer un devis PRO en 30 s
    </div>
    <p style="font-size:14px;line-height:1.55;margin:0 0 14px;color:#6c6c70;">
      Après 30 jours : <strong>19 €/mois HT</strong> (moins qu'un café/jour).
      Sinon, ton compte reste gratuit avec les chantiers déjà créés.
    </p>
    """
    html = _shell(
        title="🎁 30 jours gratuits — offre perso",
        inner_html=inner,
        cta_text="Créer mon compte gratuit →",
        cta_url="https://www.mesurechassis.com",
    ).replace("{unsub_email}", email)
    return subject, body_text, html


# ─────────────────────────────────────────────────────────────────
# Config séquence : (day_offset, target_step, template_fn)
# ─────────────────────────────────────────────────────────────────
SEQUENCE: list[tuple[int, int, Callable]] = [
    (3, 1, _tpl_j3),
    (7, 2, _tpl_j7),
    (14, 3, _tpl_j14),
    (30, 4, _tpl_j30),
]


# ─────────────────────────────────────────────────────────────────
# Auth admin (compatible token statique OU short JWT admin_map)
# ─────────────────────────────────────────────────────────────────
def _check_admin_token(token: str) -> None:
    """Autorise soit PLATFORM_ADMIN_TOKEN long-vécu, soit un short JWT
    (scope admin_map) signé avec ce token — même mécanisme que
    admin_tools._check_token."""
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré")
    if token == expected:
        return
    try:
        import jwt as _jwt
        claims = _jwt.decode(token, expected, algorithms=["HS256"], leeway=10)
        # Accepte les scopes admin_map (partagé avec Map & Traction)
        if claims.get("scope") in ("admin_map", "admin_marketing"):
            return
    except Exception:
        pass
    raise HTTPException(401, "Token admin invalide")


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────
class RunSequenceOut(BaseModel):
    ran_at: str
    dry_run: bool
    sent: dict
    errors: list
    total_subscribers: int


@router.post("/run-sequence", response_model=RunSequenceOut)
async def run_sequence(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    dry_run: bool = Query(False, description="Simule sans envoyer d'emails"),
):
    """
    CRON quotidien : envoie J3/J7/J14/J30 aux inscrits éligibles.

    À appeler 1× par jour (Railway Cron, GitHub Action, ou curl manuel) :
        curl -X POST 'https://backend/api/admin/newsletter/run-sequence?token=XXX'

    Idempotent : chaque abonné a un `sequence_step` incrémental.
    Un email n'est envoyé qu'une seule fois.
    """
    _check_admin_token(token)

    coll = db["newsletter_subscribers"]
    now = datetime.now(timezone.utc)

    total = await coll.count_documents({"unsubscribed": {"$ne": True}})
    sent_counts: dict[str, int] = {"j3": 0, "j7": 0, "j14": 0, "j30": 0}
    errors: list[dict] = []

    # Un curseur par jalon, du plus court au plus long
    for day_offset, target_step, tpl_fn in SEQUENCE:
        step_key = f"j{day_offset}"
        # Éligibles : (sequence_step < target_step) AND (created_at <= now - day_offset)
        # created_at cutoff = now - day_offset days
        from datetime import timedelta
        cutoff = now - timedelta(days=day_offset)

        cursor = coll.find({
            "unsubscribed": {"$ne": True},
            "sequence_step": {"$lt": target_step},
            "created_at": {"$lte": cutoff},
        })

        async for sub in cursor:
            email = sub.get("email")
            if not email:
                continue
            if dry_run:
                sent_counts[step_key] += 1
                continue
            try:
                subject, text, html = tpl_fn(email)
                result = send_email(
                    to=email,
                    subject=subject,
                    body=text,
                    html=html,
                )
                delivered = bool(result.get("delivered"))
                # Toujours avancer le step (même si mock/erreur — pour ne pas boucler)
                await coll.update_one(
                    {"email": email},
                    {"$set": {
                        "sequence_step": target_step,
                        f"sent_{step_key}_at": now,
                        f"sent_{step_key}_delivered": delivered,
                    }},
                )
                sent_counts[step_key] += 1
                log.info("newsletter_seq: sent %s to %s (delivered=%s)",
                         step_key, email, delivered)
            except Exception as exc:  # noqa: BLE001
                log.exception("newsletter_seq: %s failed for %s: %s",
                              step_key, email, exc)
                errors.append({"step": step_key, "email": email, "err": str(exc)})

    return RunSequenceOut(
        ran_at=now.isoformat(),
        dry_run=dry_run,
        sent=sent_counts,
        errors=errors,
        total_subscribers=total,
    )


@router.get("/preview/{step}")
async def preview_template(
    step: int,
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
    email: str = Query("demo@mesurechassis.com"),
):
    """Aperçu HTML d'un email de la séquence (pour tester le rendu)."""
    _check_admin_token(token)
    tpl_map = {3: _tpl_j3, 7: _tpl_j7, 14: _tpl_j14, 30: _tpl_j30}
    if step not in tpl_map:
        raise HTTPException(404, f"Step doit être 3, 7, 14 ou 30 (reçu {step})")
    subject, _text, html = tpl_map[step](email)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content=f"<!-- Subject: {subject} -->\n{html}",
        media_type="text/html; charset=utf-8",
    )


@router.get("/stats")
async def sequence_stats(
    token: str = Query(..., description="PLATFORM_ADMIN_TOKEN"),
):
    """
    Statistiques de la séquence : nombre d'inscrits par étape, taux de
    délivrabilité, dernière exécution.
    """
    _check_admin_token(token)
    coll = db["newsletter_subscribers"]

    total = await coll.count_documents({})
    unsubscribed = await coll.count_documents({"unsubscribed": True})
    active = total - unsubscribed

    steps: dict[str, int] = {}
    for step in range(5):
        c = await coll.count_documents({
            "sequence_step": step,
            "unsubscribed": {"$ne": True},
        })
        steps[f"step_{step}"] = c

    return {
        "total": total,
        "active": active,
        "unsubscribed": unsubscribed,
        "by_step": steps,
        "step_legend": {
            "0": "Welcome envoyé (J0)",
            "1": "J3 envoyé (trapèze)",
            "2": "J7 envoyé (Sambre)",
            "3": "J14 envoyé (TVA)",
            "4": "J30 envoyé (offre 30j)",
        },
    }



# ─────────────────────────────────────────────────────────────────
# 🎨 Marketing Dashboard HTML — hub centralisé
# Accessible depuis l'admin panel de l'app mobile (bouton "Marketing")
# ─────────────────────────────────────────────────────────────────
@router.get("/dashboard", include_in_schema=False)
async def marketing_dashboard(
    token: str = Query(..., description="short JWT admin_marketing ou PLATFORM_ADMIN_TOKEN"),
):
    """Dashboard HTML unifié : Newsletter + Broadcasts."""
    _check_admin_token(token)
    coll = db["newsletter_subscribers"]

    # Stats newsletter
    total = await coll.count_documents({})
    unsubscribed = await coll.count_documents({"unsubscribed": True})
    active = total - unsubscribed
    steps = {}
    for step in range(5):
        c = await coll.count_documents({
            "sequence_step": step,
            "unsubscribed": {"$ne": True},
        })
        steps[step] = c

    # Stats broadcast (users réels — même filtre que /admin/users/notify-*)
    try:
        from routes.admin_tools import _is_technical_account
    except Exception:
        def _is_technical_account(email: str) -> bool:  # fallback
            el = (email or "").lower()
            return (
                not el or "@example.com" in el
                or el.startswith("pytest_") or el.startswith("test_")
            )
    real_users = 0
    async for u in db.users.find({}, {"email": 1}):
        if not _is_technical_account(u.get("email", "")):
            real_users += 1

    flag_counts: dict[str, int] = {}
    async for doc in db.users.find({"broadcast_flags": {"$exists": True}}, {"broadcast_flags": 1}):
        flags = doc.get("broadcast_flags", {}) or {}
        for k, v in flags.items():
            if v is True:
                flag_counts[k] = flag_counts.get(k, 0) + 1

    flag_rows = "".join(
        f'<tr><td>{k}</td><td style="text-align:right;font-weight:600">{v}</td></tr>'
        for k, v in sorted(flag_counts.items())
    ) or '<tr><td colspan="2" style="color:#8e8e93;text-align:center;padding:16px">Aucun broadcast envoyé pour le moment</td></tr>'

    from fastapi.responses import HTMLResponse
    html = f"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MesureChâssis · Marketing Dashboard</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; padding:16px; background:#0b0b0d; color:#f5f5f7;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    font-size:14.5px; line-height:1.5;
  }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  .sub {{ color:#8e8e93; margin:0 0 20px; font-size:12.5px; }}
  .card {{ background:#1c1c1e; border-radius:14px; padding:16px; margin-bottom:14px; }}
  .card h2 {{ font-size:14px; margin:0 0 12px; color:#00C853; text-transform:uppercase; letter-spacing:1px; }}
  .stat-row {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
  .stat {{ background:#2c2c2e; padding:12px; border-radius:10px; text-align:center; }}
  .stat .num {{ font-size:22px; font-weight:800; color:#fff; }}
  .stat .lbl {{ font-size:10.5px; color:#8e8e93; text-transform:uppercase; margin-top:2px; }}
  .btn {{
    display:inline-block; background:#00C853; color:#001B44;
    padding:10px 16px; border-radius:8px; font-weight:700;
    font-size:13px; text-decoration:none; margin:4px 4px 4px 0; border:none; cursor:pointer;
  }}
  .btn-outline {{ background:transparent; border:1px solid #48484a; color:#f5f5f7; }}
  .btn-danger {{ background:#FF453A; color:#fff; }}
  input, textarea {{
    background:#2c2c2e; border:1px solid #48484a; color:#f5f5f7;
    padding:10px 12px; border-radius:8px; font-size:14px;
    width:100%; margin-bottom:8px; font-family:inherit;
  }}
  label {{ font-size:12px; color:#8e8e93; display:block; margin-bottom:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  table td {{ padding:6px 0; border-bottom:1px solid #2c2c2e; }}
  #log {{ background:#000; padding:10px; border-radius:8px; font-family:'SF Mono',Monaco,monospace;
          font-size:11px; color:#00C853; max-height:200px; overflow-y:auto; white-space:pre-wrap; margin-top:10px; }}
  .steps {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .step-pill {{ background:#2c2c2e; padding:6px 10px; border-radius:100px; font-size:11.5px; color:#8e8e93; }}
  .step-pill strong {{ color:#fff; }}
</style>
</head><body>

<h1>📣 Marketing Dashboard</h1>
<p class="sub">Newsletter · Broadcasts email · Tests</p>

<!-- 📚 NEWSLETTER -->
<div class="card">
  <h2>📚 Newsletter (guide gratuit)</h2>
  <div class="stat-row">
    <div class="stat"><div class="num">{total}</div><div class="lbl">Total</div></div>
    <div class="stat"><div class="num" style="color:#00C853">{active}</div><div class="lbl">Actifs</div></div>
    <div class="stat"><div class="num" style="color:#FF453A">{unsubscribed}</div><div class="lbl">Désinscrits</div></div>
  </div>
  <p style="margin:14px 0 6px;font-size:12px;color:#8e8e93;">Progression séquence :</p>
  <div class="steps">
    <div class="step-pill"><strong>{steps[0]}</strong> Welcome (J0)</div>
    <div class="step-pill"><strong>{steps[1]}</strong> J3 trapèze</div>
    <div class="step-pill"><strong>{steps[2]}</strong> J7 Sambre</div>
    <div class="step-pill"><strong>{steps[3]}</strong> J14 TVA</div>
    <div class="step-pill"><strong>{steps[4]}</strong> J30 offre</div>
  </div>
  <div style="margin-top:16px">
    <button class="btn btn-outline" onclick="runSeq(true)">🧪 Dry-run</button>
    <button class="btn" onclick="runSeq(false)">▶️ Envoyer maintenant</button>
    <a class="btn btn-outline" target="_blank" href="/api/admin/newsletter/preview/3?token={token}">👀 J3</a>
    <a class="btn btn-outline" target="_blank" href="/api/admin/newsletter/preview/7?token={token}">👀 J7</a>
    <a class="btn btn-outline" target="_blank" href="/api/admin/newsletter/preview/14?token={token}">👀 J14</a>
    <a class="btn btn-outline" target="_blank" href="/api/admin/newsletter/preview/30?token={token}">👀 J30</a>
  </div>
</div>

<!-- 🚀 BROADCAST NOUVELLE VERSION -->
<div class="card">
  <h2>🚀 Broadcast — Nouvelle version app</h2>
  <p style="font-size:12.5px;color:#8e8e93;margin:0 0 12px">
    Envoie un email à tous les users réels ({real_users} au total).
    Idempotent : chaque user ne reçoit qu'une fois par version.
  </p>
  <label>Version</label>
  <input id="ver" value="1.0.35" placeholder="1.0.35">
  <label>Nouveautés (une par ligne, max 5)</label>
  <textarea id="hi" rows="4" placeholder="Correction de bugs&#10;Amélioration exports PDF&#10;Formulaire TVA plus rapide"></textarea>
  <button class="btn btn-outline" onclick="notifyVer(true)">🧪 Dry-run</button>
  <button class="btn" onclick="notifyVer(false)">▶️ Envoyer</button>
  <a class="btn btn-outline" target="_blank" href="#" id="previewVer">👀 Preview</a>
  <script>
    document.getElementById('ver').addEventListener('input', updPreview);
    document.getElementById('hi').addEventListener('input', updPreview);
    function updPreview() {{
      const v = document.getElementById('ver').value;
      const h = document.getElementById('hi').value.split('\\n').filter(x=>x.trim()).join('|');
      document.getElementById('previewVer').href =
        '/api/admin/users/broadcast-preview/new-version?token={token}&version=' +
        encodeURIComponent(v) + '&highlights=' + encodeURIComponent(h);
    }}
    updPreview();
  </script>
</div>

<!-- 🍎 BROADCAST TVA -->
<div class="card">
  <h2>🍎 Broadcast — Exigence TVA (users grandfathered)</h2>
  <p style="font-size:12.5px;color:#8e8e93;margin:0 0 12px">
    Notifie UNIQUEMENT les Google/Apple users créés avant le 15 juillet 2026
    et dont la company n'a pas encore de vat_number/business_id.
    Idempotent (flag : notified_vat_lock_2026_07).
  </p>
  <button class="btn btn-outline" onclick="notifyVat(true)">🧪 Dry-run (aperçu cibles)</button>
  <button class="btn" onclick="notifyVat(false)">▶️ Envoyer</button>
  <a class="btn btn-outline" target="_blank" href="/api/admin/users/broadcast-preview/vat-requirement?token={token}">👀 Preview</a>
</div>

<!-- 📊 HISTORIQUE BROADCASTS -->
<div class="card">
  <h2>📊 Broadcasts envoyés</h2>
  <table>{flag_rows}</table>
</div>

<div id="log">Prêt.</div>

<script>
const TOKEN = '{token}';
function log(s) {{
  const el = document.getElementById('log');
  el.textContent += '\\n' + new Date().toISOString().substring(11,19) + ' — ' + s;
  el.scrollTop = el.scrollHeight;
}}
async function runSeq(dry) {{
  log((dry?'DRY-RUN':'ENVOI') + ' séquence newsletter…');
  try {{
    const r = await fetch(`/api/admin/newsletter/run-sequence?token=${{TOKEN}}&dry_run=${{dry}}`, {{method:'POST'}});
    const j = await r.json();
    log(JSON.stringify(j, null, 2));
  }} catch (e) {{ log('❌ ' + e.message); }}
}}
async function notifyVer(dry) {{
  const v = document.getElementById('ver').value.trim();
  const hi = document.getElementById('hi').value.split('\\n').map(x=>x.trim()).filter(Boolean);
  if (!v) return alert('Version obligatoire.');
  if (!dry && !confirm('Envoi RÉEL à ' + {real_users} + ' users pour la v' + v + '. Confirmer ?')) return;
  log((dry?'DRY-RUN':'ENVOI') + ' broadcast v' + v + '…');
  try {{
    const r = await fetch(`/api/admin/users/notify-new-version?token=${{TOKEN}}`, {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{latest_version:v, highlights:hi, dry_run:dry}}),
    }});
    const j = await r.json();
    log(JSON.stringify(j, null, 2));
  }} catch (e) {{ log('❌ ' + e.message); }}
}}
async function notifyVat(dry) {{
  if (!dry && !confirm('Envoi RÉEL du mail TVA aux Google users grandfathered. Confirmer ?')) return;
  log((dry?'DRY-RUN':'ENVOI') + ' broadcast TVA…');
  try {{
    const r = await fetch(`/api/admin/users/notify-vat-requirement?token=${{TOKEN}}`, {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{dry_run:dry}}),
    }});
    const j = await r.json();
    log(JSON.stringify(j, null, 2));
  }} catch (e) {{ log('❌ ' + e.message); }}
}}
</script>

</body></html>"""
    return HTMLResponse(html)
