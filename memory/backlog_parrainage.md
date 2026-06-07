# 💎 Programme de Parrainage MesureChâssis — Build 9

**Date** : 4 juin 2026
**Demandé par** : Michel Pezzuto
**Modèle retenu** : **Option B — Mois Pro gratuits** (mise à jour 4 juin soir)
**Inspiration** : Revolut (insistance UI), Notion/Slack (modèle mois gratuits)

---

## 🎯 PRINCIPE FINAL

```
👤 Michel parraine son ami menuisier (lien personnel ou code)
     ↓
👨‍🔧 L'ami s'inscrit + utilise l'app
     ↓
🎁 Michel reçoit X mois Pro gratuits
🎁 L'ami reçoit Y mois Pro gratuits (bienvenue)
```

**Avantages du modèle "mois gratuits"** :
- 🟢 Aucune complexité de paiement (pas de Stripe Connect, pas de TVA, pas de KYC)
- 🟢 Augmente la rétention (les utilisateurs restent plus longtemps)
- 🟢 Modèle "tested & proven" : Notion, Slack, Dropbox
- 🟢 Dev rapide : 2-3 jours
- 🟢 Pas de risque légal/comptable

---

## 🛠️ Spécs à finaliser AVEC Michel (avant code)

### Q1 — Récompenses
- **Suggestion** : 
  - Parrain reçoit **1 mois Pro gratuit** par filleul actif
  - Filleul reçoit **1 mois Pro gratuit** à l'inscription (bienvenue)
- À confirmer

### Q2 — Condition pour débloquer la récompense parrain
- **A)** À l'inscription du filleul (risqué, fraude possible)
- **B)** Après 1ère semaine d'utilisation active (recommandé)
- **C)** Après 1er abonnement payant du filleul (le plus sûr)

### Q3 — Plafond
- Illimité ? Max X/mois ?
- **Suggestion** : illimité avec antifraude (1 compte par IP/email)

### Q4 — Top parrains
- Afficher leaderboard ? Récompenses bonus pour le top 3 ?

---

## 🏗️ Architecture technique (MVP simple)

### Backend
```python
# Champs ajoutés à la collection users
{
  "referral_code": "MICHEL2026",      # unique, généré à l'inscription
  "referred_by": "JEAN2026",          # code du parrain (si applicable)
  "referral_credits_months": 3,        # mois gratuits accumulés
  "referral_uses": [                   # filleuls amenés
    {
      "user_id": "uuid-filleul",
      "registered_at": datetime,
      "activated_at": datetime,        # 1ère semaine d'usage
      "reward_granted": true,
      "reward_amount_months": 1
    }
  ]
}

# Endpoints
GET    /api/referrals/me            # mon code + mes stats
POST   /api/auth/register           # accepte ?referral_code= en body
POST   /api/referrals/redeem-credits # appliquer les crédits à l'abonnement
```

### Frontend
1. **Section "Parrainage" dans Profil** :
   - Affichage code unique + bouton COPIER
   - Bouton PARTAGER (WhatsApp, SMS, Email)
   - Stats : X invités, Y actifs, Z mois gratuits gagnés
2. **Champ "Code parrain (optionnel)" à l'inscription**
3. **Bannière dashboard** : "🎁 1 mois Pro offert pour chaque ami parrainé !"
4. **Notification email** au parrain quand récompense créditée

### Stripe (extension simple)
- Quand le parrain a X mois de crédit accumulé → on retarde la prochaine facturation de X mois
- Pas de transfert d'argent réel, juste modification de la `subscription.trial_end` ou skip facturations

---

## 🎨 UX inspirée de Revolut (insistance)

### Touchpoints (où mettre en avant)
1. **Bannière dashboard** après 3ème chantier créé
2. **Card dédiée** dans la page profil
3. **Modal popup** : 1 fois après 7 jours d'utilisation
4. **Footer PDF** : "📄 Mesuré avec MesureChâssis — Invitez vos collègues, 1 mois Pro offert"
5. **Email** à J+14 d'inscription : "Vous aimez l'app ? Faites-en profiter vos collègues"

### Design pattern
```
┌────────────────────────────────────────┐
│  🎁 PARRAINAGE MESURECHÂSSIS          │
│                                          │
│  Offrez 1 mois Pro à vos collègues     │
│  et gagnez 1 mois Pro pour vous !       │
│                                          │
│  ╔═══════════════════════════════╗     │
│  ║  Votre code : MICHEL2026     ║     │
│  ║  [📋 COPIER]  [🚀 PARTAGER] ║     │
│  ╚═══════════════════════════════╝     │
│                                          │
│  📊 Vos résultats                       │
│  • 3 collègues invités                  │
│  • 2 actifs sur l'app                   │
│  • 2 mois Pro gagnés ✅                 │
│                                          │
└────────────────────────────────────────┘
```

---

## ⏱️ Estimation effort

| Tâche | Temps |
|---|---|
| Backend (champs + 3 endpoints) | 2h |
| Frontend (page profil + bannières + share) | 3h |
| Intégration Stripe (crédit subscription) | 2h |
| Tests E2E + antifraude basique | 1h |
| **TOTAL** | **~8h** |

---

## 🚦 Pré-requis avant code

1. ✅ Apple a accepté Build 7
2. ✅ Build 8 livré (workflow RBAC + 14 formes + FAQ)
3. ✅ Décisions Michel sur Q1-Q4
4. ✅ Stripe webhook réparé OU validation manuelle des crédits

---

## 💬 Notes Michel

- **4 juin matin** : Initialement parlait de cash 20-80€
- **4 juin soir** : Confirme préférer **Option B (mois gratuits Pro)** — plus simple, plus malin
- Style **Revolut** : insistant, mis en avant dans l'UI
