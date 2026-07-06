# 🤖 Roadmap Play Store — 12 testeurs Samsung (À FAIRE LE MOMENT VENU)

## Contexte (07/2026 — demande utilisateur)
Google Play exige 12 testeurs pendant 14 jours (test fermé) avant la publication publique.
Michel veut recruter 12 artisans avec Samsung et les récompenser.

## Engagements pris envers l'utilisateur
1. **Aucune perte de données** : les chantiers des testeurs sont côté serveur (MongoDB prod).
   Le passage test fermé → Play Store public est transparent (mêmes comptes/identifiants).
2. **Gratuité à vie pour les 12 testeurs** : à implémenter quand la facturation sera activée
   (fin du BETA_MODE) → ajouter un flag société `lifetime_free: true` (ou statut
   `subscription_status: "offered"`) qui bypass le paywall dans deps.py::is_subscription_blocked.
   ~5 min de dev. Prévoir aussi un petit écran/commande admin pour marquer une société "offerte".
3. Argument de recrutement : « Testez 14 jours, gardez tous vos chantiers, gratuit à vie pour vous ».

## Outils déjà en place
- Page publique `devenir-testeur.tsx` (collecte des candidatures).
- Outil admin « Testeurs » (`/admin/testers`, web only, réservé PLATFORM_OWNER_EMAILS)
  pour copier les emails vers la Play Console.

## Checklist le jour J (mise sur Play Store)
- [ ] Générer le build Android via le bouton Publish d'Emergent.
- [ ] Créer le test fermé dans la Play Console + ajouter les 12 emails testeurs.
- [ ] 14 jours de test avec 12 testeurs actifs (opt-in).
- [ ] Demander la production dans la Play Console.
- [ ] Marquer les 12 sociétés testeurs en `lifetime_free` (à implémenter à ce moment-là).
