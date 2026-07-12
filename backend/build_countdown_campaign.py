"""Génère les 31 visuels + captions de la campagne countdown "Jeton Café".

Option A retenue par l'utilisateur : SAFE (aucune marque nommée, teasing vague uniquement).
Thème visuel : Café / marron chaleureux + logo MesureChâssis + gros compteur "J-XX".

Sortie :
  /app/backend/public_downloads/countdown/day_XX.png            (31 × 1080×1080 PNG)
  /app/backend/public_downloads/countdown/captions.json         (LinkedIn/Facebook/Instagram)
  /app/backend/public_downloads/countdown_v1.zip                (ZIP complet)

Pivot :
  Jour J = 12 août 2026  →  J-30 = 13 juillet 2026
"""
from __future__ import annotations

import json
import os
import zipfile
from datetime import date, datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = "/app/backend/public_downloads/countdown"
os.makedirs(OUT, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════
J_ZERO = date(2026, 8, 12)   # Jour J = 12 août 2026
SIZE = 1080                  # Format carré Instagram/LinkedIn/Facebook

# Palette Café / marron chaleureux
BG_DARK = (46, 26, 16)          # marron café expresso
BG_MID = (78, 52, 38)           # marron moyen
BG_LIGHT = (110, 74, 54)        # marron latte
CREAM = (245, 230, 211)         # crème (texte principal)
CREAM_SOFT = (222, 205, 180)    # crème adouci
GOLD = (215, 168, 110)          # doré caramel (accent)
GOLD_BRIGHT = (240, 195, 130)   # doré vif
WHITE = (255, 255, 255)
MUTED = (168, 148, 122)


_FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def font(size: int, bold: bool = True):
    p = _FONT_BOLD if bold else _FONT_REG
    return ImageFont.truetype(p, size)


# ═══════════════════════════════════════════════════════════════════════
# CONTENU — 31 jours (J-30 à J-0)
# 3 captions par jour : LinkedIn (pro/long), Facebook (chaleureux), Instagram (court + emojis)
# ═══════════════════════════════════════════════════════════════════════
HASH_COMMON = "#MesureChâssis #JetonCafé #Menuiserie #ArtisansPro"
HASH_LI = HASH_COMMON + " #Belgique #Wallonie #Bruxelles #Productivité"
HASH_FB = HASH_COMMON + " #Artisan #Chantier #FenêtresPortes"
HASH_IG = HASH_COMMON + " #Métier #ChantierLife #Café #Fenêtre #Menuisier #Belgique"

# Chaque entrée : n, title (affiché sur le visuel), et 3 captions
DAYS = [
    # ═══ Phase 1 · Annonce & transparence (J-30 → J-24) ══════════════
    {
        "n": 30, "title": "Le compte à rebours commence",
        "linkedin": (
            "☕ J-30 avant un lancement pensé pour les menuisiers de Wallonie et de Bruxelles.\n\n"
            "Chaque jour à partir d'aujourd'hui, je vais partager avec vous une pièce du puzzle. "
            "Une seule promesse : à la fin, il y aura du café. Beaucoup de café. Offert aux artisans qui "
            "utilisent MesureChâssis sur leurs chantiers.\n\n"
            "Restez branchés. 👀\n\n" + HASH_LI
        ),
        "facebook": (
            "☕ J-30 ! Aujourd'hui commence un compte à rebours de 30 jours. À la clé : une belle surprise "
            "pour tous les menuisiers professionnels de Wallonie et Bruxelles.\n\n"
            "Restez avec nous, ça vaut le coup 😉\n\n" + HASH_FB
        ),
        "instagram": (
            "☕ J-30. Le compte à rebours démarre. 🎉\n\n"
            "Menuisiers pros, restez branchés — une surprise vous attend le 12 août. 🪟✨\n\n" + HASH_IG
        ),
    },
    {
        "n": 29, "title": "Je m'appelle Michel",
        "linkedin": (
            "👋 J-29. Je m'appelle Michel Pezzuto. Menuisier de métier, fondateur de MesureChâssis.\n\n"
            "J'ai passé les 18 derniers mois à construire un outil pour les gens qui sortent leur mètre "
            "ruban dans le froid le matin. Pas pour un investisseur. Pas pour la Silicon Valley. Pour vous.\n\n"
            "Aujourd'hui, on lance un compte à rebours ensemble. Le 12 août, quelque chose va changer pour "
            "les menuisiers du plat pays. 🇧🇪\n\n" + HASH_LI
        ),
        "facebook": (
            "👋 J-29. Salut ! Moi c'est Michel. Menuisier depuis longtemps, développeur d'une petite app "
            "à côté depuis 18 mois : MesureChâssis.\n\n"
            "Rendez-vous ici chaque jour jusqu'au 12 août pour une belle surprise 💛\n\n" + HASH_FB
        ),
        "instagram": (
            "👋 J-29. Moi c'est Michel, menuisier + fondateur de MesureChâssis. 🪟\n\n"
            "On se retrouve chaque jour ici jusqu'au 12 août ! 📆✨\n\n" + HASH_IG
        ),
    },
    {
        "n": 28, "title": "Le vrai problème",
        "linkedin": (
            "🤔 J-28. Combien de fois avez-vous perdu un carnet de mesures dans le camion ?\n"
            "Combien de fois avez-vous re-mesuré une fenêtre parce que vous ne saviez plus si c'était "
            "1246 ou 1264 mm ?\n\n"
            "Ce problème n'est pas normal. Il coûte du temps, de l'argent, de la crédibilité. "
            "MesureChâssis existe pour ça.\n\n" + HASH_LI
        ),
        "facebook": (
            "🤔 J-28. Vous avez déjà perdu un carnet de mesures dans le camion ? Re-mesuré une fenêtre "
            "parce que vous ne saviez plus si c'était 1246 ou 1264 mm ?\n\n"
            "On est passés par là. Et on a construit une solution 💪\n\n" + HASH_FB
        ),
        "instagram": (
            "📓❌ J-28. Perdre son carnet de mesures = perdre 2h.\n\n"
            "Y'a mieux à faire. 🪟💡\n\n" + HASH_IG
        ),
    },
    {
        "n": 27, "title": "On a écrit aux géants",
        "linkedin": (
            "📩 J-27. Transparence totale : nous avons envoyé une proposition à plusieurs grands réseaux "
            "de stations-service actifs en Belgique.\n\n"
            "L'idée ? Offrir un café aux menuisiers pros qui utilisent MesureChâssis sur leurs chantiers. "
            "Un vrai partenariat, du vrai café, une vraie reconnaissance du métier.\n\n"
            "Réponse dans 27 jours. On croise les doigts. 🤞\n\n" + HASH_LI
        ),
        "facebook": (
            "📩 J-27. On a écrit aux grandes enseignes de carburants pour leur proposer un truc simple : "
            "offrir un café aux menuisiers pros.\n\n"
            "Qui va dire OUI en premier ? 👀\n\n" + HASH_FB
        ),
        "instagram": (
            "📩 J-27. On a écrit aux géants. ⛽☕\n\n"
            "Réponse bientôt. 🤞\n\n" + HASH_IG
        ),
    },
    {
        "n": 26, "title": "Et aux fabricants",
        "linkedin": (
            "🏭 J-26. On a aussi contacté plusieurs grands fabricants européens de profilés fenêtres "
            "(PVC, alu, mixte).\n\n"
            "Leur proposer de soutenir les artisans du terrain — les vrais, ceux qui posent chaque semaine "
            "leurs produits sur les chantiers. Qui répondra le premier ?\n\n"
            "On est patients. Et on est nombreux. 🇧🇪\n\n" + HASH_LI
        ),
        "facebook": (
            "🏭 J-26. Les fabricants de fenêtres et de profilés sont aussi de la partie.\n\n"
            "On leur a proposé de soutenir les menuisiers pros. À suivre… 👀\n\n" + HASH_FB
        ),
        "instagram": (
            "🏭 J-26. Fabricants alu, PVC, bois : à vous de jouer ! 🪟💪\n\n" + HASH_IG
        ),
    },
    {
        "n": 25, "title": "Pourquoi le café ?",
        "linkedin": (
            "☕ J-25. Pourquoi parler café dans une campagne pour menuisiers ?\n\n"
            "Parce que le café est LE rituel du chantier. Avant chaque mesure, chaque devis, chaque "
            "discussion avec le client, il y a un café. C'est notre langage commun.\n\n"
            "On veut vous l'offrir. Reste à trouver qui accepte de nous accompagner. 🤝\n\n" + HASH_LI
        ),
        "facebook": (
            "☕ J-25. Le café est le rituel du chantier. Avant chaque mesure, chaque devis, il y a un café.\n\n"
            "On veut vous l'offrir. C'est aussi simple que ça 💛\n\n" + HASH_FB
        ),
        "instagram": (
            "☕ J-25. Le café = la vraie monnaie du chantier. 💛\n\n" + HASH_IG
        ),
    },
    {
        "n": 24, "title": "Wallonie & Bruxelles",
        "linkedin": (
            "🇧🇪 J-24. La campagne concernera dans un premier temps la Wallonie et Bruxelles.\n\n"
            "Parce que c'est chez nous. Parce qu'on connaît le terrain. Parce qu'on a rencontré "
            "personnellement des dizaines de menuisiers d'ici.\n\n"
            "Flandres, France, Luxembourg : votre tour arrive juste après. 🌍\n\n" + HASH_LI
        ),
        "facebook": (
            "🇧🇪 J-24. On commence par la Wallonie et Bruxelles. Parce que c'est chez nous, parce qu'on "
            "connaît le terrain.\n\n"
            "Flandres, France, Luxembourg : ne bougez pas, votre tour arrive ! 🌍\n\n" + HASH_FB
        ),
        "instagram": (
            "🇧🇪 J-24. Wallonie & Bruxelles d'abord. Le reste ensuite. 🌍✨\n\n" + HASH_IG
        ),
    },
    # ═══ Phase 2 · Features App (J-23 → J-15) ════════════════════════
    {
        "n": 23, "title": "14 formes de châssis",
        "linkedin": (
            "🪟 J-23. Fenêtre rectangle, cintrée, triangle, œil-de-bœuf, trapèze, anse de panier, "
            "coulissant, porte d'entrée…\n\n"
            "14 formes différentes reconnues et modélisées dans MesureChâssis. Chaque forme a ses cotes, "
            "ses tolérances, ses règles métier.\n\n"
            "Qu'est-ce qu'il vous manque encore ? Dites-le en commentaire. 👇\n\n" + HASH_LI
        ),
        "facebook": (
            "🪟 J-23. 14 formes de châssis prises en charge : rectangle, cintré, triangle, œil-de-bœuf, "
            "trapèze, coulissant, porte d'entrée, etc.\n\n"
            "Il manque quelque chose ? Dites-le en commentaire 👇\n\n" + HASH_FB
        ),
        "instagram": (
            "🪟 J-23. 14 formes de châssis. Tout est prévu. ✅\n\n" + HASH_IG
        ),
    },
    {
        "n": 22, "title": "L'IA lit ton cahier des charges",
        "linkedin": (
            "🤖 J-22. Votre client vous envoie un PDF de 8 pages avec 22 fenêtres à mesurer ?\n\n"
            "L'IA de MesureChâssis le lit à votre place. En 45 secondes, elle extrait toutes les "
            "ouvertures, les cotes, les matériaux, les couleurs et même les coordonnées du client.\n\n"
            "Vous vérifiez. Vous validez. Vous gagnez 30 minutes par chantier. ⏱️\n\n" + HASH_LI
        ),
        "facebook": (
            "🤖 J-22. L'IA de MesureChâssis lit vos cahiers des charges à votre place. En 45 secondes, "
            "toutes les fenêtres sont extraites du PDF client.\n\n"
            "30 minutes gagnées par chantier ⏱️\n\n" + HASH_FB
        ),
        "instagram": (
            "🤖 J-22. PDF client → IA → chantier créé en 45 sec. ⚡\n\n" + HASH_IG
        ),
    },
    {
        "n": 21, "title": "Exports PDF, Excel, ERP",
        "linkedin": (
            "📄 J-21. Un chantier = 4 formats d'export : PDF client brandé à votre logo, Excel devis, "
            "CSV ERP, JSON API.\n\n"
            "Branchez-le à votre logiciel de fabrication. Utilisez-le comme vous voulez. Nous ne vous "
            "enfermons jamais dans notre écosystème.\n\n" + HASH_LI
        ),
        "facebook": (
            "📄 J-21. 4 formats d'export : PDF client, Excel devis, CSV ERP, JSON API.\n\n"
            "Utilisez-les comme vous voulez. Zéro enfermement 💪\n\n" + HASH_FB
        ),
        "instagram": (
            "📄 J-21. PDF · Excel · ERP · JSON. Vous choisissez. ✅\n\n" + HASH_IG
        ),
    },
    {
        "n": 20, "title": "Photos anti-litige",
        "linkedin": (
            "📸 J-20. Chaque ouverture peut recevoir jusqu'à 6 photos horodatées et géolocalisées.\n\n"
            "Le client signe sur votre écran. Signature + photos + heure GMT + coordonnées GPS = valeur "
            "juridique dans un tribunal FR ou BE.\n\n"
            "Fini les litiges du type « je n'avais pas commandé ça ». 🛡️\n\n" + HASH_LI
        ),
        "facebook": (
            "📸 J-20. 6 photos par ouverture, horodatées + GPS + signature client sur votre écran.\n\n"
            "Fini les litiges 🛡️\n\n" + HASH_FB
        ),
        "instagram": (
            "📸 J-20. Photos + signature + GPS. Anti-litige. 🛡️\n\n" + HASH_IG
        ),
    },
    {
        "n": 19, "title": "Yann, ton copilote IA",
        "linkedin": (
            "🤖 J-19. Yann est un copilote IA intégré dans MesureChâssis. Il connaît les DTU (36.5, 44.1), "
            "les normes EN 14351, les tolérances par pays.\n\n"
            "Demandez-lui : « Quelle est la tolérance sur un châssis alu en rénovation en Belgique ? » "
            "Réponse en 5 secondes, avec sources.\n\n"
            "Formation continue offerte à chaque abonné pro. 🎓\n\n" + HASH_LI
        ),
        "facebook": (
            "🤖 J-19. Yann, notre copilote IA, connaît toutes les normes (DTU, EN 14351, tolérances par "
            "pays).\n\n"
            "Vous posez une question métier, il répond en 5 sec. 🎓\n\n" + HASH_FB
        ),
        "instagram": (
            "🤖 J-19. Yann. IA. Normes. 5 secondes. 🎓\n\n" + HASH_IG
        ),
    },
    {
        "n": 18, "title": "En équipe ou en solo",
        "linkedin": (
            "👥 J-18. Solo dans votre camion ou 15 dans votre atelier ? MesureChâssis s'adapte.\n\n"
            "4 rôles : Admin, Commercial, Technicien, Lecture. Chacun voit ce dont il a besoin. Workflow "
            "anti-bourdes intégré (validation double, verrouillage automatique après export…).\n\n" + HASH_LI
        ),
        "facebook": (
            "👥 J-18. Solo ou en équipe, MesureChâssis s'adapte à votre taille.\n\n"
            "4 rôles, workflow anti-bourdes, verrouillage auto. 💪\n\n" + HASH_FB
        ),
        "instagram": (
            "👥 J-18. Solo · Duo · Équipe. Ça marche. ✅\n\n" + HASH_IG
        ),
    },
    {
        "n": 17, "title": "Bientôt : offline & laser",
        "linkedin": (
            "📡 J-17. Ce qui arrive dans les prochains mois :\n"
            "  • Mode hors-ligne complet (chantier à la cave = pas de souci)\n"
            "  • Connexion Bluetooth avec télémètre laser (Leica DISTO, Bosch GLM)\n"
            "  • Import Odoo pour génération de devis automatique (plan MAX)\n\n"
            "Des idées de features ? Écrivez-les en commentaire, je lis tout. 👇\n\n" + HASH_LI
        ),
        "facebook": (
            "📡 J-17. Bientôt disponibles :\n"
            "• Mode hors-ligne ✅\n"
            "• Télémètre laser Bluetooth 📏\n"
            "• Auto-devis Odoo 📊\n\n"
            "Des idées ? Dites-nous 👇\n\n" + HASH_FB
        ),
        "instagram": (
            "📡 J-17. Roadmap : offline · laser · devis auto. 🚀\n\n" + HASH_IG
        ),
    },
    {
        "n": 16, "title": "Guide débutant",
        "linkedin": (
            "📘 J-16. Nous avons écrit un guide de 12 pages A4 pour les métreurs qui découvrent l'app.\n\n"
            "De la définition d'une fenêtre jusqu'à votre premier export PDF. Disponible dans l'app, "
            "gratuit, imprimable. À coller dans le camion de votre apprenti. 📗\n\n" + HASH_LI
        ),
        "facebook": (
            "📘 J-16. Guide débutant en 12 pages A4, gratuit et imprimable dans l'app.\n\n"
            "Parfait pour former votre apprenti 🎓\n\n" + HASH_FB
        ),
        "instagram": (
            "📘 J-16. Guide débutant. Gratuit. Dans l'app. 🎓\n\n" + HASH_IG
        ),
    },
    {
        "n": 15, "title": "Guide pro bois/alu/PVC",
        "linkedin": (
            "📗 J-15. Un deuxième guide pour les pros : spécificités bois / alu / PVC, normes RT 2020, "
            "tolérances par matériau, workflow atelier.\n\n"
            "Écrit par un menuisier pour des menuisiers. Zéro jargon Silicon Valley. 🪵\n\n" + HASH_LI
        ),
        "facebook": (
            "📗 J-15. Guide pro : bois, alu, PVC. Toutes les normes RT 2020 + tolérances par matériau.\n\n"
            "Écrit par un menuisier pour des menuisiers 🪵\n\n" + HASH_FB
        ),
        "instagram": (
            "📗 J-15. Bois · Alu · PVC. Le guide pro. 🪵\n\n" + HASH_IG
        ),
    },
    # ═══ Phase 3 · Suspense & communauté (J-14 → J-8) ════════════════
    {
        "n": 14, "title": "Une réponse arrive...",
        "linkedin": (
            "📨 J-14. Petite mise à jour transparence : nous avons reçu une première réponse.\n\n"
            "De la part de qui ? Je ne peux pas encore le dire. Est-ce un oui, un peut-être, une "
            "contre-proposition ? Bientôt. 👀\n\n" + HASH_LI
        ),
        "facebook": (
            "📨 J-14. Première réponse reçue. Positive ? Négative ? Contre-proposition ?\n\n"
            "On vous tiendra au courant 👀\n\n" + HASH_FB
        ),
        "instagram": (
            "📨 J-14. Ça bouge. 👀\n\n" + HASH_IG
        ),
    },
    {
        "n": 13, "title": "À votre avis ?",
        "linkedin": (
            "🤔 J-13. Petit sondage : selon vous, quelle enseigne de carburant va avoir le courage de "
            "dire OUI aux menuisiers wallons ?\n\n"
            "Commentez votre pronostic. Le gagnant sera dévoilé le 12 août. 🏆\n\n" + HASH_LI
        ),
        "facebook": (
            "🤔 J-13. Sondage ! Quelle enseigne de stations-service dira OUI en premier ?\n\n"
            "Votre pronostic en commentaire 👇 Le gagnant sera dévoilé le 12 août 🏆\n\n" + HASH_FB
        ),
        "instagram": (
            "🤔 J-13. Sondage ! Quelle station dira OUI ? ⛽☕\n\n"
            "Votre avis en commentaire 👇\n\n" + HASH_IG
        ),
    },
    {
        "n": 12, "title": "Testé par des vrais",
        "linkedin": (
            "🛠️ J-12. L'app est testée sur le terrain depuis plusieurs mois par des menuisiers de "
            "Wallonie.\n\n"
            "Retours : gain de temps sur chaque chantier, moins d'erreurs, clients rassurés.\n\n"
            "Mais on ne va pas faire les fiers : on a encore plein de choses à améliorer. On écoute.\n\n"
            + HASH_LI
        ),
        "facebook": (
            "🛠️ J-12. Testée depuis des mois par de vrais menuisiers wallons.\n\n"
            "Retours : gain de temps, moins d'erreurs, clients rassurés 💪\n\n" + HASH_FB
        ),
        "instagram": (
            "🛠️ J-12. Testée par des vrais menuisiers. 🇧🇪\n\n" + HASH_IG
        ),
    },
    {
        "n": 11, "title": "Gratuit pour toujours",
        "linkedin": (
            "💛 J-11. Le plan Freemium restera gratuit à vie.\n\n"
            "Pas de piège. Pas de carte bancaire à l'inscription. Pas de « oups, ton essai gratuit vient "
            "de finir ». Vous téléchargez, vous utilisez. Point.\n\n"
            "3 chantiers gratuits pour tester + toutes les features de mesure sur ces 3 chantiers.\n\n" + HASH_LI
        ),
        "facebook": (
            "💛 J-11. Freemium gratuit à vie. 3 chantiers offerts pour tester, sans carte bancaire.\n\n"
            "Zéro piège. Promis.\n\n" + HASH_FB
        ),
        "instagram": (
            "💛 J-11. 3 chantiers gratuits. Sans carte. À vie. ✅\n\n" + HASH_IG
        ),
    },
    {
        "n": 10, "title": "Tes données restent tes données",
        "linkedin": (
            "🔒 J-10. Zéro tracking. Aucun SDK publicitaire. Aucune revente à des tiers.\n\n"
            "Vos chantiers sont hébergés sur nos serveurs européens (Belgique / France). RGPD strict. "
            "Suppression sur simple demande.\n\n"
            "Vos données restent VOS données. 🔐\n\n" + HASH_LI
        ),
        "facebook": (
            "🔒 J-10. Zéro tracking, zéro pub, zéro revente. RGPD strict.\n\n"
            "Vos données = VOS données 🔐\n\n" + HASH_FB
        ),
        "instagram": (
            "🔒 J-10. Zéro tracking. RGPD strict. 🇪🇺\n\n" + HASH_IG
        ),
    },
    {
        "n": 9, "title": "Sur l'App Store cette semaine",
        "linkedin": (
            "🍎 J-9. L'app est en cours de validation par Apple. Elle sera disponible sur l'App Store "
            "dans les prochains jours.\n\n"
            "Android (Google Play) : en préparation. Version web : disponible dès maintenant sur "
            "mesurechassis.com.\n\n" + HASH_LI
        ),
        "facebook": (
            "🍎 J-9. Bientôt sur l'App Store ! Android en préparation. Web dispo dès maintenant.\n\n"
            "👉 mesurechassis.com\n\n" + HASH_FB
        ),
        "instagram": (
            "🍎 J-9. Bientôt sur l'App Store 📱\n\n" + HASH_IG
        ),
    },
    {
        "n": 8, "title": "8 jours et le voile tombe",
        "linkedin": (
            "⏳ J-8. On approche. À nos partenaires potentiels (stations-service et fabricants "
            "menuiseries) : c'est LE moment de nous répondre.\n\n"
            "Pour tous les autres : téléchargez l'app maintenant, vous serez notifiés en direct le 12 août "
            "à 8h00.\n\n" + HASH_LI
        ),
        "facebook": (
            "⏳ J-8. On approche. Partenaires potentiels : c'est le moment !\n\n"
            "Menuisiers : téléchargez l'app pour être notifiés en direct 📲\n\n" + HASH_FB
        ),
        "instagram": (
            "⏳ J-8. Ça approche. 👀\n\n" + HASH_IG
        ),
    },
    # ═══ Phase 4 · Countdown final (J-7 → J-0) ═══════════════════════
    {
        "n": 7, "title": "Une semaine",
        "linkedin": (
            "🗓️ J-7. Une semaine avant le grand jour.\n\n"
            "Si vous êtes menuisier professionnel en Wallonie ou à Bruxelles, téléchargez MesureChâssis "
            "maintenant. Soyez parmi les premiers à savoir quelle enseigne accepte notre défi.\n\n" + HASH_LI
        ),
        "facebook": (
            "🗓️ J-7. Une semaine.\n\n"
            "Téléchargez l'app maintenant pour être prévenus en direct 📲\n\n" + HASH_FB
        ),
        "instagram": (
            "🗓️ J-7. Une. Seule. Semaine. 🔥\n\n" + HASH_IG
        ),
    },
    {
        "n": 6, "title": "6 jours, ça devient sérieux",
        "linkedin": (
            "☕ J-6. Notre partenaire café va bientôt se dévoiler. Les discussions ont bien avancé cette "
            "semaine.\n\n"
            "Spoiler : ça va vous plaire. 😉\n\n" + HASH_LI
        ),
        "facebook": (
            "☕ J-6. Les discussions avancent 🔥 Spoiler : ça va vous plaire 😉\n\n" + HASH_FB
        ),
        "instagram": (
            "☕ J-6. Ça se précise. 🔥\n\n" + HASH_IG
        ),
    },
    {
        "n": 5, "title": "Presque là",
        "linkedin": (
            "🏁 J-5. Encore quelques jours. Toutes les fonctionnalités sont en place. L'équipe est prête. "
            "Les guides sont imprimés.\n\n"
            "Il ne manque que le grand OUI de notre partenaire. 🤞\n\n" + HASH_LI
        ),
        "facebook": (
            "🏁 J-5. Tout est prêt. Il manque juste LE OUI. 🤞\n\n" + HASH_FB
        ),
        "instagram": (
            "🏁 J-5. Presque là. 🤞\n\n" + HASH_IG
        ),
    },
    {
        "n": 4, "title": "Prêts ?",
        "linkedin": (
            "🎯 J-4. Vous êtes prêts ? Nous, on est nerveux. Beaucoup.\n\n"
            "Mais aussi excités comme des gamins la veille d'un anniversaire. Merci de nous suivre "
            "depuis 26 jours. 🙏\n\n" + HASH_LI
        ),
        "facebook": (
            "🎯 J-4. Nerveux + excités = MesureChâssis prête au décollage 🚀\n\n" + HASH_FB
        ),
        "instagram": (
            "🎯 J-4. Prêts ? 🚀\n\n" + HASH_IG
        ),
    },
    {
        "n": 3, "title": "Dans 3 jours",
        "linkedin": (
            "🥁 J-3. On y est presque. On peut vous dire une chose : le nom de la station gagnante va "
            "vous étonner.\n\n"
            "Ou pas. Enfin, on verra bien. Assurez-vous d'avoir l'app installée. Révélation mardi 12 août "
            "à 8h00. 📆\n\n" + HASH_LI
        ),
        "facebook": (
            "🥁 J-3. Trois jours. Le grand nom va vous étonner. Ou pas. Ou beaucoup. On verra 😄\n\n"
            "Téléchargez l'app pour la surprise 📲\n\n" + HASH_FB
        ),
        "instagram": (
            "🥁 J-3. Trois. Petits. Jours. 🔥\n\n" + HASH_IG
        ),
    },
    {
        "n": 2, "title": "48 heures",
        "linkedin": (
            "⏰ J-2. Dernière ligne droite. Merci à tous ceux qui nous ont suivis ces 28 derniers jours.\n\n"
            "On se retrouve dans 48h pour la grande annonce. 12 août, 8h00.\n\n" + HASH_LI
        ),
        "facebook": (
            "⏰ J-2. 48h. Rdv mardi 8h00 pour l'annonce 🎉\n\n" + HASH_FB
        ),
        "instagram": (
            "⏰ J-2. 48h. 🎉\n\n" + HASH_IG
        ),
    },
    {
        "n": 1, "title": "DEMAIN",
        "linkedin": (
            "🚨 J-1. DEMAIN, on dévoile tout. La station partenaire. Le fonctionnement. Les stickers. "
            "Tout.\n\n"
            "Rendez-vous ici demain 8h00. Ne loupez pas ça. 📣\n\n" + HASH_LI
        ),
        "facebook": (
            "🚨 J-1. Demain 8h00. On révèle TOUT 🎉\n\n" + HASH_FB
        ),
        "instagram": (
            "🚨 J-1. DEMAIN. 🎉\n\n" + HASH_IG
        ),
    },
    {
        "n": 0, "title": "C'EST OFFICIEL",
        "linkedin": (
            "🎉 JOUR J. C'est officiel : nous lançons aujourd'hui le Jeton Café MesureChâssis pour les "
            "menuisiers de Wallonie et Bruxelles !\n\n"
            "Comment ça marche :\n"
            "  1. Téléchargez MesureChâssis\n"
            "  2. Créez votre premier chantier\n"
            "  3. Présentez le code Jeton Café dans la station partenaire\n"
            "  4. Repartez avec votre café offert ☕\n\n"
            "Merci à toutes celles et ceux qui nous ont suivis ces 30 derniers jours. On l'a fait "
            "ensemble. 🥂\n\n" + HASH_LI
        ),
        "facebook": (
            "🎉 JOUR J ! Le Jeton Café MesureChâssis est officiellement lancé !\n\n"
            "Téléchargez → mesurez → café offert ☕ En Wallonie et à Bruxelles 🇧🇪\n\n"
            "Merci à vous tous 💛\n\n" + HASH_FB
        ),
        "instagram": (
            "🎉 JOUR J. Jeton Café = LANCÉ. ☕🪟🚀\n\n"
            "Téléchargez → mesurez → café offert. 💛\n\n" + HASH_IG
        ),
    },
]

assert len(DAYS) == 31, f"Il faut 31 jours (J-30 à J-0), reçu {len(DAYS)}"


# ═══════════════════════════════════════════════════════════════════════
# GÉNÉRATION DU VISUEL 1080×1080
# ═══════════════════════════════════════════════════════════════════════
def _draw_gradient(canvas: Image.Image):
    """Fond dégradé café : marron foncé en haut → marron latte en bas."""
    draw = ImageDraw.Draw(canvas)
    for y in range(SIZE):
        t = y / SIZE
        r = int(BG_DARK[0] + (BG_LIGHT[0] - BG_DARK[0]) * t)
        g = int(BG_DARK[1] + (BG_LIGHT[1] - BG_DARK[1]) * t)
        b = int(BG_DARK[2] + (BG_LIGHT[2] - BG_DARK[2]) * t)
        draw.line([(0, y), (SIZE, y)], fill=(r, g, b))


def _draw_coffee_bean(canvas: Image.Image, cx: int, cy: int, radius: int, alpha: int = 60):
    """Un petit grain de café stylisé en overlay décoratif."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # ellipse principale
    d.ellipse(
        [cx - radius, cy - int(radius * 1.3), cx + radius, cy + int(radius * 1.3)],
        fill=(*GOLD, alpha),
    )
    # fente centrale
    d.line(
        [cx, cy - int(radius * 1.1), cx, cy + int(radius * 1.1)],
        fill=(*BG_DARK, min(255, alpha + 40)),
        width=max(2, radius // 8),
    )
    canvas.alpha_composite(overlay)


def _draw_multiline(draw, text: str, y_start: int, font_obj, fill, max_w: int, line_gap: int = 12):
    """Retourne y_end. Centré horizontalement."""
    words = text.split()
    lines: list[str] = []
    curr: list[str] = []
    for w in words:
        test = " ".join(curr + [w])
        bb = draw.textbbox((0, 0), test, font=font_obj)
        if bb[2] - bb[0] > max_w and curr:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    y = y_start
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_obj)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        draw.text(((SIZE - lw) // 2, y), line, font=font_obj, fill=fill)
        y += lh + line_gap
    return y


def draw_visual(day: dict) -> str:
    n = day["n"]
    canvas = Image.new("RGBA", (SIZE, SIZE), BG_DARK + (255,))
    _draw_gradient(canvas)

    # Grains de café décoratifs (positions déterministes pour cohérence)
    _draw_coffee_bean(canvas, 90, 950, 55, alpha=45)
    _draw_coffee_bean(canvas, SIZE - 110, 100, 42, alpha=35)
    _draw_coffee_bean(canvas, SIZE - 80, 990, 60, alpha=55)

    draw = ImageDraw.Draw(canvas)

    # ── Header MesureChâssis ──────────────────────────────────────
    f_brand = font(30, bold=True)
    draw.text((50, 46), "MESURECHÂSSIS", font=f_brand, fill=CREAM)
    # petite ligne dorée sous le logo
    draw.rectangle([(50, 84), (306, 88)], fill=GOLD)
    f_sub = font(19, bold=False)
    draw.text((50, 100), "Menuisiers pros · Belgique", font=f_sub, fill=CREAM_SOFT)

    # ── Badge Jeton Café en haut à droite ─────────────────────────
    badge_x, badge_y, badge_w, badge_h = SIZE - 320, 46, 270, 74
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=18, fill=(GOLD[0], GOLD[1], GOLD[2], 245), outline=CREAM, width=2,
    )
    f_badge = font(22, bold=True)
    draw.text((badge_x + 20, badge_y + 10), "JETON CAFÉ", font=f_badge, fill=BG_DARK)
    f_badge_sub = font(14, bold=False)
    draw.text((badge_x + 20, badge_y + 42), "12 août 2026", font=f_badge_sub, fill=BG_DARK)

    # ── Bloc central : compteur J-XX ou JOUR J ───────────────────
    if n == 0:
        # Jour J : gros bloc "JOUR J" + zone logo partenaire
        f_j = font(180, bold=True)
        text = "JOUR J"
        bb = draw.textbbox((0, 0), text, font=f_j)
        w = bb[2] - bb[0]
        # ombre
        draw.text(((SIZE - w) // 2 + 5, 205), text, font=f_j, fill=(0, 0, 0, 120))
        draw.text(((SIZE - w) // 2, 200), text, font=f_j, fill=GOLD_BRIGHT)

        # Zone logo partenaire (dashed effect via rectangles)
        draw.rounded_rectangle([(150, 420), (SIZE - 150, 700)],
                               radius=24, outline=GOLD, width=4)
        f_zone = font(24, bold=False)
        z1 = "[ Logo du partenaire ici ]"
        bb2 = draw.textbbox((0, 0), z1, font=f_zone)
        draw.text(((SIZE - bb2[2]) // 2, 545), z1, font=f_zone, fill=CREAM_SOFT)
    else:
        # J-XX en gros
        f_j = font(240, bold=True)
        text = f"J-{n}"
        bb = draw.textbbox((0, 0), text, font=f_j)
        w = bb[2] - bb[0]
        # ombre douce
        draw.text(((SIZE - w) // 2 + 6, 216), text, font=f_j, fill=(0, 0, 0, 130))
        draw.text(((SIZE - w) // 2, 210), text, font=f_j, fill=GOLD_BRIGHT)

        # Petit "AVANT LE JOUR J" sous le compteur
        f_hint = font(22, bold=False)
        hint = "AVANT LE GRAND JOUR"
        bb = draw.textbbox((0, 0), hint, font=f_hint)
        draw.text(((SIZE - bb[2]) // 2, 490), hint, font=f_hint, fill=CREAM_SOFT)

    # ── Titre du jour ────────────────────────────────────────────
    title = day["title"]
    f_title = font(50, bold=True)
    y_start = 780 if n == 0 else 570
    y_end = _draw_multiline(draw, title, y_start, f_title, CREAM, max_w=SIZE - 120, line_gap=14)

    # ── CTA en bas ────────────────────────────────────────────────
    f_cta = font(24, bold=False)
    cta = "Ta prochaine mesure vaut un café" if n == 0 \
        else "Télécharge MesureChâssis sur l'App Store"
    bb = draw.textbbox((0, 0), cta, font=f_cta)
    draw.text(((SIZE - bb[2]) // 2, SIZE - 120), cta, font=f_cta, fill=GOLD_BRIGHT)

    # ── Point doré déco en tout bas ──────────────────────────────
    draw.ellipse([(SIZE // 2 - 8, SIZE - 70), (SIZE // 2 + 8, SIZE - 54)], fill=GOLD)

    # Convert RGBA → RGB pour PNG plus léger et compatible partout
    final = Image.new("RGB", (SIZE, SIZE), BG_DARK)
    final.paste(canvas, (0, 0), mask=canvas.split()[3])
    out = f"{OUT}/day_{n:02d}.png"
    final.save(out, format="PNG", optimize=True)
    return out


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
def main():
    print(f"🎨 Génération de {len(DAYS)} visuels + captions (option A SAFE)...")
    outputs = []
    for d in DAYS:
        path = draw_visual(d)
        outputs.append(path)
        size_kb = os.path.getsize(path) // 1024
        print(f"  ✅ J-{d['n']:02d}  {os.path.basename(path)}  ({size_kb} Ko)")

    # Captions JSON (3 plateformes par jour)
    captions_path = f"{OUT}/captions.json"
    payload = {
        "j_zero_date": J_ZERO.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "days": [
            {
                "n": d["n"],
                "title": d["title"],
                "publish_date": (J_ZERO - timedelta(days=d["n"])).isoformat(),
                "visual_url": f"/api/campaign/countdown/visual/{d['n']}",
                "captions": {
                    "linkedin": d["linkedin"],
                    "facebook": d["facebook"],
                    "instagram": d["instagram"],
                },
            }
            for d in DAYS
        ],
    }
    with open(captions_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n📝 captions.json  ({os.path.getsize(captions_path) // 1024} Ko · "
          f"{len(DAYS) * 3} textes)")

    # ZIP complet (image + json)
    zip_path = "/app/backend/public_downloads/countdown_v1.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in outputs:
            z.write(f, os.path.basename(f))
        z.write(captions_path, "captions.json")
    print(f"📦 countdown_v1.zip  ({os.path.getsize(zip_path) // 1024} Ko)")
    print("\n✅ TERMINÉ.")


if __name__ == "__main__":
    main()
