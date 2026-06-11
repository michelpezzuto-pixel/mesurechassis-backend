# 💳 Bascule Stripe TEST → LIVE (préparé, EN ATTENTE DU FEU VERT CLIENT)

**Statut** : ⏸️ PRÉPARÉ — ne rien basculer sans validation explicite de Michel.

## État actuel (11 juin 2026)
- Backend Railway : `STRIPE_SECRET_KEY=sk_test_…` (mode TEST → bandeau "Environnement de test" sur le checkout)
- `BETA_MODE=True` dans `/app/backend/db.py` → tous les comptes sont en plan `pro` actif gratuit, paywall désactivé
- Les apps iOS/Android ne montrent AUCUN flux d'achat (conformité stores) → la bascule LIVE ne concerne que le **web**

## Variables d'environnement à remplacer sur Railway (backend)
| Variable | Valeur actuelle | Valeur LIVE à fournir |
|---|---|---|
| `STRIPE_SECRET_KEY` | sk_test_… | `sk_live_…` |
| `STRIPE_PRICE_SOLO` | price test | price LIVE (Artisan 24,99 €/mois) |
| `STRIPE_PRICE_ENTREPRISE_BASE` | price test | price LIVE (Entreprise 54,99 ou 59,99 €/mois — ⚠️ harmoniser, voir note) |
| `STRIPE_PRICE_ENTREPRISE_EXTRA` | price test | price LIVE (+4,99 €/utilisateur) |
| `STRIPE_PRICE_PRO_BASE` | price test | price LIVE (Pro 84,99 ou 89,99 €/mois — ⚠️ harmoniser) |
| `STRIPE_PRICE_PRO_EXTRA` | price test | price LIVE (+9,99 €/utilisateur) |
| `STRIPE_WEBHOOK_SECRET` | whsec test | `whsec_…` LIVE |

## Étapes (dans l'ordre, le jour J)
1. **Stripe Dashboard → mode Live** : créer les produits/prix identiques au mode test (abonnements mensuels EUR, essai 90 jours si souhaité)
2. **Webhook Live** : Developers → Webhooks → Add endpoint
   - URL : `https://capable-gratitude-production-db51.up.railway.app/api/stripe/webhook`
   - Événements : les mêmes que le webhook test (checkout.session.completed, customer.subscription.updated/deleted, invoice.payment_failed…) — voir `/app/memory/stripe_webhook_status.md`
   - Récupérer le `whsec_…`
3. **Railway** : remplacer les 7 variables ci-dessus → redéploiement automatique
4. **Test fumée** : un checkout réel à 1 € OU un coupon 100% → vérifier le passage `subscription_status=active` en DB
5. **Décision séparée** : passage `BETA_MODE=False` (fin de l'offre de lancement gratuite) — à décider indépendamment de la clé LIVE

## ⚠️ Incohérences de prix repérées dans l'UI (à harmoniser avant la commercialisation)
- subscription.tsx (web) : Entreprise **54,99 €** / Pro **84,99 €**
- company-profile.tsx + team.tsx + index.tsx (web) : Entreprise **59,99 €** / Pro **89,99 €**
→ Choisir le prix officiel et harmoniser (5 min de travail, me demander).
