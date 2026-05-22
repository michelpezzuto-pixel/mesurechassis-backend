# MesureEscalier — PRD (Product Requirements Document)

## Vision
Outil mobile de terrain pour installateurs d'escaliers, métalliers et techniciens. Mesures rapides sur chantier → calculs (Loi de Blondel) → exports professionnels PDF + DXF, partageables.

## Stack
- **Frontend**: React Native Expo SDK 54, Expo Router, TypeScript, react-native-svg
- **Backend**: FastAPI + MongoDB (Motor), JWT auth + bcrypt, ReportLab (PDF), DXF ASCII (AutoCAD-ready)
- **Voice**: OpenAI Whisper-1 via Emergent universal key
- **Theme**: Dark `#1A1E2A` + accent Vert Pomme `#8CC63F`

## Rôles (RBAC)
| Rôle       | Droits |
|------------|--------|
| Admin      | Tout. Gère l'équipe, voit tous les chantiers, supprime n'importe quel chantier. |
| Commercial | Crée des chantiers (Brouillon). Peut éditer/supprimer **uniquement en Brouillon**. Verrouille en cliquant « Transmettre au technicien ». |
| Technicien | Voit les chantiers assignés (ou non assignés). Seul à pouvoir saisir les mesures, valider la conception et exporter. Ne peut pas créer de chantier. |

## Workflow
`Brouillon` → (Commercial transmet) → `À mesurer` → (Technicien saisit) → `À vérifier` → (validation) → `Validé`

## Moteur de calcul (Loi de Blondel)
Cible `2h + g ≈ 630 mm`. Pour chaque hauteur `H`, recherche du couple `(n, h, g)` minimisant l'écart à la cible, avec contraintes `150 ≤ h ≤ 220` et `200 ≤ g ≤ 350`. Forme déduite:
- `reculement_max ≥ reculement_needed` → **Escalier Droit**
- 65% ≤ ratio < 100% → **Quart-tournant**
- < 65% → **Hélicoïdal / colimaçon**

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
