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
