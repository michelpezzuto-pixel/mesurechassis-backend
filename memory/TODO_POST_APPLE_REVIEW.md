# 🔴 TODO POST-APPLE REVIEW — MesureChâssis

**Date** : Juin 2026
**Statut** : En attente de validation Apple Build 102

## Contexte
Pour la soumission Apple Review, tout le contenu commercial / B2B / prix
a été masqué sur iOS. Une fois la validation obtenue, il faudra basculer
sur le modèle commercial réel et **refaire tous les contenus marketing**.

## Checklist de bascule (à exécuter dès qu'Apple a validé)

### 1. Backend
- [ ] Mettre `BETA_MODE = False` dans `/app/backend/db.py`
- [ ] Activer la **clé Stripe en mode LIVE** (remplacer `sk_test_...` par `sk_live_...` dans `.env`)
- [ ] Vérifier que les paywall des features (Yann, Import CDC, Exports Pro) fonctionnent en conditions réelles
- [ ] Désactiver le compte démo `applereview@mesurechassis.com` (ou le laisser comme compte test interne)

### 2. Frontend iOS
- [ ] Réactiver l'inscription Entreprise/Équipe sur iOS dans `/app/frontend/app/index.tsx`
  → Retirer le `Platform.OS === 'ios'` qui masque le bloc "Compte Entreprise"
- [ ] Réafficher la grille tarifaire dans `/app/frontend/app/subscription.tsx` sur iOS
  (si Apple l'autorise via leur Reader App Rule OU via in-app purchases)
- [ ] Vérifier qu'aucune mention "Apple Review" ne reste dans les commentaires/copy

### 3. Campagne emailing (`/app/backend/routes/campaign.py`)
- [ ] Refondre **les 3 templates** :
  - `BODY_TEMPLATE` (premier contact)
  - `RELANCE_TEMPLATE` (J+3)
  - `RELANCE_2_TEMPLATE` (J+7)
- [ ] Intégrer les nouveaux arguments :
  - "Disponible sur App Store + Google Play" (avec logos)
  - Nouveau positionnement commercial (plus "gratuit jusqu'au 30 sept")
  - Tarifs visibles
  - Témoignages clients si dispo
- [ ] Garder la **feature scan bordereau** comme accroche principale (très puissante)
- [ ] Modifier les **sujets** pour annoncer la sortie officielle

### 4. Site vitrine
- [ ] Mettre à jour `/app/site_mesurechassis_final/` :
  - Bannière "Disponible sur App Store ✨"
  - Liens deeplinks vers les stores (App Store + Play Store)
  - Retirer les mentions beta
  - Mettre les vrais tarifs

### 5. Dashboard admin
- [ ] Vérifier que les stats reflètent le nouveau modèle (acquisitions payantes)
- [ ] Possiblement ajouter une section "Conversions Trial → Pro"

### 6. Communication
- [ ] **Annonce LinkedIn** de sortie officielle
- [ ] **Email à tous les beta testeurs** pour les remercier + leur offrir un avantage (1 mois gratuit ?)
- [ ] **Post de blog / vidéo** célébrant la sortie

## Notes importantes pour le prochain agent

⚠️ **Ne JAMAIS basculer ces changements avant validation Apple confirmée**. Si on remet
les prix/B2B trop tôt, le Build sera re-rejeté.

⚠️ **L'historique des rejets Apple est sensible** : 2 rejets précédents (3.1.1, 3.1.3c, 2.2).
La 3ème tentative DOIT passer — sinon Apple peut suspendre le compte développeur.

⚠️ Garder en parallèle le site web et Android **comme issue de secours** au cas où Apple
ne valide jamais (peu probable mais à anticiper).
