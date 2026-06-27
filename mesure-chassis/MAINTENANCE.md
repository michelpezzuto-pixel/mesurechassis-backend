# Guide de Maintenance — MesureChassis

> **Public** : développeur en charge de la maintenance et de l'évolution de l'application
> MesureChassis. Suppose une connaissance préalable de l'app sœur **MesureEscalier**
> (mêmes patterns, même stack).
>
> **Convention de langue** : ce document est en français car le vocabulaire métier
> (châssis, vantail, oscillo-battant…) est spécifique au domaine français/belge
> de la menuiserie.

---

## Sommaire

1. [Objectif & périmètre](#1-objectif--périmètre)
2. [Stack technique](#2-stack-technique)
3. [Structure du code](#3-structure-du-code)
4. [Bootstrap du projet (génération initiale)](#4-bootstrap-du-projet-génération-initiale)
5. [Modèle de données châssis](#5-modèle-de-données-châssis)
6. [Patterns clés réutilisés depuis MesureEscalier](#6-patterns-clés-réutilisés-depuis-mesureescalier)
7. [Ajout de fonctionnalités](#7-ajout-de-fonctionnalités)
8. [Tests & QA](#8-tests--qa)
9. [Build & déploiement (EAS)](#9-build--déploiement-eas)
10. [Annexe — checklist artisan terrain](#10-annexe--checklist-artisan-terrain)

---

## 1. Objectif & périmètre

### 1.1 Cas d'usage cible

L'artisan menuisier arrive sur un chantier avec son iPhone/Android et doit :

| Étape | Action | Sortie attendue |
|------|--------|-----------------|
| 1 | Créer / choisir un chantier (client + adresse) | Projet créé en DB |
| 2 | Ajouter un châssis | Modal type d'ouvrant + nom |
| 3 | Saisir hauteur × largeur (mm) | Surface auto-calculée |
| 4 | Choisir matériau (PVC / Alu / Bois) + vitrage | Coefficients tarif appliqués |
| 5 | Préciser options (oscillo-battant, RAL, etc.) | Suppléments ajoutés |
| 6 | Photographier l'ouverture existante | Photo base64 attachée |
| 7 | Exporter PDF | Rapport prêt à transmettre |

### 1.2 Hors périmètre (V1)

- ❌ Gestion de stock fournisseur
- ❌ Lien comptable / facture
- ❌ Calcul thermique (Uw, Sw) — réservé V2 si demande client
- ❌ Optimisation découpe / nesting

---

## 2. Stack technique

Identique à MesureEscalier — réutilisation des compétences et de l'infra.

### 2.1 Frontend

| Composant | Version cible | Rôle |
|-----------|--------------|------|
| Expo SDK | 54+ | Toolchain mobile |
| React Native | 0.81+ | Framework UI |
| `expo-router` | 6.x | Navigation file-based |
| TypeScript | 5.x | Typage statique |
| `react-native-svg` | 15.x | Sketchs Coupe / Plan |
| `react-native-reanimated` | 4.x | Animations bottom-sheet, transitions |
| `@react-native-async-storage/async-storage` | 2.x | Cache token + projets offline |
| `react-hook-form` | 7.x | Formulaires complexes (options vantail) |
| `zustand` | 4.x *(à introduire)* | State global léger (panier de châssis en édition) |

### 2.2 Backend

| Composant | Version cible | Rôle |
|-----------|--------------|------|
| FastAPI | 0.115+ | API REST `/api/chassis/*` |
| Motor | 3.x | Driver MongoDB async |
| Pydantic v2 | 2.x | Schémas |
| python-jose | * | JWT (même secret que MesureEscalier) |
| reportlab + WeasyPrint | * | Export PDF |

### 2.3 Infra partagée

- **Auth** : un seul JWT issuer (`MesureChassis Auth` ou auth commune). L'utilisateur
  peut basculer entre les deux apps avec le même compte.
- **Storage** : même cluster MongoDB, base dédiée `mesurechassis_db` (séparation
  logique pour éviter les collisions de collections).
- **Emergent LLM Key** : disponible pour features IA (ex. dictée Whisper, suggestion
  matériau via vision GPT-4o).

---

## 3. Structure du code

Layout cible (à adopter dès le scaffold). **Toute évolution doit respecter ce plan.**

```
/app/mesure-chassis/
├── app.json                    # Config Expo (✅ déjà créé, package IDs OK)
├── package.json                # Dépendances yarn
├── tsconfig.json               # Stricts: true, paths @/* → src/*
├── metro.config.js             # ⚠ NE PAS MODIFIER après bootstrap
├── .env                        # EXPO_PUBLIC_BACKEND_URL
│
├── app/                        # Routes Expo Router (file-based)
│   ├── _layout.tsx             # Root layout : ThemeProvider + AuthProvider
│   ├── index.tsx               # Splash / redirect login ou dashboard
│   ├── login.tsx               # Écran connexion
│   ├── dashboard.tsx           # Liste des chantiers
│   ├── projects/
│   │   ├── new.tsx             # Création nouveau chantier
│   │   └── [id]/
│   │       ├── index.tsx       # Vue chantier (liste châssis + CTA + FAB)
│   │       └── chassis/
│   │           ├── [cid]/
│   │           │   ├── index.tsx       # Éditeur d'un châssis (split view)
│   │           │   └── export.tsx      # Récap PDF
│   │           └── new.tsx             # (optionnel) wizard externalisé
│   └── settings.tsx
│
├── src/
│   ├── api/
│   │   ├── client.ts           # axios instance + interceptors JWT
│   │   ├── chassis.ts          # CRUD châssis
│   │   ├── projects.ts
│   │   └── compute.ts          # POST /chassis/:id/compute (surface, prix, etc.)
│   ├── theme/
│   │   ├── colors.ts           # palette identique MesureEscalier
│   │   ├── spacing.ts          # SP.sm / md / lg / xl
│   │   ├── radius.ts
│   │   └── typography.ts
│   ├── shared-ui/              # ⚠ MIROIR de /app/frontend/src/shared-ui/
│   │   ├── Modal.tsx
│   │   ├── Picker.tsx
│   │   ├── Button.tsx
│   │   ├── Checkbox.tsx
│   │   ├── Badge.tsx
│   │   └── index.ts
│   ├── sketches/
│   │   ├── ChassisElevation.tsx        # Vue élévation côté pièce (rectangle + sens d'ouverture)
│   │   └── ChassisPlan.tsx             # Vue de dessus + sens ouverture/poussée
│   ├── utils/
│   │   ├── storage.ts          # AsyncStorage helpers
│   │   ├── format.ts           # fmt(mm), fmt(€), surface m²
│   │   ├── compute.ts          # Calcul surface, supplément RAL, etc. (mirror serveur)
│   │   └── detectStructure.ts  # (optionnel) détection cohérence vantaux
│   ├── store/
│   │   └── useChassisDraft.ts  # Zustand : draft édition châssis (autosave debounced)
│   └── types/
│       ├── api.ts              # Types miroirs des Pydantic schemas
│       └── domain.ts           # ChassisShape, OpeningSide, MaterialKind, etc.
│
├── assets/
│   ├── images/                 # icon.png, adaptive-icon.png, splash.png
│   └── fonts/
│
└── tests/                      # Tests unitaires utilitaires + UI smoke
    ├── compute.test.ts
    └── chassis-card.test.tsx
```

### 3.1 Règle d'or — où placer un nouveau fichier ?

| Type de fichier | Emplacement |
|-----------------|-------------|
| Écran navigable (URL) | `app/...` |
| Composant réutilisable spécifique châssis | `src/components/` |
| Composant partagé MesureEscalier ↔ Chassis | `src/shared-ui/` (synchronisé manuellement entre les 2 repos pour V1, puis package npm interne en V2) |
| Helper pur (sans React) | `src/utils/` |
| Appel API | `src/api/` |
| Type domaine | `src/types/` |

### 3.2 Conventions de nommage

- Fichiers de composants React : `PascalCase.tsx`
- Hooks : `useCamelCase.ts`
- Helpers purs : `kebab-case.ts` ou `camelCase.ts`
- testID : kebab-case, préfixé par le contexte : `chassis-input-largeur`, `btn-add-chassis`, `modal-shape-picker`
- Variables CSS / theme : MAJUSCULES (`C.ACCENT`, `SP.md`, `R.lg`, `FONT.button`)

---

## 4. Bootstrap du projet (génération initiale)

> **À effectuer une seule fois** quand le scaffold complet sera lancé.
> Le `app.json` étant déjà en place, il faut seulement le préserver.

### 4.1 Étape 1 — Init Expo

```bash
cd /app
# ATTENTION : ne pas écraser app.json existant
mv mesure-chassis/app.json /tmp/chassis-app.json.bak
npx create-expo-app@latest mesure-chassis --template tabs
mv /tmp/chassis-app.json.bak mesure-chassis/app.json
```

### 4.2 Étape 2 — Dépendances communes

```bash
cd /app/mesure-chassis
yarn expo install \
  expo-router expo-linking expo-constants expo-secure-store \
  expo-camera expo-image-picker expo-document-picker expo-audio \
  expo-print expo-sharing expo-file-system \
  react-native-svg react-native-gesture-handler react-native-reanimated \
  react-native-safe-area-context react-native-screens \
  @react-native-async-storage/async-storage @react-native-community/hooks \
  @shopify/flash-list

yarn add axios zustand react-hook-form @hookform/resolvers zod \
  date-fns lucide-react-native
```

### 4.3 Étape 3 — Copier les shared-ui depuis MesureEscalier

```bash
# Miroir initial (à synchroniser manuellement à chaque update)
cp -r /app/frontend/src/shared-ui /app/mesure-chassis/src/
cp -r /app/frontend/src/theme    /app/mesure-chassis/src/
```

### 4.4 Étape 4 — Backend

Créer un router FastAPI dédié sous `/app/backend/routers/chassis.py` qui réplique
la logique CRUD de `stairs_v2.py` adaptée au domaine châssis. Conserver le même
JWT issuer et les mêmes décorateurs `require_active_access`.

```
/api/projects/{pid}/chassis              GET, POST
/api/projects/{pid}/chassis/{cid}        GET, PATCH, DELETE
/api/projects/{pid}/chassis/{cid}/compute  GET
/api/projects/{pid}/chassis/{cid}/export   POST  (génère PDF)
```

### 4.5 Étape 5 — Vérif build

```bash
yarn expo prebuild --platform android
# OK si /app/mesure-chassis/android/ se génère sans erreur
yarn expo prebuild --platform ios
```

---

## 5. Modèle de données châssis

### 5.1 Pydantic (backend) — **catalogue officiel à 7 formes**

```python
# /app/backend/models/chassis_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ── 7 FORMES OFFICIELLES (planche artisan menuisier) ──────────────────────
# Référence visuelle : /app/mesure-chassis/src/sketches/index.tsx
ChassisShape = Literal[
    "rectangulaire",  # Fenêtre fixe rectangulaire (4 carreaux)
    "trapeze",        # Trapèze (sommet incliné, 2 vantaux)
    "triangulaire",   # Triangle (2 vantaux + axe vertical)
    "oeil_de_boeuf",  # Œil de bœuf (ovale + croix centrale)
    "porte",          # Porte simple (verticale étroite + poignée)
    "porte_garage",   # Porte de garage (large + lames horizontales)
    "coulissant",     # Coulissant (2 vantaux + flèche directionnelle)
]

MaterialKind = Literal["pvc", "alu", "bois", "mixte_bois_alu"]
GlazingKind  = Literal["double", "triple", "feuillete", "phonique"]
OpeningSide  = Literal["gauche", "droite", "haut", "bas", "fixe"]

class ChassisOption(BaseModel):
    key: Literal["ral", "imposte", "allege", "renfort_alu", "poignee_premium",
                 "grille_ventilation", "store_integre"]
    value: Optional[str] = None
    supplement_eur: float = 0.0

class Chassis(BaseModel):
    id: str
    name: str = "Châssis 1"
    shape: ChassisShape = "rectangulaire"
    hauteur_mm: int = Field(..., ge=200, le=4000)
    largeur_mm: int = Field(..., ge=200, le=6000)
    material: MaterialKind = "pvc"
    glazing: GlazingKind = "double"
    opening_side: OpeningSide = "droite"
    options: List[ChassisOption] = []
    photo_base64: Optional[str] = None
    remarks: Optional[str] = None
    created_at: str
    updated_at: str

class ChassisCompute(BaseModel):
    surface_m2: float
    base_price_eur: float
    options_total_eur: float
    total_eur: float
    warnings: List[str] = []
```

### 5.2 Formule de surface par forme

| Shape | Formule surface (m²) | Notes |
|-------|----------------------|-------|
| `rectangulaire` | `H × L / 1e6` | Standard |
| `trapeze` | `((H + h_min) / 2) × L / 1e6` | Demande aussi `hauteur_min_mm` (côté bas du sommet incliné) |
| `triangulaire` | `(H × L) / 2 / 1e6` | Triangle isocèle |
| `oeil_de_boeuf` | `π × (H/2) × (L/2) / 1e6` | Ellipse |
| `porte` | `H × L / 1e6` | Inclure le seuil |
| `porte_garage` | `H × L / 1e6` | Multiplier par 1.4 pour pose (renfort) |
| `coulissant` | `H × L / 1e6` | Idem rectangulaire |

> ⚠️ Pour `trapeze` et `triangulaire`, prévoir un champ supplémentaire
> `hauteur_min_mm` (trapèze) ou `pente` (triangle) côté schéma Pydantic.

### 5.3 Stockage MongoDB

```
db.projects.chassis = [
  {
    id, name, shape, hauteur_mm, largeur_mm, hauteur_min_mm?, 
    material, glazing, opening_side,
    options: [...],
    photo_base64, remarks,
    created_at, updated_at
  },
  ...
]
```

---

## 6. Patterns clés réutilisés depuis MesureEscalier

Ces patterns ont été éprouvés terrain dans MesureEscalier et **doivent être
répliqués tels quels** pour la cohérence UX.

### 6.1 ShapeSelectorBar (7 chips en tête d'éditeur — bibliothèque officielle)

Les 7 formes officielles, avec leur sketch line-art associé (cf.
`/app/mesure-chassis/src/sketches/index.tsx`) :

| Clé             | Label artisan              | Sketch              |
|-----------------|----------------------------|---------------------|
| `rectangulaire` | Fenêtre fixe rectangulaire | 4 carreaux verticaux|
| `trapeze`       | Trapèze                    | Sommet incliné      |
| `triangulaire`  | Triangulaire               | Triangle isocèle    |
| `oeil_de_boeuf` | Œil de bœuf                | Ellipse + croix     |
| `porte`         | Porte                      | Verticale + poignée |
| `porte_garage`  | Porte de garage            | Lames horizontales  |
| `coulissant`    | Coulissant                 | 2 vantaux + flèche  |

Implémentation recommandée — un ScrollView horizontal pour absorber les 7 chips :

```tsx
import { ChassisSketch, CHASSIS_SHORT, ChassisShape } from '@/src/sketches';

const SHAPES: ChassisShape[] = [
  'rectangulaire', 'trapeze', 'triangulaire', 'oeil_de_boeuf',
  'porte', 'porte_garage', 'coulissant',
];

<ScrollView horizontal showsHorizontalScrollIndicator={false}>
  {SHAPES.map(key => (
    <TouchableOpacity
      key={key}
      style={[styles.chip, current === key && styles.chipActive]}
      onPress={() => changeShape(key)}
      testID={`shape-chip-${key}`}
    >
      <ChassisSketch shape={key} width={28} height={28}
        stroke={current === key ? C.DARK : C.WHITE} strokeWidth={1.2} />
      <Text style={styles.chipTxt}>{CHASSIS_SHORT[key]}</Text>
    </TouchableOpacity>
  ))}
</ScrollView>
```

- Mêmes principes que MesureEscalier : chip actif sur fond vert, switch on-the-fly
  via PATCH `/chassis/{cid}`, confirmation Alert si données saisies.

### 6.2 Auto-seed à la création (POST chassis)

```python
# /app/backend/routers/chassis.py
SEED_TEMPLATES = {
    "rectangulaire":  {"hauteur_mm": 1450, "largeur_mm": 1000, "opening_side": "fixe"},
    "trapeze":        {"hauteur_mm": 1800, "largeur_mm": 1200, "opening_side": "fixe",
                       "hauteur_min_mm": 600},
    "triangulaire":   {"hauteur_mm": 1500, "largeur_mm": 1500, "opening_side": "fixe"},
    "oeil_de_boeuf":  {"hauteur_mm":  800, "largeur_mm":  600, "opening_side": "fixe"},
    "porte":          {"hauteur_mm": 2150, "largeur_mm":  900, "opening_side": "droite"},
    "porte_garage":   {"hauteur_mm": 2100, "largeur_mm": 2500, "opening_side": "haut"},
    "coulissant":     {"hauteur_mm": 2100, "largeur_mm": 2400, "opening_side": "droite"},
}
```

Évite le spinner mort et l'utilisateur entre directement dans un formulaire
pré-rempli avec des valeurs canoniques modifiables.

### 6.3 Split view Élévation / Plan

Identique à Coupe/Plan de MesureEscalier :
- **Gauche** : `ChassisElevation` — rectangle vu de face avec sens d'ouverture (flèches)
- **Droite** : `ChassisPlan` — vue de dessus avec angle d'ouverture (arc + flèche poussée/tirée)

```tsx
<View style={styles.splitBlock}>
  <View style={styles.splitCol}>
    <Text style={styles.splitTitle}>ÉLÉVATION</Text>
    <ChassisElevation chassis={c} width={156} height={150} />
  </View>
  <View style={styles.splitDivider} />
  <View style={styles.splitCol}>
    <Text style={styles.splitTitle}>VUE EN PLAN</Text>
    <ChassisPlan chassis={c} width={156} height={150} />
  </View>
</View>
```

### 6.4 Footer sticky [← RETOUR] / [↑ EXPORTER]

```tsx
<View style={styles.bottomBar}>
  <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => router.back()}>
    <Ionicons name="arrow-back" /><Text>RETOUR</Text>
  </TouchableOpacity>
  <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={() => router.push(`./export`)}>
    <Ionicons name="share-outline" /><Text>EXPORTER</Text>
  </TouchableOpacity>
</View>
```

### 6.5 FAB "+" + CTA dans empty state

Lorsqu'il n'y a aucun châssis sur un chantier :
- Empty state avec bordure pointillée verte + CTA primaire centré "AJOUTER MON PREMIER CHÂSSIS"
- FAB rond vert en bas-droite toujours visible (testID="fab-add-chassis")
- Banner orange si projet verrouillé.

### 6.6 Bloc DonnéesTechniques

Sous la visualisation split, regrouper en un seul bloc :

| KPI | Valeur | Unité |
|-----|--------|-------|
| Surface | 1.45 | m² |
| Prix base | 480 | € HT |
| Suppléments | 75 | € HT |
| **Total** | **555** | **€ HT** |

+ Banner "Pose 2 personnes requise" si largeur > 2400 mm.

### 6.7 Smart picker contextuel (V2)

Pour les options multiples (RAL, imposte, allège), proposer des suggestions
contextuelles basées sur le matériau et la forme choisis. Mêmes mécaniques que
`suggestNextTroncon()` dans MesureEscalier.

---

## 7. Ajout de fonctionnalités

### 7.1 Workflow type : ajouter une nouvelle option de châssis

Exemple : ajouter l'option **"Grille de ventilation hygrosensible"**.

#### Étape 1 — Backend

Étendre `ChassisOption.key` :

```python
key: Literal[
    "ral", "imposte", "allege", "renfort_alu", "poignée_premium",
    "grille_ventilation"  # 🆕
]
```

Adapter le calcul dans `chassis_compute_service.py` :

```python
OPTION_PRICES = {
    "grille_ventilation": 45.0,  # €
    ...
}
```

#### Étape 2 — Frontend

Ajouter la traduction dans `src/types/domain.ts` :

```ts
export const OPTION_LABEL: Record<ChassisOptionKey, string> = {
  ...,
  grille_ventilation: 'Grille de ventilation hygro',
}
```

Ajouter au picker d'options dans l'éditeur (`app/projects/[id]/chassis/[cid]/index.tsx`).

#### Étape 3 — Tests

Ajouter un cas dans `tests/compute.test.ts` :

```ts
test('grille de ventilation ajoute 45€', () => {
  const c = mockChassis({ options: [{ key: 'grille_ventilation' }] });
  expect(compute(c).options_total_eur).toBe(45);
});
```

#### Étape 4 — QA visuelle

Screenshot avant/après dans `/tmp/screen_grille.png` via le screenshot tool.
Vérifier l'affichage de l'option dans le bloc DonnéesTechniques.

### 7.2 Ajouter une nouvelle forme (V2)

Si un client demande **"Châssis cintré"** ou **"Imposte triangulaire"** :

1. Étendre `ChassisShape` literal côté backend.
2. Ajouter une carte dans le modal de sélection (en haut de l'éditeur).
3. Créer le sketch SVG dédié (`ChassisCintreElevation.tsx`).
4. Compléter `seed_templates` avec une géométrie par défaut.
5. Adapter `detectStructure()` si la nouvelle forme implique des sous-sections.
6. Tester sur les 3 viewports (iPhone 12, Samsung S21, tablette).

### 7.3 Synchronisation `shared-ui`

Tant que `@shared-ui` n'est pas extrait en package npm interne (V2), la
synchronisation est **manuelle** :

```bash
# Sens MesureEscalier → MesureChassis (canonique)
rsync -av --delete \
  /app/frontend/src/shared-ui/  \
  /app/mesure-chassis/src/shared-ui/

# Vérifier qu'aucune divergence n'existe
diff -r /app/frontend/src/shared-ui /app/mesure-chassis/src/shared-ui
```

**Règle** : tout fix bug ou ajout d'un composant partagé se fait d'abord côté
MesureEscalier, puis est dupliqué côté MesureChassis. Jamais l'inverse.

---

## 8. Tests & QA

### 8.1 Backend — pytest

Dossier : `/app/backend/tests/test_chassis.py` (à créer).

Tests minimums attendus avant chaque release :

| Test | Objectif |
|------|----------|
| `test_create_chassis_auto_seed` | Vérifie auto-seed selon shape |
| `test_compute_surface` | Surface = (H × L) / 1_000_000 |
| `test_compute_price_with_options` | Total = base + supléments |
| `test_warning_large_chassis` | Warning si largeur > 2400 |
| `test_patch_shape_preserves_data` | Switch shape ne perd pas les valeurs |
| `test_unauthorized_chassis_access` | 401 si pas de JWT |

Cible : **15+ tests passants** avant publication.

### 8.2 Frontend — smoke tests via testing agent

Utiliser `expo_frontend_testing_agent` UNIQUEMENT après autorisation
explicite de l'utilisateur.

Scénarios prioritaires (chacun en viewport iPhone 12 = 390×844) :

1. **Login → Dashboard → Création chantier → Modal chassis 4 cartes → Création.**
2. **Édition champ hauteur → recalcul surface temps réel.**
3. **Switch shape via ShapeSelectorBar avec dialog confirmation.**
4. **Empty state → FAB visible → CTA centré → modal s'ouvre.**
5. **Export PDF → écran récap → bouton génération.**

### 8.3 Linting

```bash
# Frontend
yarn lint        # eslint
yarn type-check  # tsc --noEmit

# Backend
ruff check /app/backend
ruff format --check /app/backend
```

À lancer **systématiquement** avant tout `git commit` (ou avant un build EAS).

---

## 9. Build & déploiement (EAS)

### 9.1 Configuration `eas.json` (à créer)

```json
{
  "cli": { "version": ">= 13.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" },
      "ios":     { "simulator": false }
    },
    "production": {
      "autoIncrement": true,
      "channel": "production"
    }
  },
  "submit": {
    "production": {
      "android": {
        "serviceAccountKeyPath": "./google-service-account.json",
        "track": "production"
      },
      "ios": {
        "appleId": "<apple_id>",
        "ascAppId": "<asc_app_id>"
      }
    }
  }
}
```

### 9.2 Procédure release

```bash
cd /app/mesure-chassis

# 1. Bump version
# Éditer app.json : version + versionCode + buildNumber

# 2. Build preview interne (APK testable)
eas build --platform android --profile preview

# 3. Build production
eas build --platform all --profile production

# 4. Soumission
eas submit --platform android --latest   # → Play Console
eas submit --platform ios     --latest   # → App Store Connect
```

### 9.3 Vérifications avant submit

- [ ] `app.json` → version bumpée
- [ ] `app.json` → `android.versionCode` incrémenté
- [ ] `app.json` → `ios.buildNumber` incrémenté
- [ ] Permissions `android.permissions` et `ios.infoPlist` à jour
- [ ] Tests backend verts (`pytest`)
- [ ] TypeScript compile (`yarn type-check`)
- [ ] Tests visuels OK sur 3 dimensions (iPhone, Android, tablette)
- [ ] Pas de logs `console.log` orphelins en production
- [ ] CHANGELOG.md mis à jour

---

## 10. Annexe — checklist artisan terrain

Critères de validation **non-techniques** à vérifier régulièrement avec un
artisan menuisier réel (idéalement le client pilote) :

### 10.1 Ergonomie

- [ ] L'app reste utilisable avec des **gants** (touch targets ≥ 48dp)
- [ ] Lisible en **plein soleil** (contraste fort, texte ≥ 14pt)
- [ ] Saisie clavier numérique pour toutes les dimensions
- [ ] Auto-save : ne **jamais** perdre une donnée par déconnexion réseau
- [ ] Mode offline → file d'attente de sync au retour 4G

### 10.2 Vocabulaire

- [ ] Aucun jargon technique anglais
- [ ] Termes belges/français corrects (`tablette` plutôt que `tablette extérieure`,
      `imposte` plutôt que `transom`)
- [ ] Tooltips explicatifs sur les options non évidentes

### 10.3 Précision métier

- [ ] Validation H × L cohérente (pas de châssis > 6000mm de large par défaut)
- [ ] Coefficients tarifs paramétrables côté admin (pas en dur dans le code)
- [ ] Photo obligatoire au moins pour 1 châssis par chantier ?

### 10.4 Performance

- [ ] Liste de 30+ châssis dans un chantier → scroll fluide (FlashList)
- [ ] Recalcul temps réel < 100 ms sur iPhone 12
- [ ] Export PDF d'un chantier de 20 châssis < 5 s

---

## 📌 Contacts & ressources

- Repo principal : `/app`
- Documentation MesureEscalier : `/app/test_result.md` + `/app/memory/`
- Test credentials : `/app/memory/test_credentials.md`
- Application IDs officiels :
  - MesureEscalier — `com.mesurechassis.escalier`
  - MesureChassis  — `com.mesurechassis.chassis`

---

*Document maintenu à jour par convention : toute évolution majeure de l'architecture
MesureChassis doit être reflétée ici dans la même PR/commit.*
