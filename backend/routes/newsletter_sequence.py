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
# Auth admin (même mécanisme que admin_tools.py)
# ─────────────────────────────────────────────────────────────────
def _check_admin_token(token: str) -> None:
    expected = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected:
        raise HTTPException(500, "PLATFORM_ADMIN_TOKEN non configuré")
    if token != expected:
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
