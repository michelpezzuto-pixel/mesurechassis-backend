"""
Génère les NOUVELLES pages HTML : CGU, CGV, Cookies, FAQ, Télécharger, 404, À propos.
Toutes utilisent le wrap commun (head + header + footer).
"""
from _shared import page_wrap, ANDROID_URL, IOS_URL, YEAR


# =============================================================================
# CGU — Conditions Générales d'Utilisation (droit belge)
# =============================================================================
def make_cgu() -> str:
    body = f"""
<h1>Conditions Générales d'<em>Utilisation</em></h1>
<p class="meta">Dernière mise à jour : 1{chr(101)}r janvier {YEAR}</p>

<p class="lead">Les présentes Conditions Générales d'Utilisation (« CGU ») régissent l'accès et l'usage de l'application MesureChâssis. En utilisant l'application, vous acceptez sans réserve l'intégralité des présentes CGU.</p>

<h2>1. Objet</h2>
<p>MesureChâssis est une application mobile SaaS (Software as a Service) destinée aux professionnels du secteur de la menuiserie. Elle permet la prise de mesures de châssis sur chantier, leur enregistrement, leur vérification et l'export de fiches techniques au format PDF, Excel, CSV et JSON.</p>

<h2>2. Acceptation des conditions</h2>
<p>L'utilisation de l'application implique l'acceptation pleine et entière des présentes CGU. Si vous n'acceptez pas tout ou partie des présentes conditions, vous ne devez pas utiliser l'application. L'éditeur se réserve le droit de modifier ces CGU à tout moment ; les modifications entrent en vigueur dès leur publication.</p>

<h2>3. Inscription et création de compte</h2>
<p>L'accès à l'application nécessite la création d'un compte utilisateur. Lors de l'inscription, vous vous engagez à :</p>
<ul>
  <li>Fournir des informations exactes, à jour et complètes ;</li>
  <li>Maintenir la confidentialité de vos identifiants (email, mot de passe) ;</li>
  <li>Notifier immédiatement tout usage non autorisé de votre compte ;</li>
  <li>Être âgé d'au moins 18 ans et agir en qualité de professionnel.</li>
</ul>
<p>Deux types de comptes sont proposés : <strong>Artisan</strong> (indépendant, 1 utilisateur) et <strong>Entreprise</strong> (2 utilisateurs inclus, places supplémentaires facturées).</p>

<h2>4. Période d'essai (Bêta gratuite)</h2>
<p>Une période d'essai gratuite de <strong>90 jours</strong> est proposée à tout nouvel utilisateur, sans engagement et sans nécessité de communiquer un moyen de paiement. À l'expiration de cette période, l'utilisateur sera invité à souscrire un abonnement payant pour continuer à utiliser l'application. Aucun prélèvement ne sera effectué sans accord préalable explicite.</p>
<p>Afin de prévenir tout abus, un mécanisme d'empreinte d'appareil (IP + User-Agent) est utilisé pour vérifier l'unicité des comptes d'essai.</p>

<h2>5. Utilisation autorisée</h2>
<p>L'utilisateur s'engage à utiliser l'application de manière loyale, dans le respect des lois en vigueur. Sont notamment interdits :</p>
<ul>
  <li>Toute utilisation à des fins illégales, frauduleuses ou contraires à l'ordre public ;</li>
  <li>La revente, la sous-licence ou la mise à disposition de l'application à des tiers non autorisés ;</li>
  <li>L'extraction massive de données (scraping, reverse engineering) ;</li>
  <li>Toute tentative d'accès non autorisé aux systèmes de l'éditeur ;</li>
  <li>L'injection de code malveillant, virus ou tout élément susceptible de nuire au service.</li>
</ul>

<h2>6. Gestion des rôles</h2>
<p>L'application met en œuvre une gestion stricte des rôles :</p>
<ul>
  <li><strong>Administrateur</strong> : accès complet, gestion des utilisateurs, exports, facturation ;</li>
  <li><strong>Commercial</strong> : création de chantiers, gestion clients ;</li>
  <li><strong>Technicien</strong> : prise de mesures sur chantier, ajout de photos.</li>
</ul>
<p>Le compte « Artisan » ne permet pas d'ajouter d'autres utilisateurs.</p>

<h2>7. Propriété intellectuelle</h2>
<p>L'ensemble des éléments composant l'application (code source, interface, logos, textes, icônes, marques, base de données) demeure la propriété exclusive de l'éditeur ou de ses ayants droit. Toute reproduction, représentation, modification ou exploitation non expressément autorisée est strictement interdite et constitue une contrefaçon, sanctionnée par les articles XI.293 et suivants du Code de droit économique belge.</p>

<h2>8. Données utilisateur</h2>
<p>L'utilisateur reste propriétaire des données qu'il saisit dans l'application (mesures, photos, clients, chantiers). L'éditeur s'engage à ne pas exploiter ces données à des fins commerciales et à les protéger conformément au RGPD. Voir notre <a href="confidentialite.html">Politique de confidentialité</a>.</p>

<h2>9. Suspension et résiliation</h2>
<p>L'éditeur se réserve le droit de suspendre ou résilier un compte en cas de :</p>
<ul>
  <li>Violation des présentes CGU ;</li>
  <li>Défaut de paiement après mise en demeure restée infructueuse ;</li>
  <li>Atteinte à la sécurité du service ;</li>
  <li>Demande d'une autorité compétente.</li>
</ul>
<p>L'utilisateur peut résilier son compte à tout moment depuis la section « Profil » de l'application. Conformément au RGPD, la suppression entraîne l'anonymisation ou l'effacement des données personnelles sous 30 jours.</p>

<h2>10. Disponibilité du service</h2>
<p>L'éditeur s'efforce de maintenir l'application accessible 24h/24 et 7j/7, sans garantie de continuité absolue. Des interruptions peuvent survenir pour maintenance, mise à jour ou en cas de force majeure. Aucune indemnité ne pourra être réclamée à ce titre.</p>

<h2>11. Limitation de responsabilité</h2>
<p>L'application est fournie « en l'état ». L'éditeur ne saurait être tenu responsable :</p>
<ul>
  <li>Des erreurs de mesure ou de saisie commises par l'utilisateur ;</li>
  <li>Des conséquences financières d'une utilisation inappropriée ;</li>
  <li>De la perte de données résultant d'un usage non conforme ;</li>
  <li>Des dommages indirects (perte d'exploitation, manque à gagner).</li>
</ul>
<p>Conformément à l'article 1733 du Code civil belge, la responsabilité de l'éditeur est limitée au montant des sommes effectivement versées par l'utilisateur au cours des 12 derniers mois.</p>

<h2>12. Droit applicable et juridiction</h2>
<p>Les présentes CGU sont soumises au droit belge. Tout litige relatif à leur interprétation ou à leur exécution relève de la compétence exclusive des tribunaux de l'arrondissement judiciaire du siège social de l'éditeur, sauf disposition légale contraire applicable aux consommateurs.</p>

<h2>13. Contact</h2>
<p>Pour toute question relative aux présentes CGU, vous pouvez nous contacter à <a href="mailto:info@mesurechassis.com">info@mesurechassis.com</a> ou via notre <a href="contact.html">page de contact</a>.</p>
"""
    return page_wrap(
        "Conditions Générales d'Utilisation — MesureChâssis",
        "CGU de l'application MesureChâssis. Conditions d'accès et d'usage du service SaaS de prise de mesures pour menuisiers.",
        "cgu.html",
        "cgu",
        body,
    )


