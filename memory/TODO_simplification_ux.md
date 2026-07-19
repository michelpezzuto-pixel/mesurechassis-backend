# 🎯 TODO — Simplification UX / Mode Découverte

**Status** : SPEC en attente — à décider APRÈS la tournée terrain de Michel
**Priorité** : À définir en fonction des retours terrain
**Date création** : 15 juillet 2026
**Contexte** : Michel a peur que l'app soit perçue comme "usine à gaz" par les
menuisiers. Doute très pertinent (Curse of Knowledge du fondateur).

---

## 🎯 Objectif

Réduire la friction de la première utilisation pour maximiser la conversion
Download → Première mesure valide. Objectif : **90 secondes** pour qu'un
menuisier lambda ait sa première mesure exportée en PDF.

---

## 📋 Prérequis absolu — Tournée terrain d'abord

**AVANT toute implémentation**, Michel doit :
1. Aller voir **5 menuisiers** minimum
2. Les faire installer l'app **devant lui**
3. **Observer en silence** (ne pas guider)
4. Chronométrer combien de temps jusqu'à la 1re mesure valide
5. Noter les blocages, les mots exacts, les questions posées

Cette data va **déterminer** quelle approche implémenter (voir A/B/C ci-dessous).

---

## 🅰️ Approche recommandée — Mode Découverte progressif

### Concept
Un flag `user.experience_level` qui détermine la richesse de l'UI :
- `discovery` (par défaut au signup)
- `regular` (auto-upgrade après 3 chantiers)
- `power_user` (auto-upgrade après 10 chantiers OU clic manuel "Mode Pro")

### Ce qui est visible en mode `discovery`
✅ **Écran d'accueil épuré** :
- Un gros bouton central "**+ Nouveau chantier**"
- Liste "Mes chantiers" (0-3 items max avant CTA)
- Bouton "?" en haut à droite pour l'aide/support

✅ **Wizard nouveau chantier simplifié** :
- Étape 1 : Nom client + Adresse (2 champs)
- Étape 2 : Type de baie (limité à 3 : Rectangle, Trapèze, Cintré)
- Étape 3 : Prise des mesures (formulaire minimal)
- Étape 4 : Export PDF (bouton unique, gros, orange)

❌ **Caché en mode discovery** (accessible via menu "..." ou débloqué plus tard) :
- Import IA cahier des charges
- Formes complexes (9 autres formes)
- Rôles multiples (admin/commercial/technicien)
- Export XLSX / JSON
- Jeton Café (sauf si campagne active)
- Dashboard admin stats
- Multi-plans (Freemium/Standard/Team/Pro)

### Auto-upgrade
```typescript
// Backend : après création chantier
if (chantiers_lifetime_count == 3 && user.experience_level == "discovery") {
  user.experience_level = "regular"
  // Notification in-app : "🎉 Nouvelles fonctionnalités débloquées !"
}
```

### Effort
- Backend : ~1h (champ `experience_level`, endpoints update)
- Frontend : ~3-4h (conditionnels UI, animation de déblocage)
- Tests : ~1h

**Total ~5-6h**

---

## 🅱️ Approche complémentaire — Onboarding vidéo

### Concept
Au 1er lancement de l'app :
1. Une vidéo verticale (60-90s) qui montre le workflow complet
2. Ensuite, overlay tooltips sur les 3 premiers clics :
   - "👆 Touche ici pour ton premier chantier"
   - "👆 Choisis la forme de la baie"
   - "👆 Prends ta première mesure"
3. Bouton "Passer" toujours visible

### Contenu vidéo
- Format vertical 9:16 (compatible iPhone)
- Style : screen recording avec voix-off IA (ElevenLabs)
- Storyboard :
  - 0-5s : Logo + "Voici comment ça marche"
  - 5-20s : Créer un chantier (screencast)
  - 20-50s : Prendre une mesure (screencast + zoom)
  - 50-75s : Export PDF (résultat)
  - 75-90s : CTA "À toi de jouer 🚀"

### Effort
- Tournage vidéo : ~1h (CapCut + ElevenLabs)
- Frontend : ~1h (composant `FirstLaunchTutorial.tsx` + AsyncStorage flag)

**Total ~2h**

---

## 🅲️ Approche checklist "Live Coach"

### Concept
Panneau flottant en bas d'écran (dismissable) :
```
┌────────────────────────────────────┐
│  🎯 Prise en main  (2/5)     [X]   │
│  ✅ Créer un compte                │
│  ✅ Créer ton 1er chantier         │
│  ⬜ Prendre ta 1re mesure          │
│  ⬜ Exporter en PDF                │
│  ⬜ Inviter ton équipe (optionnel) │
└────────────────────────────────────┘
```
- Se coche automatiquement à chaque action
- Disparaît une fois 100 % complet
- Peut être ré-affiché depuis les paramètres

