"""📱 Campagne LANCEMENT — « MesureChâssis est dispo sur l'App Store ».

Envoie un email chaleureux et court à tes prospects pour leur annoncer la
sortie officielle de l'app sur l'App Store, en insistant sur :

    ✅ App gratuite (3 chantiers offerts à vie)
    ✅ Pas de carte requise
    ✅ Standard illimité à 19,99 € HT/mois
    ✅ Bouton App Store direct

Le script utilise :
    • ``services/prospection_utils.upsert_prospect``  → gestion prospects
    • ``services/prospection_utils.send_prospect_email`` → envoi+RGPD+dedup
    • Fenêtre horaire 15h30-17h30 Bruxelles (best-practice Michel)

Modes d'exécution :
    python send_launch_appstore.py --dry-run     # génère HTML dans /tmp/, n'envoie rien
    python send_launch_appstore.py --preview 3   # affiche 3 mails générés + quitte
    python send_launch_appstore.py               # envoi réel (respect fenêtre horaire)
    python send_launch_appstore.py --force       # bypass fenêtre horaire (⚠️ tests uniquement)
    python send_launch_appstore.py --relance     # cible ceux JAMAIS touchés sur cette campagne
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from services.prospection_utils import (  # noqa: E402
    build_unsubscribe_footer,
    campaign_stats,
    is_send_window_open,
    list_never_contacted,
    ProspectionError,
    send_prospect_email,
    upsert_prospect,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("launch_appstore")


CAMPAIGN_SLUG = "launch_appstore_v1"
APP_STORE_URL = "https://apps.apple.com/fr/app/mesurechâssis/id6776357930"
SITE_URL = "https://mesurechassis.com"
GUIDE_URL = "https://window-field-app.preview.emergentagent.com/api/_downloads/guide-debutant/preview"

# ═════════ LISTE DE CIBLES (À COMPLÉTER PAR MICHEL DEMAIN) ═════════
#
# Formats acceptés — laisser first_name/company vides si inconnus :
#   {"email": "jean@example.com", "first_name": "Jean", "company": "Menuiserie Jean"}
#
# Les 8 contacts déjà touchés par b2b/sponsors sont pré-listés — le module
# `prospection_utils` détectera automatiquement la déduplication.
# ═══════════════════════════════════════════════════════════════════════
TARGETS: list[dict] = [
    # === Placeholder : à remplacer par la vraie liste demain ===
    # {"email": "…", "first_name": "…", "company": "…"},
]


# ═════════ TEMPLATE EMAIL ═════════
def render_email(*, first_name: str | None, company: str | None,
                 prospect_id: str, email: str) -> tuple[str, str]:
    """Retourne (subject, body_html) personnalisé pour un prospect."""
    salut = f"Bonjour {first_name}," if first_name else "Bonjour,"
    company_line = (
        f"<p>J'espère que tout va bien chez <strong>{company}</strong>.</p>"
        if company else ""
    )
    subject = "🎉 MesureChâssis est dispo — gratuit sur l'App Store"
    body_html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;color:#1A1A1E">
<div style="max-width:600px;margin:0 auto;background:#fff;padding:32px 28px">

<!-- Header -->
<div style="text-align:center;padding-bottom:20px;border-bottom:3px solid #FF5A00">
  <div style="font-family:Segoe UI,sans-serif;font-weight:800;font-size:22pt;letter-spacing:-1px;color:#1A1A1E">
    MESURECHÂSSIS
  </div>
  <div style="font-size:11px;color:#8A8A92;letter-spacing:2px;text-transform:uppercase;margin-top:4px">
    Mesures terrain · Menuiseries pro
  </div>
</div>

<!-- Body -->
<div style="padding:24px 4px;font-size:15px;line-height:1.7;color:#1A1A1E">

<p style="font-size:16px">{salut}</p>

{company_line}

<p>C'est <strong>Michel Pezzuto</strong>, fondateur de MesureChâssis. Je te contacte car j'ai enfin une bonne nouvelle à partager.</p>

<div style="background:linear-gradient(135deg,#FF5A00 0%,#FF7A20 100%);color:#fff;padding:20px 24px;border-radius:12px;margin:24px 0;text-align:center">
  <div style="font-size:14px;font-weight:600;letter-spacing:1px;text-transform:uppercase;opacity:.9;margin-bottom:6px">
    ✅ C'est officiel
  </div>
  <div style="font-size:22px;font-weight:800;line-height:1.3">
    MesureChâssis est disponible<br>gratuitement sur l'App&nbsp;Store
  </div>
</div>

<p>L'app est conçue pour <strong>les menuisiers pros</strong> qui prennent des mesures sur chantier — bois, alu, PVC. Elle remplace le carnet + le mètre ruban approximatif par :</p>

<ul style="padding-left:18px">
  <li><strong>Prise de mesures assistée</strong> (3 largeurs, 3 hauteurs, 2 diagonales) sur 14 formes différentes — rectangle, cintré, trapèze, œil-de-bœuf…</li>
  <li><strong>Import IA d'un cahier des charges</strong> (PDF, Excel, photo) — l'IA détecte automatiquement toutes les ouvertures + les coordonnées client + la structure du mur</li>
  <li><strong>Photos anti-litige</strong> horodatées + signature client sur écran</li>
  <li><strong>Exports pros</strong> — PDF client, Excel devis, CSV ERP, JSON API</li>
</ul>

<p style="margin-top:24px"><strong>🎁 Ce que je t'offre en découverte</strong></p>

<ul style="padding-left:18px">
  <li><strong>3 chantiers offerts À VIE</strong> — pas de carte, pas d'engagement</li>
  <li>Si tu veux passer en illimité ensuite : <strong>19,99 € HT/mois</strong> (Standard) ou <strong>49,99 €</strong> avec équipe jusqu'à 5 personnes (Team)</li>
  <li>14 jours d'essai gratuit sur tous les plans payants</li>
</ul>

<div style="text-align:center;margin:32px 0">
  <a href="{APP_STORE_URL}" style="display:inline-block;background:#000;color:#fff;text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:700;font-size:15px;box-shadow:0 4px 14px rgba(0,0,0,.15)">
    📱 Télécharger sur l'App Store
  </a>
  <div style="font-size:12px;color:#8A8A92;margin-top:12px">
    Version Android en préparation
  </div>
</div>

<p>Le guide débutant t'aide à démarrer en 15 minutes :<br>
<a href="{GUIDE_URL}" style="color:#FF5A00;font-weight:600;text-decoration:underline">📗 Consulter le guide débutant</a></p>

<p>Si t'as des questions ou des retours, réponds simplement à ce mail — je lis tout personnellement.</p>

<p>Bonne route à toi et bon boulot,<br>
<strong>Michel Pezzuto</strong><br>
Fondateur — MesureChâssis<br>
<span style="color:#8A8A92;font-size:13px">+32 496 65 00 32 · info@mesurechassis.com · <a href="{SITE_URL}" style="color:#FF5A00">mesurechassis.com</a></span>
</p>

</div>

{build_unsubscribe_footer(prospect_id, email)}

</div>
</body></html>"""
    return subject, body_html