# =============================================================================
# CGV — Conditions Générales de Vente
# =============================================================================
def make_cgv() -> str:
    body = f"""
<h1>Conditions Générales de <em>Vente</em></h1>
<p class="meta">Dernière mise à jour : 1{chr(101)}r janvier {YEAR}</p>

<p class="lead">Les présentes Conditions Générales de Vente (« CGV ») régissent les abonnements payants à l'application MesureChâssis. Elles s'appliquent à toute commande passée à compter de la fin de la période d'essai gratuite.</p>

<h2>1. Champ d'application</h2>
<p>Les présentes CGV s'appliquent à tous les abonnements souscrits par les professionnels (B2B) à l'application MesureChâssis. Elles complètent les <a href="cgu.html">CGU</a> et constituent ensemble le contrat liant l'utilisateur à l'éditeur.</p>

<h2>2. Offres et tarifs</h2>
<p>Tarifs en vigueur au {YEAR} (hors TVA, prix indicatifs susceptibles d'évolution avec préavis de 30 jours) :</p>

<h3>Plan Artisan — 24,99 €/mois HT</h3>
<ul>
  <li>1 utilisateur unique</li>
  <li>Chantiers et exports illimités</li>
  <li>Stockage cloud sécurisé</li>
  <li>Support par email</li>
</ul>

<h3>Plan Entreprise — 54,99 €/mois HT</h3>
<ul>
  <li>2 utilisateurs inclus (Administrateur + Technicien ou Commercial)</li>
  <li>Utilisateurs supplémentaires : <strong>+4,99 €/mois HT par siège supplémentaire</strong></li>
  <li>Gestion d'équipe et rôles avancés</li>
  <li>Logo entreprise sur les exports PDF</li>
  <li>Support prioritaire</li>
</ul>

<p>La TVA applicable est celle en vigueur en Belgique (21 %) sauf dispositions spécifiques (autoliquidation intra-UE B2B avec numéro de TVA valide).</p>

<h2>3. Période d'essai et facturation</h2>
<p>Tout nouvel utilisateur bénéficie d'une <strong>période d'essai gratuite de 90 jours</strong>. À l'expiration de cette période :</p>
<ul>
  <li>Si l'utilisateur a souscrit un abonnement, la facturation démarre automatiquement ;</li>
  <li>À défaut de souscription, l'accès aux fonctionnalités est restreint mais les données sont conservées pendant 12 mois.</li>
</ul>

<h2>4. Modalités de paiement</h2>
<p>Les abonnements sont prélevés mensuellement par carte bancaire via notre prestataire de paiement Stripe (PCI-DSS niveau 1). Les moyens acceptés sont : Visa, MasterCard, American Express, Bancontact, SEPA.</p>
<p>En cas d'échec de prélèvement, deux nouvelles tentatives seront effectuées sur 7 jours. Au-delà, l'accès au compte sera suspendu jusqu'à régularisation. Des frais de relance forfaitaires de 15 € pourront être appliqués conformément à l'article XX.21 du CDE.</p>

<h2>5. Reconduction et résiliation</h2>
<p>L'abonnement est conclu pour une durée indéterminée et reconduit tacitement chaque mois. L'utilisateur peut résilier à tout moment depuis l'interface « Profil » de l'application. La résiliation prend effet à la fin de la période en cours déjà facturée — aucun remboursement au prorata.</p>

<h2>6. Droit de rétractation</h2>
<p>L'application étant exclusivement destinée à un usage professionnel (B2B), le droit de rétractation de 14 jours prévu pour les consommateurs (art. VI.47 du CDE) <strong>ne s'applique pas</strong>. Toutefois, la période d'essai de 90 jours en tient lieu fonctionnellement.</p>

<h2>7. Évolution des tarifs</h2>
<p>L'éditeur se réserve le droit d'ajuster ses tarifs avec un préavis de 30 jours par email. L'utilisateur dispose alors d'un droit de résiliation sans frais s'il refuse le nouveau tarif.</p>

<h2>8. Facturation</h2>
<p>Les factures sont émises automatiquement à chaque prélèvement et envoyées par email à l'adresse renseignée dans le compte. Elles sont également archivées et téléchargeables depuis l'application pendant 10 ans (article XV.20 du CDE).</p>

<h2>9. Niveau de service (SLA)</h2>
<p>L'éditeur s'engage sur un niveau de disponibilité de <strong>99,5 % par mois</strong>, hors maintenances planifiées notifiées 48 h à l'avance. En cas de manquement avéré, un avoir au prorata de l'indisponibilité pourra être accordé sur demande écrite.</p>

<h2>10. Données et portabilité</h2>
<p>L'utilisateur peut à tout moment exporter ses données (clients, chantiers, mesures) au format CSV ou JSON depuis l'application. En cas de résiliation, un délai de 30 jours est accordé pour récupérer ses données avant suppression définitive.</p>

<h2>11. Médiation et litiges</h2>
<p>En cas de litige, l'utilisateur est invité à contacter le service client à <a href="mailto:info@mesurechassis.com">info@mesurechassis.com</a>. À défaut de résolution amiable, le litige sera porté devant les tribunaux belges compétents.</p>
<p>Conformément à l'article 14 du règlement UE n° 524/2013, une plateforme européenne de règlement en ligne des litiges est disponible : <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">https://ec.europa.eu/consumers/odr</a>.</p>

<h2>12. Force majeure</h2>
<p>Aucune partie ne pourra être tenue responsable d'un manquement résultant d'un cas de force majeure (catastrophe naturelle, guerre, panne réseau internet généralisée, attaque cybernétique massive, décision gouvernementale).</p>
"""
    return page_wrap(
        "Conditions Générales de Vente — MesureChâssis",
        "CGV de MesureChâssis. Tarifs, modalités de paiement, droit de rétractation, résiliation pour l'abonnement SaaS B2B.",
        "cgv.html",
        "cgv",
        body,
    )


