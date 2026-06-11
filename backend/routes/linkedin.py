"""Campagne LinkedIn 15 jours — posts pré-rédigés + suivi de publication.

L'admin ouvre /admin/linkedin chaque matin : le « post du jour » s'affiche
avec son visuel de marque, il copie le texte en 1 clic, le colle dans
LinkedIn, attache l'image, puis marque le jour comme publié.
Les visuels PNG (1080×1080) sont générés par scripts/generate_linkedin_cards.py
et committés dans static/linkedin/.
"""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from db import db
from deps import require_admin

router = APIRouter()

IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "linkedin"

SITE = "https://mesurechassis.com"

# ── Les 15 posts (ton artisan authentique, objectif notoriété pré-lancement) ──
POSTS = [
    {
        "day": 1,
        "title": "Pourquoi j'ai créé MesureChâssis",
        "subtitle": "L'histoire d'un carnet de notes qui m'a coûté trop cher",
        "text": """30 ans sur les chantiers. Et toujours le même rituel : le carnet de notes, le crayon, et la prière pour que personne ne se trompe en recopiant les cotes le soir.

Un jour, une erreur de recopiage m'a coûté un châssis complet. Refabrication, délai, client mécontent. Ce jour-là, je me suis dit : il doit exister un outil pour nous. J'ai cherché. Il n'existait pas.

Alors je l'ai créé.

MesureChâssis, c'est l'application que j'aurais voulu avoir pendant toutes ces années : on prend les mesures sur chantier, guidé étape par étape, et la fiche technique part en production sans aucune ressaisie.

Pendant 15 jours, je vais vous montrer tout ce qu'elle sait faire. Suivez-moi, ça va parler à tous ceux qui ont déjà perdu une après-midi à cause d'un chiffre mal recopié. 👇

👉 {site}""",
        "hashtags": "#menuiserie #châssis #artisan #construction #BTP #digitalisation",
        "visual_kicker": "L'HISTOIRE",
    },
    {
        "day": 2,
        "title": "L'erreur à 1 500 €",
        "subtitle": "Ce que coûte vraiment un chiffre mal recopié",
        "text": """Parlons argent. Une erreur de cote, concrètement, c'est quoi ?

❌ Un châssis fabriqué aux mauvaises dimensions : 800 à 2 000 € de perte sèche
❌ 2 à 4 semaines de délai supplémentaire
❌ Un client qui ne vous rappellera pas
❌ Et la réputation, elle, ne se refabrique pas

La cause n°1 ? Ce n'est presque jamais la prise de mesure elle-même. C'est la RESSAISIE : du carnet vers le devis, du devis vers la production. Chaque recopiage est une occasion de se tromper.

MesureChâssis supprime la ressaisie : la cote saisie sur chantier est LA cote qui arrive en production. Une seule saisie, zéro recopiage, zéro erreur de transmission.

Demain, je vous montre comment l'assistant guide la prise de mesures, même pour les baies les plus tordues. 👇

👉 {site}""",
        "hashtags": "#menuiserie #artisan #rentabilité #châssis #fenêtres #BTP",
        "visual_kicker": "LE PROBLÈME",
    },
    {
        "day": 3,
        "title": "Un assistant qui vous guide, cote après cote",
        "subtitle": "Impossible d'oublier une mesure",
        "text": """Vous connaissez ce moment : retour à l'atelier, et là... « il me manque la hauteur d'allège ». Retour sur chantier. 45 minutes de route. Pour UNE cote.

L'assistant de MesureChâssis fonctionne comme une checklist intelligente :

✅ Il vous demande les mesures une par une, dans le bon ordre
✅ Largeur, hauteur, diagonales, allège, retombée de linteau... rien ne peut être oublié
✅ Il vérifie la cohérence (une diagonale incohérente ? il vous alerte sur place, pas le lendemain)
✅ Photos et notes attachées directement à chaque ouverture

Résultat : quand vous quittez le chantier, le dossier est COMPLET. Pas de retour, pas de coup de fil au client, pas de « je crois que c'était 1240 ».

Et ça marche pour toutes les formes de baies — même les plus exotiques. C'est justement le sujet de demain. 👇

👉 {site}""",
        "hashtags": "#menuiserie #priseDeMesures #artisan #châssis #productivité",
        "visual_kicker": "FONCTIONNALITÉ",
    },
    {
        "day": 4,
        "title": "12 formes de baies. Oui, même le bow-window.",
        "subtitle": "Du rectangle au plein cintre",
        "text": """« Les apps de mesure, c'est bien pour les rectangles. Mais moi, j'ai un plein cintre sur une ferme de 1890... »

Je suis du métier, je sais que nos chantiers ne sont pas des catalogues IKEA. C'est pourquoi MesureChâssis gère 12 formes de baies :

▫️ Rectangle, trapèze, parallélogramme
▫️ Plein cintre, arc surbaissé, anse de panier
▫️ Œil-de-bœuf, ovale
▫️ Pan coupé, polygone
▫️ Triangle d'about, bow-window

Pour chaque forme, l'assistant adapte automatiquement les cotes demandées : un plein cintre n'a pas les mêmes points de mesure qu'un trapèze, et l'app le sait.

Le schéma se dessine sous vos yeux pendant la saisie. Votre atelier reçoit un plan coté clair, pas un croquis sur un coin de table.

Demain : la fiche PDF qui part en production en 1 clic. 👇

👉 {site}""",
        "hashtags": "#menuiserie #châssis #fenêtres #savoirFaire #artisanat #rénovation",
        "visual_kicker": "FONCTIONNALITÉ",
    },
    {
        "day": 5,
        "title": "De la mesure à la fiche de production en 1 clic",
        "subtitle": "PDF technique prêt pour l'atelier",
        "text": """Le soir, après le chantier, il y a deux types d'artisans :

1️⃣ Celui qui passe 1h à recopier ses notes, dessiner les baies, taper la fiche pour l'atelier
2️⃣ Celui qui appuie sur un bouton

Avec MesureChâssis, chaque chantier génère en 1 clic une fiche PDF technique complète :

📄 Toutes les ouvertures avec schémas cotés
📄 Matériaux, couleurs, types de vitrage, sens d'ouverture
📄 Notes et photos de chantier
📄 En-tête à votre nom — prête à envoyer au fabricant ou à classer au dossier

La fiche est propre, standardisée, lisible par n'importe quel atelier. Fini les « c'est quoi ce chiffre là ? » au téléphone.

Et pour ceux qui bossent avec des logiciels de production : exports CSV et XML aussi (j'en reparle au jour 10).

Demain, on parle des artisans solos — l'app a été pensée pour vous d'abord. 👇

👉 {site}""",
        "hashtags": "#menuiserie #PDF #production #atelier #artisan #efficacité",
        "visual_kicker": "FONCTIONNALITÉ",
    },
    {
        "day": 6,
        "title": "Artisan solo : votre bureau tient dans votre poche",
        "subtitle": "Pensé pour ceux qui font tout, tout seuls",
        "text": """Quand on est artisan solo, on est à la fois le commercial, le métreur, l'acheteur, le poseur et le comptable. Le soir, il reste les devis. Et le carnet de notes à déchiffrer.

MesureChâssis en mode Artisan, c'est :

🔧 Vos chantiers organisés par client, avec adresse et contact
🔧 La prise de mesures guidée (fini les oublis)
🔧 Les fiches PDF générées sur place — vous pouvez les envoyer au fabricant depuis la voiture
🔧 L'historique complet : ce client vous rappelle 2 ans après ? Tout est là.

Pas d'usine à gaz : l'app fait UNE chose et la fait bien — transformer vos relevés de chantier en dossiers de production impeccables.

Vous gagnez quoi ? Environ 45 minutes par chantier. Sur une semaine à 5 relevés, c'est une demi-journée. Faites le calcul sur l'année.

Demain : le mode Entreprise, pour ceux qui bossent en équipe. 👇

👉 {site}""",
        "hashtags": "#artisan #indépendant #menuiserie #TPE #gestionDeChantier",
        "visual_kicker": "POUR LES ARTISANS",
    },
    {
        "day": 7,
        "title": "En équipe : commercial, technicien, admin — chacun son rôle",
        "subtitle": "Le mode Entreprise",
        "text": """Dans une entreprise de menuiserie, l'info circule comme ça : le commercial promet, le technicien mesure, le bureau ressaisit, l'atelier découvre. Et entre chaque étape... des pertes en ligne.

MesureChâssis en mode Entreprise structure tout ça :

👔 Le COMMERCIAL crée le chantier, renseigne le client, assigne le technicien
📐 Le TECHNICIEN reçoit sa mission sur son téléphone, fait le relevé guidé sur place
🗂️ L'ADMIN voit tout en temps réel : avancement, statistiques, exports
🔒 Chacun voit ce qu'il doit voir — pas plus, pas moins

Plus de « il est où le dossier Dupont ? ». Le dossier Dupont est dans l'app, complet, avec les photos, à la seconde où le technicien quitte le chantier.

Demain, je vous montre LA fonctionnalité préférée des patrons : le verrou fabrication. 👇

👉 {site}""",
        "hashtags": "#menuiserie #PME #équipe #organisation #BTP #management",
        "visual_kicker": "POUR LES ENTREPRISES",
    },
    {
        "day": 8,
        "title": "Le verrou fabrication : plus rien ne bouge",
        "subtitle": "La fonctionnalité préférée des patrons",
        "text": """Scénario classique : la commande part en fabrication lundi. Mercredi, quelqu'un « corrige juste une petite cote » dans le dossier. L'atelier, lui, travaille sur la version de lundi. Vous connaissez la suite.

Le VERROU FABRICATION de MesureChâssis :

🔒 Quand le chantier part en production, l'admin le verrouille
🔒 Plus aucune modification possible — par personne
🔒 Le dossier devient LA référence unique et définitive
🔒 Besoin de changer quand même ? Seul l'admin peut déverrouiller, en conscience, et ça se voit

C'est simple, presque bête. Mais ça élimine une source d'erreurs que tous les ateliers connaissent : la cote modifiée après le lancement de fab.

La confiance entre le terrain, le bureau et l'atelier, ça se construit avec des outils comme ça.

Demain : pourquoi l'app parle 3 langues (et ce que ça change en Belgique). 👇

👉 {site}""",
        "hashtags": "#menuiserie #production #qualité #atelier #PME #process",
        "visual_kicker": "POUR LES ENTREPRISES",
    },
    {
        "day": 9,
        "title": "FR / EN / NL : une app qui parle comme vos équipes",
        "subtitle": "Pensée pour la Belgique (et au-delà)",
        "text": """En Belgique, un chantier peut commencer en français à Charleroi et finir en néerlandais à Anvers. Et nos équipes sont à l'image du pays : multilingues.

MesureChâssis est intégralement trilingue :

🇫🇷 Français
🇬🇧 Anglais
🇳🇱 Néerlandais

Chaque utilisateur choisit SA langue. Le technicien flamand travaille en néerlandais, le bureau francophone en français — sur le MÊME chantier, dans la MÊME app.

Et les documents suivent : les fiches PDF sortent dans la langue de votre choix. Un fabricant aux Pays-Bas ? Fiche en néerlandais. Un client international ? Fiche en anglais.

C'est un détail pour certains. Pour ceux qui travaillent des deux côtés de la frontière linguistique, c'est un vrai confort au quotidien.

Demain : les exports CSV/XML pour connecter l'app à vos logiciels. 👇

👉 {site}""",
        "hashtags": "#Belgique #menuiserie #multilingue #Flandre #Wallonie #export",
        "visual_kicker": "FONCTIONNALITÉ",
    },
    {
        "day": 10,
        "title": "CSV, XML, PDF : vos données vous appartiennent",
        "subtitle": "Compatible avec vos outils de production",
        "text": """Une app métier qui garde vos données en otage, c'est non. J'en ai trop vu.

MesureChâssis exporte tout, dans les formats que les logiciels de production comprennent :

📊 CSV — pour vos tableurs, vos devis, votre compta
📐 XML structuré — pour l'intégration avec les logiciels de fabrication
📄 PDF — pour l'humain : fiches techniques cotées et illustrées

Concrètement : le relevé fait sur chantier le matin peut être dans votre logiciel de chiffrage l'après-midi, sans une seule ressaisie.

Vos données restent VOS données. Vous les exportez quand vous voulez, vous en faites ce que vous voulez.

(Et pour les utilisateurs d'ERP métier type Elcia ou Ramasoft : des passerelles dédiées sont dans les tuyaux 😉)

Demain : le tableau de bord qui vous dit où en sont tous vos chantiers, en un coup d'œil. 👇

👉 {site}""",
        "hashtags": "#menuiserie #données #ERP #interopérabilité #production #BTP",
        "visual_kicker": "FONCTIONNALITÉ",
    },
    {
        "day": 11,
        "title": "Tous vos chantiers, en un coup d'œil",
        "subtitle": "Suivi et statistiques en temps réel",
        "text": """Combien de chantiers en cours ? Combien d'ouvertures relevées cette semaine ? Lequel attend depuis 10 jours ?

Si la réponse est « il faudrait que je demande »... ce post est pour vous.

Le tableau de bord MesureChâssis affiche en temps réel :

📊 Vos chantiers par statut : en cours, à mesurer, en fabrication, terminés
📊 L'activité de l'équipe : qui a relevé quoi, quand
📊 Les statistiques : ouvertures par mois, par technicien, par type
📊 Les chantiers qui dorment (et qu'il faudrait réveiller)

Pour un patron, c'est la fin du « point chantiers » du lundi qui dure 1h. L'info est là, à jour, dans la poche.

Demain, je vous raconte un truc plus personnel : comment un menuisier de métier a réussi à créer une application mobile. Spoiler : sans savoir coder. 👇

👉 {site}""",
        "hashtags": "#tableauDeBord #gestion #menuiserie #PME #pilotage #BTP",
        "visual_kicker": "POUR LES ENTREPRISES",
    },
    {
        "day": 12,
        "title": "Un menuisier qui code ? Non. Un menuisier qui ose.",
        "subtitle": "Les coulisses de la création",
        "text": """On me demande souvent : « Mais Michel, tu sais coder, toi ? »

Non. Je sais mesurer un châssis, poser une fenêtre, et reconnaître une erreur de cote à 10 mètres. C'est exactement pour ça que MesureChâssis fonctionne.

Les outils génériques sont créés par des développeurs qui n'ont jamais mis les pieds sur un chantier. Moi, j'ai fait l'inverse : 30 ans de terrain, et les technologies d'aujourd'hui (oui, l'IA m'a beaucoup aidé) pour transformer cette expérience en application.

Chaque écran, chaque cote demandée, chaque alerte vient d'une situation réelle que j'ai vécue :
🔹 La diagonale qu'on oublie ? Vécue.
🔹 La cote modifiée après le départ en fab ? Vécue.
🔹 Le retour sur chantier pour UNE mesure ? Vécue. Trop de fois.

La leçon que j'en tire : notre expertise métier vaut de l'or. Les outils pour la transformer en solutions n'ont jamais été aussi accessibles. Osez.

Demain : comment économiser 2 mois d'abonnement (légalement 😄). 👇

👉 {site}""",
        "hashtags": "#entrepreneuriat #artisanat #reconversion #IA #innovation #menuiserie",
        "visual_kicker": "LES COULISSES",
    },
    {
        "day": 13,
        "title": "Parrainez un confrère, gagnez 2 mois",
        "subtitle": "Le programme de parrainage",
        "text": """Dans notre métier, les bons outils se transmettent de bouche à oreille. Une bonne visseuse, un bon fournisseur, une bonne app : on se le dit entre confrères.

J'ai voulu récompenser ça. Le programme de parrainage MesureChâssis :

🤝 Vous parrainez une entreprise ou un artisan avec votre code personnel
🎁 Dès qu'il devient client actif : 2 MOIS OFFERTS sur votre abonnement
🎁 Et lui démarre accompagné — tout le monde y gagne
♾️ Sans limite : 5 filleuls = 10 mois offerts

Le code se partage en 2 secondes depuis l'app (WhatsApp, SMS, email).

Vous connaissez un confrère qui note encore ses cotes sur un bout de placo ? Vous savez quoi faire. 😄

Demain : ce que les premiers utilisateurs en disent. 👇

👉 {site}""",
        "hashtags": "#parrainage #menuiserie #artisan #boucheAOreille #communauté",
        "visual_kicker": "BON PLAN",
    },
    {
        "day": 14,
        "title": "Ils l'utilisent avant tout le monde",
        "subtitle": "Ce que disent les premiers retours",
        "text": """Depuis quelques semaines, des artisans et entreprises de menuiserie utilisent MesureChâssis en avant-première. Leurs retours façonnent l'app chaque jour.

Ce qui revient le plus :

💬 « Le guidage des mesures, c'est exactement ce qui manquait. Même mon apprenti ne peut plus rien oublier. »
💬 « La fiche PDF est plus propre que ce que je faisais en 1h sur l'ordinateur. »
💬 « Le verrou fabrication a déjà évité une boulette chez nous. »

Et le plus beau compliment qu'on m'ait fait : « On sent que c'est un gars du métier qui l'a pensée. »

Chaque suggestion est lue (par moi, pas par un chatbot) et les meilleures sont déjà dans l'app. C'est ça, construire un outil AVEC le métier plutôt que POUR le métier.

Demain, dernier jour de cette série : le récap complet et la suite de l'aventure. Ne le manquez pas. 👇

👉 {site}""",
        "hashtags": "#témoignages #menuiserie #artisan #feedback #communauté",
        "visual_kicker": "ILS EN PARLENT",
    },
    {
        "day": 15,
        "title": "15 jours, 15 fonctionnalités : le récap",
        "subtitle": "Et maintenant, à vous de jouer",
        "text": """Il y a 15 jours, je vous racontais l'erreur de recopiage qui m'a poussé à créer MesureChâssis. Récap de tout ce qu'on a vu :

✅ Assistant de mesures guidé — zéro oubli (J3)
✅ 12 formes de baies, du rectangle au bow-window (J4)
✅ Fiches PDF de production en 1 clic (J5)
✅ Mode artisan solo (J6) et mode entreprise avec rôles (J7)
✅ Verrou fabrication (J8)
✅ Trilingue FR/EN/NL (J9)
✅ Exports CSV/XML (J10)
✅ Tableau de bord temps réel (J11)
✅ Parrainage : 2 mois offerts (J13)

Tout ça, créé par un menuisier, pour les menuisiers.

📲 L'application arrive très bientôt sur l'App Store et Google Play.
🌐 En attendant : toutes les infos sur {site}

Si cette série vous a plu ou fait penser à un confrère : un partage de ce post est le plus beau coup de main que vous puissiez me donner. 🙏

Merci de m'avoir suivi. L'aventure ne fait que commencer. 🚀""",
        "hashtags": "#menuiserie #châssis #lancement #artisan #construction #BTP #app",
        "visual_kicker": "LE RÉCAP",
    },
]

