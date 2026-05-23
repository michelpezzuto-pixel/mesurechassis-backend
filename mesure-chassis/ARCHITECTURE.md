# Architecture — MesureChassis

> Vue d'ensemble technique de l'application MesureChassis. Complément du
> [`MAINTENANCE.md`](./MAINTENANCE.md) qui couvre les opérations quotidiennes.

---

## 1. Vue système — haut niveau

```
┌──────────────────────────────────────────────────────────────────────┐
│                          UTILISATEUR (artisan)                       │
│                  iPhone / Android — Expo Go ou Build                 │
└──────────────────┬───────────────────────────────────────────────────┘
                   │  HTTPS (JWT Bearer)
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Kubernetes Ingress (preview.emergentagent.com)      │
│  / → port 3000 (Metro/web)     /api/* → port 8001 (FastAPI)         │
└─────────────────┬─────────────────────────────────┬──────────────────┘
                  │                                 │
                  ▼                                 ▼
       ┌─────────────────────┐         ┌─────────────────────────┐
       │  EXPO ROUTER APP    │         │   FastAPI Backend        │
       │  (mesure-chassis)   │         │   (port 8001, /api)      │
       │  - app/             │ ◀──────▶│   - routers/             │
       │    ├ login.tsx      │  REST   │     ├ auth.py            │
       │    ├ dashboard.tsx  │  JSON   │     ├ projects.py        │
       │    └ projects/[id]/ │         │     ├ chassis.py  🆕     │
       │      chassis/[cid]/ │         │     └ exports.py         │
       │  - src/             │         │   - models/              │
       │    ├ api/           │         │     └ chassis_schemas.py │
       │    ├ sketches/      │         │   - services/            │
       │    ├ shared-ui/     │         │     └ chassis_compute.py │
       │    └ utils/         │         └─────────┬───────────────┘
       └─────────────────────┘                   │ Motor (async)
                                                  ▼
                                       ┌─────────────────────────┐
                                       │  MongoDB (port 27017)    │
                                       │  - users                 │
                                       │  - projects              │
                                       │    {chassis: [...]}  🆕  │
                                       └─────────────────────────┘
```

---

## 2. Flow d'une saisie de châssis (séquence)

```
Artisan                Mobile App                Backend                 MongoDB
   │                        │                       │                        │
   │ Tap "+" (FAB)          │                       │                        │
   ├──────────────────────▶ │                       │                        │
   │                        │ Open Modal 5 cartes   │                        │
   │ Choisit "Ouvrant 1V"   │                       │                        │
   │ Tape "Cuisine - droite"│                       │                        │
   │ Valide                 │                       │                        │
   ├──────────────────────▶ │ POST /chassis         │                        │
   │                        ├─────────────────────▶ │ Auto-seed template     │
   │                        │                       ├──────────────────────▶ │ INSERT
   │                        │                       │ {hauteur:1450, larg:700│
   │                        │                       │  shape:"ouvrant_1v"…}  │
   │                        │ ◀───────────────────  │ ◀──────────────────────│
   │                        │ Navigate to editor    │                        │
   │ Édite hauteur 1500     │                       │                        │
   ├──────────────────────▶ │ debounce 250ms        │                        │
   │                        │ PATCH /chassis/{cid}  │                        │
   │                        ├─────────────────────▶ │ UPDATE                 │
   │                        │                       ├──────────────────────▶ │
   │                        │ GET /chassis/{cid}/compute                     │
   │                        ├─────────────────────▶ │ surface=1.05m², 565€   │
   │                        │ ◀───────────────────  │                        │
   │                        │ Update KPIs in real-time                       │
   │ Tap "Exporter"         │                       │                        │
   ├──────────────────────▶ │ POST /export          │                        │
   │                        ├─────────────────────▶ │ Build PDF (ReportLab)  │
   │                        │ ◀──────────────────── │                        │
   │ Reçoit PDF base64      │                       │                        │
   │ partage via OS native  │                       │                        │
```

---

## 3. Composants frontend — diagramme de dépendances

```
┌─────────────────────────────────────────────────────────────────────┐
│                          app/_layout.tsx                            │
│  (AuthProvider, ThemeProvider, SafeAreaProvider)                    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
            ┌─────────────────────┴────────────────────┐
            ▼                                          ▼
┌──────────────────────────┐         ┌──────────────────────────────┐
│   dashboard.tsx          │         │   projects/[id]/index.tsx     │
│   - Liste chantiers      │         │   - Liste châssis             │
│   - useProjects() hook   │         │   - Empty state + FAB         │
│   - FlashList            │         │   - Modal 5 cartes (création) │
└──────────────────────────┘         └────────────────┬─────────────┘
                                                       │
                                                       ▼
                              ┌───────────────────────────────────────────┐
                              │ projects/[id]/chassis/[cid]/index.tsx     │
                              │ (ChassisEditor)                            │
                              │                                            │
                              │  ┌─────────────────────────────────────┐  │
                              │  │ <ShapeSelectorBar />  (5 chips)     │  │
                              │  ├─────────────────────────────────────┤  │
                              │  │ <KPIRow />  (Surface, Prix base…)   │  │
                              │  ├─────────────────────────────────────┤  │
                              │  │ <SplitVisualBlock>                  │  │
                              │  │   <ChassisElevation />              │  │
                              │  │   <ChassisPlan />                   │  │
                              │  │ </SplitVisualBlock>                 │  │
                              │  ├─────────────────────────────────────┤  │
                              │  │ <ChassisFields />  (H, L, options)  │  │
                              │  ├─────────────────────────────────────┤  │
                              │  │ <DataBlock />  (KPIs + warnings)    │  │
                              │  ├─────────────────────────────────────┤  │
                              │  │ <Footer /> [← RETOUR] [↑ EXPORTER] │  │
                              │  └─────────────────────────────────────┘  │
                              └───────────────────────────────────────────┘
```

