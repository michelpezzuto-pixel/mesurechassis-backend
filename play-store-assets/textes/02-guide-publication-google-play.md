# 🚀 GUIDE COMPLET - PUBLIER MESURECHÂSSIS SUR GOOGLE PLAY STORE

---

## ⚠️ ÉTAPE 0 — OBLIGATOIRE : Payer les 25 $ chez Google

Avant TOUT, vous devez créer un compte développeur Google Play.

### À faire MAINTENANT
1. Allez sur **[play.google.com/console/signup](https://play.google.com/console/signup)**
2. Connectez-vous avec votre compte Google
3. Choisissez le **type de compte** :
   - 🏢 **Organisation** (RECOMMANDÉ pour votre société MesureChâssis)
     - ✅ Plus crédible
     - ✅ Pas obligé de divulguer votre nom personnel sur la fiche Play Store
     - ✅ **EXEMPT de la règle des 20 testeurs / 14 jours** dans certains cas (vérification D-U-N-S possible)
     - ⚠️ Demande un numéro D-U-N-S (gratuit, 5-7 jours) ou les statuts de votre société
   - 👤 **Personnel**
     - ⚠️ **OBLIGATOIRE de faire le test fermé 20 testeurs / 14 jours**
4. Payez les **25 $ USD** (frais uniques, pas d'abonnement)
5. Acceptez les conditions
6. Validez votre identité (carte d'identité scannée)

⏱️ **Délai validation Google : 24-48h**

---

## ✅ ÉTAPE 1 — Compte Expo (gratuit)

Vous m'avez dit avoir créé un compte sur expo.dev avec votre Google.

**Donnez-moi votre username Expo** (visible en haut à droite sur expo.dev).

Format : `@votre-username`

---

## ✅ ÉTAPE 2 — Je génère le fichier AAB (durée : ~20 min)

Une fois votre username Expo donné, je lance dans cet ordre :

```bash
# 1. Login Expo (vous me donnerez un token)
eas login

# 2. Initialiser le projet EAS
eas build:configure

# 3. Lancer le build production Android
eas build --platform android --profile production
```

À la fin, vous obtenez **un lien de téléchargement** vers le fichier `.aab` (Android App Bundle).
Téléchargez-le sur votre PC.

---

## ✅ ÉTAPE 3 — Créer la fiche app dans Google Play Console

1. Connectez-vous sur **[play.google.com/console](https://play.google.com/console)**
2. Cliquez **"Créer une application"**
3. Remplissez :
   - **Nom de l'app** : `MesureChâssis`
   - **Langue par défaut** : Français (France)
   - **Type** : Application
   - **Gratuite ou payante** : Gratuite
4. Cochez les déclarations obligatoires (RGPD, contenu, etc.)
5. **Créer**

---

## ✅ ÉTAPE 4 — Configurer la fiche Play Store

Dans le menu de gauche, allez dans **"Présence sur le Store" → "Fiche Play Store principale"**.

### À copier-coller depuis le fichier `01-textes-fiche-play-store.md` :

| Champ | Source dans mon fichier |
|-------|-------------------------|
| Nom | "NOM DE L'APP" |
| Description courte | "DESCRIPTION COURTE" |
| Description complète | "DESCRIPTION LONGUE" |
| Icône | `icon-512x512.png` |
| Image de bannière | `feature-graphic-1024x500.png` |
| Captures d'écran téléphone | Les 6 fichiers du dossier `screenshots/` |
| Catégorie | `Outils` (puis `Productivité` en secondaire) |

### Politique de confidentialité
URL à indiquer : `https://mesurechassis.com/confidentialite.html`

⚠️ **Vérifiez d'abord que cette page est accessible** sur votre site Easyhost !

---

## ✅ ÉTAPE 5 — Configurer le test fermé (20 testeurs)

Dans le menu de gauche : **"Tests" → "Test fermé"** → **"Commencer"**

### A. Créer la liste de testeurs
1. Onglet **"Testeurs"**
2. **"Créer une liste d'adresses e-mail"**
3. Nom : `Testeurs MesureChâssis`
4. Ajoutez **20 adresses Gmail** (vraiment 20 différentes !) :
   - Vos emails personnels secondaires
   - Famille (Gmail uniquement, pas Hotmail/Outlook)
   - Amis menuisiers/artisans
   - Collaborateurs
   - ⚠️ **Astuce** : si vous manquez de testeurs, créez-vous 5-10 comptes Gmail supplémentaires (gratuit)
5. **Enregistrer**
6. ✅ Cocher la case **"Utiliser cette liste pour ce test fermé"**

### B. Importer le fichier AAB
1. Onglet **"Versions"** → **"Créer une version"**
2. **Importez le fichier `.aab`** que je vous aurai fourni
3. **Notes de version** (à copier depuis mon fichier de textes) :
   ```
   🎉 Bienvenue sur MesureChâssis !
   Première version publique...
   ```
4. **Suivant** → **Enregistrer**

### C. Lancer le déploiement
1. Cliquez **"Examiner la version"**
2. Cliquez **"Démarrer le déploiement vers les tests fermés"**
3. ⏱️ Google valide en **2h à 7 jours** (la 1ère fois c'est plus long)

---

## ✅ ÉTAPE 6 — Pendant les 14 jours

### Lien d'adhésion testeurs
Une fois le test "En ligne", récupérez le **lien d'adhésion** dans l'onglet "Testeurs" (format `https://play.google.com/apps/testing/com.mesurechassis.app`).

### Envoyez ce message à vos 20 testeurs :

```
Salut !

Je lance MesureChâssis, une app pour les menuisiers, et j'ai besoin
de toi pour la phase de test (obligation de Google).

➡️ 1. Clique sur ce lien depuis ton téléphone Android :
   [LIEN ICI]

➡️ 2. Accepte de devenir testeur

➡️ 3. Télécharge l'app via le bouton "Télécharger sur Google Play"

➡️ 4. IMPORTANT : Garde l'app installée sur ton téléphone pendant
   14 jours minimum (tu n'as PAS besoin de l'utiliser activement,
   juste de ne pas la désinstaller).

Sans ces 14 jours, je ne peux pas publier officiellement.

Merci 1000 fois pour ton aide ! 🙏

— [Votre nom]
```

### À surveiller pendant ces 14 jours
- Allez régulièrement sur la console pour voir le **nombre de testeurs actifs**
- Si certains désinstallent, **relancez-les** ou ajoutez de nouveaux testeurs
- Le compteur Google s'incrémente : il faut **20 testeurs ACTIFS pendant 14 jours**

---

## ✅ ÉTAPE 7 — Après les 14 jours : Publication publique

Une fois la condition validée :

1. Menu **"Tests" → "Test fermé"** → onglet **"Tableau de bord"**
2. Vous verrez : ✅ **"Vous êtes éligible à publier en production"**
3. Allez dans **"Production" → "Versions"** → **"Créer une version"**
4. Réutilisez le même `.aab`
5. **Examiner la version** → **Lancer le déploiement vers la production**

⏱️ **Délai review Google : 1-7 jours** (souvent 24-48h pour un compte vérifié)

🎉 **Une fois validé, votre app est publique sur Google Play Store !**

---

## 📊 RÉCAPITULATIF DES DÉLAIS

| Étape | Durée |
|-------|-------|
| Créer compte Google Play (25$) | 1h (paiement) + 24-48h (validation) |
| Générer AAB via EAS Build | ~20 min |
| Créer fiche Play Store | 1-2h (vous, copier-coller) |
| Review Google test fermé | 2h - 7 jours |
| Période de test obligatoire | **14 jours fixes** |
| Review Google production | 1-7 jours |
| **TOTAL minimum** | **~3 semaines** |

---

## 🆘 EN CAS DE PROBLÈME

Si Google rejette votre app :
1. Lisez attentivement le **motif de rejet** (en français dans la console)
2. Les rejets fréquents :
   - ❌ Politique de confidentialité non accessible → vérifiez `mesurechassis.com/confidentialite.html`
   - ❌ Permissions non justifiées → mes textes les justifient correctement
   - ❌ Description trop "marketing" / promesses excessives → mes textes restent factuels
   - ❌ Icône de mauvaise qualité → `icon-512x512.png` est OK
3. Revenez me voir, on corrige et on resoumet

---

## 📞 BESOIN D'AIDE ?

À chaque étape bloquante, **revenez me voir** avec :
- Le message d'erreur exact (capture d'écran)
- L'étape sur laquelle vous bloquez

On débloque ensemble en 5 minutes ! 🚀
