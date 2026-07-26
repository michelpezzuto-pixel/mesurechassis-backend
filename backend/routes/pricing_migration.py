"""
routes/pricing_migration.py — Migration vers modèle payant (juillet 2026)
==========================================================================
Deux endpoints admin réservés à Michel :

1. POST /api/admin/pricing-migration/mark-grandfathered
   Marque les users existants avec flag `grandfathered_lifetime_free=true`
   Utile si vous voulez PROTÉGER certains users historiques.

2. POST /api/admin/pricing-migration/send-warning-emails
   Envoie l'email personnalisé "Le modèle change dans 7 jours" via Resend
   à tous les users actifs.

3. POST /api/admin/pricing-migration/activate-paid-mode
   Bascule BETA_MODE=false (nécessite redémarrage manuel Railway pour prendre effet
   ou utilisation de l'env var directement).

⚠️ Ces endpoints sont protégés par require_platform_owner (email whitelist).
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_platform_owner
from email_service import send_email

logger = logging.getLogger("mesurechassis.pricing_migration")
router = APIRouter(tags=["admin_pricing_migration"])


# ═══════════════════════════════════════════════════════════════════════
# 1. MARK GRANDFATHERED — Protection des users historiques
# ═══════════════════════════════════════════════════════════════════════
class MarkGrandfatheredBody(BaseModel):
    """Optionnel : filtrer par date de création (avant cutoff = protégés)."""
    only_active_users: bool = True  # ignore les comptes fantômes sans chantier
    dry_run: bool = True             # dry-run par défaut (ne modifie rien)


@router.post("/admin/pricing-migration/mark-grandfathered")
async def mark_grandfathered(
    body: MarkGrandfatheredBody,
    user=Depends(require_platform_owner),
):
    """
    Marque les users existants "actifs" avec grandfathered_lifetime_free=true.
    Ils garderont un accès Pro à vie même après activation du mode payant.

    Critères pour être marqué :
      - only_active_users=true : au moins 1 chantier existant à leur nom
      - Sinon : tous les users existants
    """
    now = datetime.now(timezone.utc).isoformat()

    if body.only_active_users:
        # Récupère les user_ids qui ont au moins 1 chantier
        active_pipeline = [
            {"$group": {"_id": "$created_by"}},
            {"$match": {"_id": {"$ne": None}}},
        ]
        active_ids = [d["_id"] async for d in db.chantiers.aggregate(active_pipeline)]
        query = {"user_id": {"$in": active_ids}}
    else:
        query = {}

    if body.dry_run:
        count = await db.users.count_documents(query)
        return {
            "dry_run": True,
            "would_mark_count": count,
            "message": f"Dry-run : {count} users seraient marqués grandfathered. Ré-appelle avec dry_run=false pour appliquer.",
        }

    result = await db.users.update_many(
        query,
        {
            "$set": {
                "grandfathered_lifetime_free": True,
                "grandfathered_at": now,
                "grandfathered_reason": "user_historic_beta_free",
            }
        },
    )
    logger.info("Grandfathering appliqué à %d users", result.modified_count)

    return {
        "dry_run": False,
        "marked_count": result.modified_count,
        "message": f"✅ {result.modified_count} users marqués grandfathered à vie.",
    }


# ═══════════════════════════════════════════════════════════════════════
# 2. SEND WARNING EMAILS — Prévenir les users 7 jours avant
# ═══════════════════════════════════════════════════════════════════════
class SendWarningBody(BaseModel):
    subject: str = "🎁 MesureChâssis évolue — Ce que ça change pour toi"
    launch_date: str = "prochaine mise à jour App Store (dans quelques jours)"
    dry_run: bool = True
    limit: Optional[int] = None  # Limite pour tester (envoie à N users seulement)


def _build_warning_email_html(user_name: str, launch_date: str) -> str:
    """Génère le HTML de l'email de warning personnalisé."""
    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0d0d0f;color:#f0f0f2;font-family:-apple-system,sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 24px">
  <h1 style="color:#FF6B35;margin-bottom:24px">Salut {user_name} 👋</h1>

  <p style="line-height:1.6;font-size:1rem">
    Je suis Michel, le fondateur de MesureChâssis. J'ai un truc important à te dire.
  </p>

  <p style="line-height:1.6;font-size:1rem">
    Ces derniers mois, j'ai amélioré MesureChâssis avec l'aide de la communauté :
    IA d'import du cahier des charges, Assistant Yann, laser Bluetooth,
    14 formes de menuiseries, exports pro... L'app est <strong>vraiment aboutie</strong>.
  </p>

  <p style="line-height:1.6;font-size:1rem">
    Pour continuer à faire évoluer l'app et vivre de ce projet, je dois faire
    un changement <strong>à la {launch_date}</strong> :
  </p>

  <div style="background:#1a1a1e;border-left:4px solid #FF6B35;padding:20px;border-radius:8px;margin:24px 0">
    <h3 style="color:#FF6B35;margin-top:0">🎁 Ce qui reste GRATUIT à vie</h3>
    <ul style="line-height:1.8">
      <li>Jusqu'à <strong>3 chantiers</strong> actifs</li>
      <li>Jusqu'à <strong>5 ouvertures</strong> cumulées</li>
      <li>Export PDF · Photos anti-litige</li>
      <li>Toutes les 14 formes de menuiseries</li>
      <li>Yann IA (10 questions/mois)</li>
      <li>Import IA CDC (3 imports/mois)</li>
    </ul>
    <p style="margin-bottom:0"><strong>Toutes tes données restent intactes.</strong></p>
  </div>

  <div style="background:#1a1a1e;border-left:4px solid #22c55e;padding:20px;border-radius:8px;margin:24px 0">
    <h3 style="color:#22c55e;margin-top:0">⭐ Ce qui devient payant</h3>
    <ul style="line-height:1.8">
      <li><strong>Chantiers illimités</strong> · Ouvertures illimitées</li>
      <li>Yann IA illimité · Import CDC illimité</li>
      <li>Laser Bluetooth · Exports Excel/CSV/JSON/ERP</li>
      <li>Mode équipe multi-users</li>
    </ul>
    <p style="margin-bottom:0">
      <strong>Artisan Pro : 19€/mois</strong> — plus abordable que la moitié des solutions du marché.
    </p>
  </div>

  <h3 style="color:#FF6B35;margin-top:32px">🎁 Cadeau pour toi (utilisateur historique)</h3>
  <p style="line-height:1.6">
    Comme tu es sur MesureChâssis depuis le début, tu bénéficies de
    <strong>14 jours d'essai Pro supplémentaires</strong> dès la mise à jour.
    Pas de carte bancaire demandée, pas d'engagement.
  </p>

  <div style="text-align:center;margin:32px 0">
    <a href="https://mesurechassis.com/tarifs.html"
       style="display:inline-block;background:#FF6B35;color:#000;padding:14px 32px;
              border-radius:12px;text-decoration:none;font-weight:800;font-size:1rem">
      Voir les nouveaux tarifs →
    </a>
  </div>

  <p style="line-height:1.6;font-size:.95rem;color:#a8a8b0">
    Si tu as des questions ou un feedback, réponds à cet email — je lis tout personnellement.
    Merci de ta confiance depuis le début 🙏
  </p>

  <p style="line-height:1.6;font-size:.95rem;color:#a8a8b0;margin-top:24px">
    Michel Pezzuto<br>
    Fondateur MesureChâssis<br>
    <a href="https://calendly.com/michelpezzuto/30min" style="color:#FF6B35">📞 Réserver 15 min avec moi</a>
  </p>

  <hr style="border:none;border-top:1px solid #2a2a30;margin:32px 0">
  <p style="font-size:.75rem;color:#666;text-align:center">
    Tu reçois cet email car tu es utilisateur de MesureChâssis.
    <br>Si tu ne souhaites plus recevoir nos emails :
    <a href="https://mesurechassis.com/unsubscribe" style="color:#a8a8b0">se désinscrire</a>
  </p>
