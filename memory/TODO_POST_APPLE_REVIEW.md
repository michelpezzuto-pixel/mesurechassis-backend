# 🔴 TODO POST-APPLE REVIEW — MesureChâssis

**Date** : Juin 2026
**Statut** : En attente de validation Apple Build 108

## 🚨 RAPPEL CRITIQUE POUR L'AGENT
Dès que Michel dit *"Apple a validé"* ou équivalent :
1. ▶️ Exécuter cette checklist (Backend / Frontend / Campagne / Tarifs)
2. ▶️ **PROPOSER À MICHEL** de lancer le plan SEO : voir `/app/memory/seo_action_plan.md`
   → Première étape rapide (1h30) : Google Business Profile + Search Console + Trustpilot
3. ▶️ Mettre à jour Stripe avec les nouveaux tarifs : voir `/app/memory/pricing.md`
   (Solo 19€ / Entreprise 59€ / Pro 249€ / Trial 14 jours / paiement via site web façon Shopify)

## Contexte
Pour la soumission Apple Review, tout le contenu commercial / B2B / prix
a été masqué sur iOS. Une fois la validation obtenue, il faudra basculer
sur le modèle commercial réel et **refaire tous les contenus marketing**.

## Checklist de bascule (à exécuter dès qu'Apple a validé)

### 1. Backend
- [ ] Mettre `BETA_MODE = False` dans `/app/backend/db.py`
- [ ] Activer la **clé Stripe en mode LIVE** (remplacer `sk_test_...` par `sk_live_...` dans `.env`)
- [ ] Vérifier que les paywall des features (Yann, Import CDC, Exports Pro) fonctionnent en conditions réelles
- [ ] Désactiver le compte démo `applereview@mesurechassis.com` (ou le laisser comme compte test interne)

### 2. Frontend iOS
- [ ] Réactiver l'inscription Entreprise/Équipe sur iOS dans `/app/frontend/app/index.tsx`
  → Retirer le `Platform.OS === 'ios'` qui masque le bloc "Compte Entreprise"
- [ ] Réafficher la grille tarifaire dans `/app/frontend/app/subscription.tsx` sur iOS
  (si Apple l'autorise via leur Reader App Rule OU via in-app purchases)
- [ ] Vérifier qu'aucune mention "Apple Review" ne reste dans les commentaires/copy

### 3. Campagne emailing (`/app/backend/routes/campaign.py`)
- [ ] Refondre **les 3 templates** :
  - `BODY_TEMPLATE` (premier contact)
  - `RELANCE_TEMPLATE` (J+3)
  - `RELANCE_2_TEMPLATE` (J+7)
- [ ] Intégrer les nouveaux arguments :
  - "Disponible sur App Store + Google Play" (avec logos)
  - Nouveau positionnement commercial (plus "gratuit jusqu'au 30 sept")
  - Tarifs visibles
  - Témoignages clients si dispo
- [ ] Garder la **feature scan bordereau** comme accroche principale (très puissante)
- [ ] Modifier les **sujets** pour annoncer la sortie officielle

### 4. Site vitrine
- [ ] Mettre à jour `/app/site_mesurechassis_final/` :
  - Bannière "Disponible sur App Store ✨"
  - Liens deeplinks vers les stores (App Store + Play Store)
  - Retirer les mentions beta
  - Mettre les vrais tarifs

### 5. Dashboard admin
- [ ] Vérifier que les stats reflètent le nouveau modèle (acquisitions payantes)
- [ ] Possiblement ajouter une section "Conversions Trial → Pro"

### 6. Communication
- [ ] **Annonce LinkedIn** de sortie officielle
- [ ] **Email à tous les beta testeurs** pour les remercier + leur offrir un avantage (1 mois gratuit ?)
- [ ] **Post de blog / vidéo** célébrant la sortie

### 7. 🌍 EXPANSION EUROPÉENNE (vision Michel — 24/06/2026)
**Trigger** : "quand l'app sera sur Apple Store, tout le monde pourra y accéder"
→ Phase d'expansion internationale à partir de la France/Belgique vers toute l'Europe.

**Pays cibles prioritaires** :
- 🇮🇹 Italie (forte tradition menuiserie, marché énorme)
- 🇪🇸 Espagne
- 🇩🇪 Allemagne (gros volume professionnel)
- 🇵🇹 Portugal
- 🇨🇭 Suisse (déjà BE/CH proximité linguistique)
- Puis tous les pays de l'Espace économique européen

**Travaux requis** :

**a) APPLICATION mobile (Expo)**
- [ ] Étendre i18n actuel (FR/EN/NL) à : IT, ES, DE, PT, PL, CS
- [ ] Vérifier que toutes les strings UI sont via `useTranslation()` (pas hardcodées)
- [ ] Locales date/nombre par pays (séparateurs décimaux : virgule en FR/DE, point en EN/IT)
- [ ] Devises affichées par pays (EUR partout mais SEK/DKK/CZK pour exports paywall)
- [ ] **Validation TVA VIES** déjà fonctionnelle pour TOUS les 27 pays UE (vérifier dans `vat_validator.py`)

