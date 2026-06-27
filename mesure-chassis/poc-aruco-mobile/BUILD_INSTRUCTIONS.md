# Build iOS du POC ArUco — pas-à-pas

> ⚠️ Ce POC **ne fonctionne pas** dans Expo Go ni dans la preview web.
> Il faut un **iOS Dev Build** car on utilise un frame processor natif Swift +
> OpenCV C++.

## Pré-requis

- Un iPhone (iOS 15.1+)
- Un compte Apple Developer (gratuit suffit pour 7 jours, payant 99 $/an pour
  illimité)
- Soit un **Mac avec Xcode 15+** (build local)
  → soit utiliser le **bouton « Publish »** d'Emergent pour un build EAS cloud

## 1. Installer les dépendances JS

```bash
cd /app/mesure-chassis/poc-aruco-mobile
yarn install
```

## 2. Télécharger OpenCV iOS Framework

**Une seule fois**, ~150 MB :

1. Va sur https://opencv.org/releases/
2. Télécharge `opencv-4.10.0-ios-framework.zip` (ou plus récent, tant que ≥ 4.7)
3. Décompresse-le
4. Place le dossier `opencv2.framework` ici :

```
modules/aruco-detector/ios/Frameworks/opencv2.framework
```

**Vérification :**

```bash
ls modules/aruco-detector/ios/Frameworks/opencv2.framework/
# Tu dois voir : Headers/  Info.plist  Modules/  opencv2
```

## 3. Générer le projet iOS natif (`prebuild`)

```bash
yarn prebuild:ios
```

Cela crée le dossier `ios/` avec :

- le projet Xcode
- l'autolinking du module local `aruco-detector`
- l'injection automatique de OpenCV via le `.podspec`
- `Info.plist` configuré avec `NSCameraUsageDescription`

## 4a. Build EAS (cloud — recommandé)

Dans l'interface Emergent :

1. Clique sur **Publish** en haut à droite
2. Choisis **iOS Development Build**
3. Fournis tes identifiants Apple Developer si demandé
4. Attends que le `.ipa` soit prêt (~15 min)
5. Scanne le QR code pour l'installer sur ton iPhone

*Ou en ligne de commande (si tu as `eas-cli` configuré) :*

```bash
yarn build:ios:dev
```

## 4b. Build local Xcode (alternative — Mac requis)

```bash
cd ios
pod install
cd ..
yarn ios
```

Ou ouvre `ios/POCArUcoMobile.xcworkspace` dans Xcode :

- sélectionne ton iPhone comme cible
- onglet **Signing & Capabilities** → choisis ton Team
- bouton **Run** ▶️

## 5. Tester

1. Lance l'app sur ton iPhone
2. Autorise l'accès caméra à la 1ère ouverture
3. Pointe vers tes marqueurs imprimés en 50 mm
4. Tu dois voir :
   - un **cadre cyan** autour de chaque marqueur détecté
   - le **`#ID`** au centre
   - le HUD en haut à gauche avec : compteur + résolution + FPS
   - les **chips d'IDs** en bas

## Dépannage rapide

| Symptôme | Solution |
|---|---|
| `[poc-aruco] Native plugin "detectAruco" not found` | Le module natif n'est pas linké. Refais `yarn prebuild:ios` puis rebuild. |
| Crash au lancement, log `opencv2.framework not found` | Tu n'as pas placé OpenCV dans `modules/aruco-detector/ios/Frameworks/`. Refais l'étape 2. |
| Caméra noire | Permissions iOS. Va dans **Réglages → Confidentialité → Caméra → POC ArUco** |
| Aucun marqueur détecté même collé sur la caméra | Vérifie que tu as bien imprimé le PDF généré par `/api/poc/markers.pdf` (dictionnaire DICT_4X4_50). |
| FPS très bas (< 5) | Normal en mode debug. En release c'est ~25-30 fps. |

## Pourquoi cette stack ?

- **vision-camera v4** : seule lib mature avec frame processors JSI low-latency
- **OpenCV vendored** : version contrôlée, ArUco en core depuis 4.7 = pas de `opencv_contrib`
- **Obj-C++ bridge** : ne pas exposer le C++ d'OpenCV directement à Swift (limitations d'interop)
- **Module Expo local** : autolinking propre via `expo prebuild`, pas de patches manuels