# =============================================================================
# COOKIES — Politique
# =============================================================================
def make_cookies() -> str:
    body = f"""
<h1>Politique <em>Cookies</em></h1>
<p class="meta">Dernière mise à jour : 1{chr(101)}r janvier {YEAR}</p>

<p class="lead">Cette politique explique l'utilisation des cookies et traceurs sur le site mesurechassis.com et au sein de l'application MesureChâssis, conformément au RGPD et à la directive ePrivacy (loi du 13 juin 2005 sur les communications électroniques, transposée en Belgique).</p>

<h2>Qu'est-ce qu'un cookie ?</h2>
<p>Un cookie est un petit fichier texte déposé sur votre appareil par le site que vous visitez. Il permet de mémoriser des informations (préférences, session de connexion, statistiques) pendant ou entre vos visites.</p>

<h2>Cookies utilisés</h2>

<h3>1. Cookies strictement nécessaires (exemptés de consentement)</h3>
<p>Ces cookies sont indispensables au fonctionnement du site et de l'application. Ils ne peuvent pas être désactivés.</p>
<ul>
  <li><strong>mc_session</strong> — Session utilisateur authentifiée (JWT). Durée : 7 jours.</li>
  <li><strong>mc_cookie_consent</strong> — Mémorise votre choix sur le bandeau cookies. Durée : 12 mois.</li>
  <li><strong>mc_csrf</strong> — Protection contre les attaques CSRF. Durée : session.</li>
</ul>

<h3>2. Cookies de mesure d'audience (anonymisés)</h3>
<p>Nous n'utilisons <strong>aucun outil de tracking marketing</strong> (Google Analytics, Facebook Pixel, Hotjar, etc.) sur le site vitrine. Les statistiques d'usage de l'application sont collectées de manière agrégée et anonyme via nos propres serveurs.</p>

<h3>3. Cookies tiers</h3>
<p>Aucun cookie tiers (publicité, retargeting, réseaux sociaux) n'est déposé sur ce site. Seules les polices Google Fonts sont chargées (sans tracking).</p>

<h2>Vos choix</h2>
<p>Vous pouvez à tout moment :</p>
<ul>
  <li><strong>Configurer votre navigateur</strong> pour refuser tous les cookies ou être averti avant chaque dépôt. Notez que cela peut altérer certaines fonctionnalités du site ;</li>
  <li><strong>Effacer les cookies déjà déposés</strong> depuis les paramètres de votre navigateur ;</li>
  <li><strong>Revenir sur votre consentement</strong> en vidant le stockage local du site.</li>
</ul>

<h3>Comment désactiver les cookies ?</h3>
<ul>
  <li><strong>Chrome</strong> : Paramètres → Confidentialité et sécurité → Cookies et autres données des sites</li>
  <li><strong>Firefox</strong> : Paramètres → Vie privée et sécurité → Cookies</li>
  <li><strong>Safari</strong> : Préférences → Confidentialité</li>
  <li><strong>Edge</strong> : Paramètres → Cookies et autorisations de site</li>
</ul>

<h2>Données personnelles</h2>
<p>Les cookies strictement nécessaires peuvent contenir des données personnelles (identifiant de session). Leur traitement est encadré par notre <a href="confidentialite.html">Politique de confidentialité</a> et le RGPD.</p>

<h2>Modifications</h2>
<p>Cette politique peut être modifiée à tout moment. Les modifications prennent effet dès leur publication sur cette page. Nous vous invitons à consulter régulièrement cette page.</p>

<h2>Contact</h2>
<p>Pour toute question : <a href="mailto:info@mesurechassis.com">info@mesurechassis.com</a></p>
"""
    return page_wrap(
        "Politique cookies — MesureChâssis",
        "Politique d'utilisation des cookies sur MesureChâssis. Conformité RGPD et directive ePrivacy belge.",
        "cookies.html",
        "cookies",
        body,
    )


