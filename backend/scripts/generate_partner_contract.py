"""Génération du PDF "Contrat de Partenariat Affilié" — MesureChâssis.

Document juridique simple (1-2 pages) à envoyer à un influenceur ou créateur
de contenu pour officialiser un partenariat affilié.

Conformité BE/FR : mention RGPD, mention partenariat sponsorisé (#ad / #partenariat),
clause de résiliation à tout moment, clause de paiement.

Sortie : /app/backend/static/contrat_partenariat_modele.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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

PRIMARY = colors.HexColor("#FF6B35")
TEXT = colors.HexColor("#1A1A1F")
GREY = colors.HexColor("#666666")
LIGHT = colors.HexColor("#F4F4F6")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, leading=22,
                    textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, leading=15,
                    textColor=TEXT, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=styles["BodyText"], fontSize=9.5, leading=13,
                   textColor=TEXT, alignment=TA_JUSTIFY)
SMALL = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=11,
                       textColor=GREY)


def build_contract_pdf(output: Path) -> Path:
    doc = SimpleDocTemplate(
        str(output), pagesize=A4,
        topMargin=14 * mm, bottomMargin=14 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="MesureChâssis - Contrat de Partenariat Affilié",
    )
    story = []

    # Header
    story.append(Paragraph("CONTRAT DE PARTENARIAT AFFILIÉ", H1))
    story.append(Paragraph("MesureChâssis — Programme Influence & Création", SMALL))
    story.append(Spacer(1, 14))

    # Parties
    story.append(Paragraph("ENTRE LES PARTIES SOUSSIGNÉES", H2))
    parties_data = [
        [Paragraph("<b>L'ÉDITEUR</b>", P),
         Paragraph("Michel Pezzuto — MesureChâssis (entreprise individuelle)<br/>"
                   "Sombreffe, Belgique<br/>"
                   "Email : contact@mesurechassis.com<br/>"
                   "Site : www.mesurechassis.com<br/>"
                   "Ci-après désigné « <b>l'Éditeur</b> »", P)],
        [Paragraph("<b>LE PARTENAIRE</b>", P),
         Paragraph("Nom / raison sociale : ………………………………………………<br/>"
                   "Pseudo / chaîne : ………………………………………………<br/>"
                   "Plateforme principale : ………………………………………………<br/>"
                   "Email : ………………………………………………<br/>"
                   "Adresse : ………………………………………………<br/>"
                   "IBAN (pour virements) : ………………………………………………<br/>"
                   "Ci-après désigné « <b>le Partenaire</b> »", P)],
    ]
    t = Table(parties_data, colWidths=(35 * mm, 130 * mm))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.4, GREY),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, GREY),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Article 1
    story.append(Paragraph("ARTICLE 1 — OBJET DU CONTRAT", H2))
    story.append(Paragraph(
        "Le présent contrat a pour objet de définir les conditions dans lesquelles "
        "le Partenaire fera la promotion de l'application MesureChâssis (« <b>l'Application</b> ») "
        "auprès de son audience, en échange d'une rémunération calculée sur "
        "les abonnements payants effectivement générés par sa recommandation.", P,
    ))

    # Article 2 - Code
    story.append(Paragraph("ARTICLE 2 — CODE PROMO PERSONNALISÉ", H2))
    story.append(Paragraph(
        "L'Éditeur fournit au Partenaire un <b>code promo personnalisé</b> "
        "(format : <i>NOMDUPARTENAIRE-XXXX</i>) qu'il devra communiquer à son audience. "
        "Tout utilisateur s'inscrivant à l'Application via ce code sera "
        "automatiquement rattaché au Partenaire pour le suivi des conversions.", P,
    ))
    story.append(Paragraph(
        "<b>Code attribué :</b> ………………………………………………", P,
    ))

    # Article 3 - Rémunération
    story.append(Paragraph("ARTICLE 3 — RÉMUNÉRATION", H2))
    story.append(Paragraph(
        "Le Partenaire perçoit une commission égale à <b>20 % (vingt pour cent)</b> "
        "hors taxes du chiffre d'affaires net généré par chaque utilisateur "
        "s'étant inscrit via son code promo, et ce pendant une durée de "
        "<b>12 (douze) mois consécutifs</b> à compter de leur première facture payée.", P,
    ))
    story.append(Paragraph(
        "<b>Modalités de versement :</b><br/>"
        "• Les commissions sont calculées en fin de mois civil.<br/>"
        "• Le paiement est effectué par virement SEPA dans les 15 jours suivants.<br/>"
        "• Aucun seuil minimum : même 1 € de commission est payé.<br/>"
        "• Le Partenaire reçoit chaque mois un récapitulatif détaillé "
        "(par email + accès au tableau de bord).", P,
    ))

    # Article 4 - Avantages
    story.append(Paragraph("ARTICLE 4 — AVANTAGES SUPPLÉMENTAIRES", H2))
    story.append(Paragraph(
        "L'Éditeur octroie au Partenaire :<br/>"
        "• Un <b>compte Pro à vie GRATUIT</b> sur l'Application (valeur : 249 €/mois × 12 = "
        "2 988 € par an).<br/>"
        "• Une <b>réduction de 1 mois gratuit supplémentaire</b> à offrir à son audience "
        "via le code promo.<br/>"
        "• Une mention « <b>Partenaire officiel</b> » sur le site web de l'Application.<br/>"
        "• Un <b>accès anticipé</b> aux nouvelles fonctionnalités pour les tester en avant-première.", P,
    ))

    # Article 5 - Engagements partenaire
    story.append(Paragraph("ARTICLE 5 — ENGAGEMENTS DU PARTENAIRE", H2))
    story.append(Paragraph(
        "Le Partenaire s'engage à :<br/>"
        "• Mentionner explicitement le caractère partenarial de la communication "
        "(<b>#partenariat</b>, <b>#ad</b>, ou <b>#publicité</b> selon les usages "
        "de la plateforme), conformément à la loi belge et française.<br/>"
        "• Ne pas diffuser de fausses informations sur l'Application ou ses tarifs.<br/>"
        "• Ne pas pratiquer de spam ni d'envoi non sollicité.<br/>"
        "• Respecter l'image de marque MesureChâssis (logos, couleurs, ton bienveillant).", P,
    ))

    # Article 6 - Engagements éditeur
    story.append(Paragraph("ARTICLE 6 — ENGAGEMENTS DE L'ÉDITEUR", H2))
    story.append(Paragraph(
        "L'Éditeur s'engage à :<br/>"
        "• Fournir au Partenaire un <b>tableau de bord</b> avec ses statistiques en temps réel.<br/>"
        "• Verser les commissions dans les délais prévus à l'Article 3.<br/>"
        "• Fournir un <b>kit média</b> (logos, captures, vidéos) pour faciliter la création de contenu.<br/>"
        "• Répondre aux questions du Partenaire sous 48 h ouvrées.", P,
    ))

    # Article 7 - Durée et résiliation
    story.append(Paragraph("ARTICLE 7 — DURÉE ET RÉSILIATION", H2))
    story.append(Paragraph(
        "Le présent contrat prend effet à sa signature et est conclu pour une "
        "<b>durée indéterminée</b>. Chaque partie peut y mettre fin à tout moment "
        "par simple email avec un préavis de <b>15 jours</b>. Les commissions déjà "
        "acquises avant la résiliation restent dues et seront versées normalement.", P,
    ))

    # Article 8 - Données personnelles
    story.append(Paragraph("ARTICLE 8 — DONNÉES PERSONNELLES (RGPD)", H2))
    story.append(Paragraph(
        "Les données personnelles du Partenaire (nom, email, IBAN) sont collectées "
        "et traitées par l'Éditeur uniquement pour les besoins du présent contrat "
        "(suivi commercial, paiement des commissions, communication). Elles ne sont "
        "transmises à aucun tiers et sont conservées pendant la durée du contrat "
        "+ 5 ans (obligations comptables). Le Partenaire peut exercer ses droits "
        "RGPD à tout moment par email à <b>contact@mesurechassis.com</b>.", P,
    ))

    # Article 9 - Droit applicable
    story.append(Paragraph("ARTICLE 9 — DROIT APPLICABLE ET JURIDICTION", H2))
    story.append(Paragraph(
        "Le présent contrat est régi par le droit belge. En cas de litige, les "
        "parties s'efforcent de trouver une solution amiable. À défaut, "
        "compétence est attribuée aux tribunaux de Namur (Belgique).", P,
    ))

    # Signature
    story.append(Spacer(1, 14))
    story.append(Paragraph("FAIT À ……………………… , LE ……… / ……… / 20………", P))
    story.append(Paragraph("EN DEUX EXEMPLAIRES ORIGINAUX", P))
    story.append(Spacer(1, 18))

    sig_data = [
        [Paragraph("<b>L'ÉDITEUR</b><br/>Michel Pezzuto<br/>(signature précédée de la mention<br/>"
                   "« Lu et approuvé »)", P),
         Paragraph("<b>LE PARTENAIRE</b><br/>……………………………………<br/>(signature précédée de la mention<br/>"
                   "« Lu et approuvé »)", P)],
        [Paragraph("<br/><br/><br/><br/>", P), Paragraph("<br/><br/><br/><br/>", P)],
    ]
    t = Table(sig_data, colWidths=(82 * mm, 82 * mm))
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.4, GREY),
        ("LINEABOVE", (0, 1), (-1, 1), 0.4, GREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    # Footer
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "<i>Contrat-type édité le " + "$DATE$" + ". Document à imprimer en 2 exemplaires, "
        "signer, scanner et renvoyer à contact@mesurechassis.com.</i>", SMALL,
    ))

    doc.build(story)
    return output


if __name__ == "__main__":
    out = Path("/app/backend/static/contrat_partenariat_modele.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    result = build_contract_pdf(out)
    print(f"✅ PDF contrat généré : {result} ({result.stat().st_size / 1024:.1f} Ko)")
