# 🚀 MesureChâssis — Déploiement Freemium v1.1 (26 juillet 2026)

## 📦 Ce qui a été fait dans ce release

### 🎯 Backend — Nouveau modèle payant complet

**8 fichiers modifiés/créés :**

| Fichier | Rôle |
|---|---|
| `backend/.env` | +2 Price IDs Stripe (Artisan Pro 19€, Entreprise Pro 69€) |
| `backend/db.py` | Nouvelles constantes limites Freemium + BETA_MODE togglable via env |
| `backend/routes/stripe_routes.py` | Trial 90j→14j, alias plans artisan_pro/entreprise_pro |
| `backend/routes/chantiers.py` | Paywall CHANTIERS (max 3 en gratuit) |
| `backend/routes/mesures.py` | Paywall OUVERTURES (max 5 en gratuit) |
| `backend/routes/yann.py` | Paywall YANN (max 10 questions/mois en gratuit) |
| `backend/routes/spec_import.py` | Paywall IA CDC IMPORT (max 3/mois en gratuit) |
| `backend/routes/limits.py` (**NOUVEAU**) | Module central de vérification des limites |
| `backend/routes/trial_expiration.py` (**NOUVEAU**) | Auto-downgrade lazy à J+14 |
| `backend/routes/pricing_migration.py` (**NOUVEAU**) | Endpoints admin migration + emails users |

**3 nouveaux endpoints API :**

- `GET /api/limits/status` — Compteurs Freemium temps réel (chantiers, ouvertures, Yann, IA CDC)
- `GET /api/trial/status` — Jours/heures restants de trial
- `POST /api/admin/pricing-migration/mark-grandfathered` — Protéger users historiques
- `POST /api/admin/pricing-migration/send-warning-emails` — Envoyer email personnalisé aux users

### 🌐 Site web

- `www/index.html` mis à jour :
  - Bandeau top : "🎁 Gratuit jusqu'octobre" → "⭐ 14 jours d'essai gratuit"
  - Section tarifs refondue :
    - Suppression du plan "Entreprise Gratuit à vie"
    - Artisan Gratuit : nouvelles limites (3 chantiers, 5 ouvertures, Yann 10/mois, IA 3/mois)
    - Entreprise Pro : 59€ → **69€**
    - Entreprise MAX : 249€ → **299€** avec badge "Bientôt" (pas encore codé)

### 🍎 App Store submission

- 7 captures d'écran 1290×2796 prêtes (ID Michel flouté)
- Vidéo App Preview 15.9s conforme Apple
- Description v1.1 + What's New + Notes pour reviewer rédigés

---

## ⚡ ORDRE DE DÉPLOIEMENT (à suivre STRICTEMENT)

### 🟢 Étape 1 — Backend (Railway) — SAFE, aucun impact user

1. Puller le code sur Railway (auto-deploy via git ou manuel)
2. **NE PAS TOUCHER** `BETA_MODE` dans les variables Railway pour l'instant
3. Vérifier que le backend démarre sans erreur (logs Railway)
4. Vérifier avec `curl` que les endpoints répondent :
   ```
   curl https://capable-gratitude-production-db51.up.railway.app/api/limits/status → 401 attendu
   curl https://capable-gratitude-production-db51.up.railway.app/api/trial/status → 401 attendu
   ```
   
✅ À ce stade, **rien n'a changé pour vos users** — ils gardent l'accès Pro illimité (BETA_MODE=true).

### 🟡 Étape 2 — Site web (FTP)

1. Uploader `mesurechassis-diff-20260726b.zip` → juste `index.html` à remplacer
2. Vérifier sur mesurechassis.com que :
   - Bandeau haut affiche "14 jours d'essai"
   - Section tarifs affiche 4 plans (Artisan Gratuit / Artisan Pro / Entreprise Pro 69€ / Entreprise MAX "Bientôt")

### 🟠 Étape 3 — App Store submission (Apple)

1. Build & submit nouvelle version 1.1 avec :
   - Les 7 captures d'écran fournies
   - La vidéo App Preview
   - La description mise à jour
   - Le "What's New"
   - Les notes reviewer (voir `APPSTORE-v1.1-description.md`)