# =============================================================================
# FAQ
# =============================================================================
def make_faq() -> str:
    qa_groups = [
        ("Démarrage", [
            ("Sur quels appareils l'application fonctionne-t-elle ?",
             "MesureChâssis est disponible sur iOS 15 et plus, Android 9 et plus. Une version web responsive est également accessible depuis n'importe quel navigateur récent (Chrome, Safari, Firefox, Edge)."),
            ("Comment créer mon compte ?",
             "Téléchargez l'application, sélectionnez « Inscription », choisissez votre type de compte (Artisan ou Entreprise), renseignez vos informations et validez. La bêta gratuite démarre immédiatement sans CB requise."),
            ("Puis-je essayer l'application sans engagement ?",
             "Oui ! Tous les nouveaux comptes bénéficient de 90 jours d'essai gratuit, sans carte bancaire requise. Vous pouvez résilier à tout moment depuis votre profil."),
            ("Quelle est la différence entre Artisan et Entreprise ?",
             "Le plan Artisan (24,99 €/mois HT) est destiné aux indépendants : 1 seul utilisateur, fonctionnalités complètes. Le plan Entreprise (54,99 €/mois HT) inclut 2 utilisateurs avec gestion d'équipe (Admin, Commercial, Technicien), logo entreprise sur les PDF, et permet d'ajouter des sièges supplémentaires à 4,99 €/mois HT chacun."),
        ]),
        ("Fonctionnalités", [
            ("Quels types de formes de châssis sont supportés ?",
             "Le wizard prend en charge 7 formes : Rectangle/Carré, Porte d'entrée, Porte de garage, Trapèze, Triangle, Œil-de-bœuf, et bientôt Plein cintre, Arc surbaissé, Angle 90° et Bow-Window."),
            ("Comment fonctionne la vérification des diagonales ?",
             "L'application applique automatiquement le théorème de Pythagore à chaque saisie de cotes pour détecter les incohérences géométriques. Une alerte s'affiche si l'écart dépasse le seuil paramétré."),
            ("Puis-je ajouter des photos aux mesures ?",
             "Oui, chaque ouverture peut être documentée avec plusieurs photos (avant, après, détails techniques). Les photos sont stockées de manière sécurisée et incluses dans les exports PDF."),
            ("L'application fonctionne-t-elle hors-ligne ?",
             "Vous pouvez prendre des mesures en mode hors-ligne. Les données sont synchronisées automatiquement dès que la connexion est rétablie."),
            ("Quels formats d'export sont disponibles ?",
             "PDF technique avec votre logo (prêt fournisseur), Excel (XLSX), CSV, et JSON pour intégration CNC / ERP."),
            ("Comment fonctionne la dictée vocale ?",
             "Lors de la création d'un chantier ou de l'ajout de notes, tapez sur l'icône « microphone » pour dicter vos notes en mains-libres. Compatible iOS et Android."),
        ]),
        ("Tarifs & facturation", [
            ("Comment se passe la facturation ?",
             "À l'issue des 90 jours d'essai, vous serez invité à choisir un plan. Le paiement est mensuel par carte bancaire via Stripe. Les factures sont envoyées par email et archivées dans votre compte."),
            ("Puis-je changer de plan en cours d'abonnement ?",
             "Oui, vous pouvez passer du plan Artisan au plan Entreprise (ou inversement) à tout moment. Le changement prend effet immédiatement, avec ajustement au prorata."),
            ("Comment ajouter un utilisateur supplémentaire à mon plan Entreprise ?",
             "Depuis l'écran « Équipe » de votre admin, cliquez sur « Inviter un membre ». Au-delà du 3e utilisateur, un supplément de 4,99 €/mois HT par siège vous est facturé après confirmation."),
            ("La TVA est-elle incluse dans les tarifs affichés ?",
             "Non, tous les tarifs affichés sont HT (hors taxes). La TVA belge de 21 % est ajoutée. Pour les entreprises de l'UE disposant d'un numéro de TVA valide, l'autoliquidation s'applique."),
            ("Quels moyens de paiement acceptez-vous ?",
             "Cartes Visa, MasterCard, American Express, Bancontact, et prélèvement SEPA. Tous les paiements sont sécurisés via Stripe (PCI-DSS niveau 1)."),
        ]),
        ("Données & sécurité", [
            ("Où sont stockées mes données ?",
             "Toutes les données sont hébergées en Union européenne (centres de données conformes RGPD) avec chiffrement au repos (AES-256) et en transit (TLS 1.3)."),
            ("Mes données sont-elles sauvegardées ?",
             "Oui, des sauvegardes automatiques quotidiennes sont effectuées avec une rétention de 30 jours. Vous pouvez également exporter vos données à tout moment."),
            ("Puis-je supprimer mon compte ?",
             "Oui, en 1 clic depuis votre profil. Conformément au RGPD, vos données personnelles sont anonymisées ou supprimées sous 30 jours. Voir notre <a href=\"confidentialite.html\">politique RGPD</a>."),
            ("Mes clients voient-ils mes données ?",
             "Non. Vos données restent strictement confidentielles. Seuls les membres de votre équipe que vous invitez explicitement peuvent y accéder, selon leur rôle."),
        ]),
        ("Support", [
            ("Comment contacter le support ?",
             "Par email : <a href=\"mailto:info@mesurechassis.com\">info@mesurechassis.com</a>. Réponse sous 24h ouvrées (12h pour les comptes Entreprise)."),
            ("Y a-t-il une formation incluse ?",
             "Le <a href=\"guide.html\">guide d'utilisation</a> en ligne est gratuit et exhaustif. Pour les équipes Entreprise, une session d'onboarding visio de 30 min est offerte."),
            ("Comment suggérer une amélioration ?",
             "Depuis l'application, allez dans « Feedback » et soumettez votre idée. Toutes les suggestions sont étudiées par notre équipe produit."),
        ]),
    ]

    faq_html = ""
    for group_title, qs in qa_groups:
        faq_html += f'<h2>{group_title}</h2>\n'
        for q, a in qs:
            faq_html += f'<details class="faq-item">\n<summary>{q}</summary>\n<p>{a}</p>\n</details>\n'

    body = f"""
<h1>Questions <em>fréquentes</em></h1>
<p class="lead">Toutes les réponses sur MesureChâssis : fonctionnalités, tarifs, sécurité, support. Vous ne trouvez pas votre réponse ? <a href="contact.html">Contactez-nous</a>.</p>

<style>
.faq-item {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: .75rem;
  overflow: hidden;
  transition: border-color .2s;
}}
.faq-item[open] {{ border-color: var(--border-orange); }}
.faq-item summary {{
  padding: 1.1rem 1.4rem;
  cursor: pointer;
  font-weight: 600;
  color: var(--white);
  font-family: var(--font-head);
  font-size: 1rem;
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.faq-item summary::-webkit-details-marker {{ display: none; }}
.faq-item summary::after {{
  content: '+';
  color: var(--orange);
  font-size: 1.5rem;
  transition: transform .2s;
  font-weight: 300;
}}
.faq-item[open] summary::after {{ content: '×'; }}
.faq-item p {{
  padding: 0 1.4rem 1.2rem;
  margin: 0;
  color: var(--gray2);
  line-height: 1.7;
}}
</style>

{faq_html}

<div style="margin-top:3rem;padding:2rem;background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
  <h3 style="margin-top:0">Vous ne trouvez pas votre réponse ?</h3>
  <p>Notre équipe répond en moins de 24h ouvrées.</p>
  <a href="contact.html" class="btn-primary" style="display:inline-block;margin-top:.5rem">✉️ Nous contacter</a>
</div>
"""
    return page_wrap(
        "FAQ — Questions fréquentes — MesureChâssis",
        "Toutes les réponses sur MesureChâssis : tarifs, fonctionnalités, sécurité, RGPD, support. Réponses claires aux questions des menuisiers.",
        "faq.html",
        "faq",
        body,
    )


