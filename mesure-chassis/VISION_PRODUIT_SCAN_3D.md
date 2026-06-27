# Vision Produit — Scan 3D d'escalier par marqueurs ArUco

> Document de référence métier + technique. À reprendre quand le développement
> de cette feature sera lancé (probablement dans un repo dédié `mesure-escalier-scan`
> ou comme module de MesureEscalier).

---

## 1. Vision produit

### 1.1 Cible utilisateur
**Mesureur professionnel** (ferronnier, menuisier, métreur, BIM coordinator) qui doit relever un escalier existant pour le réintégrer dans un logiciel de DAO/CAO (AutoCAD, SolidWorks, Archicad, Revit, Fusion 360).

### 1.2 Promesse
> "Posez des markers, photographiez, recevez votre escalier en DXF."

Workflow ultra-rapide (5-10 min sur place) vs méthode traditionnelle (60-90 min
au mètre laser + report manuel sur PC).

### 1.3 Cas d'usage
- Pose de garde-corps (ferronnerie)
- Habillage / rénovation d'escalier
- Rénovation BIM (intégration dans maquette numérique)
- Devis sur photo (atelier)
- Archivage patrimoine (architecte du patrimoine)

---

## 2. Technologie — Fiducial markers ArUco / AprilTag

### 2.1 Principe
Motifs noir & blanc imprimés que la caméra du téléphone localise dans l'espace
3D avec **précision sub-millimétrique** (±0.5 mm à 1 m).

### 2.2 Bibliothèques
| Stack | Cas d'usage | Maintenance |
|-------|-------------|-------------|
| **OpenCV ArUco** | C++/Python natif, intégration via JNI/Obj-C | ★★★★★ |
| **AprilTag (umich)** | Plus robuste sous mauvaise lumière | ★★★★ |
| **react-native-aruco** | Wrapper RN, plus simple mais limité | ★★★ |
| **ARKit Image Anchors** | iOS only, intégré natif, très précis | ★★★★ |
| **ARCore Augmented Images** | Android only, équivalent ARKit | ★★★★ |

**Recommandation** : OpenCV ArUco compilé en module natif Swift + Java, exposé
via JSI à React Native. Le plus contrôlable et le plus précis.

---

## 3. Matériel — Les 4 options de marker

### Option 1 — Marqueurs imprimés laminés (V1 MVP)
- Pastilles plastifiées 5×5 cm, marker ArUco imprimé
- ~30 cts unité, kit de 20 = ~6€
- Posés à plat (limitation : biais possible sur arêtes)

### Option 2 — Marqueurs aimantés
- Pastille aimantée 4 cm + marker collé
- ~1€ unité
- Idéal structures métalliques (limons inox, ferronnerie)

### Option 3 — **Clips d'arête 3D — produit signature**
- Petit clip plastique en "L" inversé imprimé 3D
- Face supérieure plate avec ArUco numéroté
- Se pose directement sur l'arête de marche → **position exacte sans biais**
- ~50 cts d'impression, vente 3-5€ en kit
- **Brevet déposable** : géométrie spécifique optimisée pour nez de marche

### Option 4 — Pucks UWB Bluetooth (non recommandé)
- Précision insuffisante (~5-10 cm) pour escalier

---

## 4. Workflow complet

```
1. CALIBRATION CAMÉRA (1 fois par téléphone)
   - L'app affiche une mire de calibration imprimable
   - Mesureur prend 10 photos sous différents angles
   - Algorithme détermine focale + distorsion → précision sub-mm garantie

2. POSE DU POINT DE RÉFÉRENCE
   - Marker #0 posé sur un point connu (mur, sol, repère chantier)
   - Mesureur saisit X/Y/Z du point #0 (peut être 0/0/0 ou
     valeurs absolues si chantier déjà géoréférencé)

3. POSE DES MARKERS SUR L'ESCALIER
   - Marker #1, #2, ... sur chaque point clé :
     * 2 marqueurs par nez de marche (gauche + droit)
     * 2 marqueurs au départ
     * 2 marqueurs à l'arrivée
     * 1 par jambage limon
     * 1 sur palier intermédiaire si tournant
   - Typique : 24-30 marqueurs pour un escalier 14 marches 1/4 tournant

4. CAPTURE
   - Mesureur balaye lentement l'escalier en filmant
   - App détecte en temps réel chaque marker visible
   - Affiche : "23/28 markers acquis ✓"
   - Multipass : refaire un balayage si marqueurs manqués

5. RECONSTRUCTION
   - L'app interpole les surfaces entre marqueurs :
     * Plan de marche (4 marqueurs par marche)
     * Contremarche (déduite de 2 marqueurs verticaux)
     * Limon (suite de points alignés)
     * Profil 3D complet

6. EXPORT MULTI-FORMAT
   - DXF (AutoCAD, BricsCAD) — texte ASCII, simple à générer
   - DWG (AutoCAD natif) — via librairie ODA Drawings SDK (payant)
   - IFC (BIM) — IfcOpenShell
   - STEP / IGES (SolidWorks) — via OpenCASCADE
   - STL / OBJ / GLB (générique) — Three.js export
   - PDF avec cotes (livrable client)
```

---

## 5. Précision attendue

| Configuration | Précision |
|---------------|-----------|
| Marker ArUco bien éclairé à 1 m, caméra calibrée | **±0.5 mm** |
| Marker à 3 m | ±2 mm |
| Sans LiDAR, caméra seule | ±1-3 mm global |
| Avec LiDAR (iPhone Pro) en complément | ±0.5 mm garanti |

