# 📅 Reprise demain — Google Play + iOS (2 juin 2026 soir)

## ✅ Accomplissements de cette session (soir)

### Google Play Store — État ACTUEL
- ✅ Build v24 récupéré sur EAS (Android Play Store build, version 1.0.0 (24), finished)
- ✅ Identifié que v22 est en Test Interne, v24 sur EAS jamais uploadé
- ✅ Promu v22 vers "Tests fermés - testeur mesurechassis" 
- ✅ Notes de version remplies (texte marketing complet)
- ✅ 9 pays/régions ajoutés (Belgique, France, Cameroun + 6 autres)
- ✅ Type de compte confirmé : **Compte PERSONNEL** (ID: 8830659857655625785)

### Stripe (debug en pause)
- ✅ Backend Railway online et stable
- ❌ Webhook Stripe 400 "Signature invalide" — debug en pause, BETA_MODE=True compense
- 🔑 Secret webhook a été rotaté plusieurs fois sans succès — soupçon : proxy Railway modifie body

## 🟡 Ce qui reste à faire DEMAIN

### Google Play — Reprise rapide (~20 min)
1. **Créer liste de 5 testeurs Gmail** (minimum pour démarrer)
   - User a déjà commencé à réfléchir à sa liste
   - 5 c'est suffisant pour LANCER la review Google
   - On ajoutera 7+ autres testeurs pendant les 14 jours
2. Sur Play Console → Tests fermés → Testeurs → "Créer une liste d'emails"
3. Confirmer la release (Prévisualiser et confirmer)
4. **Envoyer pour examen** → Google review 1-3 jours
5. Vérifier le souci "Désynchroniser de la production" (probablement bénin)

### Apple App Store — Démarrer (~2-3 heures)
1. Installer Node.js sur PC (installer .exe, 5 min)
2. Activer PowerShell pour exécuter scripts : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
3. Cloner le projet sur le PC : `git clone <url-repo>`
4. Lancer `npx eas login` puis `npx eas build --platform ios --profile production`
5. Pendant que ça build (~30 min) : créer la fiche App Store Connect
6. Une fois build OK : upload sur TestFlight via EAS submit
7. Review Apple (1-7 jours)

## ⚠️ Important pour la reprise

### Limitation Google compte PERSONNEL
- 12 testeurs actifs minimum
- 14 jours minimum en Tests Fermés
- AVANT de pouvoir publier en Production
- Pendant ces 14 jours, on peut ajouter des testeurs au fur et à mesure
- App accessible aux testeurs via lien d'opt-in Play Store

### Comptes développeur
- Google Play : Compte Personnel "MesureChâssis", ID 8830659857655625785
- Apple Developer : Activé (user a confirmé "1A")

### Bundle / Package
- Android : `com.mesurechassis.escalier`
- iOS : `com.mesurechassis.escalier`

## 💬 Notes user

- User: non-développeur, guidé pas-à-pas via interfaces graphiques
- A travaillé toute la journée le 2 juin 2026 (soir)
- Très patient mais fatigué en fin de journée
- A dit "ok on reprend demain mais peut-être que j'aurai d'autres questions"
- → Être disponible pour répondre à des questions diverses (techniques OU marketing OU flyer OU etc.) avant de continuer la publication

## 🎯 Plan recommandé pour demain matin

1. Saluer + demander comment il va
2. Rappeler le récap : on doit juste créer la liste de 5 testeurs Gmail + envoyer à Google
3. Répondre à ses questions éventuelles
4. Continuer Google Play (étape 1-5 ci-dessus)
5. Une fois Google en review → attaquer iOS

## 📦 Fichiers mémoire à relire

- /app/memory/next_session_stores.md (plan publication global)
- /app/memory/stripe_webhook_status.md (debug Stripe en pause)
- /app/memory/test_credentials.md (info@mesurechassis.com / admin1234 sur Railway prod)
- /app/memory/pricing.md (grille tarifaire 24,99/54,99/84,99€)
- Ce fichier (state à la reprise demain)