# =============================================================================
# TELECHARGER
# =============================================================================
def make_telecharger() -> str:
    body = f"""
<h1>Télécharger <em>MesureChâssis</em></h1>
<p class="lead">L'application est en cours de validation par les stores officiels. En attendant, vous pouvez accéder à la version bêta complète via les canaux ci-dessous.</p>

<style>
.dl-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin: 2rem 0;
}}
@media (max-width: 700px) {{ .dl-grid {{ grid-template-columns: 1fr; }} }}
.dl-card {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem 1.5rem;
  text-align: center;
  transition: border-color .2s, transform .2s;
}}
.dl-card:hover {{ border-color: var(--border-orange); transform: translateY(-3px); }}
.dl-card .icon-os {{ font-size: 3rem; margin-bottom: .75rem; display: block; }}
.dl-card h3 {{ margin: 0 0 .5rem; color: var(--white); }}
.dl-card .platform {{ font-size: .85rem; color: var(--gray3); margin-bottom: 1.25rem; }}
.dl-card .status-badge {{
  display: inline-block;
  padding: .35rem .8rem;
  border-radius: 20px;
  font-size: .78rem;
  font-weight: 600;
  margin-bottom: 1rem;
}}
.status-beta {{ background: var(--orange-dim); color: var(--orange); border: 1px solid var(--border-orange); }}
.status-soon {{ background: rgba(255,255,255,.05); color: var(--gray2); border: 1px solid var(--border); }}
.dl-btn {{
  display: inline-block;
  padding: .85rem 1.5rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  margin-top: .5rem;
  width: 100%;
  font-size: .95rem;
}}
.dl-btn-primary {{ background: var(--orange); color: var(--white); }}
.dl-btn-disabled {{ background: var(--bg3); color: var(--gray2); border: 1px solid var(--border); cursor: not-allowed; }}
.dl-info {{ font-size: .82rem; color: var(--gray3); margin-top: 1rem; line-height: 1.5; }}

.notify-form {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  margin: 2rem 0;
}}
.notify-form input[type=email] {{
  width: 100%;
  padding: .85rem 1rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--white);
  font-family: var(--font-body);
  font-size: 1rem;
  margin-bottom: .75rem;
}}
.notify-form input[type=email]:focus {{ outline: none; border-color: var(--orange); }}
.notify-form button {{
  width: 100%;
  padding: .85rem;
  background: var(--orange);
  color: var(--white);
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  font-size: 1rem;
}}
.notice-banner {{
  background: var(--orange-dim);
  border: 1px solid var(--border-orange);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  margin: 2rem 0;
  display: flex;
  gap: .75rem;
  align-items: flex-start;
}}
</style>

<div class="notice-banner">
  <div style="font-size:1.5rem">ℹ️</div>
  <div>
    <strong style="color:var(--white)">En attente de validation officielle</strong>
    <p style="margin:.25rem 0 0;font-size:.92rem">Notre application est en cours de soumission auprès du Google Play Store et de l'App Store. En attendant, accédez à la version bêta complète via le canal Internal Testing (Android) ou recevez une notification dès la sortie iOS.</p>
  </div>
</div>

<div class="dl-grid">

  <div class="dl-card">
    <span class="icon-os">🤖</span>
    <h3>Android</h3>
    <div class="platform">Téléphones &amp; tablettes · Android 9+</div>
    <span class="status-badge status-beta">● Bêta disponible</span>
    <a href="{ANDROID_URL}" target="_blank" rel="noopener" class="dl-btn dl-btn-primary">
      ⬇️ Rejoindre le test interne
    </a>
    <p class="dl-info">Cliquez sur le lien, acceptez de devenir testeur, puis téléchargez l'application depuis le Play Store comme une app classique. Mises à jour automatiques.</p>
  </div>

  <div class="dl-card">
    <span class="icon-os">🍎</span>
    <h3>iOS</h3>
    <div class="platform">iPhone &amp; iPad · iOS 15+</div>
    <span class="status-badge status-soon">⏳ Bientôt disponible</span>
    <a href="#notify" class="dl-btn dl-btn-disabled" onclick="document.getElementById('notify').scrollIntoView({{behavior:'smooth'}});return false;">
      🔔 Recevoir une notification
    </a>
    <p class="dl-info">Notre version iOS est en cours de soumission TestFlight. Laissez votre email ci-dessous, vous serez averti dès l'ouverture du bêta-test.</p>
  </div>

</div>

<h2 id="notify">Soyez averti dès la sortie iOS</h2>
<form class="notify-form" id="notifyForm" onsubmit="return submitNotify(event)">
  <p style="margin-bottom:1rem">Entrez votre email pour recevoir un lien d'installation TestFlight dès qu'il sera disponible. Aucun spam, aucune utilisation commerciale.</p>
  <input type="email" name="email" placeholder="vous@entreprise.fr" required aria-label="Votre email">
  <button type="submit">🔔 Me prévenir dès la sortie</button>
  <p id="notifyFeedback" style="margin-top:.75rem;color:var(--green);text-align:center;display:none">✅ Merci ! Nous vous écrirons dès que la version iOS sera prête.</p>
</form>

<h2>Version Web (accessible immédiatement)</h2>
<p>Vous pouvez également accéder à la version web complète depuis n'importe quel navigateur récent (Chrome, Safari, Firefox, Edge), sur ordinateur ou mobile :</p>
<p><a href="beta.html" class="btn-primary" style="display:inline-block;padding:.75rem 1.25rem">🌐 Accéder à la version web</a></p>

<h2>Configuration requise</h2>
<ul>
  <li><strong>Android</strong> : version 9 (Pie) ou plus récente · 100 Mo d'espace libre</li>
  <li><strong>iOS</strong> : iOS 15 ou plus récent · iPhone 8 minimum</li>
  <li><strong>Web</strong> : Chrome 90+, Safari 15+, Firefox 88+, Edge 90+</li>
  <li><strong>Connexion</strong> : 4G/Wi-Fi recommandée pour la synchro (mode hors-ligne supporté)</li>
</ul>

<script>
function submitNotify(e) {{
  e.preventDefault();
  var email = e.target.email.value;
  // Envoi vers backend FastAPI : POST /api/notify-ios
  fetch('/api/notify-ios', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{email: email}})
  }}).catch(function() {{ /* silently fail */ }});
  document.getElementById('notifyFeedback').style.display = 'block';
  e.target.reset();
  return false;
}}
</script>
"""
    return page_wrap(
        "Télécharger MesureChâssis — Android Bêta · iOS bientôt",
        "Téléchargez MesureChâssis. Bêta Android via Internal Testing Play Store. Version iOS bientôt disponible — laissez votre email pour être averti.",
        "telecharger.html",
        "telecharger",
        body,
    )


