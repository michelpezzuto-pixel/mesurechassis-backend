# 🔧 Workflow Chantier — Wall Config OPTIONNELLE

**Créé le** : 04/07/2026  
**Demandé par** : Utilisateur (Yann)

---

## 🎯 EXIGENCE — Rendre le wall_config totalement OPTIONNEL

### 🚨 Situation actuelle (à modifier)

Aujourd'hui dans `frontend/app/chantier/[id]/new-mesure.tsx` :
- Créer une **ouverture** oblige à passer par l'étape 1 "Wall Config" 
  (masonry_type, épaisseur bloc, insulation_mode…)
- `masonry_type` est **required** — bloque le passage à l'étape suivante
- Si le `wall_config` du chantier existe déjà, on saute l'étape 1 (bien)
- **Mais la 1ère mesure oblige toujours à saisir ces infos**

### ✅ Workflow souhaité par l'utilisateur

**Étape 1 — Créer un chantier manuellement**
- Nom client, adresse, éventuellement téléphone/email
- Aucune obligation de saisir épaisseur murs / type maçonnerie
- Chantier créé en une étape rapide

**Étape 2 — Depuis la fiche chantier, choix libre**
Le mesureur voit 2 boutons de même niveau, **aucun n'est prérequis de l'autre** :
- 🪟 **"Ajouter une ouverture"** → peut créer directement sans avoir saisi wall_config
- 🧱 **"Renseigner les dimensions des murs"** → peut le faire à tout moment (avant, pendant, après les ouvertures)

**Étape 3 — Wall config OPTIONNELLE**
- Si l'utilisateur ne saisit **jamais** le wall_config → OK, l'app fonctionne quand même
- Les mesures d'ouverture restent cohérentes (les feuillures sont juste des champs libres si pas de masonry_type)
- Sur le PDF d'export : section "Dimensions des murs" affichée seulement si renseignée

**Étape 4 — Scan CDC auto-remplit si présent**
Quand l'utilisateur importe un CDC (fonction IA existante) :
- Si le CDC mentionne les **dimensions des murs** → wall_config auto-rempli
- Si le CDC mentionne les **coordonnées client** (adresse, téléphone, email) → auto-rempli
- Champs pré-remplis sont **modifiables** (l'utilisateur peut corriger avant validation)

---

## 🛠️ CHANGEMENTS TECHNIQUES REQUIS

### Backend (`backend/models.py` + routes)
- `Chantier.wall_config` : déjà Optional ✓
- Ajouter endpoint `PATCH /api/chantiers/{id}/wall-config` (dédié) pour update indépendante
- Mettre à jour prompt IA du scan CDC pour extraire :
  - `wall_config.masonry_type`, `wall_config.gros_oeuvre_mm`, `wall_config.insulation_mode`
  - `client_phone`, `client_email` (en plus de l'adresse déjà extraite)

### Frontend

**`frontend/app/chantier/[id]/new-mesure.tsx`** :
- Retirer l'étape 1 "Wall Config" comme obligatoire pour créer une ouverture
- Rendre `masonry_type` **optionnel** dans la validation
- Si non renseigné → utiliser des valeurs par défaut génériques dans le wizard
  (ex: pas de feuillures affichées, saisie libre)
- Bouton "Renseigner les murs (optionnel)" visible mais non-bloquant

**`frontend/app/chantier/[id]/index.tsx`** (page détails chantier) :
- Afficher **2 boutons de même niveau visuel** :
  - "🪟 Ajouter une ouverture" (primary)
  - "🧱 Dimensions des murs" (secondary, badge "optionnel" si vide)
- Retirer la logique `showEditWall = canEditMesures && !!chantier?.wall_config?.masonry_type`
  → afficher **toujours** le bouton wall config (que ce soit "Renseigner" ou "Modifier")

**`frontend/app/chantier/[id]/pdf-preview.tsx`** :
- Afficher la section "Murs" **uniquement si** wall_config est significatif
- Sinon : cacher proprement la section (déjà en place ✓)

**Nouvel écran : `frontend/app/chantier/[id]/wall-config.tsx`**
- Écran dédié wall config (indépendant du wizard new-mesure)
- Formulaire : masonry_type, gros_oeuvre_mm, insulation_mode, iti/ite thickness
- Bouton "Enregistrer" (pas de bloquant)
- Bouton "Ignorer pour l'instant"

### Import CDC (IA)

**`backend/routes/import_spec.py` (ou équivalent)** :
- Enrichir le prompt IA pour détecter :
  - Épaisseurs de murs (ex: "cloison 20cm brique + isolation 12cm laine minérale")
  - Type de maçonnerie (brique, béton, parpaing, bois, métal…)
  - Type d'isolation (ITI, ITE, aucune)
  - Coordonnées client complètes (nom, adresse, code postal, ville, téléphone, email)
- Retourner un JSON avec :
```json
{
  "client": {
    "name": "M. Dupont",
    "address": "12 rue de la Paix, 75001 Paris",
    "phone": "+33 6 12 34 56 78",
    "email": "dupont@example.com"
  },
  "wall_config": {
    "masonry_type": "brique",
    "gros_oeuvre_mm": 200,
    "insulation_mode": "iti",
    "iti_thickness_mm": 120
  },
  "ouvertures": [...]
}
```

---

## 📌 PRIORITÉ

**P1 — Post-Apple validation** (améliore l'UX de manière significative pour les nouveaux utilisateurs = clé pour l'onboarding).

### Sprint dédié : "Wall Config Optionnelle + CDC Auto-fill"
- 1j : Backend endpoint PATCH wall-config + prompt IA enrichi
- 1j : Frontend refactor new-mesure (masonry_type optionnel)
- 1j : Frontend nouvel écran wall-config dédié
- 1j : Frontend page détails chantier (nouveaux boutons, layout)
- 1j : Tests + refinement + i18n

**Total** : 5 jours de dev.

---

## 🎨 BÉNÉFICE UX

**Avant** : L'utilisateur DOIT saisir des infos techniques (maçonnerie) avant de pouvoir prendre sa première mesure → friction élevée.

**Après** : L'utilisateur crée un chantier en 30 sec, prend ses mesures d'ouverture immédiatement, et complète le wall_config plus tard (ou jamais si pas utile pour son cas).

**Impact business** : ↑ taux d'onboarding, ↓ abandon dès la première mesure.

---

**⏸️ NE PAS COMMENCER TANT QUE APPLE N'A PAS VALIDÉ BUILD 113**
