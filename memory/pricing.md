# 📊 Stratégie tarifaire MesureChâssis (validée 01/06/2026)

## Essai gratuit
- **Durée** : 3 mois (au lieu du modèle classique 14 jours)
- **Comportement** : Tout débloqué pendant 3 mois
- **Après expiration** : Blocage total tant qu'aucun paiement n'est effectué

## Plan Artisan Solo
- **Prix** : 24,99€/mois
- **Inclus** : 1 utilisateur (l'artisan lui-même)
- **Pas d'évolution** : Pour ajouter quelqu'un, bascule sur Entreprise

## Plan Entreprise Starter
- **Prix de base** : 54,99€/mois
- **Inclus** : 3 utilisateurs (commerciaux/techniciens en combinaisons libres)
- **Utilisateur supplémentaire** : +4,99€/mois/utilisateur

## Plan Entreprise Pro
- **Prix de base** : 84,99€/mois
- **Inclus** : 6 utilisateurs + fonctionnalités avancées (Bluetooth, etc.)
- **Utilisateur supplémentaire** : +9,99€/mois/utilisateur
- **Message UI** : « Cette option aura des fonctionnalités comme le Bluetooth et bien d'autres pour encore plus faciliter les prises de mesures »

## Implémentation Stripe (à venir Sprint 3)
- Trial period : 90 jours (`trial_period_days: 90`)
- Plans avec abonnement métré (per-user) sur Stripe Billing
