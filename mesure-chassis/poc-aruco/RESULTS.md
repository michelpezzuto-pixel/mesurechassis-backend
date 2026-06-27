# POC ArUco — Rapport de simulation

> Simulation Monte-Carlo (1000 itérations) de la pipeline complète
> détection ArUco → reconstruction → cotes métier.
>
> **Attention** : ces chiffres viennent d'un MODÈLE THÉORIQUE basé sur les
> specs publiques d'OpenCV ArUco. Ils doivent être confirmés/infirmés par
> des tests terrain réels avec le module mobile natif.

## Configuration testée

| Paramètre | Valeur |
|-----------|--------|
| Escalier référence | 14 marches, h=178.0 mm, g=270.0 mm, largeur=1000.0 mm |
| Nombre de markers posés | 30 (2 par nez + palier) |
| Distance caméra-marker moyenne | ~1.5 m |
| Bruit détection ArUco | σ = 1.0 px (OpenCV bonne lumière) |
| FOV caméra simulée | 78.0° (iPhone 14) |
| Résolution simulée | 1920 px |
| Biais calibration | 0.3 mm |

## Résultats — précision attendue

| Métrique | Moyenne | P95 | Max |
|----------|--------:|----:|----:|
| **Erreur 3D marker (RMS)**     | 3.55 mm | 5.77 mm | 10.57 mm |
| **Hauteur de marche** | 1.59 mm | 3.92 mm | 7.62 mm |
| **Giron**             | 1.61 mm | 3.92 mm | 7.43 mm |
| **Largeur escalier**  | 2.28 mm | 5.58 mm | 11.46 mm |

## Lecture honnête des résultats

- **Hauteur de marche / giron** : en moyenne **1.6-1.6 mm d'écart**.
  95% des mesures sont dans **±3.9 mm**.
- **Largeur escalier** : précision attendue **±5.6 mm à P95**.
- **Cas pire (Max)** : on a vu jusqu'à **7.6 mm d'écart** sur certaines marches.

## Mise en perspective

| Norme / besoin | Tolérance | Vert/Orange/Rouge |
|----------------|----------:|:-:|
| NF P 01-012 (garde-corps) hauteur | ±5 mm | 🟢 |
| Tolérance habillage escalier menuiserie | ±3 mm | 🟠 |
| Ferronnerie sur mesure (rampe métal) | ±2 mm | 🟠 |
| Promesse marketing initiale ("sub-mm") | ±0.5 mm | 🔴 NON TENABLE sans LiDAR ou laser-mètre complémentaire |

## Conclusions du POC théorique

1. La pipeline ArUco seule donne une précision **réaliste de ±2-4 mm sur cotes métier**
   à 1.5 m de distance, en bonne lumière, avec calibration soignée.
2. La promesse marketing initiale "sub-mm" est **trompeuse** sans capteur complémentaire
   (laser-mètre Bluetooth ou LiDAR iPhone Pro).
3. La précision **est suffisante** pour :
   - Garde-corps NF P 01-012 (±5 mm) ✅
   - Habillage menuiserie courant (±3 mm) ⚠️ limite
   - Devis et préfabrication globale ✅
4. La précision **n'est PAS suffisante** pour :
   - Ferronnerie sur mesure exigeant ±2 mm ❌
   - Pose de pièces préfabriquées en usine sans ajustement chantier ❌

## Recommandations avant V1

1. **Refaire ce test sur chantier réel** avec module natif Swift OpenCV.
2. **Compléter avec un mètre laser Bluetooth** pour validation 1-2 points critiques.
3. **Ne pas vendre "sub-mm"** mais "**précision typique ±2-3 mm, validée laser sur points clés**".
4. **Tester explicitement** sous mauvaise lumière (cave, contre-jour), qui dégradera σ.

## Fichiers générés

- `/tmp/escalier_poc_truth.dxf` → vérité terrain (escalier parfait) — ouvrir dans AutoCAD/BricsCAD
- `/tmp/escalier_poc.dxf` → relevé bruité (1 tirage) — pour visualiser l'écart à l'œil

*Rapport généré automatiquement par `precision_simulation.py`.*
