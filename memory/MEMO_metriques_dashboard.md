# 📊 Mémo Michel — Voir ses métriques MesureChâssis en autonomie

**Créé le** : 15 juillet 2026

---

## 👥 Voir les inscrits (base MesureChâssis)

### 🗺️ Carte géographique (le plus visuel)
```
https://TON-BACKEND-RAILWAY.up.railway.app/api/admin/map?token=TON_PLATFORM_ADMIN_TOKEN
```

Filtres via URL :
- `&days=7` : derniers 7 jours
- `&only_active=true` : uniquement comptes actifs

### 📊 Données brutes JSON
```
https://TON-BACKEND-RAILWAY.up.railway.app/api/admin/map/data?token=TON_PLATFORM_ADMIN_TOKEN
```

Retourne :
- `total` : nombre total d'inscrits
- `by_country` : répartition par pays
- `by_region` : répartition par région
- `points` : liste complète

### 🗄️ MongoDB Atlas (source de vérité)
1. https://cloud.mongodb.com
2. Login avec identifiants Atlas
3. Database → Browse Collections → **users**
4. Filtres pratiques :
   - Google users : `{"google_linked": true}`
   - Cette semaine : `{"created_at": {"$gte": "2026-07-08"}}`
5. MongoDB Charts pour dashboards graphiques

### 🔑 Où trouver PLATFORM_ADMIN_TOKEN ?
Railway → projet MesureChâssis → onglet **Variables** → `PLATFORM_ADMIN_TOKEN`

---

## 🍎 App Store Connect (téléchargements Apple)

### Accès
1. https://appstoreconnect.apple.com
2. Login avec Apple ID développeur
3. **Analyses** (barre gauche) → sélectionner MesureChâssis

### KPI clés
| Métrique | Onglet | Signification |
|---|---|---|
| **Impressions** | Aperçu | Ont vu la fiche App Store |
| **Vues page produit** | Aperçu | Ont cliqué sur la fiche |
| **Téléchargements** | Aperçu / Acquisition | Ont installé l'app ✅ |
| **Sessions** | Utilisation | Ouvertures de l'app |

### ⚠️ Délai
Chiffres mis à jour avec **24-48h de latence**. Ne pas paniquer J+1 après une pub.

### 📱 App iPhone officielle
Cherche "**App Store Connect**" dans l'App Store — appli Apple gratuite pour checker les stats depuis le mobile.

---

## 💳 Stripe (paiements)

- https://dashboard.stripe.com
- Onglets utiles :
  - **Paiements** : revenus détaillés
  - **Abonnements** : liste des clients actifs et churn
  - **Analyses** : MRR, taux de conversion, churn rate

---

## 🎯 Tableau récap "où regarder ?"

| Question | Outil |
|---|---|
| Combien ont téléchargé l'app ? | 🍎 App Store Connect |
| Combien se sont inscrits ? | 🗺️ Carte admin ou MongoDB |
| Combien ont payé ? | 💳 Stripe |
| Combien ouvrent l'app ? | 🍎 App Store Connect (Sessions) |
| Où sont-ils géographiquement ? | 🗺️ Carte admin |
| Google vs email/password ? | 🗄️ MongoDB `{"google_linked": true}` |

---

## 📈 Ratios business à surveiller

- **Downloads → Inscriptions** : idéal > 40 %. En dessous = onboarding à améliorer
- **Inscriptions → Payants** : idéal > 5-10 % en SaaS B2B
- **Churn mensuel** : Stripe → Analyses → Retention

---

## 🆘 Si l'URL ne marche pas

- Vérifier que Railway est bien "Deployed" (pas "Building")
- Vérifier le token dans Railway → Variables
- Le token contient des caractères spéciaux → ne pas l'encoder URL