---

## 4. Contrats API — table sommaire

| Méthode | Endpoint | Body | Réponse | Notes |
|--------|----------|------|---------|-------|
| `GET`  | `/api/projects/{pid}/chassis` | — | `Chassis[]` | Liste |
| `POST` | `/api/projects/{pid}/chassis` | `{name, shape}` | `Chassis` | Auto-seed selon shape |
| `GET`  | `/api/projects/{pid}/chassis/{cid}` | — | `Chassis` | Détail |
| `PATCH`| `/api/projects/{pid}/chassis/{cid}` | `Partial<Chassis>` | `Chassis` | Update champs |
| `DELETE`| `/api/projects/{pid}/chassis/{cid}` | — | `204` | Suppression |
| `GET`  | `/api/projects/{pid}/chassis/{cid}/compute` | — | `ChassisCompute` | Surface, prix, warnings |
| `POST` | `/api/projects/{pid}/chassis/{cid}/export` | `{format: "pdf"}` | `{base64, filename}` | PDF rapport |
| `POST` | `/api/projects/{pid}/chassis/{cid}/photo` | `{photo_base64}` | `Chassis` | Upload photo terrain |

**Sécurité** : tous les endpoints requièrent `Authorization: Bearer <JWT>` valide.
Le décorateur backend `require_active_access` vérifie que :
- L'utilisateur est authentifié
- L'utilisateur a droit d'accès au projet (créateur, technicien assigné, ou admin)
- Le projet n'est pas verrouillé pour les opérations d'écriture

---

## 5. Tables de référence métier

### 5.1 Matériaux et prix de base (à externaliser en DB admin)

| Matériau | Coefficient prix m² | Notes |
|----------|---------------------|-------|
| `pvc` | 240 €/m² | Référence |
| `alu` | 380 €/m² | +58% vs PVC |
| `bois` | 420 €/m² | +75% |
| `mixte_bois_alu` | 520 €/m² | Premium |

### 5.2 Vitrages

| Type | Supplément €/m² |
|------|-----------------|
| `double` | 0 (inclus) |
| `triple` | +60 |
| `feuilleté` | +90 |
| `phonique` | +110 |

### 5.3 Options

| Clé | Description | Prix |
|-----|-------------|------|
| `ral` | RAL spécifique (hors blanc) | +12% du total |
| `imposte` | Imposte fixe au-dessus | +180 € |
| `allege` | Allège vitrée en partie basse | +150 € |
| `renfort_alu` | Renfort aluminium (PVC seulement) | +45 € |
| `poignée_premium` | Poignée design | +35 € |

> ⚠️ **Important** : ces valeurs sont **indicatives**. Les vrais barèmes doivent
> venir d'une collection `pricing` administrable par le client. Ne pas hardcoder
> dans le code de production.

---

## 6. Gestion d'état frontend

### 6.1 State global (Zustand)

```ts
// src/store/useChassisDraft.ts
interface ChassisDraftStore {
  // Le châssis en édition + son patch optimiste local
  current: Chassis | null;
  setCurrent: (c: Chassis) => void;
  patchLocal: (patch: Partial<Chassis>) => void;
  // Debounced PATCH server
  commitDebounced: (cid: string) => void;
}
```

### 6.2 Cache serveur (React Query — optionnel V2)

Pour V1, simple `useEffect` + `useState`.
Pour V2, migrer vers `@tanstack/react-query` si la liste de châssis dépasse
20 items et qu'on veut un cache intelligent.

### 6.3 Persistance offline

- **AsyncStorage** : token JWT + projets récents (lecture seule cache)
- **Queue de sync** *(V2)* : opérations PATCH en attente quand pas de réseau,
  rejouées au retour de connectivité.

---

## 7. Sécurité

| Aspect | Implémentation |
|--------|----------------|
| Auth | JWT signé HS256 (même secret que MesureEscalier) |
| Storage local | `expo-secure-store` pour le token (pas `AsyncStorage`) |
| HTTPS | Géré par Kubernetes Ingress (cert Let's Encrypt) |
| Validation input | Pydantic côté backend + Zod côté frontend |
| Permissions device | Camera, micro, photos — descriptions iOS + permissions Android dans `app.json` |
| Données photo | Stockées en base64 dans MongoDB pour V1 (limite 16MB par doc). V2 : extraction vers S3 ou GridFS. |

---

## 8. Performance — objectifs SLA

| Indicateur | Objectif | Mesure |
|------------|----------|--------|
| Cold start app | < 3 s | iPhone 12 |
| Affichage liste 30 châssis | < 500 ms | FlashList |
| Recalcul compute | < 200 ms | Backend |
| Export PDF 20 châssis | < 5 s | Backend + transfert |
| Taille de bundle JS | < 4 MB | gzipped |

---

## 9. Évolutions planifiées (roadmap technique)

| Version | Feature | Effort estimé |
|---------|---------|---------------|
| 1.0 | MVP : CRUD chassis + compute + PDF export | 2-3 semaines |
| 1.1 | Mode offline + queue sync | 1 semaine |
| 1.2 | Pricing administrable + multi-fournisseur | 2 semaines |
| 2.0 | Extraction `@shared-ui` en package npm interne | 1 semaine |
| 2.1 | Calcul thermique (Uw, Sw) + label CEE | 3 semaines (expertise métier requise) |
| 2.2 | Dictée vocale Whisper pour remarques chantier | 1 semaine |
| 3.0 | Mode Atelier (production) : suivi de commande | 4+ semaines |

---

*Document vivant — synchroniser à chaque évolution architecturale majeure.*
