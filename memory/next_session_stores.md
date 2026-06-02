# 🎯 Prochaine session — Publication App Store + Play Store

## 📅 Objectif principal
Rendre l'application MesureChâssis **publiquement accessible** sur :
- 🍎 **App Store** (Apple) — actuellement RIEN n'est en place
- 🤖 **Play Store** (Google) — actuellement v22 en Test Interne uniquement

## 📋 État actuel des stores

### Google Play Store
- ✅ Compte Play Console créé
- ✅ Fiche complétée (textes, screenshots, feature graphic 1024x500)
- ✅ Build v22 en **"Test Interne"** (accès restreint)
- ✅ Build v24 généré sur EAS (avec workflow Artisan + page Me + Stripe)
- 🟡 À FAIRE : passer de "Test Interne" → "Test Fermé" → "Test Ouvert" → "Production"
- 🟡 À FAIRE : potentiellement uploader le .aab v24 (ou v25 selon les changements récents)

### Apple App Store
- ❌ **RIEN n'est commencé** côté Apple
- ❌ Compte Apple Developer Program à activer ($99/an)
- ❌ App Store Connect à configurer
- ❌ Build iOS jamais généré sur EAS (bloqué par disponibilité user PC pour eas-cli)
- ❌ TestFlight à configurer
- ❌ Fiche App Store à créer (textes, screenshots iPhone)

## 🛣️ Marche à suivre proposée (à valider avec user à la reprise)

### Phase A — Google Play Store (PRIORITÉ 1, le plus rapide)
1. Vérifier l'état du build v24/v25 sur EAS
2. Décider si on génère un v25 (si modifs frontend récentes) ou si v24 suffit
3. Uploader le .aab sur Play Console
4. Passer de "Test Interne" → "Test Fermé" (avec liste de testeurs)
5. Puis → "Test Ouvert" (public mais flag "beta")
6. Puis → "Production" (publication officielle)
7. ⚠️ Délais Google : 1-7 jours de review entre chaque étape

### Phase B — Apple App Store (PRIORITÉ 2, plus complexe)
1. ⚠️ Pré-requis user : compte Apple Developer Program actif (99€/an)
2. ⚠️ Pré-requis user : disponibilité PC pour installer `eas-cli` (commande terminal)
3. Configurer EAS pour build iOS (clés Apple, certificats)
4. Générer un premier build iOS sur EAS
5. Créer la fiche App Store Connect (textes, screenshots iPhone)
6. Soumettre via TestFlight → review Apple (1-3 jours)
7. Une fois TestFlight OK → soumission App Store officielle (review 1-7 jours)

## 🚨 Points de vigilance à la reprise

### Côté code (Frontend Expo)
- ⚠️ Vérifier que `app.json` a toutes les permissions iOS/Android déclarées proprement
- ⚠️ Vérifier les icônes (1024x1024 iOS, adaptive icon Android)
- ⚠️ Vérifier les screenshots dans `/app/frontend/assets/marketing_screenshots/`
- ⚠️ Vérifier que `EXPO_PUBLIC_BACKEND_URL` pointe bien vers Railway production en mode build

### Côté contenu Store
- 📝 Textes marketing : déjà rédigés en FR pour Play Store, à adapter en EN pour App Store
- 🖼️ Screenshots : doivent être faits sur iPhone (différents des screenshots Android)
- 🎨 Icon : doit être 1024x1024 sans transparence pour iOS

### Côté backend
- ✅ Railway production déjà actif et stable
- ✅ BETA_MODE=True (accès gratuit pour les premiers utilisateurs) — IDÉAL pour la sortie publique
- 🟡 Bug webhook Stripe peut rester non-fixé (BETA gratuit = pas besoin de Stripe)

## ❓ Questions à poser à user à la reprise

1. **Apple Developer Program** : avez-vous déjà payé les 99€/an ou faut-il s'inscrire ?
2. **Disponibilité PC** : pouvez-vous installer eas-cli sur votre PC (commande terminal) ou préférez-vous qu'on trouve une alternative ?
3. **Priorité** : on commence par Play Store (plus avancé) ou on fait les 2 en parallèle ?
4. **Stratégie BETA** : on garde BETA_MODE=True (accès gratuit) à la publication, ou on bascule en mode payant ?
5. **Domaine** : voulez-vous configurer `mesurechassis.com` (site web + emails pro Resend) avant la publication, ou après ?

## 📦 Documents/Assets à préparer ensemble
- [ ] Screenshots iPhone (5-10 captures, format App Store)
- [ ] Description App Store en anglais (4000 chars max)
- [ ] Mots-clés App Store (100 chars, séparés par virgules)
- [ ] Politique de confidentialité (URL publique requise — peut être hébergée sur Railway)
- [ ] Conditions générales d'utilisation (URL publique requise)
- [ ] Email de support (info@mesurechassis.com déjà existe ✅)
- [ ] URL marketing du site (`mesurechassis.com` ou Linktree provisoire)

## ⏱️ Temps estimé
- **Phase A (Play Store)** : 2-4 heures de travail + 1-3 jours d'attente Google
- **Phase B (App Store)** : 4-6 heures de travail + 1-7 jours d'attente Apple
- **Total réaliste** : 1-2 semaines avant publication officielle sur les 2 stores
