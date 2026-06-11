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