### Effort ~5h

---

## 🚦 Décision finale à prendre APRÈS la tournée

Selon ce que Michel constate sur le terrain :

| Constat terrain | Approche recommandée |
|---|---|
| 5/5 galèrent au 1er lancement | 🅰️ + 🅱️ (combo puissant) |
| 3-4/5 galèrent | 🅰️ Mode Découverte seul |
| 2/5 galèrent, sur des points précis | Ajustements ciblés (cacher juste 2-3 features) |
| 0-1/5 galère | Aucune modif — l'app est déjà bien |

---

## 📊 Métriques à mesurer avant/après

Une fois implémenté :
- **Time to First Value (TTFV)** : temps entre signup et 1re mesure exportée
- **Objectif** : < 90 secondes en mode `discovery`
- **Taux d'activation** : % users qui font au moins 1 chantier dans les 7 jours
- **Objectif** : > 60 %

À tracker dans `db.users` :
- `first_chantier_at`
- `first_mesure_at`
- `first_pdf_export_at`

---

## 📝 Checklist tournée terrain (à imprimer/emmener)

- [ ] Installer l'app devant le menuisier
- [ ] Chrono : temps entre install et 1re mesure valide
- [ ] Noter les mots exacts prononcés
- [ ] Noter les endroits où il hésite / clique au mauvais endroit
- [ ] Noter les features qu'il cherche et ne trouve pas
- [ ] Photographier son atelier (contexte)
- [ ] Demander son âge et son niveau tech (1-5)
- [ ] Demander : "Sur 10, tu recommandes à combien de collègues ?"
- [ ] Demander : "Tu paierais combien / mois pour l'utiliser ?"

À faire pour 5 menuisiers = ~3h terrain total (30 min par visite).

---

## 🆕 Idée Michel du 15/07/2026 — Métaphore "Calculatrice iOS"

Michel a eu l'intuition brillante d'utiliser le mental model de la
calculatrice iOS (Simple vs Scientifique) pour structurer l'app.

### Concept
- **Mode Simple** = gratuit, UI épurée, 5 chantiers à vie/mois, 3 formes,
  scan IA limité, PDF simple
- **Mode Scientifique** = payant, toutes les features débloquées, UI riche
- Bascule visuelle via toggle en haut à droite du dashboard
- Analogie universelle (tout le monde connaît la calc iOS)

### Pourquoi c'est puissant
- Résout la peur "usine à gaz" (Simple par défaut = zéro intimidation)
- Monétisation limpide (Scientifique = ce que tu paies pour)
- Mental model gravé dans l'inconscient Apple (aucune éducation à faire)

### Questions à valider en tournée
1. **Scan IA en gratuit ?** — Compromis : 1 scan gratuit à vie ("wow moment")
   puis paywall. Stratégie éprouvée (Notion AI, Grammarly).
2. **5 chantiers à vie vs /mois ?** — À vie = paywall en 2 semaines
   (frustration ?). Par mois = plus fair mais moins d'urgence upgrade.

### Ce que ça remplacerait
Actuellement 4 plans : Freemium / Standard (24.99€) / Team (59.99€) / Pro.
Avec cette nouvelle structure :
- Mode Simple = Freemium
- Mode Scientifique = Standard/Team/Pro (fusion en 1 UI, différenciation
  par capacités : mono-user vs équipe vs multi-sites)

### Implémentation technique (spéculative, à confirmer)
- Flag `user.ui_mode`: `simple` | `scientific`
- Par défaut : `simple` au signup
- Toggle switch en header du dashboard
- Si Scientific + plan free → paywall modal
- Mapping features → mode :
  - `simple`: rectangle, trapèze, cintré, PDF, scan IA (1x)
  - `scientific`: tout

### Combinaison recommandée avec les 3 approches ci-dessus
- Le **Mode Simple** intègre le concept d'**Approche A** (Discovery)
- L'**onboarding vidéo** (Approche B) reste utile pour expliquer le toggle
- La **checklist Live Coach** (Approche C) peut être conservée pour le mode
  Simple uniquement

---

## 🎯 Comment reprendre

Quand Michel revient de sa tournée :
1. Michel partage les observations brutes
2. On analyse ensemble les blocages récurrents
3. On teste l'accueil de la métaphore Simple/Scientifique auprès des menuisiers
   (question à poser : "Tu utiliserais l'app en mode Simple ou Scientifique ?")
4. On choisit A / B / C / D (métaphore calculatrice) ou combo
5. On code selon la spec retenue
6. Test avec les mêmes 5 menuisiers (validation avant/après)