**b) SITE WEB (mesurechassis.com)**
- [ ] Refonte multilingue avec sélecteur de langue en header
- [ ] Hreflang tags pour SEO (`<link rel="alternate" hreflang="it" href="...">`)
- [ ] Pages clés à traduire : index, tarifs, à-propos, FAQ, CGU/CGV
- [ ] URLs localisées (`/it/`, `/es/`, `/de/`...)
- [ ] Vidéo hero (cf prompt Michel du 24/06) en version sous-titrée par langue

**c) BACKEND**
- [ ] Email templates campagne en toutes langues (selon le pays détecté du prospect)
- [ ] Détection langue auto (header Accept-Language ou champ explicite)
- [ ] Resend : configurer reply-to / from name localisé

**d) MARKETING**
- [ ] Identifier prospects par pays (LinkedIn Sales Navigator, ProDevis bases régionales)
- [ ] Campagne email pays par pays (commencer 30/jour PAR PAYS pour ne pas griller le domaine)
- [ ] Partenariats locaux : équivalents Elcia dans chaque pays (Wartmann en CH, Lobor en IT, etc.)

### 8. 🤖 FEATURE YANN-FEEDBACK (vision Michel — 24/06/2026)
- [ ] Intégrer Yann (IA Claude Sonnet 4.5) pour analyser les feedbacks utilisateurs reçus
- [ ] Détection automatique des bugs vs features requests vs compliments
- [ ] Catégorisation auto par module (mesures / exports / chantiers / etc.)
- [ ] Dashboard admin avec sentiment analysis et priorisation
- [ ] **À détailler** quand on attaque (spécification fonctionnelle à co-construire avec Michel)


### 9. 💰 STRATÉGIE SPONSORSHIP B2B — Vision Michel 24/06/2026

**Objectif** : Monétiser via les gammistes/profilistes du secteur menuiserie au lieu (ou en complément) de la conversion artisan-à-artisan classique.

**Cibles prioritaires** (par ordre de pertinence belge/francophone) :
- 🇧🇪 **Aliplast** (Tisselt, Belgique) — gammiste alu majeur, prioritaire géo
- 🇩🇪 **Schüco** (Bielefeld, Allemagne)
- 🇧🇪 **Reynaers Aluminium** (Duffel, Belgique) — historique belge
- 🇩🇪 **Profine / KÖMMERLING** (PVC premium)
- 🇧🇪 **AluK Group** (gammiste alu)
- 🇩🇪 **Heroal** (alu)
- 🇸🇪 **Sapa Building Systems** (devenu Hydro)

**5 modèles de monétisation envisagés** (du plus discret au plus rentable) :

1. **Catalogue Produits Embarqué** ⭐ RECO PRINCIPALE
   - Modal "Profil utilisé" avec gammes Schüco/Aliplast/Reynaers/etc.
   - Pricing : 5-15K€/an par gammiste
   - 5 gammistes = 25-75K€/an passifs
   - Apple OK ✅ (non-intrusif)
   - Bonus : exports PDF mentionnent automatiquement le profil

2. **White Label / OEM** 🚀 DEAL MAJEUR
   - Le gammiste distribue l'app sous SA marque ("Schüco MeasurePro", "Aliplast Survey")
   - Pricing : 50-200K€/an + variable
   - **C'est le pitch à présenter à Batibouw 2027** (cf section "BATIBOUW 2027")
   - Attention : peut impliquer exclusivité