→ Conformité normes ferronnerie (NF P 01-012) et BIM (LOD 400) assurée.

---

## 6. Modèle économique — Le "Kit Mesure'Escalier"

### 6.1 Hardware (one-shot)
```
🎁 KIT PHYSIQUE (vendu avec abonnement annuel)
├── 24 clips d'arête imprimés 3D avec marker ArUco numéroté
├── 8 pastilles aimantées pour structures métalliques
├── 1 plaque "point de référence" magnétique
├── 1 mire de calibration A4 plastifiée
├── 1 mètre laser Bluetooth d'appoint (optionnel)
└── 1 mallette en mousse découpée

💰 Tarif suggéré : 89-129 € HT le kit complet
```

### 6.2 Software (récurrent)
```
💻 ABONNEMENT APP
├── Free trial 14 jours
├── 19 € / mois (paiement mensuel)
├── 199 € / an (paiement annuel — économie 30%)
└── Plan Atelier : 49 €/mois pour 5 mesureurs (centralisation projets)
```

### 6.3 Avantage différenciant
1. Hardware physique = barrière à l'entrée vs concurrents purs SaaS
2. Clips imprimés 3D = signature produit visible sur chaque chantier
3. Revenu mix one-shot + récurrent
4. Marge confortable (clips coûtent 50 cts, vendus 3-5€)

---

## 7. Roadmap d'implémentation

| Phase | Durée | Livrable |
|-------|------:|----------|
| **V0** Spike technique | 1 sem | Module RN qui détecte ArUco via OpenCV et affiche les coordonnées 3D |
| **V1** MVP | 4 sem | Workflow complet : calibration + référence + capture + reconstruction + export DXF |
| **V1.5** Multi-export | 2 sem | IFC + STEP + STL + PDF avec cotes |
| **V2** Clips 3D | 2 sem | Modélisation et impression des clips signature + détection optimisée |
| **V2.5** Mode atelier | 3 sem | Synchronisation multi-mesureur, gestion projets équipe |
| **V3** Devis automatique | 4 sem | Catalogue intégré (garde-corps, habillage) + génération devis depuis modèle 3D |

---

## 8. Dépendances techniques

```bash
# Backend (Python/FastAPI)
pip install opencv-python opencv-contrib-python   # ArUco + calibration
pip install numpy scipy                            # Geometry math
pip install ezdxf                                  # Export DXF
pip install ifcopenshell                           # Export IFC
pip install trimesh                                # Mesh manipulation + STL/OBJ

# Frontend (Expo/RN) — development build requis (pas Expo Go)
yarn add react-native-vision-camera                # Camera frames
yarn add react-native-worklets-core                # Real-time frame processing
# Module natif Swift/Java pour OpenCV ArUco bindings
```

---

## 9. Risques & mitigation

| Risque | Mitigation |
|--------|------------|
| Mauvais éclairage chantier (cave, sous-sol) | Clips fluorescents + flash iPhone activé |
| Marker partiellement caché par poussière | Détection partielle ArUco OK jusqu'à 30% de coin manquant |
| Calibration utilisateur ratée | Tutoriel vidéo embarqué + check qualité auto avant capture |
| Export DWG (format propriétaire Autodesk) | Démarrer par DXF (libre), DWG en V1.5 via ODA SDK (licence ~3000$/an) |
| Concurrence (Polycam, Magicplan) | Spécialisation ESCALIER + workflow métier + kit hardware |

---

## 10. POC réalisable

Si validation, je peux scaffolder un POC dans `/app/mesure-escalier-scan/poc/` :

```
poc/
├── README.md                    # Build & run
├── package.json
├── app.json                     # Permissions caméra
├── ios/
│   └── ArucoDetector.swift      # Bindings OpenCV ArUco
├── android/
│   └── ArucoDetector.java
├── app/
│   ├── calibration.tsx          # Étape calibration caméra
│   ├── reference.tsx            # Pose du marker #0
│   └── capture.tsx              # Scan live + acquisition markers
└── src/
    ├── geometry/
    │   ├── triangulate.ts       # Reconstitution 3D depuis points
    │   └── interpolate.ts       # Surfaces entre markers
    └── export/
        └── dxf.ts               # Génération fichier DXF
```

**Démontre** :
- Calibration caméra
- Détection live de 8 markers ArUco posés sur un escalier de test
- Reconstruction des nez de marche
- Export DXF importable dans AutoCAD

**Effort POC** : 1 semaine de dev intensif (1 dev expérimenté natif iOS + RN).

---

## 11. Points à valider avec un mesureur professionnel

Avant d'implémenter, faire valider par 2-3 mesureurs ferronniers/menuisiers :

- [ ] Le workflow de pose de 24 markers est-il acceptable terrain ? (vs mètre laser solo)
- [ ] Préfèrent-ils clips imprimés 3D ou pastilles aimantées ?
- [ ] Quel format de sortie est le plus utile pour eux : DXF ? IFC ? STEP ?
- [ ] Acceptent-ils 89-129€ pour le kit + 19€/mois ?
- [ ] Quels points clés sont absolument requis sur l'escalier (au-delà des nez de marche) ?

---

*Vision archivée le 23 mai 2026. À transposer dans le repo de production quand
le développement de cette feature sera priorisé après MesureEscalier V1.*
