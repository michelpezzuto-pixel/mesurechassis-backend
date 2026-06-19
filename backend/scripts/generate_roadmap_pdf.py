"""Génération du PDF roadmap personnelle de Michel — Juin → Octobre 2026.

Génère un PDF imprimable A4 de ~10 pages mélangeant :
  • Vision 3 mois & objectifs chiffrés
  • Journée type heure par heure (semaine + weekend)
  • Roadmap hebdomadaire détaillée (juin → août → sprint final septembre)
  • Conseils sociaux/perso adaptés à Sombreffe (BE) sans voiture
  • Récapitulatif imprimable des tâches quotidiennes

Sortie : /app/backend/static/roadmap_michel_juin_octobre_2026.pdf
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ───────────────────────────────────────────────────────────────────────────
# Palette (cohérent avec l'app MesureChâssis)
# ───────────────────────────────────────────────────────────────────────────
PRIMARY = colors.HexColor("#FF6B35")  # orange MesureChâssis
DARK_BG = colors.HexColor("#0F0F11")
SOFT = colors.HexColor("#1A1A1F")
TEXT = colors.HexColor("#1A1A1F")
GREY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#F4F4F6")
GREEN = colors.HexColor("#4CAF50")
PURPLE = colors.HexColor("#9333EA")

styles = getSampleStyleSheet()

H1 = ParagraphStyle(
    "H1",
    parent=styles["Heading1"],
    fontSize=24,
    leading=28,
    textColor=PRIMARY,
    spaceAfter=8,
    alignment=TA_LEFT,
)
H2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=15,
    leading=18,
    textColor=TEXT,
    spaceBefore=12,
    spaceAfter=6,
)
H3 = ParagraphStyle(
    "H3",
    parent=styles["Heading3"],
    fontSize=12,
    leading=14,
    textColor=PRIMARY,
    spaceBefore=8,
    spaceAfter=4,
)
P = ParagraphStyle(
    "P",
    parent=styles["BodyText"],
    fontSize=10,
    leading=14,
    textColor=TEXT,
    alignment=TA_LEFT,
)
SMALL = ParagraphStyle(
    "Small",
    parent=styles["BodyText"],
    fontSize=8,
    leading=11,
    textColor=GREY,
)
COVER_TITLE = ParagraphStyle(
    "CoverTitle",
    parent=styles["Title"],
    fontSize=34,
    leading=40,
    textColor=PRIMARY,
    alignment=TA_CENTER,
)
COVER_SUB = ParagraphStyle(
    "CoverSub",
    parent=styles["Normal"],
    fontSize=13,
    leading=18,
    textColor=TEXT,
    alignment=TA_CENTER,
)


def _hr():
    """Ligne horizontale en forme de mini-table."""
    t = Table([[" "]], colWidths=[180 * mm], rowHeights=[1.5])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PRIMARY)]))
    return t


def _kv_table(rows: list[tuple[str, str]], col_w=(35 * mm, 145 * mm)):
    """Tableau 2 colonnes (label, valeur) — utilisé pour les journées."""
    data = [[Paragraph(f"<b>{k}</b>", P), Paragraph(v, P)] for k, v in rows]
    t = Table(data, colWidths=col_w)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
            ]
        )
    )
    return t


def _week_table(week_num: int, dates: str, theme: str, focus: list[tuple[str, str]]):
    """Encadré pour une semaine de roadmap."""
    header = [[
        Paragraph(f'<font color="#FFFFFF"><b>S{week_num} · {dates}</b></font>', P),
        Paragraph(f'<font color="#FFFFFF"><b>{theme}</b></font>', P),
    ]]
    body = [[Paragraph(f"<b>{d}</b>", P), Paragraph(t, P)] for d, t in focus]
    data = header + body
    t = Table(data, colWidths=(40 * mm, 140 * mm))
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("BACKGROUND", (0, 1), (0, -1), LIGHT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DDDDDD")),
            ]
        )
    )
    return t


# ───────────────────────────────────────────────────────────────────────────
# Contenu — Journées types
# ───────────────────────────────────────────────────────────────────────────
JOURNEE_SEMAINE = [
    ("06:30", "🛏️ Réveil. Pas de téléphone tout de suite. Étirements rapides 5 min."),
    ("06:35", "💧 Grand verre d'eau citron (acide citrique = réveil métabolique)."),
    ("06:45", "🚿 Douche fraîche (terminer 30 sec à l'eau froide = énergie + focus)."),
    ("07:00", "🥣 Petit-déjeuner SOLIDE : 2 œufs + avoine + fruit + thé/café noir."),
    ("07:30", "📊 <b>MesureChâssis (15 min)</b> : check rapide stats backend (nouveaux inscrits, parrainage, feedback)."),
    ("07:45", "📱 Une session LinkedIn (10 min) : like 5 posts, commenter 2 menuisiers."),
    ("08:00", "💻 <b>DEEP WORK 1 (4h)</b> : travail produit avec l'agent IA. Pas de notifications. Pas de Slack/SMS."),
    ("12:00", "🍴 Déjeuner équilibré (protéines + légumes). Pas de fast-food."),
    ("12:45", "🚉 Train Sombreffe → Gembloux (env. 8 min). Gare à 5 min à pied."),
    ("13:00", "🏋️ <b>BASIC-FIT Gembloux</b> (1h) — alterner cardio (lundi/mer/ven) et muscu (mardi/jeu)."),
    ("14:15", "🚉 Retour train Gembloux → Sombreffe."),
    ("14:45", "☕ Café + collation (fruit + amandes)."),
    ("15:00", "💻 <b>DEEP WORK 2 (2h30)</b> : marketing — emails prospection, contenus LinkedIn, suivi prospects."),
    ("17:30", "📲 Réseaux sociaux (45 min) : 1 post LinkedIn (storytelling MesureChâssis), 1 post Facebook (groupe menuisiers BE/FR/LU)."),
    ("18:15", "🍝 Préparation dîner OU sortie (cf. page suivante)."),
    ("19:00", "🍽️ Dîner."),
    ("20:00", "📚 Lecture / Podcast (30 min) : business, productivité, sciences."),
    ("20:30", "🚶 Marche digestive 20 min dans Sombreffe (sentier Tombelles de Ligny si beau temps)."),
    ("21:00", "📝 Journaling (10 min) : 3 victoires du jour + 1 chose à améliorer demain."),
    ("21:30", "📵 Téléphone OFF. Mode avion."),
    ("22:00", "😴 Coucher (visez 8h de sommeil)."),
]

JOURNEE_WEEKEND = [
    ("08:00", "🛏️ Réveil libre (mais pas après 9h, sinon décalage hormonal)."),
    ("08:30", "🥐 Petit-déjeuner long. Lecture journal."),
    ("09:30", "📊 <b>MesureChâssis (1h)</b> : revue de la semaine (KPIs prospects, feedback, retours utilisateurs)."),
    ("10:30", "🏃 Activité physique alternative : course à pied à Sombreffe, vélo (si tu en as un), randonnée."),
    ("12:00", "🚉 Train vers Namur (25 min) OU Charleroi (30 min) OU Bruxelles (50 min)."),
    ("13:00", "🍽️ Restaurant solo OU avec amis (cf. conseils sociaux)."),
    ("14:30", "🎯 <b>Activité sociale obligatoire</b> : musée, expo, ciné, marché. Pas rester seul à la maison."),
    ("17:00", "☕ Café terrasse. Engager 1 conversation avec un inconnu (entrainement social)."),
    ("18:30", "🚉 Retour Sombreffe."),
    ("19:30", "🍽️ Dîner."),
    ("20:30", "📺 Détente : série, film. PAS de travail."),
    ("23:00", "😴 Coucher."),
]


# ───────────────────────────────────────────────────────────────────────────
# Contenu — Roadmap par semaine (15 semaines : S25 → S39)
# ───────────────────────────────────────────────────────────────────────────
ROADMAP = [
    # ===== JUIN — STABILISATION =====
    {
        "n": 25,
        "dates": "19-22 juin 2026",
        "theme": "🟡 STABILISATION & RETOURS",
        "focus": [
            ("Lundi", "Apple Review Build 101 — relances si pas de retour à J+3."),
            ("Mardi", "Recevoir et traiter 1er feedback Dominique Devos (WinFox/Luxembourg). Appel 15 min."),
            ("Mercredi", "Upgrade Resend Pro (20$/mois). Upload site v2 sur easyhost.be."),
            ("Jeudi", "Relancer 30 prospects (campagne email auto J+3)."),
            ("Vendredi", "Bilan semaine : analyse stats, planning S26."),
            ("Samedi", "🎯 SOCIAL — sortir à Namur (visite Citadelle, restaurant centre-ville)."),
            ("Dimanche", "Repos + lecture. Préparation contenus LinkedIn S26 (3 posts)."),
        ],
    },
    {
        "n": 26,
        "dates": "23-29 juin",
        "theme": "🟢 PUBLICATION APP STORES",
        "focus": [
            ("Lundi", "Validation Apple → mise en ligne App Store. Si refusé : retour brief avec agent IA."),
            ("Mardi", "Google Play : push final + publication. Vérif Android (boutons mesure alignés)."),
            ("Mercredi", "Communication ’nous sommes en ligne !’ : email aux 261 prospects + posts LinkedIn/FB."),
            ("Jeudi", "30 nouveaux contacts B2B (relances + nouvelles cibles)."),
            ("Vendredi", "Relance Elcia Pro Devis — point sur partenariat."),
            ("Samedi", "🎯 SOCIAL — Bruxelles : musée + match. Speed-friending OU app rencontre."),
            ("Dimanche", "Repos. Préparation S27."),
        ],
    },
    # ===== JUILLET — ACQUISITION =====
    {
        "n": 27,
        "dates": "30 juin - 6 juillet",
        "theme": "🚀 ACQUISITION — 50 INSCRITS",
        "focus": [
            ("Lundi", "Mise à jour Stripe (Price IDs 19,99/59,99/249€ + add-on Yann 5€)."),
            ("Mardi", "Connecter webhook Stripe au flag yann_addon_active."),
            ("Mercredi", "Webinar gratuit 30 min : ’Comment MesureChâssis simplifie le terrain’ (groupes FB menuisiers)."),
            ("Jeudi", "30 emails prospection + suivi feedback utilisateurs."),
            ("Vendredi", "Bilan semaine : analyse conversion, ajustement messages email."),
            ("Samedi", "🎯 SOCIAL — événement local Sombreffe/Gembloux (marché, brocante, fête locale)."),
            ("Dimanche", "Repos + planning hebdo S28."),
        ],
    },
    {
        "n": 28,
        "dates": "7-13 juillet",
        "theme": "📊 ANALYSE & ITÉRATION",
        "focus": [
            ("Lundi", "Tableau de bord admin : suivi conversion parrainage → essai → payant."),
            ("Mardi", "Appels téléphoniques aux 5 utilisateurs les plus actifs (15 min chacun)."),
            ("Mercredi", "Démo en visio pour 2 prospects intéressés (planifiés via email)."),
            ("Jeudi", "Refonte petits écrans secondaires d’après retours."),
            ("Vendredi", "30 emails prospection."),
            ("Samedi", "🎯 SOCIAL — Charleroi : cinéma + restaurant. Application rencontre (Bumble, Hinge) — répondre aux matchs."),
            ("Dimanche", "Préparer 3 posts LinkedIn S29."),
        ],
    },
    {
        "n": 29,
        "dates": "14-20 juillet",
        "theme": "🤖 STREAMING YANN + TUTOS",
        "focus": [
            ("Lundi", "Streaming Yann (SSE) — réponses mot par mot, meilleure UX."),
            ("Mardi", "Tournage 1ère vidéo tuto (’Créer mon premier chantier’ en 90 sec)."),
            ("Mercredi", "Tournage 2e vidéo tuto (’Exporter mes mesures’)."),
            ("Jeudi", "Tournage 3e vidéo tuto (’Parrainage et abonnement’)."),
            ("Vendredi", "Intégration des 3 vidéos dans l’app (écran Centre d’aide)."),
            ("Samedi", "🎯 SOCIAL — sortie Namur (festival d’été, terrasse, rencontres)."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 30,
        "dates": "21-27 juillet",
        "theme": "🇧🇪🇫🇷🇱🇺 PROSPECTION INTERNATIONALE",
        "focus": [
            ("Lundi", "Ajout 100 nouveaux prospects (FR + LU + NL)."),
            ("Mardi", "Email campaign FR (50 envois) + suivi LinkedIn."),
            ("Mercredi", "Email campaign LU/NL (50 envois) — adaptation langue."),
            ("Jeudi", "Relance Elcia Pro Devis (2e contact, demande de RDV)."),
            ("Vendredi", "Bilan KPIs juillet."),
            ("Samedi", "🎯 SOCIAL — barbecue solo dans le parc OU rejoindre un groupe Meetup BE."),
            ("Dimanche", "Repos."),
        ],
    },
    # ===== AOÛT — ITÉRATION & POLISH =====
    {
        "n": 31,
        "dates": "28 juillet - 3 août",
        "theme": "🧪 ITÉRATION PRODUIT",
        "focus": [
            ("Lundi", "Mode hors-ligne robuste (sync auto background)."),
            ("Mardi", "Notifications in-app (rappels chantiers à mesurer)."),
            ("Mercredi", "Refonte écran chantier mesure (UX d’après retours)."),
            ("Jeudi", "Tests utilisateurs (5 testeurs cible)."),
            ("Vendredi", "Bug fix priorité haute + déploiement."),
            ("Samedi", "🎯 SOCIAL — Festival ou concert (Belgique = été = festivals)."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 32,
        "dates": "4-10 août",
        "theme": "📐 MODULE DEVIS (PRO)",
        "focus": [
            ("Lundi", "Spec module Devis auto (formule Pro 249€)."),
            ("Mardi", "Backend : génération PDF devis depuis mesures."),
            ("Mercredi", "Frontend : écran ’Créer un devis’."),
            ("Jeudi", "Tests & itération."),
            ("Vendredi", "30 emails prospection (cibler entreprises plus grosses)."),
            ("Samedi", "🎯 SOCIAL — Bruxelles weekend (musée + restaurant gastronomique solo)."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 33,
        "dates": "11-17 août",
        "theme": "🌍 MULTILINGUE NL/EN",
        "focus": [
            ("Lundi", "Vérification i18n complète des nouvelles features."),
            ("Mardi", "Yann répond en NL/EN selon la langue de l’utilisateur."),
            ("Mercredi", "Site web NL/EN (traduction des nouvelles sections)."),
            ("Jeudi", "Beta-tests avec 3 utilisateurs néerlandophones."),
            ("Vendredi", "Bilan KPIs mi-août."),
            ("Samedi", "🎯 SOCIAL — Mer du Nord en train (Ostende, Knokke)."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 34,
        "dates": "18-24 août",
        "theme": "💪 OPTIMISATION CONVERSION",
        "focus": [
            ("Lundi", "A/B test pricing : afficher d’abord Pro 249€ ou Solo 19,99€."),
            ("Mardi", "Amélioration onboarding (1ère mesure réalisée en < 3 min)."),
            ("Mercredi", "Email automation : séquence 7 jours pour les nouveaux freemium."),
            ("Jeudi", "30 emails prospection."),
            ("Vendredi", "Bilan semaine."),
            ("Samedi", "🎯 SOCIAL — événement professionnel (salon, networking) si dispo."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 35,
        "dates": "25-31 août",
        "theme": "🎯 PRÉ-LANCEMENT",
        "focus": [
            ("Lundi", "Test campagne email ’Plus que 30 jours pour la gratuité’."),
            ("Mardi", "Affiner la bannière compte à rebours dans l’app."),
            ("Mercredi", "Vidéo de présentation ’Pourquoi MesureChâssis’ (60 sec)."),
            ("Jeudi", "Pousser la vidéo sur LinkedIn, Facebook, et site web."),
            ("Vendredi", "Bilan KPIs fin août : où en est-on vs objectif 150 inscrits ?"),
            ("Samedi", "🎯 SOCIAL — sortie en grande équipe (si tu as construit ton réseau social, fais-en profit)."),
            ("Dimanche", "Repos. Préparation septembre."),
        ],
    },
    # ===== SEPTEMBRE — SPRINT FINAL =====
    {
        "n": 36,
        "dates": "1-7 septembre",
        "theme": "🏁 SPRINT FINAL J-30",
        "focus": [
            ("Lundi", "Campagne email J-30 : ’Plus qu’un mois pour profiter du gratuit’."),
            ("Mardi", "Webinar live sur Zoom (’Bilan de la beta + roadmap après-1er octobre’)."),
            ("Mercredi", "Activation finale des Price IDs Stripe en mode prod."),
            ("Jeudi", "Tests checkout Stripe (Solo, Entreprise, Pro, add-on Yann)."),
            ("Vendredi", "Communication LinkedIn/Facebook : compte à rebours."),
            ("Samedi", "🎯 SOCIAL — repos mental indispensable. Spa, sauna, massage à Sombreffe ou env."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 37,
        "dates": "8-14 septembre",
        "theme": "🔔 BANNIÈRES ’DERNIERS JOURS’",
        "focus": [
            ("Lundi", "Bannière in-app ’Plus que X jours’ (compteur visible permanent)."),
            ("Mardi", "Push notifications (si déployé) ’Plus que 18 jours’."),
            ("Mercredi", "Story LinkedIn personnelle : ’Mon parcours d’indépendant à Sombreffe’."),
            ("Jeudi", "Démos en direct (3-5 prospects sérieux)."),
            ("Vendredi", "Bilan."),
            ("Samedi", "🎯 SOCIAL — sortie famille/amis. Recharger les batteries."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 38,
        "dates": "15-21 septembre",
        "theme": "💳 PRÉ-ABONNEMENTS",
        "focus": [
            ("Lundi", "Activer les paywalls techniques (BETA_MODE → False scheduled for 30 sept)."),
            ("Mardi", "Email ’Plus que 15 jours’ — offre early-bird 1 mois supplémentaire."),
            ("Mercredi", "Témoignages clients (vidéos 30 sec, posts LinkedIn)."),
            ("Jeudi", "Suivi premiers abonnements (Solo 19,99€)."),
            ("Vendredi", "Bilan."),
            ("Samedi", "🎯 SOCIAL — événement professionnel BE (salons d’automne)."),
            ("Dimanche", "Repos."),
        ],
    },
    {
        "n": 39,
        "dates": "22-30 septembre",
        "theme": "🚀 LIGNE D'ARRIVÉE",
        "focus": [
            ("Lundi", "Email J-7 ’Plus qu’une semaine !’"),
            ("Mardi", "Webinar final 1h ’Bienvenue à la nouvelle ère MesureChâssis’."),
            ("Mercredi", "Email J-4 + push notification."),
            ("Jeudi", "Email J-3."),
            ("Vendredi", "Email J-2. Mode SUPPORT max disponibilité."),
            ("Samedi", "Email J-1. Soirée détente — bien dormir."),
            ("Dimanche", "🚨 BASCULEMENT BETA_MODE=False à 23:59. ✅ MesureChâssis devient officiellement payant. ✨ 1er octobre 2026 = nouvelle ère."),
        ],
    },
]


# ───────────────────────────────────────────────────────────────────────────
# Conseils stratégiques
# ───────────────────────────────────────────────────────────────────────────
CONSEILS_SOCIAUX = [
    "<b>🚉 Transport sans voiture</b> — Sombreffe est très bien desservi : gare à 5 min à pied. Gembloux 8 min (Basic-Fit, restos), Namur 25 min, Bruxelles 50 min, Charleroi 30 min. Achète un abonnement SNCB Standard Multi (~70€/mois) — rentable dès 12 trajets/mois.",
    "<b>🏋️ Sport quotidien</b> — Basic-Fit Gembloux ouvert tôt (06h) et tard (23h). 6 min de marche depuis la gare. Abonnement Premium ~30€/mois = accès illimité + tous les clubs en Belgique. Alterne cardio/muscu pour éviter le plateau.",
    "<b>🍴 Repas équilibrés</b> — Cuisine 2x par semaine en batch (dimanche + mercredi soir) pour la semaine. Évite le fast-food. Hydratation = 2L d’eau/jour minimum. Cafés : max 3 par jour, dernier avant 14h.",
    "<b>👥 Rencontres / Vie sociale</b> — Tu es célibataire : (1) Apps Bumble / Hinge / Tinder — sois patient, 30 min/jour max. (2) Meetup.com Belgique : groupes business, sport, randonnée. (3) Speed-dating Namur/Bruxelles. (4) Engage 1 conversation/jour avec un inconnu (entraînement à la posture sociale).",
    "<b>🍻 Sorties à Sombreffe / environs</b> — Sombreffe centre : peu d’options. Vise Gembloux (centre-ville animé jeudi-samedi, plusieurs bars), Namur (rue Saint-Loup, Beffroi), Charleroi (Quartier Rive Gauche). Trains derniers : vérifie sncb.be (souvent 23h-00h).",
    "<b>🧠 Santé mentale</b> — Tu vas vivre 3 mois intenses. Une session journaling le soir + 1 journée OFF par semaine (samedi ou dimanche) sont NON-NÉGOCIABLES. Pas de culpabilité à ne rien faire.",
    "<b>📱 TikTok & Instagram (gérés par toi)</b> — Conseils : (1) Format vertical 9:16. (2) Hook dans les 3 premières secondes. (3) Pose une question à la fin pour générer des commentaires. (4) Publie 3x/semaine minimum, mais qualité > quantité. (5) Inspire-toi de @lesartisansdufrance ou @menuiserie_passion (recherche hashtag #menuisier).",
]


# ───────────────────────────────────────────────────────────────────────────
# Génération
# ───────────────────────────────────────────────────────────────────────────
def build_pdf(output: Path) -> Path:
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        title="MesureChâssis — Roadmap personnelle Michel",
        author="Michel Pezzuto",
    )

    story = []

    # ─── COUVERTURE ─────────────────────────────────────────────────
    story.append(Spacer(1, 50))
    story.append(Paragraph("MesureChâssis", COVER_TITLE))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        '<font color="#FF6B35">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</font>',
        COVER_SUB,
    ))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "<b>Roadmap personnelle de Michel</b><br/>"
        "Juin → 1<sup>er</sup> Octobre 2026",
        COVER_SUB,
    ))
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "<i>Stratégie & exécution quotidienne — 14 semaines<br/>"
        "Sombreffe → conquête du marché menuisier BE/FR/LU/NL</i>",
        COVER_SUB,
    ))
    story.append(Spacer(1, 50))

    intro = (
        "<b>Vision 3 mois.</b><br/><br/>"
        "Tu pars d’un produit prêt techniquement (Build 101 en review Apple, parrainage actif, "
        "Yann l’assistant IA opérationnel, site v2 livré). En 14 semaines, tu vas transformer "
        "MesureChâssis en SaaS rentable :<br/><br/>"
        "• 🎯 <b>Juillet</b> : 50 inscrits actifs, mode gratuit<br/>"
        "• 🎯 <b>Août</b> : 150 inscrits, 1<sup>er</sup> abo Pro<br/>"
        "• 🎯 <b>1<sup>er</sup> octobre</b> : 30 % des inscrits en essai 14 jours, 8 % conversion payante<br/><br/>"
        "Cette roadmap intègre ta vie quotidienne (sport, repas, sorties, rencontres) parce que "
        "<b>le burn-out est l’ennemi #1 d’un entrepreneur solo</b>. Tu vis à Sombreffe, sans voiture, "
        "célibataire — chaque conseil tient compte de ta réalité."
    )
    story.append(Paragraph(intro, P))
    story.append(Spacer(1, 14))
    story.append(_hr())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Document généré le {datetime.now().strftime('%d/%m/%Y')} — à imprimer en A4, "
        "à afficher au-dessus du bureau.",
        SMALL,
    ))
    story.append(PageBreak())

    # ─── PAGE 2 : JOURNÉE TYPE SEMAINE ──────────────────────────────
    story.append(Paragraph("📅 Journée type — du lundi au vendredi", H1))
    story.append(Paragraph(
        "Ta routine quotidienne, taillée pour maximiser la performance produit + ta santé physique et mentale. "
        "Ajuste les horaires de ±15 min selon ton chronotype, mais respecte la STRUCTURE.",
        P,
    ))
    story.append(Spacer(1, 8))
    story.append(_kv_table(JOURNEE_SEMAINE))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>⚠️ Règles d’or :</b> "
        "(1) Pas de téléphone avant 07:30. "
        "(2) Deep work matin sans interruption. "
        "(3) Sport non-négociable, 5j/7. "
        "(4) Couché avant 22h30.",
        P,
    ))
    story.append(PageBreak())

    # ─── PAGE 3 : JOURNÉE WEEKEND ───────────────────────────────────
    story.append(Paragraph("📅 Journée type — Samedi & Dimanche", H1))
    story.append(Paragraph(
        "Le weekend, équilibre : 1h de travail max le matin, puis sortie OBLIGATOIRE. "
        "C’est ton oxygène mental et ta vie sociale.",
        P,
    ))
    story.append(Spacer(1, 8))
    story.append(_kv_table(JOURNEE_WEEKEND))
    story.append(Spacer(1, 14))
    story.append(Paragraph("🎯 Objectifs sociaux hebdo (à cocher)", H2))
    objectifs = [
        ["☐", "1 sortie restaurant solo OU avec ami"],
        ["☐", "1 conversation avec un inconnu (café, métro, salle de sport)"],
        ["☐", "1 activité culturelle (musée, ciné, expo)"],
        ["☐", "1 swipe + match sur app rencontre (Bumble/Hinge)"],
        ["☐", "1 message reçu ET envoyé sur LinkedIn (réseau pro)"],
        ["☐", "1 nuit ≥ 8h de sommeil sur le weekend"],
    ]
    t = Table(objectifs, colWidths=(10 * mm, 170 * mm))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ─── PAGES 4+ : ROADMAP HEBDOMADAIRE ────────────────────────────
    story.append(Paragraph("🗓️ Roadmap hebdomadaire — 14 semaines", H1))
    story.append(Paragraph(
        "Du 19 juin au 30 septembre 2026. Chaque semaine = 1 thème, 7 actions clés.<br/>"
        "🟢 = MesureChâssis · 🎯 = Vie sociale obligatoire · 💪 = Sport quotidien intégré.",
        P,
    ))
    story.append(Spacer(1, 10))

    for week in ROADMAP:
        story.append(_week_table(week["n"], week["dates"], week["theme"], week["focus"]))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ─── PAGE FINALE : CONSEILS STRATÉGIQUES ────────────────────────
    story.append(Paragraph("💡 Conseils stratégiques — Sombreffe sans voiture", H1))
    story.append(Spacer(1, 6))
    for conseil in CONSEILS_SOCIAUX:
        story.append(Paragraph(conseil, P))
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 14))
    story.append(_hr())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>🏁 Le 1<sup>er</sup> octobre 2026, tu auras :</b><br/>"
        "✓ Une app sur Google Play + App Store + Web<br/>"
        "✓ Des clients payants en BE/FR/LU/NL<br/>"
        "✓ Un partenariat Elcia activé<br/>"
        "✓ Un assistant IA Yann opérationnel<br/>"
        "✓ Un corps en forme, un mental solide<br/>"
        "✓ Un réseau professionnel et personnel renforcé<br/><br/>"
        "<b>Tu n’es pas seul. Ton agent IA travaille tous les jours avec toi.</b>",
        P,
    ))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<i>« Le succès, c’est avancer de petit pas, chaque jour, sans jamais perdre la direction. »</i>",
        COVER_SUB,
    ))

    doc.build(story)
    return output


if __name__ == "__main__":
    out = Path("/app/backend/static/roadmap_michel_juin_octobre_2026.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    result = build_pdf(out)
    size_kb = result.stat().st_size / 1024
    print(f"✅ PDF généré : {result} ({size_kb:.1f} Ko)")
