# MesureChâssis — PRD

Application Expo (React Native, mobile + web) de digitalisation des relevés de mesures pour entreprises de pose de menuiseries (fenêtres, portes, baies, trapèzes).

## Personas / Rôles
- **Admin** : pilotage de l'app, consultation des feedbacks utilisateurs.
- **Commercial** : crée des chantiers, fait le devis, suit le statut.
- **Technicien** : relève les mesures sur le terrain.

## Fonctionnalités (MVP livré)
1. **Authentification JWT** (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`)
   avec rôles Admin/Commercial/Technician — token stocké via `expo-secure-store`.
2. **Dashboard chantiers** — liste filtrable par statut (Devis à faire / Technique à valider / Clôturé) + recherche client/adresse.
3. **Création de chantier** via modal (client + adresse).
4. **Vue détail chantier** : infos client, liste des ouvertures mesurées, alertes, photos.
5. **4 blocs de mesure dynamiques** avec schéma SVG :
   - **Standard** : 3 largeurs, 3 hauteurs, 2 diagonales → alertes _Faux-aplomb_ (>5 mm) et _Hors-équerre_.
   - **Coulissant** : 3 largeurs + 5 hauteurs (détection flèche linteau).
   - **Porte** : 3 largeurs, 2 hauteurs, 2 diagonales.
   - **Trapèze** : calcul automatique de la pente en degrés (`atan(Δh/Δl)`).
6. **Photo par ouverture** : caméra native ou galerie (base64 inline).
7. **Bouton persistant rouge "⚠️ Signaler une anomalie / Idée"** sur tous les écrans de mesure — envoie commentaire + snapshot des données saisies + contexte page vers `/api/feedbacks`.
8. **Clôture chantier** : résumé visuel + export PDF (ReportLab) + export JSON, et passage du statut à `cloture`.

## Modèles MongoDB
- `users` (id, name, email, role, company_id, hashed_password)
- `chantiers` (id, client_name, address, status, created_by, assigned_to, created_at)
- `mesures` (id, chantier_id, block_type, label, dimensions, options, photo_url, alerts, slope_angle_deg)
- `feedbacks` (id, user_id, user_email, page_context, user_comment, screenshot_data, encoded_data_snapshot, created_at)

## Logique métier
- Détection faux-aplomb : `max(largeurs) - min(largeurs) > 5 mm` ou idem hauteurs.
- Hors-équerre : `diag_1 ≠ diag_2`.
- Trapèze : angle pente = `atan(|h_grande - h_petite| / |l_inter - l_petite|)` en degrés.

## Données de démo (seedées automatiquement)
- 3 comptes (admin/commercial/tech) — cf. `test_credentials.md`.
- 5 chantiers couvrant les 3 statuts.

## Stack
- Backend : FastAPI + Motor + MongoDB + ReportLab + PyJWT + Passlib(bcrypt).
- Frontend : Expo SDK 54 + Expo Router + react-native-svg + expo-camera + expo-image-picker + expo-print + expo-sharing.

## Routes API
| Méthode | Route | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | — | Inscription (avec `company_id` optionnel) |
| POST | `/api/auth/login` | — | Connexion |
| GET  | `/api/auth/me` | Bearer | Utilisateur courant |
| GET  | `/api/users` | Bearer | Liste utilisateurs (même société) |
| POST | `/api/chantiers` | Bearer | Créer un chantier (société du user) |
| GET  | `/api/chantiers?status_filter=&q=` | Bearer | Liste filtrée par société + statut + recherche |
| GET  | `/api/chantiers/{id}` | Bearer | Détail (404 si autre société) |
| PATCH| `/api/chantiers/{id}` | Bearer | MAJ statut / `assigned_to` / champs |
| DELETE | `/api/chantiers/{id}` | Bearer | Suppression (cascade mesures) |
| POST | `/api/mesures` | Bearer | Créer une ouverture (calcule alertes & pente) |
| GET  | `/api/chantiers/{id}/mesures` | Bearer | Mesures du chantier |
| DELETE | `/api/mesures/{id}` | Bearer | Supprime une mesure |
| POST | `/api/feedbacks` | Bearer | Envoi feedback |
| GET  | `/api/feedbacks` | Admin | Liste feedbacks (sa société uniquement) |
| DELETE | `/api/feedbacks/{id}` | Admin | Supprime un feedback (sa société) |
| GET  | `/api/chantiers/{id}/export.pdf` | Bearer | PDF (isolé par société) |
| GET  | `/api/chantiers/{id}/export.json` | Bearer | JSON brut (isolé par société) |

## Multi-tenant
Tous les endpoints chantiers / mesures / feedbacks / exports filtrent automatiquement par le `company_id` de l'utilisateur courant. Les utilisateurs d'une société ne voient jamais les données d'une autre.

## Workflow de mesure — Wizard 3 étapes (iter 6 — refonte complète)
1. **Étape 1 — Sélection** : 4 cartes A/B/C/D épurées (CHÂSSIS STANDARD / CHÂSSIS COULISSANT / PORTE D'ENTRÉE / CHÂSSIS TRAPÈZE). A, B, C → workflow rectangulaire ; D → workflow trapèze.
2. **Étape 2 — Cotes baie brute** :
   - Champs : Largeur, Hauteur, Diagonale 1, Diagonale 2 (+ Réserve Sol Fini si PORTE D'ENTRÉE).
   - **Auto-Pythagore** : dès que Largeur ET Hauteur sont remplies, le système pré-remplit Diagonale 1 et 2 avec `Math.round(√(W² + H²))` et badge `AUTO (Pythagore)` orange.
   - Pour chaque diagonale : **bouton vert "Valider"** (verrouille la valeur calculée) OU **bouton gris "Modifier"** (efface, ouvre clavier numérique). État `manual` accepté tel quel.
   - **Blocage strict** : SUIVANT impossible tant qu'une cote est vide OU qu'une diagonale est encore en état `AUTO` non confirmée. Border rouge + "COTE OBLIGATOIRE MANQUANTE".
3. **Étape 3 — Maçonnerie & isolation (INDICATIF)** :
   - `bloc_thickness` obligatoire.
   - Cartes radio :
     - A) **FAÇADE ISOLANTE EXTÉRIEURE (ITE)** → Épais. Isolant + Épais. Crépi
     - B) **ISOLATION INTÉRIEURE (ITI)** → Épais. Isolant + Épais. Plâtre/Finition
     - C) **BRIQUE DE PAREMENT** → Épais. Coulisse/Isolant + Épais. Brique
     - D) **CRÉPI SIMPLE** → Épais. Crépi/Finition (1 seul champ)
   - Tous les sous-champs marqués `(INDICATIF)` en gris.

## Top-bar "Signaler un problème"
Mini-bouton rouge non-intrusif **en haut à droite** de chaque étape du wizard. Ouvre un modal textuel rapide qui envoie commentaire + snapshot (step, blockType, s2, s3) à `/api/feedbacks` → consultable par l'admin via `/admin/feedbacks`.

1. **Étape 1 — Sélection type châssis** : 4 icônes A/B/C/D épurées (CHÂSSIS STANDARD, CHÂSSIS COULISSANT, PORTE D'ENTRÉE, CHÂSSIS TRAPÈZE) — aucun texte descriptif sous les icônes.
2. **Étape 2 — Prise à la mesure (baie brute)** : SVG _béton brut hachuré + linteau + sous-sol coupe_ (rect. ou trapèze), pas de menuiserie. Champs obligatoires :
   - `bay_height`, `bay_width`, `bay_diagonal`, `floor_reserve` (mm). Le champ "Réserve Sol Fini" a bordure rouge + icône warning + helper "OBLIGATOIRE — MANQUANT". Validation bloquante avant transition.
3. **Étape 3 — Conception maçonnerie & isolation (INDICATIF)** :
   - `bloc_thickness` obligatoire ; `wall_type` ∈ {ITE, ITI, CRÉPI SIMPLE} en cartes radio avec coupe SVG du mur.
   - Champs révélés selon type, tous marqués `(INDICATIF)` :
     - ITE → `insulation_thickness`, `finish_outer` (Crépi)
     - ITI → `insulation_thickness`, `finish_inner` (Plâtre/Finition)
     - CRÉPI SIMPLE → `finish_outer` (Crépi Ext.) + `finish_inner` (Crépi Int.)

## Modèles MongoDB — mise à jour iter 4
- `mesures` accepte 9 nouveaux champs optionnels côté BE (validés strictement côté FE) :
  `bay_height`, `bay_width`, `bay_diagonal`, `floor_reserve`,
  `bloc_thickness`, `wall_type` ("ite"|"iti"|"crepi_simple"),
  `insulation_thickness`, `finish_outer`, `finish_inner`.
- Les anciens champs (`width_top`, `height_left`, `diag_*`, etc.) restent optionnels pour rétrocompatibilité.
- L'export PDF affiche d'abord les nouveaux champs (libellés FR) puis les legacy si présents.

## Sécurité par rôle (iter 3)
- `POST /api/chantiers`, `PATCH /api/chantiers/{id}` : admin + commercial uniquement
- `DELETE /api/chantiers/{id}` : admin uniquement
- `POST /api/mesures` : tous les rôles authentifiés (le technicien est le primary user terrain)
- `GET /api/stats/company`, `GET /api/feedbacks`, `DELETE /api/feedbacks/{id}` : admin uniquement
- `POST /api/auth/push-token` : tout user (enregistre son propre token)

## Notifications push (iter 3)
- `POST /api/auth/push-token` enregistre le token Expo Push de l'utilisateur courant
- Quand un chantier reçoit un nouveau `assigned_to` via `PATCH /api/chantiers/{id}`, le backend envoie automatiquement (best-effort) une notification Expo Push au user assigné via `https://exp.host/--/api/v2/push/send`
- ⚠️ Limite Expo Go SDK 53+ : les push distants ne fonctionnent qu'en build EAS (Publish via Emergent)

## Mode hors-ligne (iter 3)
- File d'attente locale via `AsyncStorage` pour les créations de mesures
- Détection de l'état réseau via `@react-native-community/netinfo`
- Synchronisation automatique au retour du réseau, plus bandeau dashboard "N mesures en attente · Toucher pour synchroniser"
- Le service vit dans `src/services/offlineQueue.ts` ; le sync est démarré dans `app/_layout.tsx`

## Statistiques admin (iter 3)
- `GET /api/stats/company` (admin) retourne :
  - `total_chantiers`, `by_status` (3 statuts), `closure_rate` (%)
  - `total_mesures`, `total_alerts`
  - `by_technician` : liste triée par nb de mesures, avec `mesures` et `alerts` par user
- Écran `/admin/stats` accessible depuis le dashboard via icône graphique

## Business smart-add
Le feedback continu (anomalie/idée + snapshot des données) construit une **boucle de feedback produit** automatique : chaque chantier réel devient une source d'amélioration UX/métier traçable côté admin — différenciateur fort vs concurrents (papier + Excel).

## 🍎 Re-soumission Apple Store (11 juin 2026)
- **Contexte** : Build 1.0.0 (7) refusé par Apple le 5 juin — Guidelines 2.2 (Beta Testing) + 3.1.1 (Payments).
- **Correctifs build 1.1.0 (8)** :
  - iOS : tous les prix/CTA d'abonnement masqués (company-profile, modal formule, sièges supplémentaires team.tsx, parrainage)
  - iOS : bandeau "Mon abonnement" neutre, sans URL d'achat externe (conformité 3.1.3)
  - Toutes plateformes : wording "BETA GRATUITE / phase de test" → "OFFRE DE LANCEMENT" (i18n FR/EN/NL)
  - "(Bluetooth laser, à venir)" retiré de l'inscription
- **Compte démo Apple Review (prod Railway)** : `applereview@mesurechassis.com` / `AppleReview2026!` + chantier démo
- **Build 9** : compilé sur EAS et **soumis sur App Store Connect** (⚠️ build 8 NE PAS UTILISER : bug `)}` parasite dans dashboard.tsx = crash iOS, corrigé en build 9)
- **Bug critique corrigé** : `)}` orphelin dans dashboard.tsx (texte brut dans SafeAreaView → crash natif)

## 🤖 Préparation Play Store + Stripe LIVE (11 juin 2026, après-midi)
- Masquage des prix/CTA Stripe étendu à **Android** (Google Play Billing policy) : seul le **web** affiche les plans (`Platform.OS === "web"`)
- Build Android AAB lancé sur EAS : `81fe2c95-aa4e-4288-bf71-8c3efc5f3593` (version code 27)
- Fiche Play Store complète : `/app/memory/play_store_listing_fr.md` (⚠️ compte Play Console à créer, type ORGANISATION recommandé, feature graphic 1024×500 à créer)
- Plan de bascule Stripe LIVE : `/app/memory/stripe_live_switch.md` (⏸️ EN ATTENTE feu vert client — incohérences de prix 54,99/59,99 repérées à harmoniser)
- **Dossier complet** : `/app/memory/apple_resubmission.md` (réponse à Apple EN + notes review + étapes restantes)
- **Vigilance** : clé Stripe backend en mode TEST → passer en LIVE avant commercialisation web.

## 💰 Tarification dynamique + assets Play Store (11 juin 2026, après-midi)
- **Tarifs officiels confirmés par le client** : Artisan 24,99 € / Entreprise 59,99 € (3 comptes : 1 admin + 2 équipe, +4,99 €/user sup.) / Pro 89,99 € (6 comptes, +9,99 €/user sup.)
- **Nouveau module `/app/backend/seats.py`** : config sièges par plan + `sync_stripe_seats()` (aligne la quantité du line item "extra user" Stripe à chaque ajout/suppression de membre — no-op sans abonnement Stripe)
- `company.py` (création/suppression membre) et `invitations.py` : seat check par plan (402 EXTRA_SEAT_REQUIRED dynamique), testé E2E : Entreprise 402@3e siège/4,99 €, Pro OK jusqu'à 5 sièges puis 402@6e/9,99 € ✅
- Tests pytest : `/app/backend/tests/test_seats.py` (5/5 ✅)
- **Contraste boutons abonnement corrigé** : orange plein #FF5A00 + texte blanc (vérifié screenshot ✅)
- **Feature graphic Play Store 1024×500 générée** (script `/app/scripts/generate_feature_graphic.py`) — téléchargeable via `GET /api/_downloads/play-feature-graphic`
- **AAB Android final** : v1.1.0 versionCode 27 → lien direct dans play_store_listing_fr.md
- ⚠️ Le backend Railway doit être redéployé (Save to GitHub) pour embarquer la nouvelle logique de sièges.

## 🧪 Système de recrutement de testeurs Google Play (11 juin 2026, soir)
- **Page publique `/devenir-testeur`** (sans login) : pitch + formulaire (nom, société, Gmail, tél) → `POST /api/testers/register` (dédup par email, notification Resend à info@mesurechassis.com à chaque inscription)
- **Vue admin `/admin/testers`** (bouton "Testeurs" sur dashboard, web only) : compteurs objectif 12, bouton "Copier tous les emails" (collage direct dans Play Console), marquer "AJOUTÉ", supprimer
- Backend : `/app/backend/routes/testers.py` (GET/PATCH/DELETE admin-only, register public)
- Testé E2E : inscription web ✅, doublon idempotent ✅, email invalide 400 ✅, 401 sans auth ✅, notification Resend ✅, vue admin ✅
- ⚠️ Redéployer (Save to GitHub → Railway + web) pour rendre la page publique accessible en production

## 🌐 Page testeurs hébergée sur mesurechassis.com (11 juin 2026, fin de journée)
- Constat : le déploiement Emergent d'une app Expo fournit les builds mobiles, pas d'URL web → solution retenue : page statique sur le site vitrine du client (Easyhost, upload FileZilla)
- `/app/backend/static/devenir-testeur.html` : page autonome aux couleurs du site (Syne/DM Sans, #FF6B35), formulaire fetch → `https://capable-gratitude-production-db51.up.railway.app/api/testers/register`
- Téléchargeable via `GET /api/_downloads/devenir-testeur-html` — à uploader à la racine du site → URL finale `https://mesurechassis.com/devenir-testeur.html`
- CORS Railway vérifié OK pour l'origine mesurechassis.com ✅
- ⚠️ PRÉREQUIS : "Save to GitHub" pour que Railway reçoive routes/testers.py (sinon 404, vérifié)
- Le site vitrine pointe encore vers la preview (beta.html → window-field-app.preview...) : à corriger lors de la mise à jour du site (backlog)

## 🚂 Fix déploiement Railway (11 juin 2026, soir) — IMPORTANT POUR FUTURS AGENTS
- **Problème** : "Save to GitHub" pousse TOUT le workspace sur la branche `conflict_070626_1317`, alors que l'ancienne branche `main` contenait le backend À LA RACINE. Railway buildait la racine → échec.
- **Fixes appliqués** :
  1. Railway Settings → Source → Root Directory = `/backend` (fait par le client)
  2. Branche connectée = `conflict_070626_1317` (auto-deploy ON)
  3. Créé `/app/backend/Procfile` + `/app/backend/railway.json` (commande uvicorn)
  4. `requirements.txt` réécrit PROPREMENT (16 paquets pinés, identiques à l'ancien main) — l'ancien contenait un pip freeze complet avec `emergentintegrations` introuvable sur PyPI → c'était la cause du build failed
- **⚠️ RÈGLE** : ne JAMAIS remettre un pip freeze complet dans requirements.txt (Railway casse). Ajouter uniquement les nouveaux paquets réellement importés.
- **Résultat** : Deployment successful ✅ — API testeurs + tarification par plan + compte Apple review actifs en production
- Chaîne testeur E2E validée en prod : page mesurechassis.com/devenir-testeur.html → API Railway → email Resend vers info@mesurechassis.com ✅

## 🌐 Mise à jour site vitrine préparée (11 juin 2026, soir)
- 13 pages récupérées depuis mesurechassis.com et transformées (51 remplacements) :
  - Wording "Bêta/bêta gratuite" → "Offre de lancement" / "avant-première" (0 occurrence restante)
  - Tous les liens preview Emergent (qui se met en veille) → https://mesurechassis.com/devenir-testeur.html
  - 2 QR codes régénérés vers la page testeur ; CTA renommés ("Devenir testeur →", "S'inscrire au programme de test")
- Script reproductible : /app/scripts/update_site_vitrine.py
- Archive : GET /api/_downloads/site-maj-offre-lancement (à dézipper et uploader via le gestionnaire Easyhost, écrase les 13 .html)
- Email de campagne testeurs finalisé et remis au client (lien devenir-testeur.html)

## 🔄 Site vitrine V2 — audit fonctionnalités (11 juin 2026, suite)
- Client a signalé : guide obsolète (7 formes au lieu de 12, formes "V2" annoncées comme à venir alors qu'implémentées)
- Corrections appliquées sur les 14 pages (archive régénérée, même endpoint /api/_downloads/site-maj-offre-lancement) :
  - "7 formes" → "12 formes" partout (guide grille complète A→R avec Plein cintre, Arc surbaissé, Pan coupé, Bow-window, Polygone, Ovale ; Triangle retiré car remplacé par Polygone)
  - PRIX corrigés : Entreprise 54,99 → 59,99 € (index, FAQ, CGV) + mention plan Pro 89,99 € dans FAQ
  - FAQ : +2 questions (multilingue FR/EN/NL, parrainage 2 mois offerts)
  - index.html : featureList SEO enrichie (trilingue + parrainage), softwareVersion 1.1.0
- Flux entreprise déjà bien documenté dans guide.html (Commercial → Technicien → Admin → verrou fabrication) ✅
- ⚠️ Resterait à faire : remplacer l'image images/7-formes-de-baies.jpg (capture d'app montrant l'ancien wizard 7 formes)

## 📣 Module Campagne emailing testeurs — TERMINÉ ✅ (11 juin 2026, soir)
- **But** : prospection des 56 artisans belges en 1 clic pour recruter les 12 testeurs Google Play.
- Backend `/app/backend/routes/campaign.py` (branché dans server.py) :
  - `POST /api/campaign/send-batch` — envoie le lot du jour (MAX 15/jour anti-spam Resend, 3s entre envois, statut `sending` anti double-clic, BackgroundTasks + asyncio.to_thread)
  - `GET /api/campaign/stats` — pending/sent/failed/sent_today/converted (croisement avec tester_signups)
  - `GET /api/campaign/prospects` + `POST /api/campaign/prospects/import` (dédoublonné)
  - Seed auto au démarrage depuis `/app/backend/static/liste_prospects_testeurs.csv` (idempotent → fonctionne aussi sur Railway au déploiement)
  - Tout est protégé `require_admin` (RBAC vérifié : 401 sans token)
- Frontend `/app/frontend/app/admin/campagne.tsx` : stats (à contacter / envoyés / quota jour / inscrits), bouton "ENVOYER LE LOT DU JOUR", liste prospects avec badges, polling 4s pendant l'envoi. Bouton "Campagne" (megaphone) dans le dashboard admin — VISIBLE SUR MOBILE (le client envoie depuis son iPhone). Header expo-router masqué dans _layout.tsx.
- Email : objet sans "beta" (conformité stores), corps personnalisé {company}, lien devenir-testeur.html, mention STOP (RGPD).
- **Tests** : envoi réel validé via delivered@resend.dev (Resend 200 OK, statut sent, prospect test supprimé) ; pytest `tests/test_campaign.py` (4 tests) ; screenshots dashboard + écran campagne OK. AUCUN email réel envoyé aux prospects — premier clic = le client.
- ⚠️ Pour la prod : pousser via "Save to GitHub" → Railway redéploie → seed auto des 56 prospects → le client clique chaque jour depuis son iPhone.
- ⚠️ Volume de masse (France/Luxembourg) → basculer sur Brevo plus tard (ne pas augmenter DAILY_LIMIT au-delà de ~15 avec Resend).

## 🇱🇺 Extension campagne Luxembourg + adaptation pays (11 juin 2026, nuit)
- Option B client : email adapté par pays — `country` sur chaque prospect (`be`/`fr`/`lu`)
  - BE : objet/corps avec "app belge" (inchangé) ; FR/LU : "app de prise de mesures pensée pour le métier" / "conçue par un menuisier"
  - `SUBJECTS` + `ORIGIN_PHRASES` dans routes/campaign.py ; fallback country manquant → "be"
- CSV `/app/backend/static/liste_prospects_testeurs.csv` réécrit avec colonne PAYS : 56 BE + 28 LU = 84 prospects (TEBA écarté, pas d'email ; 0 doublon)
- DB locale à jour : 84 pending (stats API vérifiées). Railway : seed auto au prochain déploiement.
- Tests : pytest test_campaign.py 5/5 (dont test_adaptation_pays)
- �待 Liste FRANCE pas encore fournie par le client — à importer de la même façon (PAYS=fr) quand il l'enverra.

## 🔁 Relance J+5 + France + anti-doublon Outlook (11 juin 2026, fin de soirée)
- **Relance auto J+5** : `RELANCE_TEMPLATE` + `RELANCE_DELAY_DAYS=5` dans routes/campaign.py
  - Éligible si status=sent, jamais relancé, sent_at ≤ J-5, et PAS inscrit testeur (croisement tester_signups)
  - Relances envoyées EN PRIORITÉ dans le lot quotidien, quota global 15/jour (premiers envois + relances confondus via `_quota_used_today`)
  - Sujet "Re: <sujet pays>", verrou anti double-clic (relance_sent_at horodaté au scheduling), `relance_failed` si échec
  - Stats : +`relance_due`, +`relances_sent` ; UI : badge bleu "RELANCÉ", ligne info "🔁 X relances J+5 incluses"
- **France** : 15 prospects importés (IDF/Normandie/Bretagne, PAYS=fr) → total 99
- **Anti-doublon Outlook** : le client avait envoyé 9 emails manuellement le 11/06 ~20h15 (identifiés via capture Outlook) :
  hoyauxjeannoel, chassisiso, artisanduchassis, menuiseriebrahy, moustimath, info.rrconcept, adnet.laurent, genotte.chassis, tdschassis (tous @gmail)
  → marqués sent (sent_via=outlook_manuel, sent_at=2026-06-11T18:15Z), relance J+5 auto le 16/06
  → CSV : colonne `CONTACTE_LE` ajoutée + seed adapté → la prod Railway seedera ces 9 comme "sent" (pas de doublon en prod)
- État : 90 pending / 9 sent / quota jour 9/15 (6 restants aujourd'hui)
- Tests : 11/11 pytest (test_relance_j5 ajouté), envoi relance réel validé via delivered@resend.dev, écran 99 prospects vérifié
- ⚠️ Le client doit refaire "Save to GitHub" (son push précédent ne contient ni la France, ni la relance, ni l'anti-doublon)

## 📊 Récap hebdo automatique par email (11 juin 2026, 23h)
- `send_weekly_recap()` + `weekly_recap_loop()` dans routes/campaign.py — tâche de fond asyncio (lancée au lifespan, AUCUNE dépendance ajoutée → Railway safe)
- Chaque LUNDI ≥ 7h UTC (≈9h belge), 1 fois max/semaine (marqueur `db.campaign_meta` key=weekly_recap)
- Contenu : envois/relances/inscrits de la semaine + objectif X/12 testeurs + restants + relances dues
- Destinataire : info@mesurechassis.com (constante RECAP_RECIPIENT)
- Endpoint manuel : `POST /api/campaign/recap-now` (admin) — testé en réel : Resend 200 OK, delivered=true
- Tests : 7/7 pytest test_campaign.py (test_recap_hebdo_config ajouté)
- ⚠️ Le récap automatique ne tourne en continu QUE sur Railway (le preview Emergent s'endort) → refaire "Save to GitHub"

## 💼 Campagne LinkedIn 15 jours (11 juin 2026, nuit) — TERMINÉ ✅
- Choix client : profil perso Michel, objectif notoriété pré-lancement, ton artisan authentique, visuels générés, écran in-app
- Backend `/app/backend/routes/linkedin.py` : 15 posts FR pré-rédigés (storytelling J1→J15 : histoire, problème, wizard, 12 formes, PDF, artisan solo, entreprise/rôles, verrou fab, trilingue, exports, dashboard, coulisses IA, parrainage, témoignages, récap)
  - `GET /api/linkedin/today` (premier jour non publié), `GET /api/linkedin/posts`, `POST /api/linkedin/mark-posted`, `POST /api/linkedin/unmark-posted` (admin) ; progression dans `db.linkedin_progress`
  - `GET /api/linkedin/image/{day}` PUBLIC (PNG marketing, permet appui long → enregistrer sur iPhone)
- Visuels : `scripts/generate_linkedin_cards.py` (PIL, 1080×1080, charte #FF5A00/#0C0C0E, badge JOUR X/15, kicker, titre, carte app, footer 2 lignes) → 15 PNG committés dans `static/linkedin/`
- Frontend `/app/frontend/app/admin/linkedin.tsx` : barre de progression, post du jour, visuel, COPIER LE TEXTE (expo-clipboard, texte+hashtags), MARQUER COMME PUBLIÉ → jour suivant, liste 15 jours avec coches. Bouton "LinkedIn" dashboard admin + Stack.Screen
- Tests : pytest 4/4 (test_linkedin.py), cycle complet curl (mark J1 → today=J2 → unmark → J1), UI screenshot OK (copie validée), visuel vérifié sans chevauchement (corrigé footer)
- ⚠️ "Save to GitHub" nécessaire pour avoir le module en prod (mais le client l'utilise depuis le preview comme la campagne email)

## 🛠️ Fix double-clic LinkedIn (12 juin 2026, matin)
- Le client avait cliqué 4× "MARQUER COMME PUBLIÉ" → jours 1-4 marqués. Corrigé en DB : seul J1 reste publié, J2 affiché.
- Anti-récidive : bouton à 2 temps (1er clic → "CONFIRMER : JOUR X PUBLIÉ ?" orange, expire après 4s ; 2e clic → validation) + verrou `marking`. Testé screenshot : confirmation + expiration OK, progression intacte (1/15).
- ✅ Premier lot email du matin parti (logs Resend 200 : pasquarelli, raposo, winchassis, mister-chassis, mordant, profenetres, chassisprime...) — campagne opérationnelle en conditions réelles.

## 📘 Version Facebook ajoutée (12 juin 2026, matin)
- Décision client : poster aussi sur Facebook (profil perso, pas encore de page entreprise)
- Backend : champ `fb_hashtags` (3 premiers hashtags) ajouté à chaque post dans routes/linkedin.py
- Frontend : 2 boutons de copie — "COPIER POUR LINKEDIN" (bleu LI, texte+hashtags complets) et "COPIER POUR FACEBOOK" (bleu FB #1877F2, texte+3 hashtags max)
- Tests : 5/5 pytest (test_version_facebook), copie FB validée en screenshot

## 📘 Kit page Facebook (12 juin 2026)
- Assets générés : `static/linkedin/fb_profil.png` (logo app 1024×1024) + `fb_couverture.png` (bannière 1640×856, PIL, charte app)
- Endpoint public : `GET /api/linkedin/asset/{fb_profil.png|fb_couverture.png}` (whitelist FB_ASSETS)
- Checklist de création de page fournie au client (catégorie, à propos, CTA, username, etc.)

## 🌐 Icônes sociales sur le site vitrine (12 juin 2026)
- Page Facebook créée par le client : https://www.facebook.com/share/1Feu4NEyDx/ — LinkedIn perso : https://www.linkedin.com/in/michel-pezzuto-aa4797235
- 13 pages HTML de /app/site_mesurechassis_final/ : bloc `social-mc` (SVG inline FB #1877F2 + LI #0A66C2) inséré sous l'email du footer
- ZIP régénéré : /app/site_mesurechassis_final.zip — téléchargeable via GET /api/_downloads/site-mesurechassis (vérifié 200)
- ⏳ Client doit téléverser le ZIP sur Easyhost

## 🔁 Consultation des jours passés (12 juin 2026)
- Liste "LES 15 POSTS" cliquable : toucher un jour → mode consultation (bandeau bleu "toucher pour revenir au post du jour", boutons copie LI/FB actifs, bouton MARQUER masqué). Testé screenshot : J1 consultable, retour J2 OK.
- Cas d'usage : rattrapage Facebook du J1 que le client avait publié sur LinkedIn seulement.

## 📋 Dossier de continuité d'entreprise (12 juin 2026)
- Demande client : protéger MesureChâssis en cas de disparition (continuité/succession)
- Conseils donnés : gestionnaire de mots de passe ou enveloppe notaire, successeur désigné, contact légataire Apple/Google, notaire (SRL/succession)
- Document créé : /app/backend/static/dossier_continuite.html (imprimable, pour repreneur non-technique : écosystème, coûts ~30-50€/mois, revenus, 3 options continuer/pauser/vendre, checklist 30 jours, champs à compléter à la main)
- Endpoint : GET /api/_downloads/dossier-continuite (vérifié 200)


## 💡 Idées futures / Backlog produit (à ne PAS implémenter sans demande explicite)

### 🪵 Menuiserie intérieure (notée le 13 juin 2026)
- **Demande client** : "Je pense que ça peut être intéressant de rajouter la menuiserie intérieure. On ne va pas le faire pour l'instant. Est-ce que tu peux garder ça en mémoire ?"
- **Statut** : ⏸️ EN PAUSE — idée gardée en mémoire, à ne pas développer tant que le client ne le redemande pas explicitement
- **Périmètre potentiel à explorer le jour J** :
  - Portes intérieures (simples, doubles, coulissantes intérieures, à galandage)
  - Placards / dressings sur mesure
  - Cloisons et verrières d'intérieur
  - Escaliers (mesure de trémie, hauteur sol-à-sol, giron, échappée)
  - Plinthes / habillages
- **Impact technique anticipé** :
  - Nouveau type de bloc de mesure (`block_type = "interieur"`) avec sous-types
  - Nouveaux schémas SVG dédiés
  - Possible ajout d'un champ "Catégorie chantier" : Extérieur / Intérieur / Mixte
  - Export PDF à enrichir avec nouvelle section
- **Pourquoi c'est pertinent** : élargit le marché total adressable (TAM) — les menuisiers font souvent les deux (ext. + int.), permettrait d'augmenter le prix moyen ou de garder le client toute l'année

### ✅ DÉCISION STRATÉGIQUE — Architecture produit (13 juin 2026)
- **Validé par le client** : la menuiserie intérieure sera **intégrée dans la même app** (PAS d'app séparée).
- Modèle de pricing à 3 paliers prévu :
  - **MesureChâssis Basic** — 25 €/mois — Extérieur uniquement (état actuel)
  - **MesureChâssis Pro** — 39 €/mois — Basic + Module Intérieur + Exports avancés + Devis auto
  - **MesureChâssis Entreprise** — sur devis — Multi-équipes >10 + intégration ERP (Elcia)
- Activation via toggle d'abonnement Stripe (price_id différents par formule)
- Argumentaire : effet plateforme, lock-in client, TAM élargi à 42 000 entreprises FR/BE

---

## 🚀 BACKLOG FONCTIONNALITÉS FUTURES (13 juin 2026)
Brainstorm validé avec le client. Toutes ces idées sont en réserve, à implémenter selon la roadmap. **Ne rien développer sans validation explicite préalable.**

### 🥇 Pépites (fort impact, complexité raisonnable)
1. **Détection auto des cotes par photo (IA)** — GPT-4o Vision / Gemini 3 Pro Vision — référence d'échelle (carte bancaire / mètre)
2. **Module Devis automatique** — PDF généré depuis les mesures + catalogue produits perso + envoi email signé
3. **Signature électronique du bon de commande** — `react-native-signature-canvas` — closing immédiat sur place
4. **Planning des poses (vue calendrier)** — drag & drop + affectation poseur + sync Google Cal/Outlook
5. **Carnet clients (mini-CRM)** — historique + recontact auto à 5 ans + anniversaire chantier

### 🥈 Très utiles (bon ROI, complexité moyenne)
6. **Croquis main libre annoté** — `@shopify/react-native-skia`
7. **Bon de commande fournisseur** — formats Schüco/Reynaers/Aluk (avant l'API Elcia)
8. **Facturation intégrée** — numérotation auto + suivi paiements + export comptable (FEC/Sage/Cegid)
9. **Statistiques business (dashboard patron)** — CA, taux conversion devis→commande, marge moyenne
10. **Vidéo de l'ouverture (annotation vocale)** — contexte pour le poseur avant d'arriver
11. **Géolocalisation des chantiers** — carte + itinéraire optimisé tournée pose — `react-native-maps`
12. **Alertes intelligentes** — relances devis, upsell triple vitrage, anticipation matériel

### 🥉 Sympas (à envisager plus tard)
13. **QR Code sur chaque baie** — étiquette posée + caractéristiques Uw/garantie/date
14. **Calcul aides énergétiques** — MaPrimeRénov' (FR) + Primes Énergie (BE)
15. **Assistant IA pour techniciens** — base de connaissance interne contextuelle
16. **Mode hors-ligne complet** — `expo-sqlite` + watermelonDB — chantier sans réseau
17. **Portail client** — lien magique + suivi étape par étape
18. **Demande d'avis Google automatique** — SMS/email 3j après pose
19. **Garantie & SAV trackable** — certificat + ticketing SAV
20. **Bibliothèque produits collaborative** — catalogue communautaire (Schüco LivIng, Reynaers SlimLine, etc.)

### 🌟 Disruptifs (gros effet WOW)
21. **Mode AR (Réalité Augmentée)** — mesures auto via ARKit/ARCore + visualisation 3D — `expo-three`
22. **Visio-mesure à distance** — devis national sans déplacement
23. **Comparateur multi-fournisseurs** — 3 devis fournisseurs en parallèle (position plateforme)

### ⚠️ Règle d'or à respecter
N'ajouter une feature QUE SI :
- Plusieurs clients la réclament, OU
- Elle débloque une nouvelle formule de prix, OU
- Elle est un argument de closing décisif en démo

Sinon = bruit qui complexifie le produit. À NE PAS faire sans demande explicite du client.


## 🔷 NOUVELLE FORME DE BAIE À AJOUTER — Pentagone asymétrique / Sous-pente (13 juin 2026)

### Demande client
"Une forme supplémentaire à rajouter mais pas maintenant, on attend toujours que Google et Apple soient en règle, garde-le en mémoire" (photo fournie d'une baie en sous-pente).

### Statut
⏸️ **EN ATTENTE** — ne PAS implémenter tant que :
1. Apple Build 9 n'est pas validé/refusé ✅
2. Google Play (12 testeurs sur 14 jours) n'est pas complet ✅

Toute modification du code de mesure pendant la review = risque de devoir re-soumettre.

### Description technique de la forme
- **Type** : Pentagone à base horizontale, 2 côtés verticaux, et 2 pans inclinés convergeant vers un sommet (souvent asymétrique).
- **Usage typique** : Combles aménagés, sous-pente, mezzanines, baies de pignon, lucarnes triangulaires.
- **Variante** : peut être symétrique (sommet centré, "fronton") ou asymétrique (sommet décalé, comme sur la photo client).
- **Photo de référence** : fournie par le client le 13/06/2026 (baie composée de 3 vantaux fixes, sous-pente, ciel bleu visible).

### Spécifications de mesure (à implémenter le jour J)
**Cotes à saisir (8 valeurs)** :
- **L_bas** (largeur de la base horizontale)
- **H_gauche** (hauteur du côté gauche vertical)
- **H_droite** (hauteur du côté droit vertical)
- **Pan_gauche** (longueur du pan incliné gauche, du haut du côté gauche au sommet)
- **Pan_droit** (longueur du pan incliné droit, du sommet au haut du côté droit)
- **H_sommet** (hauteur du sommet par rapport à la base — pour calcul vérification)
- **Décalage_sommet** (position horizontale du sommet par rapport au côté gauche — permet asymétrie)
- **Diagonale_vérif** (diagonale du coin bas-gauche au sommet, ou bas-droit au sommet — contrôle géométrie)

**Alertes à calculer** :
- ⚠️ **Asymétrie sommet** : si `Décalage_sommet ≠ L_bas / 2` → on annote "Pentagone asymétrique"
- ⚠️ **Pente gauche/droite** : calcul en degrés via `atan((H_sommet - H_gauche) / Décalage_sommet)` et `atan((H_sommet - H_droite) / (L_bas - Décalage_sommet))`
- ⚠️ **Cohérence géométrique** : Pythagore sur les pans inclinés vs cotes verticales et horizontales
- ⚠️ **Faux-aplomb** sur les 2 côtés verticaux

### Impact technique anticipé
- Nouveau `block_type = "pentagone_souspente"` (ou similaire)
- Nouveau schéma SVG dédié (5 segments — base + 2 verticaux + 2 pans inclinés)
- Aperçu visuel dans l'app : forme dessinée dynamiquement avec les cotes saisies (comme déjà fait pour Trapèze)
- Export PDF : section dédiée avec dessin coté
- Multilingue (FR/EN/NL) à ajouter pour les libellés

### Stockage de la photo de référence
La photo fournie par le client doit servir de **référence visuelle** pour le développement le jour J.
À sauvegarder dans `/app/memory/assets/forme_pentagone_souspente_2026-06-13.jpg` si besoin (photo iPhone client, baie 3 vantaux sous-pente).

