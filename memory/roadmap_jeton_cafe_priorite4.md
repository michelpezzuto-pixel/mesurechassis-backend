# ☕ Système « Jeton Café » — Dossier technique (PRIORITÉ 4)

**Spécifié par** : Michel (08/07/2026)
**Statut** : À DÉVELOPPER en dernier (après P1 Service Pro, P2 CDC, P3 Onboarding).

## Concept
Levier d'acquisition terrain + fidélisation des artisans, via les stations-service partenaires.

## Fonctionnement détaillé
1. **Déclencheur (QR Code de campagne)**
   - Activé UNIQUEMENT pour les utilisateurs ayant installé l'app via un QR code spécifique
     déployé chez les stations partenaires (pancartes physiques).
   - À l'inscription, ce "tag" campagne est lié au compte (ex: `campaign_tag: "station-XYZ"`).
   - Les comptes SANS ce tag ne voient jamais la fonctionnalité.

2. **Processus (création d'ouverture)**
   - Quand un artisan crée une "ouverture" (fenêtre/porte), une pop-up s'affiche :
     « Vous avez gagné un café ! » → génère un jeton (statut: gagné/non consommé).

3. **Rôle du « Pompiste »**
   - L'artisan se rend à la station et présente son écran au pompiste.
   - Le pompiste appuie sur un bouton de validation dédié (dans l'interface artisan ou
     une interface pompiste dédiée) → le jeton est "consommé".
   - Sécurité à prévoir : éviter l'auto-validation par l'artisan (code pompiste, PIN station,
     ou interface pompiste séparée).

4. **Gestion & Relance**
   - Comptage des jetons validés en temps réel.
   - Automatisation : si utilisateur inactif OU objectifs de jetons non atteints 10 jours avant
     la fin du mois → relance ciblée (« Nouveau projet, nouvelle pause ! ») pour inciter à créer
     une nouvelle ouverture et repasser à la station.

## Notes techniques (à préciser au moment du dev)
- Modèle `Jeton` : `id`, `user_id`, `company_id`, `ouverture_id`, `status` (gagné/consommé),
  `earned_at`, `consumed_at`, `station_id`, `validated_by`.
- Champ compte : `campaign_tag` (renseigné à l'inscription via deep-link/QR).
- Endpoint validation pompiste : sécurisé (PIN station ou rôle pompiste).
- Écran/section "Mes cafés" côté artisan + interface validation pompiste.
- Relances : réutiliser l'infra emails Resend + logique de scheduling (comme campagne).
- ⚠️ iOS : "gagner un café" est une récompense marketing, pas un achat → OK Apple tant
  qu'aucun prix/paiement n'est affiché. À valider au moment du dev.
- Lié à l'idée "2 mois gratuits" pour les comptes issus de la campagne pompe à essence.

## Questions ouvertes à trancher au moment du dev
- Interface pompiste : dans l'app artisan (bouton + code) ou app/web séparée ?
- 1 café par ouverture ? plafond par jour/semaine ?
- Que se passe-t-il à l'expiration du jeton (validité) ?
- Lien exact entre "jeton café" et "2 mois gratuits" (le café est-il un cadeau physique
  à la station, ou débloque-t-il du temps d'abonnement gratuit ?).
