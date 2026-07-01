# 📧 Stratégie Campagne Email — Post-Apple Approval

**Statut** : ⏸️ EN ATTENTE — À exécuter dès que Apple approuve MesureChâssis (Build 110+)

**Créé le** : 01/07/2026  
**Décision utilisateur** : Ne PAS envoyer 500 emails d'un coup → warm-up progressif

---

## ⚠️ POURQUOI PAS 500 EMAILS D'UN COUP

1. **Réputation domaine détruite** — Gmail/Orange/Free bloquent les pics anormaux (30 → 500 = spam auto)
2. **Resend gratuit limité à 100/jour** — passer à Resend Pro (20€/mois, 50k emails) au bon moment
3. **Risque RGPD/CNIL** — amende jusqu'à 4% du CA
4. **Conversion catastrophique** — cold email en masse : 0.5-1% vs cold email progressif : 5-15%

---

## ✅ STRATÉGIE "WARM-UP PROGRESSIF"

| Semaine | Volume/jour | Cumul | Objectif |
|---------|-------------|-------|----------|
| Sem. 1-2 | 30/j (actuel) | 300 | Warm-up réputation |
| Sem. 3-4 | 50/j | 700 | Confirmer réputation |
| Sem. 5-6 | 100/j | 2 000 | Croissance saine |
| Sem. 7+ | 150-200/j | 5 000+/mois | Rythme croisière |

**Résultat estimé sur 1 mois de croisière** : 4 500 emails → ~600 ouvertures → ~120 clics → **30-60 inscriptions payantes**

---

## 🚀 ACTIONS À FAIRE AU LANCEMENT (post-Apple)

### Phase 1 — Setup technique (jour 1)
1. ⚙️ Passer `DAILY_LIMIT` de 30 → 50 dans `/app/backend/routes/campaign.py`
2. 📧 **Configurer SPF/DKIM/DMARC** sur `mesurechassis.com` (impératif pour délivrabilité)
3. 💳 Upgrader **Resend gratuit → Resend Pro** (20€/mois, 50 000 emails)
4. 🔍 Vérifier reverse DNS + warm-up score sur mail-tester.com

### Phase 2 — Dashboard analytics (semaine 1)
5. 📊 Ajouter tracking Resend :
   - Taux d'ouverture par jour/semaine/région
   - Taux de clic sur le lien app
   - Taux de conversion en inscriptions payantes
   - Bounces / plaintes SPAM (alerter si >2%)
6. 🎯 Endpoint `/admin/campagne/analytics` avec graphiques

### Phase 3 — Scaling progressif (semaine 2-8)
7. 📈 Augmenter progressivement `DAILY_LIMIT` : 50 → 100 → 150
8. 🎯 **Segmentation** : d'abord France, puis Belgique, puis Luxembourg
9. 🔄 **A/B testing** : 2 versions de sujet, garder le meilleur
10. 📆 **Relance intelligente** : ceux qui ouvrent mais ne cliquent pas → relance J+7 personnalisée

### Phase 4 — Croissance long terme
11. 💡 Multi sous-domaines emails (`hello@`, `contact@`, `pro@`) pour scaler sans risque
12. 🎬 **Landing page dédiée** avec vidéo TikTok #1 pour convertir les cliqueurs
13. 🔗 **Programme parrainage** : chaque client existant peut inviter 3 collègues (déjà en place)

---

## 📊 KPIs À SURVEILLER

| Métrique | Seuil OK | Seuil ALERTE |
|----------|----------|--------------|
| Taux d'ouverture | >20% | <10% |
| Taux de clic | >2% | <0.5% |
| Taux de bounce | <2% | >5% |
| Plaintes SPAM | <0.1% | >0.5% |
| Désinscriptions | <2% | >5% |

**Si SPAM >0.5%** → PAUSE immédiate, warm-up sur nouveau sous-domaine.

---

## 🛠️ FICHIERS À MODIFIER

- `/app/backend/routes/campaign.py` — `DAILY_LIMIT`, `PAUSE_BETWEEN_SENDS_S`
- `/app/backend/email_service.py` — templates + tracking pixel
- `/app/frontend/app/admin/campagne.tsx` — dashboard analytics
- `/app/frontend/app/admin/analytics.tsx` — NEW (graphiques campagne)

---

**⏸️ NE RIEN LANCER TANT QUE APPLE N'A PAS VALIDÉ BUILD 110+**
