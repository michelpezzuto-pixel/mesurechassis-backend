# ⭐ Rating Prompt — Guide d'activation

Statut : **PRÊT** mais **DÉSACTIVÉ** (feature flag OFF).
Objectif : demander un avis 5 étoiles App Store au moment le plus favorable
= juste après validation d'un café Jeton (pic de dopamine utilisateur).

---

## 📁 Fichiers concernés

- **`/app/frontend/src/services/ratingPrompt.ts`** — logique (feature flag,
  throttling, appel StoreKit).
- **`/app/frontend/src/components/RatingPromptModal.tsx`** — modale custom
  française avec copywriting Michel.
- **`/app/frontend/src/components/CafeJetonModal.tsx`** — déclencheur
  intégré dans l'étape `"success"` après validation PIN pompiste.

---

## 🚦 Comment activer (au lancement de la campagne Jeton Café)

### Option A — Activation permanente (recommandée pour le lancement)

Dans `/app/frontend/src/services/ratingPrompt.ts`, ligne ~28 :

```ts
const RATING_PROMPT_ENABLED_DEFAULT = false;
                                    // ^ passer à `true`
```

Puis **rebuild + soumettre à Apple** (nouveau build iOS obligatoire, car
c'est du code frontend).

### Option B — Activation via variable d'env (utile pour QA/beta)

Sans re-toucher au code, ajouter dans `/app/frontend/.env` :

```env
EXPO_PUBLIC_RATING_PROMPT_ENABLED=true
```

Idéal pour tester sur un build TestFlight avant de basculer la production.

---

## 🛡️ Garde-fous automatiques (déjà en place)

- ✅ **iOS uniquement** — Android sera ajouté quand la version Play arrivera.
- ✅ **Max 1 prompt par 90 jours** par appareil (via `AsyncStorage`).
- ✅ **Si "Pas maintenant" cliqué** → skip pendant 30 jours.
- ✅ **Si utilisateur a déjà noté** → plus jamais reproposé.
- ✅ **StoreKit disponibilité** vérifiée avant affichage.

---

## 🧪 Reset pour tests QA

En dev, appeler la fonction utilitaire dans une console React Native :

```ts
import { _resetRatingPromptState } from "@/src/services/ratingPrompt";
await _resetRatingPromptState();
```

---

## 📊 Copywriting utilisé

- **Titre** : « Un café, une note ? »
- **Corps** : « Content de votre café ? Si MesureChâssis vous aide au
  quotidien sur vos chantiers, un petit avis 5 étoiles nous aide énormément
  à continuer le développement. »
- **Signature** : « Merci, confrère ! ☕ »
- **Bouton principal** : `LAISSER 5 ÉTOILES` (déclenche StoreKit natif)
- **Bouton secondaire** : `Pas maintenant`

---

## ⚠️ Rappel Apple StoreKit

- Apple limite à **3 prompts natifs par utilisateur par an** (toutes apps
  confondues).
- Notre modale custom NE consomme PAS ces 3 prompts (elle ne fait que
  précéder StoreKit → économise le quota Apple si l'utilisateur refuse).
- Impossible de savoir si l'utilisateur a réellement laissé une note
  (Apple ne fournit pas cette info par design privé).