2. Attendre l'approbation Apple (2-7 jours)

### 🔴 Étape 4 — DÉCISION FINALE (le jour J)

Le jour où votre app v1.1 est publiée sur l'App Store :

#### 4a. Marquer users historiques (si vous voulez les protéger)
```bash
# Test d'abord en dry-run
curl -X POST https://capable-gratitude-production-db51.up.railway.app/api/admin/pricing-migration/mark-grandfathered \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"only_active_users": true, "dry_run": true}'

# Puis pour de vrai
curl -X POST ... -d '{"only_active_users": true, "dry_run": false}'
```

**Note** : Vous aviez dit "vire les tous, pas de grandfathering". Si vous confirmez, sautez cette étape.

#### 4b. Envoyer email personnalisé à tous les users
```bash
# Dry-run d'abord (voir combien seront concernés)
curl -X POST https://capable-gratitude-production-db51.up.railway.app/api/admin/pricing-migration/send-warning-emails \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "limit": 5}'

# Puis envoi pour de vrai (attention, prend quelques minutes)
curl -X POST ... -d '{"dry_run": false}'
```

#### 4c. ⚡ ACTIVER le mode payant (le point de non-retour)
Dans Railway → Settings → Variables :
```
BETA_MODE=false
```
Puis restart backend Railway.

À partir de ce moment :
- ✅ Les nouveaux inscrits ont 14 jours d'essai Artisan Pro
- ✅ Après J+14 sans paiement → bascule Artisan Gratuit limité
- ✅ Les limites (3 chantiers, 5 ouvertures, 10 Yann/mois, 3 IA/mois) s'appliquent

### 🟣 Étape 5 — Lancement Google Ads

Le lendemain de l'activation du mode payant, vous lancez Google Ads Belgique 5€/jour (kit fourni dans `googleads-kit-mesurechassis.html`).

---

## 🔧 Comment tester en local que tout marche bien AVANT prod

```bash
# 1. Créer un user test
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test2026!","first_name":"Test","last_name":"User"}'

# 2. Récupérer le token
# 3. En mode BETA_MODE=true → tout est illimité (rien ne change)
# 4. Ajouter BETA_MODE=false dans .env → restart → refaire les tests
#    → À partir du 4ème chantier créé, HTTP 402 avec code "free_limit_reached"
```

---

## 🎯 Résumé exécutif — Ce que vous devez faire concrètement

| # | Action | Difficulté | Temps |
|---|---|---|---|
| 1 | Push code backend sur Railway | ⭐ | 5 min |
| 2 | Upload index.html sur FTP hébergeur | ⭐⭐ | 10 min |
| 3 | Soumettre app v1.1 à Apple avec assets fournis | ⭐⭐⭐ | 30 min |
| 4 | Attendre approbation Apple | 😴 | 2-7 jours |
| 5 | Envoyer warning emails via endpoint | ⭐⭐ | 5 min |
| 6 | Basculer `BETA_MODE=false` sur Railway | ⭐ | 2 min |
| 7 | Lancer Google Ads (dès activation compte) | ⭐⭐ | 30 min |

**Total : ~1h30 de travail réel + 2-7 jours d'attente Apple.**

---

## 📞 Questions fréquentes

**Q : Et si un user paye pendant l'essai et annule ensuite ?**
→ Il bascule automatiquement en Artisan Gratuit limité à la fin de sa période payée. Stripe gère.

**Q : Combien de temps l'app reste-t-elle "gratuite illimitée" après la MAJ ?**
→ Zéro seconde. Le jour où `BETA_MODE=false`, les limites s'appliquent immédiatement.

**Q : Que se passe-t-il si un user avait 5 chantiers avant la MAJ ?**
→ Il garde ses 5 chantiers. Mais il ne pourra pas en créer un 6e tant qu'il n'archive pas ou ne paye pas.

**Q : Le compteur "5 ouvertures max" est-il par chantier ou global ?**
→ Global (cumulé sur tous les chantiers actifs). C'est ce qui est le plus juste économiquement.

---

Bon déploiement ! 🚀