3. **Sponsoring de Fonctionnalité ("Powered by")**
   - "Calcul Uw thermique propulsé par Aliplast"
   - Pricing : 3-8K€/an par feature

4. **Génération de leads qualifiés**
   - L'artisan finit ses mesures → "Demander un devis aux gammistes partenaires"
   - Commission 10-50€/lead transmis
   - Potentiel 10-50K€/MOIS si 1000 leads/mois

5. **Bannière in-app classique** ❌ DÉCONSEILLÉ
   - Trop peu rentable, risque Apple Guideline 4.2

**Pièges à éviter** :
- ❌ Exclusivité avec 1 gammiste trop tôt → garde-toi plusieurs partenaires
- ❌ Pub agressive qui pollue l'app
- ❌ Favoriser visuellement 1 marque (algo rotation équitable)
- ❌ **JAMAIS** vendre les données des artisans (actif #1)
- ❌ Apple rejet pour "consumer ads" → mention discrète uniquement

### 9.bis 🎪 BATIBOUW 2027 — STRATÉGIE PARASITE 🥷

**Date** : Salon Batibouw 2027 (généralement fin février / début mars à Brussels Expo)

**Mission** : Aller en mode "visiteur stratégique" sans payer de stand, et pitcher les gammistes UN PAR UN sur leur stand.

**Pourquoi cette approche** :
- 💸 Économie : un stand à Batibouw = 15-50K€ pour 1 semaine
- 🎯 Tous les décideurs gammistes sont sur place ce semaine-là (directeur marketing, directeur commercial, direction générale)
- 🤝 Approche personnelle = + de chances qu'un appel à froid LinkedIn
- 🍻 Discussion informelle stand = bien plus efficace qu'un email

**Plan d'attaque** :
1. **Préparer en amont** (janvier 2027) :
   - Pitch deck 10 slides (problème menuisier / solution app / KPIs après 1 an / proposition partenariat)
   - Démo iPad prête à montrer (login `applereview@mesurechassis.com` / `MesureChassis2026`)
   - Flyer A5 imprimé en 50 exemplaires avec QR code → app
   - Carte de visite avec photo professionnelle
2. **Au salon** :
   - J1 : repérer tous les stands gammistes + horaires d'affluence
   - J2-J3 : aller voir le commercial → demander une carte de visite du directeur marketing → revenir le surlendemain avec un mail préparé
   - J4-J5 : retour pitch avec démo live "regardez en 3 minutes ce que vos menuisiers utilisent"
3. **Suivi post-salon** (mars 2027) :
   - Email de remerciement avec deck en pièce jointe
   - Calendly pour réunion follow-up

**Si ça marche vraiment bien** :
- 🎯 Reverter la décision et **prendre un stand pour Batibouw 2028** (avec budget validé via les premiers contrats sponsoring)
- Stand cible : 18-36m², zone "Innovations digitales" du salon

**Garder en mémoire** :
- ⚠️ Ne pas oublier de **réserver les billets visiteurs** dès l'ouverture des inscriptions Batibouw (octobre 2026 généralement)
- ⚠️ S'inscrire au B2B Day du salon (jour réservé professionnels, moins de foule, + de temps pour pitcher)

**Notes commerciales** :
- Préparer un argumentaire spécifique à chaque gammiste (étude de leur catalogue avant le salon)
- Avoir un "deal type" prêt : 12K€/an Catalogue Embarqué + 12 mois d'exclusivité catégorie
- Backup : proposer un POC gratuit 3 mois si réticence (zéro risque pour eux)





## Notes importantes pour le prochain agent

⚠️ **Ne JAMAIS basculer ces changements avant validation Apple confirmée**. Si on remet
les prix/B2B trop tôt, le Build sera re-rejeté.

⚠️ **L'historique des rejets Apple est sensible** : 2 rejets précédents (3.1.1, 3.1.3c, 2.2).
La 3ème tentative DOIT passer — sinon Apple peut suspendre le compte développeur.

⚠️ Garder en parallèle le site web et Android **comme issue de secours** au cas où Apple
ne valide jamais (peu probable mais à anticiper).