# =============================================================================
# 404
# =============================================================================
def make_404() -> str:
    body = """
<div style="text-align:center;padding:4rem 0">
<h1 style="font-size:8rem;margin-bottom:0">404</h1>
<h2 style="margin-top:0">Page introuvable</h2>
<p style="max-width:500px;margin:1rem auto 2rem">La page que vous cherchez n'existe pas ou a été déplacée. Pas de panique, retournez à l'accueil ou consultez le guide.</p>
<div style="display:flex;gap:.75rem;justify-content:center;flex-wrap:wrap">
<a href="index.html" class="btn-primary">🏠 Accueil</a>
<a href="guide.html" class="btn-secondary">📘 Guide</a>
<a href="contact.html" class="btn-secondary">✉️ Contact</a>
</div>
</div>
"""
    return page_wrap(
        "404 — Page introuvable — MesureChâssis",
        "Cette page n'existe pas. Retournez à l'accueil de MesureChâssis.",
        "404.html",
        "",
        body,
    )


# =============================================================================
# À PROPOS
# =============================================================================
def make_about() -> str:
    body = """
<h1>À <em>propos</em></h1>
<p class="lead">MesureChâssis est né d'un constat simple : les menuisiers perdent en moyenne <strong>2 heures par chantier</strong> entre la prise de mesures sur papier, la ressaisie au bureau, et les allers-retours en cas d'erreur. Nous avons construit une solution qui les libère de ce fardeau.</p>

<h2>Notre mission</h2>
<p>Donner aux artisans menuisiers et aux entreprises de menuiserie un outil terrain <strong>aussi fiable que leur mètre ruban</strong>, mais infiniment plus rapide, plus précis, et qui parle directement à leurs fournisseurs et à leurs ateliers.</p>

<h2>Notre histoire</h2>
<p>Nous avons grandi entre les copeaux, les chantiers et les bureaux d'études. En interrogeant plus de 50 menuisiers belges et français, un même refrain revenait : « Mon carnet est mouillé, j'ai dû ressaisir 30 cotes, et j'ai oublié la diagonale de la baie de la cuisine ».</p>
<p>En 2025, une équipe de développeurs passionnés s'est associée à des menuisiers professionnels pour concevoir MesureChâssis. Chaque fonctionnalité a été validée sur de vrais chantiers, par de vrais artisans, avant d'être intégrée.</p>

<h2>Nos valeurs</h2>
<ul>
  <li><strong>Simplicité radicale</strong> — Un menuisier doit pouvoir saisir une mesure complète en moins de 30 secondes.</li>
  <li><strong>Données souveraines</strong> — Vos données vous appartiennent. Hébergement UE, RGPD strict, suppression en 1 clic.</li>
  <li><strong>Honnêteté commerciale</strong> — Pas de carte bancaire pendant l'essai. Pas de frais cachés. Annulation en 1 clic.</li>
  <li><strong>Proximité terrain</strong> — Chaque feedback est lu et étudié par l'équipe produit.</li>
</ul>

<h2>Roadmap publique</h2>
<p>Nous partageons ouvertement notre roadmap. Voici ce qui arrive prochainement :</p>
<ul>
  <li>✅ Wizard 7 formes (Rectangle, Trapèze, Triangle, Œil-de-bœuf, Porte, etc.)</li>
  <li>✅ Exports PDF/Excel/CSV/JSON</li>
  <li>✅ Gestion d'équipe et rôles</li>
  <li>🔄 <em>En cours</em> — 4 formes complexes (Plein cintre, Arc surbaissé, Angle 90°, Bow-Window)</li>
  <li>🔄 <em>En cours</em> — Intégration Stripe (abonnements)</li>
  <li>⏳ <em>Prévu Q3 {year}</em> — Mode sombre/clair adaptatif</li>
  <li>⏳ <em>Prévu Q3 {year}</em> — Internationalisation FR/EN/NL</li>
  <li>⏳ <em>Prévu Q4 {year}</em> — Intégration CNC (formats spécifiques machines)</li>
</ul>

<h2>Nous contacter</h2>
<p>L'équipe MesureChâssis est à votre disposition pour toute question, suggestion ou partenariat.</p>
<p>
  ✉️ <a href="mailto:info@mesurechassis.com">info@mesurechassis.com</a><br>
  💬 <a href="contact.html">Formulaire de contact</a><br>
  📘 <a href="guide.html">Guide d'utilisation</a>
</p>
""".replace("{year}", "2026")
    return page_wrap(
        "À propos — MesureChâssis",
        "Découvrez l'histoire et la mission de MesureChâssis : libérer les menuisiers du carnet papier grâce à une application terrain fiable.",
        "a-propos.html",
        "a-propos",
        body,
    )
