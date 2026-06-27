# Protocole de test physique — Markers ArUco

> Objectif : valider la **manipulation terrain** des markers avant tout dev mobile.
> Effort : ~1 heure d'impression + collage + photos. Aucun code requis.

## 📥 Fichiers à utiliser

| Fichier | Quand |
|---------|-------|
| `markers/markers_A4_50mm.pdf` | **À imprimer en priorité** — planche A4 des 12 markers ArUco 4x4_50, IDs 0–11, taille 50 mm |
| `markers/svg/ArUco_XX.svg` | Markers individuels vectoriels (si besoin d'imprimer en différentes tailles) |
| `markers/png/ArUco_XX.png` | Markers individuels bitmap 300 DPI |

---

## 🖨️ Étape 1 — Impression (10 min)

1. Ouvrir **`markers_A4_50mm.pdf`** sur votre PC
2. Imprimer sur **papier mat blanc** (jamais brillant, jamais glacé)
3. **CRITIQUE** dans le dialogue d'impression :
   - Mise à l'échelle : **100% / Taille réelle** (jamais "Adapter à la page")
   - Qualité : Haute / 600 DPI minimum
   - Recto seul, noir & blanc
4. Vérifier avec un pied à coulisse ou un mètre : le **repère 50 mm** en haut de page doit mesurer **exactement 50.0 mm** ±0.5 mm

> Si le repère n'est pas pile à 50 mm, refaire l'impression avec le bon réglage.
> Toute déviation à ce stade fausse TOUS les tests de précision suivants.

---

## ✂️ Étape 2 — Préparation des markers (15 min)

1. **Découper** chaque marker au cutter ou massicot, **à 2 mm à l'extérieur des cellules noires** (garder une marge blanche)
2. **Coller** sur un support rigide :
   - Option simple : **carton plume 3 mm** (chez Cultura, ~5 €)
   - Option durable : **PVC expansé 2 mm** (chez Castorama / Brico, ~8 €)
   - Option premium : **carton-mousse aluminisé blanc** (Foamboard, atelier d'encadrement)
3. **Redécouper** le support à 5 mm autour du marker
4. **Numéroter** au feutre fin au dos : "00", "01", … "11"

---

## 📐 Étape 3 — Test "à l'œil nu" (15 min)

But : valider que les markers sont **lisibles** avant tout dev. Pas de coordonnées, juste oui/non.

1. Allez à votre escalier de test
2. Posez 6 markers à 6 endroits clés :
   - 2 sur les coins du nez de la 1ère marche
   - 2 sur les coins du nez de la marche du milieu
   - 2 sur les coins du nez de la dernière marche
3. Reculez à **1.5 m** de l'escalier
4. **Filmez en vidéo** (iPhone caméra normale) pendant 30 sec en balayant lentement
5. **Photographiez** sous 4 angles différents :
   - De face
   - De biais 30°
   - De biais 60°
   - En contre-plongée (depuis le bas)

---

## 🔍 Étape 4 — Vérification "détection théorique"

**Méthode rapide sans code** :

1. Importez vos photos sur cette page : <https://chev.me/arucogen/>
   *(le générateur a aussi un détecteur, mais le plus simple est ci-dessous)*
2. Ou installez l'app gratuite **ArUco Marker Detector** sur iPhone/Android (chercher dans App Store)
3. Pointez l'app vers vos photos affichées sur écran PC, ou directement vers les markers physiques
4. **Critère de validation** : tous les markers doivent être détectés à 1.5 m sans flash.

**Si certains markers ne sont pas détectés** :
- Reflet sur le papier → matifier avec un coup de spray mat
- Coin abîmé → réimprimer
- Distance trop grande → tester à 1 m au lieu de 1.5 m

---

## 📝 Étape 5 — Restitution (5 min)

Remplissez ce tableau :

| Test | OK / KO | Note |
|------|---------|------|
| Repère 50 mm vérifié au pied à coulisse | _____ | |
| 12 markers découpés et collés | _____ | |
| Détection à 1.5 m face | _____ / 6 | _____ / 6 markers détectés |
| Détection à 1.5 m biais 30° | _____ / 6 | |
| Détection à 1.5 m biais 60° | _____ / 6 | |
| Détection contre-plongée | _____ / 6 | |
| Lisibilité en lumière naturelle | _____ | (de 1 à 5) |
| Lisibilité au flash | _____ | (de 1 à 5) |
| Praticité de pose sur arête | _____ | (de 1 à 5) |
| Tenue mécanique en manipulation | _____ | (de 1 à 5) |

---

## 🎯 Décisions à prendre après ce test

| Si | Alors |
|----|-------|
| ≥ 80% détection toutes conditions | ✅ ArUco 4x4_50 50mm validé → enchaîner dev mobile natif |
| 50–80% détection | 🟠 Passer en **AprilTag** ou **augmenter taille à 60 mm** |
| < 50% détection | 🔴 Revoir support / éclairage / impression avant de continuer |
| Manipulation pénible sur arête | 🟠 Concevoir clips d'arête 3D dès la V1 |

---

## ⏭️ Si test ArUco concluant

Vous pouvez tout de suite générer aussi la **série C AprilTag 50 mm** pour comparer.
Le script `generate_markers.py` peut être étendu (commande à me demander) — ou
utilisez directement <https://tools.limelightvision.io/apriltag-generator>.

## ⏭️ Si test ArUco peu concluant

Avant d'abandonner ArUco, tester :
1. Taille 60 mm (au lieu de 50)
2. Marker **5×5_100** (plus de bits, plus robuste) au lieu de 4×4_50
3. Impression sur sticker mat plutôt que papier collé

---

*Protocole créé pour valider physiquement avant tout investissement code.*
