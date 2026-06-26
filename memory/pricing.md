# 📊 Stratégie tarifaire MesureChâssis (mise à jour 26/06/2026)

> ⚠️ Paiement géré via le **site web** (comme Shopify), **PAS via Apple In-App Purchase** — pour respecter les guidelines Apple Store et éviter la commission 30%.

## Essai gratuit
- **Durée** : **14 jours** (sur tous les plans payants : Solo, Entreprise, Entreprise Pro)
- **Plan Gratuit** : pas de limitation de temps, juste les 5 formes de base à vie
- **Comportement** : Tout débloqué pendant 14 jours
- **Après expiration** : Bascule en plan Gratuit si pas de paiement (ou blocage selon décision Stripe)

## Plan Gratuit
- **Prix** : 0 €
- **Inclus** : 1 utilisateur, 5 formes de menuiseries de base, mesures manuelles, export PDF basique
- **Yann** : ❌ Non inclus — option à **+5 €/mois**

## Plan Artisan Solo
- **Prix** : **19 €/mois HT**
- **Inclus** : 1 utilisateur, formes illimitées, import CDC IA, export PDF/Excel/CNC
- **Yann** : ✅ Illimité **inclus dans le prix**
- **Bluetooth** : ❌ Non disponible (réservé Entreprise Pro)

## Plan Entreprise
- **Prix de base** : **59 €/mois HT**
- **Inclus** : 3 utilisateurs, tout le plan Solo, rôles & permissions, dashboard équipe, support prioritaire
- **Utilisateur supplémentaire** : **+5 €/mois/utilisateur**
- **Yann** : ✅ Illimité **inclus dans le prix**
- **Bluetooth** : ❌ Non disponible (réservé Entreprise Pro)

## Plan Entreprise Pro
- **Prix** : **249 €/mois HT**
- **Inclus** : **Utilisateurs illimités**, tout le plan Entreprise
- **Yann** : ✅ Illimité **inclus**
- **Bluetooth** : ✅ **Mètre laser Bluetooth inclus**
- **Tout est inclus** : tous les exports avancés, tous les imports, toutes les formes
- **Branding personnalisé + SSO + Account manager dédié**
- **"…et bien d'autres fonctions arrivent prochainement"**

## Récap option Yann
| Plan | Yann inclus ? | Coût Yann |
|------|---------------|-----------|
| Gratuit (0 €) | ❌ Non | +5 €/mois option |
| Solo (19 €) | ✅ Oui | 0 € (inclus) |
| Entreprise (59 €) | ✅ Oui | 0 € (inclus) |
| Entreprise Pro (249 €) | ✅ Oui (illimité) | 0 € (inclus) |

## Implémentation Stripe (À FAIRE après validation Apple Build 107)
- ⏸️ **Ne pas modifier Stripe maintenant** — attendre la validation Apple
- Mettre à jour `TRIAL_PERIOD_DAYS = 14` dans `stripe_routes.py` (actuellement 90)
- Mettre à jour les `STRIPE_PRICE_*` avec les nouveaux montants (19/59/249 €)
- Ajouter le price "Yann option" à +5 €/mois (pour plan Gratuit uniquement)
- Ajouter le price "user supplémentaire Entreprise" à +5 €/mois/u

## Historique des changements
- 01/06/2026 : Première version (Solo 24,99€ / Entreprise 54,99€ / Pro 84,99€ / Trial 90 jours)
- **26/06/2026** : Refonte tarifaire après refus Apple → Solo 19€ / Entreprise 59€ / Pro 249€ / Trial 14 jours / Paiement via site web (modèle Shopify)