# ═════════ RUNNER ═════════
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Génère les HTML dans /tmp/prospection_preview/ sans envoyer")
    parser.add_argument("--preview", type=int, default=0,
                        help="Nb de mails à afficher (aperçu texte) puis quitter")
    parser.add_argument("--force", action="store_true",
                        help="⚠️ Bypass la fenêtre horaire 15h30-17h30")
    parser.add_argument("--relance", action="store_true",
                        help="Cible UNIQUEMENT les prospects jamais touchés sur cette campagne")
    parser.add_argument("--limit", type=int, default=30,
                        help="Nb max d'emails à envoyer par exécution (défaut 30 = quota Resend safe)")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Délai en secondes entre chaque envoi (défaut 3s)")
    args = parser.parse_args()

    # 0. Fenêtre horaire
    open_, motif = is_send_window_open()
    log.info("⏰ Fenêtre horaire : %s", motif)
    if not open_ and not args.force and not args.dry_run:
        log.warning("⚠️  Envoi bloqué (hors fenêtre). Utilise --force pour bypass.")
        return

    # 1. Détermine la liste de destinataires
    if args.relance:
        log.info("📋 Mode relance — cherche les prospects jamais touchés par %s", CAMPAIGN_SLUG)
        recipients = await list_never_contacted(CAMPAIGN_SLUG)
        log.info("   → %d prospects jamais contactés trouvés", len(recipients))
    else:
        if not TARGETS:
            log.error("❌ La liste TARGETS est vide. Édite le script pour y ajouter les emails.")
            log.info("💡 Astuce : lance `--relance` pour envoyer aux prospects déjà en DB.")
            return
        # Upsert des targets → récupère l'id (nécessaire pour le footer)
        recipients = []
        for t in TARGETS:
            doc = await upsert_prospect(
                t["email"],
                first_name=t.get("first_name"),
                last_name=t.get("last_name"),
                company=t.get("company"),
                source="launch_appstore",
            )
            recipients.append(doc)

    # 2. Cap au limit
    recipients = recipients[: args.limit]
    log.info("📤 %d envois planifiés (limit=%d, delay=%ss)", len(recipients), args.limit, args.delay)

    # 3. Preview only ?
    if args.preview:
        for r in recipients[: args.preview]:
            subject, body = render_email(
                first_name=r.get("first_name"),
                company=r.get("company"),
                prospect_id=r["id"],
                email=r["email"],
            )
            print(f"\n═══════ TO: {r['email']} ═══════")
            print(f"SUBJECT: {subject}")
            print(f"(body: {len(body)} chars, {body.count('<p>')} paragraphes)")
        return

    # 4. Envoi
    stats = {"sent": 0, "skipped": 0, "error": 0, "dry_run": 0}
    for i, r in enumerate(recipients, start=1):
        subject, body = render_email(
            first_name=r.get("first_name"),
            company=r.get("company"),
            prospect_id=r["id"],
            email=r["email"],
        )
        try:
            result = await send_prospect_email(
                r,
                subject=subject,
                body_html=body,
                campaign_slug=CAMPAIGN_SLUG,
                dry_run=args.dry_run,
                force_send_outside_window=args.force,
            )
            stats[result["status"]] = stats.get(result["status"], 0) + 1
            emoji = {"sent": "✅", "skipped": "⏭️", "error": "❌", "dry_run": "📝"}.get(
                result["status"], "•"
            )
            log.info("%s [%d/%d] %s → %s", emoji, i, len(recipients), r["email"], result.get("reason") or result.get("status"))
        except ProspectionError as e:
            stats["error"] += 1
            log.error("❌ [%d/%d] %s → %s", i, len(recipients), r["email"], e)
        # Délai entre envois (sauf en dry-run)
        if not args.dry_run and i < len(recipients):
            await asyncio.sleep(args.delay)

    # 5. Rapport final
    log.info("═" * 60)
    log.info("📊 BILAN : sent=%d · skipped=%d · error=%d · dry_run=%d",
             stats["sent"], stats["skipped"], stats["error"], stats["dry_run"])
    global_stats = await campaign_stats(CAMPAIGN_SLUG)
    log.info("📈 Cumul campagne %s : %s", CAMPAIGN_SLUG, global_stats)


if __name__ == "__main__":
    asyncio.run(main())
