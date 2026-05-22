# MesureEscalier — PRD (Product Requirements Document)

## Vision
Outil mobile de terrain pour installateurs d'escaliers, métalliers et techniciens. Mesures rapides sur chantier → calculs (Loi de Blondel) → exports professionnels PDF + DXF, partageables.

## Stack
- **Frontend**: React Native Expo SDK 54, Expo Router, TypeScript, react-native-svg
- **Backend**: FastAPI + MongoDB (Motor), JWT auth + bcrypt, ReportLab (PDF), DXF ASCII (AutoCAD-ready)
- **Voice**: OpenAI Whisper-1 via Emergent universal key
- **Theme**: Dark `#1A1E2A` + accent Vert Pomme `#8CC63F`

## Rôles (RBAC simplifié v1.1)
| Rôle | Droits |
|---|---|
| **Admin** | Tout. Gère l'équipe, crée et modifie tous les chantiers, statistiques, paramètres, suppression. |
| **Technicien** | Terrain uniquement. Voit ses chantiers assignés + chantiers non assignés. Saisit les mesures, valide la conception, génère les exports PDF/DXF. **N'a pas accès à l'équipe.** |

### Mode artisan unique (solo_mode)
Interrupteur dans les **Paramètres** (Admin uniquement) : active la fusion Admin + Technicien.
- Création d'un chantier → instantanément verrouillé, statut `a_mesurer`, assigné à soi-même.
- Mesures saisies sans étape de transmission.
- Validation et exports directement accessibles.

## Moteur de calcul (Loi de Blondel + Règles de l'art v1.2)

### Plages de référence
- **Idéal** : h ≈ 175 mm, 2h + g ≈ 630 mm
- **Limites strictes (règles de l'art)** :
  - Giron `g ≥ 230 mm`
  - Hauteur de marche `h ≤ 210 mm`
  - `560 mm ≤ 2h + g ≤ 670 mm`
- L'algorithme cherche le couple (n, h, g) minimisant l'écart à l'idéal **tout en respectant les limites dures**. Si aucun couple valide n'est trouvable pour un escalier droit → **rejet et forçage** vers quart-tournant ou hélicoïdal.

### Forme déduite
- `reculement_max ≥ reculement_needed` ET règles dures OK → **Escalier Droit**
- 65% ≤ ratio < 100% → **Quart-tournant**
- < 65% → **Hélicoïdal / colimaçon**

### Ligne de foulée (escaliers tournants)
Pour tout escalier tournant, le giron `g` est mesuré sur la **ligne de foulée** (centre géométrique du passage, ~50 cm de la rampe), pas aux extrémités des marches balancées. Cette précision est affichée dans la carte de résultat.

### Échappée (sécurité)
Input optionnel `hauteur_sous_plafond_tremie`. Si fourni, calcul de l'espace vertical libre sous la trémie. Si `< 2000 mm` → **alerte rouge critique** (risque choc à la tête).

### Longueur du limon (atelier métallerie)
`limon = √(H² + reculement²)` — dimension exacte de la poutre à découper. Mise en avant dans une carte dédiée (Vert Pomme), incluse dans le PDF (table de calcul) et le DXF (texte LIMON + layer dédié).

## Exports
- **PDF** (`/api/projects/{id}/export/pdf`) — ReportLab : Identification client, table mesures, calculs, schéma 2D, notes.
- **DXF** (`/api/projects/{id}/export/dxf`) — ASCII LINE/TEXT, layers `STAIR_PROFILE`, `HYPOTENUSE`, `FLOOR`, `CEILING`, `TREMIE`, `LABELS`.
- **Partage natif** via `expo-sharing`.

## Endpoints clés
- Auth: `POST /auth/{register,login}`, `GET /auth/me`
- Users (admin): `GET/POST /users`, `DELETE /users/{id}`
- Projects: `GET/POST /projects`, `GET/PUT/DELETE /projects/{id}`, `POST /projects/{id}/transmit|assign`
- Measurements: `POST /projects/{id}/measurement|preview|validate`
- Exports: `GET /projects/{id}/export/{pdf,dxf}`
- Voice: `POST /transcribe` (multipart audio, Whisper FR)
- **Integration future-proof**: `GET /integration/sites/{id}` → expose `true_height_mm`, `reculement_mm`, `slope_angle_deg`, `hypotenuse_mm`, trémie, n_steps, h, g, shape → consommé par la future app sœur **MesureGardeCorps**.

## Comptes de démo (auto-seedés)
| Rôle | Email | MDP |
|---|---|---|
| Admin | admin@demo.fr | Demo1234! |
| Commercial | marc@mesureescalier.com | Demo1234! |
| Technicien | sophie@mesureescaliee.com | Demo1234! |

## Tests
- Suite pytest backend `/app/backend/tests/test_mesure_escalier.py` — 27 cas, 100% passants.
- Rapport: `/app/test_reports/iteration_1.json`.

## Améliorations business proposées
- **Mode hors-ligne** + sync (chantiers fréquemment en sous-sol sans réseau).
- **Marketplace fournisseurs** — proposer matières premières (acier/bois) directement depuis le rapport généré (commission sur transactions).
- **Photos chantier** (déjà permission micro / à étendre caméra) attachées au PDF.
- **Abonnement Pro** : illimité chantiers + DXF haute précision + branding société sur PDF.
