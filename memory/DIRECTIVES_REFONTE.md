# Directives Refonte Globale — MesureChâssis

> Source : Cahier des charges utilisateur du **09 juin 2026**.
> Statut : **Base de travail pour TOUT le développement futur**.
> Ces directives priment sur toute spécification antérieure.

---

## 1. LOGIQUE MÉTIER & SAISIE DES FORMES

### 1.1 Arc (Plein cintre / Arc surbaissé)
- **Cotes** : `Largeur totale` + `Hauteur droite` (gauche = droite par défaut).
- **Vérification** : Calculer et afficher **uniquement la longueur de l'arc**
  (la partie courbe — PAS le périmètre total).
- **Champ saisissable** "Vérification de l'arc" : valeur calculée vs valeur
  réelle mesurée au ruban, avec indicateur ✓/✗ (tolérance ±1 % ou ±15 mm).

### 1.2 Angle / Pan coupé
- **Saisie** : choix du pan coupé — `droite`, `gauche`, ou `les deux`.
- **Cotes** : longueur des arêtes, **angle (135° par défaut, éditable)**,
  largeur totale, hauteurs asymétriques (`Hg` et `Hd` indépendantes).
- **Pas de vérification périmètre** sur cette forme.

### 1.3 Polygone (NOUVEAU GROUPE — refonte majeure)
- **Entrée unique nommée "Polygone"** qui remplace
  `Triangle`, `Pentagone`, `Hexagone`, `Octogone`.
- Sélecteur du **nombre d'arêtes** : 3 / 5 / 6 / 8.
- **Cotes** : longueur de chaque arête, angle de chaque sommet
  (135° ou 120° par défaut selon le nombre d'arêtes, **éditables**),
  hauteur et largeur hors-tout.

### 1.4 Ovale
- **Simplification maximale** : `Largeur totale` + `Hauteur totale` uniquement.

### 1.5 Bow-window
- Conserver la logique actuelle pour le moment (revue après tests utilisateurs).

### 1.6 Carré / Rectangle
- Conserver la logique actuelle (diagonales).

---

## 2. REFONTE UI — PAGE CHANTIER & LISTE D'OUVERTURES

### 2.1 Densité & compacité
- Adopter une **liste compacte** : blocs plus petits → **doubler** le nombre
  d'ouvertures visibles à l'écran sans scroll.
- Densité doit être respectée **aussi bien sur iPhone que sur tablette**.

### 2.2 Visualisation
- Remplacer les **icônes génériques** par :
  - le **schéma simplifié** de la forme (via `ShapeIcon` / `ShapeSchemaV2`)
  - OU la **photo** prise sur site (si disponible) — fallback : schéma.

### 2.3 Navigation
- **Clic sur l'image = accès direct au détail** de l'ouverture (pas de menu intermédiaire).

### 2.4 Actions
- Supprimer les **boutons textuels lourds** (`MODIFIER`, `SUPPRIMER`).
- Intégrer une **icône Corbeille discrète** pour la suppression.
- La modification est intégrée au bloc (clic ouvre détail → bouton Modifier inside).

### 2.5 Bouton d'ajout
- Rendre le bouton **"Ajouter une ouverture"** plus discret pour libérer
  l'espace (FAB en bas à droite ou bouton compact en haut de liste).

---

## 3. COMPATIBILITÉ & RESPONSIVE — MULTI-SUPPORTS

### 3.1 Cibles
- **iPhone**, **iPad/tablette**, **Android phones**, **Android tablets**.

### 3.2 Adaptabilité
- L'affichage doit **s'ajuster automatiquement** selon la largeur.
- **Tablette** : exploiter la largeur → grille 2-3 colonnes, plus d'infos visibles.
- **Mobile** : compacité, manipulation au **pouce**.

### 3.3 Uniformité
- Les **interactions** (clic, suppression, modification) doivent être
  **identiques** quel que soit l'appareil.

### 3.4 Touch targets
- Maintenir au minimum **44 pt iOS / 48 pt Android** pour tous les boutons,
  malgré la compacité demandée.

### 3.5 Performance
- L'app doit rester **rapide et légère** :
  - éviter les re-renders inutiles (`useMemo`, `React.memo`)
  - éviter les listes non virtualisées (`FlashList`)
  - graceful degradation sur connexion mobile instable (cache local, retry).

---

## 4. PLAN D'EXÉCUTION (PHASES)

### ✅ Phase 1 — Arc + Angle (en cours)
- Bascule périmètre total → **longueur de l'arc** sur plein cintre + arc surbaissé.
- Confirmation que l'angle/pan coupé répond déjà à 1.2 (fait précédemment).
- **Retirer** la vérification périmètre de l'angle 90°.

### Phase 2 — Polygone unifié
- Créer la forme `polygone` avec sélecteur d'arêtes (3/5/6/8).
- Migrer Triangle/Pentagone/Hexagone/Octogone vers cette entrée.
- Cotes : longueurs arêtes + angles sommets éditables + L/H hors-tout.

### Phase 3 — Simplification Ovale
- Réduire à `L + H` seulement.

### Phase 4 — Refonte UI page chantier
- Liste compacte (densité × 2).
- Miniatures schéma SVG ou photo.
- Clic = détail direct.
- Icône Corbeille + actions discrètes.
- Bouton "Ajouter" en FAB compact.

### Phase 5 — Responsive multi-supports
- Breakpoints tablette/desktop : grille 2-3 colonnes.
- Profil pouce mobile maintenu (44 pt min).
- FlashList sur les listes longues.
- Memoization stratégique.

---

## ⚠️ Règles d'or
1. **Pas de régression** : ne jamais casser une fonctionnalité existante.
2. **Test E2E systématique** : validation Playwright après chaque phase.
3. **Communication FR** : tous les libellés, textes, helpers en français.
4. **RBAC respecté** : artisan solo / commercial / technicien / admin / super admin.
5. **iOS App Store** : pas d'allusion à Stripe ni "Premium" sur la version iOS.
