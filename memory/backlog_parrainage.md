# 💰 Programme de Parrainage MesureChâssis (Backlog Build 9)

**Date d'ajout** : 4 juin 2026
**Demandé par** : Michel Pezzuto
**Priorité** : 🟢 P1 (à coder après Build 8 et publication App Store)
**Référence** : Modèle Revolut (récompense cash 20-80€)

---

## 🎯 Concept retenu (selon Michel)

- 👤 L'utilisateur invite des amis via un lien personnel
- 💰 Si l'invité s'inscrit et utilise l'app : **20€ à 80€ cash** au parrain
- 🔁 Insistant, mis en avant dans l'UI (comme Revolut)

---

## 🛠️ Spécifications techniques à finaliser AVEC Michel

### Q1 — Montant exact
- [ ] 20€ ? 50€ ? 80€ ?
- [ ] Variable selon le plan (Free / Pro / Premium) ?
- [ ] Progressif (premier filleul = 20€, top parrain = 80€) ?

### Q2 — Conditions de déclenchement
- [ ] Filleul s'inscrit simplement
- [ ] Filleul abonné payant pendant X mois (recommandé : 3 mois)
- [ ] Filleul actif (X chantiers créés)

### Q3 — Mode de paiement
- [ ] **Virement bancaire** (Stripe Connect Transfers — TVA à gérer)
- [ ] **PayPal** (plus simple, frais 2%)
- [ ] **Crédit sur abonnement** (déduit de la prochaine facture)
- [ ] **Mix** : cash si dispo, sinon crédit

### Q4 — Cap / Limite
- [ ] Illimité
- [ ] Max X par mois (ex: 5)
- [ ] Plafond annuel (ex: 1000€)

### Q5 — Récompense filleul
- [ ] Rien
- [ ] Réduction sur 1er abonnement (-20%)
- [ ] 1 mois Pro gratuit
- [ ] 10€ crédit

---

## 🏗️ Architecture proposée (côté tech)

### Backend
```python
# Nouveau collection MongoDB : referrals
{
  "_id": ObjectId,
  "code": "MICHEL2026",  # généré unique par user
  "referrer_id": "user-uuid-michel",
  "created_at": datetime,
  "uses": [
    {
      "referred_user_id": "user-uuid-jean",
      "registered_at": datetime,
      "paid_at": datetime,
      "reward_amount": 50.00,
      "reward_status": "pending|paid|cancelled",
      "reward_method": "transfer|paypal|credit"
    }
  ]
}

# Endpoints
POST   /api/referrals/generate-code      # crée le code si pas existant
GET    /api/referrals/me                  # stats + uses
POST   /api/referrals/track/{code}       # appelé à l'inscription
GET    /api/referrals/leaderboard        # top parrains (mensuel)
POST   /api/admin/referrals/{id}/payout  # marquer payé (admin)
```

### Frontend
1. **Page "Mes parrainages"** dans le menu profil
   - Stats : 5 invités, 3 inscrits, 2 payants, 100€ gagnés
   - Liste détaillée avec dates et statuts
   - Bouton **"PARTAGER MON LIEN"** (WhatsApp/SMS/Email/Copier)
2. **Bannière promotionnelle** sur le dashboard (1ère semaine)
3. **Modal d'onboarding** : "Vous venez d'arriver ? Vous avez été parrainé ?" → champ code
4. **Notifications push/email**
   - Quand filleul s'inscrit
   - Quand récompense versée

---

## 📊 Métriques à suivre (côté analytics)

- Taux de partage du lien
- Taux de conversion filleul (clic → inscription)
- Taux de monétisation filleul (inscription → abonné payant)
- ROI marketing global : (revenus filleuls - récompenses) / récompenses
- CAC parrainage vs CAC publicité classique

---

## ⚖️ Aspects légaux à vérifier (BELGIQUE)

1. **TVA sur récompense cash** :
   - Si versée comme "remise commerciale" → pas de TVA (recommandé)
   - Si versée comme "rémunération" → TVA 21% + fiche fiscale
2. **RGPD** : 
   - Code parrainage = donnée personnelle indirecte ✅ OK
   - Email/téléphone du filleul invité = nécessite consentement
3. **Conditions générales** :
   - Ajouter clause "Programme de parrainage"
   - Limite anti-fraude (pas d'auto-parrainage, vérif IP/email)
4. **Lutte anti-blanchiment** :
   - Au-dessus de 100€/transaction → KYC requis
   - Bon de garder sous 100€

---

## 🎨 Design / UX inspiré de Revolut

### Page parrainage type :
```
┌────────────────────────────────────┐
│  💰 Gagnez jusqu'à 80€            │
│  en parrainant vos amis menuisiers │
│                                     │
│  ╔═══════════════════════════╗     │
│  ║  Votre code: MICHEL2026  ║     │
│  ║  [📋 COPIER LE LIEN]      ║     │
│  ╚═══════════════════════════╝     │
│                                     │
│  ⚡ Comment ça marche :             │
│  1. Partagez votre lien            │
│  2. Votre ami s'inscrit et paie    │
│  3. Vous recevez 50€ cash          │
│                                     │
│  📊 Vos stats :                    │
│  • 3 amis inscrits                 │
│  • 1 abonné payant                  │
│  • 50€ déjà gagnés ✅              │
│                                     │
│  [🚀 PARTAGER MAINTENANT]          │
└────────────────────────────────────┘
```

### Touchpoints stratégiques :
- ✅ Banner après 3ème chantier créé : "Vous adorez ? Faites-en profiter vos collègues !"
- ✅ Notification email à J+7 d'inscription
- ✅ Mention dans le footer du PDF généré : "Mesuré avec MesureChâssis — Invitez vos collègues : 80€ offerts"

---

## ⏱️ Estimation effort

| Tâche | Temps |
|---|---|
| Backend (collection + 5 endpoints) | 3h |
| Frontend (page parrainage + bannières) | 4h |
| Intégration Stripe Connect / PayPal | 4h |
| Tests E2E + sécurité anti-fraude | 2h |
| Aspects légaux (CGU + clauses) | 1h |
| **TOTAL** | **~14h** |

---

## 🚦 Pré-requis avant de coder

1. ✅ Apple a accepté Build 7 et il est publié
2. ✅ Build 8 livré avec workflow RBAC complet
3. ✅ Décisions Michel sur Q1-Q5 ci-dessus
4. ✅ Choix du fournisseur de paiement (Stripe Connect Transfers recommandé — déjà intégré pour les abonnements)

---

## 💬 Notes Michel

- Insistance forte : "**Insister auprès des utilisateurs**" pour qu'ils parrainent (comme Revolut)
- Modèle de récompense : **20-80€ cash** (pas mois gratuits)
- Inspiration : Revolut, Wise

---

## 🔮 Évolutions futures (V2 du parrainage)

- 🏆 Système de niveaux : Bronze (1-5) / Argent (6-20) / Or (21+) avec récompenses progressives
- 🎁 Bonus exceptionnels (mois spécifiques : "Septembre menuisiers : 100€/parrainage")
- 🤝 Programme corporate : parrainage entreprise complète (montants plus élevés, ex. 200€ pour entreprise 5+ salariés)
- 📣 Top parrains affichés publiquement (gamification)
