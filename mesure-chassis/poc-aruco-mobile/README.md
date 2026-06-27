# POC ArUco Mobile (iOS)

App Expo **ultra-minimale** dont l'unique objectif est de répondre à une question :

> Est-ce que **mon iPhone + mes marqueurs DICT_4X4_50 50 mm + mon escalier**
> permettent une détection live **fiable et stable** ?

## Périmètre (volontairement limité)

Ce POC fait **uniquement** ça :

- ✅ Ouvre la caméra arrière de l'iPhone en live
- ✅ Détecte les marqueurs **ArUco DICT_4X4_50** sur chaque frame (OpenCV natif)
- ✅ Dessine un **cadre cyan** autour de chaque marqueur détecté
- ✅ Affiche l'**ID** au centre du marqueur
- ✅ HUD : nombre de markers détectés, résolution, FPS approximatif

Il ne fait **PAS** (volontairement) :

- ❌ Pose 3D / axes XYZ (sera ajouté **après** validation du POC)
- ❌ Calibration de la caméra
- ❌ Reconstruction d'escalier
- ❌ Export DXF
- ❌ Sauvegarde de mesures
- ❌ Aucune logique métier

## Stack

- Expo SDK 54 + Expo Router 6 + React Native 0.81.5 (aligné sur `MesureEscalier`)
- `react-native-vision-camera` v4 avec un **frame processor plugin Swift** custom
- Module Expo local `modules/aruco-detector` (Swift + Objective-C++)
- **OpenCV iOS 4.10** *vendored* (ArUco est dans le **core** depuis 4.7, donc pas besoin de `opencv_contrib`)
- Overlay SVG via `react-native-svg`
- Build via **EAS Dev Build** (bouton **Publish** d'Emergent, ou local)

## ⚠️ Ne fonctionne pas dans Expo Go ni dans la preview Web

Les frame processors et OpenCV nécessitent un **build natif iOS** (Dev Client).
C'est attendu : voir [`BUILD_INSTRUCTIONS.md`](./BUILD_INSTRUCTIONS.md).

## Démarrer rapidement

```bash
cd /app/mesure-chassis/poc-aruco-mobile
yarn install

# 1. Télécharger OpenCV 4.10 iOS framework (~150 MB, une seule fois) :
#    https://opencv.org/releases/  →  opencv-4.10.0-ios-framework.zip
# 2. Décompresser et placer opencv2.framework ici :
#    modules/aruco-detector/ios/Frameworks/opencv2.framework

yarn prebuild:ios           # génère ios/ avec le module natif

# Option A : build cloud via EAS (recommandé)
yarn build:ios:dev          # ou utiliser le bouton « Publish » d'Emergent

# Option B : build local Xcode (si tu as un Mac avec Xcode)
yarn ios
```

Installe le `.ipa` sur ton iPhone (TestFlight ou installation directe), lance
l'app, autorise la caméra, vise tes marqueurs imprimés.

## Critères de validation du POC

À tester dans **ton** escalier, avec **tes** markers imprimés en 50 mm :

| Test | Critère |
|---|---|
| **Distance** | Combien de markers détectés à 1,5 m ? À 2 m ? À 2,5 m ? |
| **Angle** | Combien restent détectés à 30° de biais ? À 45° ? À 60° ? |
| **Stabilité ID** | L'ID lu est-il constant frame après frame ? Ou ça "clignote" ? |
| **Lumière** | Idem à la lumière du jour et avec éclairage tungstène/LED ? |

Si ces 4 critères passent → on a notre **fondation**, et on peut décider :
- ajout pose 3D + axes,
- calibration caméra,
- reconstruction d'escalier,
- export DXF.

Si ça ne passe pas → on ajuste : taille 60-80 mm, ou changement de
dictionnaire (AprilTag, ArUco H11, etc).

## Arborescence

```
poc-aruco-mobile/
├── README.md                    ← ce fichier
├── BUILD_INSTRUCTIONS.md        ← guide pas-à-pas pour le build iOS
├── package.json
├── app.json                     ← bundleId com.mesurechassis.pocaruco
├── eas.json
├── app/
│   ├── _layout.tsx              ← stack expo-router
│   └── index.tsx                ← écran caméra + HUD
├── src/
│   ├── components/MarkerOverlay.tsx     ← SVG cadres + IDs
│   └── lib/aruco-frame-processor.ts     ← wrapper worklet
└── modules/aruco-detector/      ← module Expo local
    ├── expo-module.config.json
    ├── package.json
    ├── index.ts
    └── ios/
        ├── ArucoDetector.podspec
        ├── ArucoDetectorModule.swift
        ├── ArucoFrameProcessorPlugin.swift  ← entrée VisionCamera
        ├── ArucoFrameProcessorPluginLoader.m ← +load auto-register
        ├── ArucoBridge.h / .mm              ← Obj-C++ ↔ OpenCV
        └── Frameworks/
            └── opencv2.framework  ← ⚠️ à télécharger toi-même
```
