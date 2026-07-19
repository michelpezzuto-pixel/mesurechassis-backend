"""Génère 2 PDF pour la tournée terrain Michel :
1. Kit_Tournee_Menuisiers.pdf — Checklist + questionnaire à imprimer
2. Script_Demo_90s.pdf — Pitch de démo à mémoriser

Usage : python3 /app/scripts/generate_michel_terrain_kit.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, grey
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Couleurs branding
ORANGE = HexColor("#FF5A00")
DARK = HexColor("#0C0C0E")
GREY_LIGHT = HexColor("#F2F2F2")
GREY_MED = HexColor("#8A8A8F")

OUT_DIR = Path("/app/downloads_michel_terrain")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(
        name="TitleOrange", fontSize=22, textColor=ORANGE,
        alignment=TA_LEFT, spaceAfter=6, fontName="Helvetica-Bold",
    ))
    s.add(ParagraphStyle(
        name="Sub", fontSize=11, textColor=GREY_MED,
        alignment=TA_LEFT, spaceAfter=14, fontName="Helvetica",
    ))
    s.add(ParagraphStyle(
        name="H2", fontSize=13, textColor=DARK, spaceBefore=10,
        spaceAfter=6, fontName="Helvetica-Bold",
    ))
    s.add(ParagraphStyle(
        name="Body", fontSize=10, textColor=DARK, leading=14,
        fontName="Helvetica",
    ))
    s.add(ParagraphStyle(
        name="BodySmall", fontSize=9, textColor=DARK, leading=12,
        fontName="Helvetica",
    ))
    s.add(ParagraphStyle(
        name="ScriptCue", fontSize=9, textColor=ORANGE,
        fontName="Helvetica-Oblique", leading=11,
    ))
    s.add(ParagraphStyle(
        name="ScriptLine", fontSize=11, textColor=DARK, leading=15,
        fontName="Helvetica", spaceAfter=8, leftIndent=8,
    ))
    return s


# ─────────────────────────────────────────────────────────────────────
# 1. KIT TOURNÉE MENUISIERS
# ─────────────────────────────────────────────────────────────────────
def build_kit_tournee():
    pdf = SimpleDocTemplate(
        str(OUT_DIR / "Kit_Tournee_Menuisiers.pdf"),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    S = styles()
    story = []

    # ── En-tête
    story.append(Paragraph("Kit Tournée Terrain", S["TitleOrange"]))
    story.append(Paragraph(
        "Visite menuisier — 1 fiche par menuisier · MesureChâssis 2026",
        S["Sub"],
    ))

    # ── Bloc identité menuisier
    data = [
        ["Nom du menuisier :", ""],
        ["Entreprise / Raison sociale :", ""],
        ["Ville :", ""],
        ["Téléphone :", ""],
        ["Email :", ""],
        ["Date de la visite :", ""],
        ["Âge estimé :", "☐ 20-30  ☐ 30-40  ☐ 40-50  ☐ 50-60  ☐ 60+"],
        ["Niveau technologique (1-5) :", "☐ 1  ☐ 2  ☐ 3  ☐ 4  ☐ 5"],
    ]
    t = Table(data, colWidths=[6 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (1, 0), (1, 5), 0.4, GREY_MED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    # ── Phase 1 : Découverte
    story.append(Paragraph(
        "PHASE 1 · Découverte (avant de montrer l'app)", S["H2"],
    ))
    story.append(Paragraph(
        "<b>Objectif :</b> comprendre son quotidien, sans parler de MesureChâssis. "
        "Écouter à 80%, parler à 20%.",
        S["Body"],
    ))
    story.append(Spacer(1, 6))

    q1 = [
        "1. Comment tu prends tes mesures aujourd'hui ? "
        "(carnet, feuille, tablette, autre ?)",
        "2. Sur un chantier, qu'est-ce qui te fait perdre le plus de temps ?",
        "3. Une erreur de mesure, ça t'est arrivé combien de fois cette année ? "
        "Combien ça t'a coûté ?",
        "4. Tu utilises déjà un logiciel de devis / gestion ? Lequel ? "
        "Combien tu payes par mois ?",
        "5. Combien de chantiers tu fais par mois en moyenne ?",
    ]
    for q in q1:
        story.append(Paragraph(q, S["Body"]))
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "________________________________________________________________________",
            S["BodySmall"],
        ))
        story.append(Paragraph(
            "________________________________________________________________________",
            S["BodySmall"],
        ))
        story.append(Spacer(1, 6))

    story.append(PageBreak())

    # ── Phase 2 : Démo silencieuse
    story.append(Paragraph(
        "PHASE 2 · Démo silencieuse — CHRONO ⏱", S["H2"],
    ))
    story.append(Paragraph(
        "<b>Règle absolue :</b> tu installes l'app sur SON téléphone, "
        "tu lui donnes l'appareil, et tu <b>NE dis RIEN</b>. Tu observes.",
        S["Body"],
    ))
    story.append(Spacer(1, 6))

    obs_data = [
        ["Étape", "Temps mis", "Bloqué ?", "Où / comment"],
        ["Installation depuis App Store", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Création du compte (Google/Apple/Email)", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Trouve le bouton Nouveau chantier", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Rempli le formulaire chantier", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Prend sa 1re mesure", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Exporte en PDF", "___ min ___ s", "☐ Oui ☐ Non", ""],
        ["Temps TOTAL du 1er PDF", "___ min ___ s", "", ""],
    ]
    t2 = Table(obs_data, colWidths=[5.5 * cm, 3 * cm, 2.5 * cm, 7 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.3, GREY_MED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Mots exacts qu'il a prononcés</b> (« c'est où ? », « je fais quoi ? », "
        "« y a trop de trucs »...) :",
        S["Body"],
    ))
    for _ in range(4):
        story.append(Paragraph(
            "________________________________________________________________________",
            S["BodySmall"],
        ))
    story.append(Spacer(1, 10))

    # ── Phase 3 : Débrief
    story.append(Paragraph(
        "PHASE 3 · Débrief (questions clés)", S["H2"],
    ))
    q3 = [
        "1. Sur 10, tu la trouves comment cette app ? Pourquoi ?",
        "2. Qu'est-ce qui te MANQUE dedans absolument ?",
        "3. Qu'est-ce qui te semble INUTILE ou EN TROP ?",
        "4. Tu paierais combien par mois pour l'utiliser au quotidien ?",
        "5. Question clé : tu connais la calculatrice iOS (Simple/Scientifique). "
        "Tu aimerais que MesureChâssis fonctionne pareil : Simple pour débuter, "
        "Scientifique pour les Pros ? ☐ Oui  ☐ Non  ☐ Peu importe",
        "6. Tu la recommanderais à combien de collègues sur 10 ?",
        "7. Tu accepterais qu'on t'appelle dans 1 mois pour un retour ? "
        "☐ Oui ☐ Non",
    ]
    for q in q3:
        story.append(Paragraph(q, S["Body"]))
        story.append(Paragraph(
            "________________________________________________________________________",
            S["BodySmall"],
        ))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ── Phase 4 : Synthèse Michel
    story.append(Paragraph(
        "PHASE 4 · Ma synthèse après la visite (5 min avant de repartir)",
        S["H2"],
    ))
    synth_data = [
        ["Le plus gros blocage observé :", ""],
        ["La feature qui l'a impressionné :", ""],
        ["Sa vraie douleur métier (« pain point ») :", ""],
        ["Prix qu'il paierait par mois :", "€ ___ / mois"],
        ["Probabilité qu'il devienne client (0-100%) :", "___ %"],
        ["Action à faire après :", ""],
    ]
    t3 = Table(synth_data, colWidths=[6.5 * cm, 11.5 * cm])
    t3.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 10),
        ("FONT", (1, 0), (1, -1), "Helvetica", 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("LINEBELOW", (1, 0), (1, -1), 0.4, GREY_MED),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t3)
    story.append(Spacer(1, 14))

    # ── Kit départ tournée
    story.append(Paragraph(
        "AVANT de partir en tournée — Checklist",
        S["H2"],
    ))
    checklist_before = [
        "☐ iPhone chargé à 100% + batterie externe",
        "☐ iPad chargé (si tu veux montrer sur grand écran)",
        "☐ 20 flyers A5 imprimés",
        "☐ 15 fiches de cette checklist imprimées (1 par visite)",
        "☐ Carte des menuisiers à visiter (Google Maps custom liste)",
        "☐ Cartes de visite MesureChâssis",
        "☐ Café / bouteille d'eau (long trajet)",
        "☐ Script de démo 90s mémorisé (voir 2e document)",
        "☐ Compte de démo créé et testé la veille",
        "☐ App bien installée sur ton téléphone (v1.0.29)",
    ]
    for c in checklist_before:
        story.append(Paragraph(c, S["Body"]))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "<b>Objectif de la journée :</b> 5 visites minimum · 1 café accepté · "
        "3 démos live · 1 personne qui installe l'app devant toi.",
        S["Body"],
    ))

    pdf.build(story)
    print(f"OK: {OUT_DIR / 'Kit_Tournee_Menuisiers.pdf'}")


# ─────────────────────────────────────────────────────────────────────
# 2. SCRIPT DÉMO 90 SECONDES
# ─────────────────────────────────────────────────────────────────────
def build_script_demo():
    pdf = SimpleDocTemplate(
        str(OUT_DIR / "Script_Demo_90s.pdf"),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    S = styles()
    story = []

    # ── En-tête
    story.append(Paragraph("Script de démo — 90 secondes", S["TitleOrange"]))
    story.append(Paragraph(
        "À mémoriser · À adapter à ton feeling · MesureChâssis 2026",
        S["Sub"],
    ))

    story.append(Paragraph(
        "<b>Règle d'or :</b> Tu ne récites pas. Tu <b>racontes</b>. "
        "Ces phrases sont un fil rouge, pas une prière.",
        S["Body"],
    ))
    story.append(Spacer(1, 12))

    # ── Le script
    sections = [
        ("0-10s · L'ACCROCHE", "Regarde le menuisier dans les yeux, souris",
         "« Bonjour Monsieur / Madame, je m'appelle Michel Pezzuto. "
         "Je suis menuisier comme vous, et j'ai créé une app "
         "pour arrêter de perdre du temps sur les mesures de châssis. "
         "Je vous en parle 90 secondes, promis. »"),

        ("10-25s · LA DOULEUR",
         "Ton un peu plus grave, tu poses le problème",
         "« Vous savez comme moi : une baie trapèze mesurée à 3 mm près, "
         "c'est 500 € de verre à recommander et un client qui vous en veut. "
         "Et le devis Excel, c'est 45 minutes le soir après le chantier. »"),

        ("25-45s · LA MAGIE (montre l'écran)",
         "Sors ton iPhone, ouvre l'app, montre en 20s",
         "« Regardez : je crée mon chantier ici… je scanne le cahier des "
         "charges du client avec l'IA... elle remplit toute seule les "
         "dimensions... je vérifie mes cotes sur site... et j'envoie le "
         "PDF au client depuis le chantier. »"),

        ("45-60s · LA PREUVE CHIFFRÉE",
         "Regarde-le, laisse un blanc de 2 secondes",
         "« Résultat : plus d'erreurs sur les baies complexes, "
         "et 2 heures gagnées par chantier. "
         "Pour un menuisier qui fait 3 chantiers par semaine, ça fait "
         "6 heures gagnées chaque semaine. »"),

        ("60-75s · LE PRIX",
         "Tu enchaînes vite, air décontracté",
         "« C'est gratuit pour commencer. Vous testez 5 chantiers. Si vous "
         "adorez, c'est 25 € par mois. Si vous êtes en équipe, 60 € par mois "
         "pour toute la boîte. Un devis rattrapé = l'app remboursée. »"),

        ("75-90s · L'APPEL À L'ACTION",
         "Tends ton téléphone. Fais-lui installer devant toi.",
         "« Vous voulez tester tout de suite ? Je vous laisse mon "
         "téléphone 2 minutes, vous installez l'app depuis l'App Store. "
         "Je vous accompagne. C'est comme ça que vous vous ferez votre "
         "propre idée. »"),
    ]

    for time_lbl, cue, line in sections:
        story.append(Paragraph(time_lbl, S["H2"]))
        story.append(Paragraph(cue, S["ScriptCue"]))
        story.append(Paragraph(line, S["ScriptLine"]))

    story.append(PageBreak())

    # ── Réponses aux objections
    story.append(Paragraph(
        "Réponses aux objections classiques",
        S["TitleOrange"],
    ))
    story.append(Paragraph(
        "Ce que tu risques d'entendre, et quoi répondre calmement.",
        S["Sub"],
    ))

    objections = [
        ("« Moi je fais tout au papier depuis 30 ans, ça marche. »",
         "« Je vous crois. Moi aussi je faisais pareil. Je vous propose juste "
         "de tester gratuitement 5 chantiers. Si à la fin vous préférez le "
         "papier, vous restez au papier. Vous risquez zéro. »"),

        ("« C'est cher pour un menuisier tout seul. »",
         "« Vous perdez combien sur UN devis raté à cause d'une erreur "
         "de mesure ? Je parie que c'est plus de 25 €. L'app se rembourse "
         "en 1 chantier. Sinon, vous êtes freemium, c'est gratuit. »"),

        ("« Je n'y connais rien en tablette / apps. »",
         "« Justement. Je l'ai faite pour des gens qui n'aiment pas "
         "l'informatique. C'est comme la calculatrice iPhone : vous "
         "appuyez sur des boutons, vous obtenez un PDF. Rien d'autre. »"),

        ("« Je vais y réfléchir. »",
         "« Bien sûr. Je vous laisse mon flyer avec le QR code de "
         "téléchargement. Je peux vous rappeler dans 15 jours pour "
         "avoir votre avis ? »  (→ note son téléphone !) "),

        ("« Ça marche sur Android ? »",
         "« Sur iPhone d'abord, l'Android arrive bientôt. Vous êtes sur "
         "quoi ? »  (Si Android → prends son email, tu le préviens dès "
         "la sortie Play Store.)"),

        ("« Vous vendez mes données ? »",
         "« Zéro. Vos mesures restent sur le serveur MesureChâssis, "
         "hébergé en Europe. Aucune revente, aucune pub. C'est vous le "
         "client, pas le produit. »"),

        ("« C'est fait par une grosse boîte ou par vous ? »",
         "« Par moi. Je suis menuisier, je l'ai créée pour mon propre "
         "usage. Aujourd'hui je la vends aux collègues. Vous parlez "
         "directement au patron. »"),
    ]

    for q, a in objections:
        story.append(Paragraph(f"<b>{q}</b>", S["Body"]))
        story.append(Spacer(1, 2))
        story.append(Paragraph(a, S["ScriptLine"]))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "3 CHOSES à toujours te rappeler pendant la démo",
        S["H2"],
    ))
    tips = [
        "1. <b>Ils te regardent TOI, pas l'écran.</b> Ton énergie, ton "
        "sourire, ta certitude — c'est 70% de la vente.",
        "2. <b>Ferme ta gueule après le prix.</b> C'est le moment où "
        "l'amateur enchaîne pour meubler. Le pro attend. Laisse le silence.",
        "3. <b>Personne n'achète parce que c'est bien.</b> Ils achètent "
        "parce que ça leur évite une douleur. Rappelle la douleur.",
    ]
    for t in tips:
        story.append(Paragraph(t, S["Body"]))
        story.append(Spacer(1, 4))

    pdf.build(story)
    print(f"OK: {OUT_DIR / 'Script_Demo_90s.pdf'}")


if __name__ == "__main__":
    build_kit_tournee()
    build_script_demo()
    print("\nFiles ready in /app/downloads_michel_terrain/")
