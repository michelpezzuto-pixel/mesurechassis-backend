# Spec technique — Scan AR d'escalier pour pose de garde-corps

> Document de faisabilité technique. À reprendre par le dev qui implémentera
> cette feature dans l'app dédiée **MesureGardeCorps** ou comme module dans
> MesureEscalier.

---

## 1. Cas d'usage métier

| Aspect | Détail |
|--------|--------|
| **Domaine** | Ferronnerie / menuiserie — pose de **garde-corps sur escalier existant** |
| **Différence avec MesureEscalier** | MesureEscalier mesure pour **construire** un escalier neuf. Cette feature mesure un escalier **déjà installé** pour y poser un accessoire. |
| **Workflow terrain** | Artisan arrive → ouvre l'app → cadre l'escalier → tape sur chaque coin clé → app reconstitue le modèle 3D → catalogue de garde-corps adaptés → devis automatique |
| **Précision requise** | ±5 mm (norme NF P 01-012 garde-corps) |

---

## 2. Trois voies techniques classées

### 🥇 Voie 1 — ARKit "point-par-point" (MVP recommandé)

| | |
|---|---|
| **Principe** | Tap sur chaque coin de marche → coordonnées 3D `(x, y, z)` en mètres |
| **Compatibilité** | iPhone 6s+ et iPad récents (~95% du parc) |
| **Précision** | ±1 cm < 3 m, ±2-3 cm > 3 m |
| **Stack** | `@viro-community/react-viro` OU module Swift natif + Expo prebuild + `react-native-vision-camera` |
| **Effort** | 2-3 semaines |

**Workflow détaillé** :
1. Tap "📷 SCANNER L'ESCALIER" → caméra AR ouvre
2. Réticule au centre de l'écran + instruction overlay
3. Pour chaque point clé : viser → tap → marker numéroté apparaît
4. Points à poser (typiquement 8-12) :
   - Départ : 2 coins du nez de la 1ère marche
   - Pour chaque marche intermédiaire : nez de marche (1 point)
   - Arrivée : 2 coins du palier haut
   - Jambage : extrémités gauche / droite (largeur escalier)
5. Validation → reconstruction géométrique (hauteur, giron, largeur, angles)

### 🥈 Voie 2 — Scan LiDAR + Apple RoomPlan

| | |
|---|---|
| **Principe** | Balayage 30 sec → mesh 3D auto + détection escaliers native |
| **Compatibilité** | **iPhone 12/13/14/15/16 Pro + iPad Pro uniquement** (~30% parc) |
| **Précision** | ±5 mm |
| **Stack** | `RoomPlan` API iOS 17.3+ ("stair detection" officiel) |
| **Effort** | 1-2 semaines (Apple fait 80% du boulot) |
| **Export** | USDZ, GLB, JSON avec cotes |

### 🥉 Voie 3 — Laser-mètre Bluetooth externe

| | |
|---|---|
| **Principe** | Bosch GLM 50-27 CG / Leica DISTO D2 → BLE → app |
| **Compatibilité** | Tous téléphones BLE |
| **Précision** | ±2 mm sur 50 m (laser certifié) |
| **Stack** | `react-native-ble-plx` |
| **Effort** | 1 semaine par modèle de laser intégré |
| **Coût matériel** | 150-180€ pour l'artisan |

### 🎁 Voie bonus — Photogrammétrie offline

30 photos sous angles différents → mesh ultra-précis via Apple Object Capture
(macOS) ou cloud (Polycam, Trnio). Pas temps réel, idéal litiges/archivage.

---

## 3. Stratégie recommandée

**Combo Voie 1 + Voie 2** avec détection auto :
- L'app détecte au lancement si l'iPhone a un LiDAR
  ```swift
  ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh)
  ```
- Si **oui** → propose le scan automatique RoomPlan (30 sec)
- Si **non** → fallback point-par-point (2-3 min)
- Toujours **proposer la calibration** par 1 mesure manuelle au mètre laser pour respecter la norme NF P 01-012

---

## 4. Roadmap d'implémentation

| Phase | Durée | Livrable |
|-------|------:|----------|
| **V1 MVP** | 3-4 sem | ARKit point-par-point + reconstruction géométrique + export STL/DXF pour atelier |
| **V1.5** | +2 sem | Détection LiDAR auto → bascule RoomPlan iOS 17 |
| **V2** | +3 sem | Catalogue garde-corps (inox, verre, fer forgé) + surimpression AR du modèle 3D sur la vidéo live |
| **V2.5** | +2 sem | BLE laser-mètre Bosch / Leica |
| **V3** | +4 sem | Devis automatique + export client en réalité augmentée |

---

## 5. Points d'attention

### Précision légale
La norme **NF P 01-012** impose ±5 mm sur la hauteur du garde-corps. La Voie 1
frôle cette précision → **toujours** proposer une calibration manuelle au mètre
laser sur 1-2 points avant validation finale.

### Offline-first
Le scan doit fonctionner **sans réseau** (chantier en sous-sol). Stockage local
du mesh USDZ, upload différé au retour 4G/Wi-Fi.

### Positionnement marché
Polycam et Magicplan font déjà du scan 3D générique mais **ne sont pas spécialisés
garde-corps**. La valeur ajoutée propre :
- Workflow métier ferronnier/menuisier
- Génération automatique du devis
- Plan d'usinage atelier (DXF/STL prêt à découpe)
- Catalogue de modèles intégré

---

## 6. Dépendances Expo / RN à prévoir

```bash
# Pour la Voie 1 ARKit point-par-point
yarn add @viro-community/react-viro
# OU module natif Swift :
yarn expo install expo-build-properties
yarn add react-native-vision-camera

# Pour la Voie 2 RoomPlan (iOS only)
# → Code Swift natif via expo prebuild + iOS module

# Pour la Voie 3 BLE
yarn add react-native-ble-plx
yarn expo install expo-build-properties
```

> ⚠️ Aucune de ces fonctionnalités ne marche dans **Expo Go** — nécessite un
> **development build** EAS (`eas build --profile development`).

---

## 7. POC minimal proposé

Si vous validez, voici ce que je peux scaffolder en autonomie dans
`/app/mesure-chassis/poc-ar-scan/` (ou directement dans le repo MesureChassis
dans votre autre env) :

```
poc-ar-scan/
├── README.md               # Build & run instructions
├── package.json
├── app.json
├── ios/
│   └── ARScanner.swift     # Module natif : caméra AR + pose de points
├── app/
│   └── scanner/
│       └── index.tsx       # UI React Native : réticule + liste points + validation
└── src/
    └── geometry/
        └── reconstruct.ts  # Reconstruction marche par marche depuis 8 points 3D
```

Démontre :
- Ouverture caméra AR
- Pose de 8 points 3D par tap
- Calcul hauteur de marche / giron / largeur
- Affichage des résultats en surimpression

**Effort POC** : 2-3 jours de dev intensif.

---

*Document créé pour cadrer la feature avant implémentation. À transposer dans le
repo MesureChassis approprié au moment du démarrage du dev.*
