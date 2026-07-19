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

## 🎯 Comment reprendre

Quand Michel revient de sa tournée :
1. Michel partage les observations brutes
2. On analyse ensemble les blocages récurrents
3. On choisit A / B / C (ou combo)
4. On code selon la spec de l'approche retenue
5. Test avec les mêmes 5 menuisiers (validation avant/après)