for _p in POSTS:
    _p["text"] = _p["text"].replace("{site}", SITE)
    # Sécurité : retire tout retour à la ligne accidentel dans les hashtags
    _p["hashtags"] = " ".join(_p["hashtags"].split())


def _progress_key(day: int) -> dict:
    return {"key": "linkedin_day", "day": day}


async def _posted_days() -> set:
    docs = await db.linkedin_progress.find({}, {"day": 1}).to_list(50)
    return {d["day"] for d in docs}


@router.get("/linkedin/today")
async def linkedin_today(user=Depends(require_admin)):
    """Le post du jour = premier jour non encore publié."""
    posted = await _posted_days()
    current = next((p for p in POSTS if p["day"] not in posted), None)
    return {
        "total": len(POSTS),
        "posted_count": len(posted),
        "done": current is None,
        "post": current,
        "image_url": f"/api/linkedin/image/{current['day']}" if current else None,
    }


@router.get("/linkedin/posts")
async def linkedin_posts(user=Depends(require_admin)):
    posted = await _posted_days()
    return {
        "posts": [
            {**p, "posted": p["day"] in posted, "image_url": f"/api/linkedin/image/{p['day']}"}
            for p in POSTS
        ]
    }


@router.post("/linkedin/mark-posted")
async def mark_posted(payload: dict, user=Depends(require_admin)):
    day = payload.get("day")
    if not isinstance(day, int) or not 1 <= day <= len(POSTS):
        raise HTTPException(400, "Jour invalide")
    await db.linkedin_progress.update_one(
        {"day": day},
        {"$set": {"day": day, "posted_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "message": f"Jour {day} marqué comme publié 🎉"}


@router.post("/linkedin/unmark-posted")
async def unmark_posted(payload: dict, user=Depends(require_admin)):
    """Annule un marquage (mauvaise manip)."""
    day = payload.get("day")
    res = await db.linkedin_progress.delete_one({"day": day})
    if res.deleted_count == 0:
        raise HTTPException(404, "Ce jour n'était pas marqué comme publié")
    return {"ok": True}


@router.get("/linkedin/image/{day}")
async def linkedin_image(day: int):
    """Visuel PNG 1080×1080 du jour — public (contenu marketing, aucun secret).

    Public pour permettre l'appui long → « Enregistrer l'image » sur iPhone
    (les balises <img> n'envoient pas le header Authorization).
    """
    path = IMAGES_DIR / f"jour_{day:02d}.png"
    if not 1 <= day <= len(POSTS) or not path.exists():
        raise HTTPException(404, "Visuel introuvable")
    return FileResponse(path, media_type="image/png", filename=f"mesurechassis_linkedin_jour{day}.png")