</div>
</body>
</html>
""".strip()


@router.post("/admin/pricing-migration/send-warning-emails")
async def send_warning_emails(
    body: SendWarningBody,
    user=Depends(require_platform_owner),
):
    """Envoie l'email "changement de modèle" à tous les users."""
    # Récupère les users à contacter (avec email valide)
    query = {"email": {"$regex": r".+@.+\..+"}}
    cursor = db.users.find(query, {"email": 1, "first_name": 1, "last_name": 1, "user_id": 1, "_id": 0})

    if body.limit:
        cursor = cursor.limit(body.limit)

    users_to_email = [u async for u in cursor]
    total = len(users_to_email)

    if body.dry_run:
        return {
            "dry_run": True,
            "would_send_count": total,
            "sample_recipients": [u.get("email") for u in users_to_email[:5]],
            "sample_html_preview": _build_warning_email_html("Michel", body.launch_date)[:500] + "...",
            "message": f"Dry-run : {total} emails seraient envoyés. Ré-appelle avec dry_run=false pour envoyer.",
        }

    # Envoi en batch (avec petit délai anti-rate-limit Resend)
    sent = 0
    failed = 0
    errors = []
    for u in users_to_email:
        try:
            name = (u.get("first_name") or "").strip() or (u.get("last_name") or "").strip() or "menuisier"
            html = _build_warning_email_html(name, body.launch_date)
            send_email(
                to=u.get("email"),
                subject=body.subject,
                body="",  # HTML utilisé à la place
                html=html,
            )
            sent += 1
        except Exception as e:
            failed += 1
            errors.append({"email": u.get("email"), "error": str(e)[:100]})

    logger.info("Warning emails envoyés : %d / %d (échecs : %d)", sent, total, failed)

    return {
        "dry_run": False,
        "total": total,
        "sent": sent,
        "failed": failed,
        "errors": errors[:10],
        "message": f"✅ {sent} emails envoyés sur {total}. Échecs : {failed}",
    }
