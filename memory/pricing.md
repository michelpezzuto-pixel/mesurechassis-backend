# Tarification MesureChâssis (pour intégration Stripe future)

> Communiqué par l'utilisateur le 24/05/2026. Ces tarifs s'appliqueront
> quand la BETA Gratuite sera levée et que Stripe sera intégré.

## Plans

### 🧑‍🔧 Artisan (compte solo)
- 1 utilisateur unique (PAS d'équipe — pas d'écran Équipe visible)
- Tous les accès activés (mesures + chantiers + exports)
- Pas de gestion d'équipe
- **Prix : 24,99 €/mois TTC**

### 🏢 Entreprise
- Compte Admin + équipe
- **Forfait de base : 54,99 €/mois** — inclut :
  - 1 Admin
  - 1 Technicien
  - 1 Commercial
- **Utilisateurs supplémentaires : +4,99 €/utilisateur/mois**
  (technicien OU commercial OU admin additionnel)

## Calcul exemple
| Configuration | Tarif mensuel |
|---|---|
| Artisan solo | à confirmer |
| Entreprise base (3 users) | 54,99 € |
| Entreprise + 2 techs supp. (5 users) | 54,99 + 2 × 4,99 = **64,97 €** |
| Entreprise + 5 users supp. (8 users) | 54,99 + 5 × 4,99 = **79,94 €** |

## Notes implémentation Stripe
- Créer 2 produits Stripe : `mc_artisan` et `mc_entreprise_base`
- Pour les sièges additionnels, utiliser un produit `mc_entreprise_seat` avec
  `metered billing` ou `quantity` updates côté Subscription Item.
- Backend doit recalculer `quantity` à chaque ajout/suppression d'utilisateur
  via webhook ou call direct à Stripe Subscriptions API.
