# 🤖 Fiche Google Play Store — MesureChâssis (Android)

## Informations administratives
- **Nom de l'app** : MesureChâssis
- **Package** : com.mesurechassis.escalier
- **Build AAB** : généré via EAS (profil production, keystore géré par Expo)

---

## ⚠️ PRÉREQUIS COMPTE GOOGLE PLAY (à faire en premier)
1. **Créer un compte développeur Play Console** : https://play.google.com/console/signup — 25 $ (paiement unique)
2. **⚠️ IMPORTANT — choisir le type de compte** :
   - **Compte ORGANISATION (recommandé)** : nécessite un numéro D-U-N-S de Bruxmove srl (gratuit, ~quelques jours). Avantage : publication directe en production.
   - **Compte PERSONNEL** : Google impose un **test fermé avec 12 testeurs pendant 14 jours** avant de pouvoir publier en production. Beaucoup plus lent !
3. Vérification d'identité Google (quelques jours possibles)

---

## 1️⃣ Titre (30 caractères max)
```
MesureChâssis
```

## 2️⃣ Description courte (80 caractères max)
```
Relevés de mesures de châssis pour menuisiers pros. PDF, équipes, chantiers.
```
(77 caractères ✅)

## 3️⃣ Description longue (4000 caractères max)
➡️ **Réutiliser la description de la fiche iOS** : `/app/memory/app_store_listing_fr.md` section 2 (elle est déjà optimisée et identique pour les deux stores).

## 4️⃣ Catégorie & tags
- **Catégorie** : Professionnel (Business)
- **Tags** : menuiserie, mesures, châssis, fenêtres, BTP, chantier

## 5️⃣ Éléments graphiques OBLIGATOIRES
| Élément | Format | Statut |
|---|---|---|
| Icône | 512×512 PNG (32 bits) | ✅ Existante (`assets/images/icon.png` à exporter en 512) |
| Bannière "feature graphic" | 1024×500 PNG/JPG | ✅ Générée — télécharger : `{BACKEND_URL}/api/_downloads/play-feature-graphic` |
| Captures téléphone | min 2, ratio 16:9 à 9:16, min 320px | ❌ À prendre (utiliser les mêmes que l'App Store) |
| Captures tablette 7"/10" | optionnelles mais recommandées | — |

## 6️⃣ Questionnaires obligatoires dans Play Console
- **Politique de confidentialité** : URL publique requise → utiliser la page Privacy de l'app web ou créer `mesurechassis.com/privacy`
- **Data Safety (Sécurité des données)** :
  - Données collectées : email, nom, téléphone (compte) ; photos (mesures) ; pas de localisation
  - Chiffrement en transit : OUI (HTTPS)
  - Suppression de compte possible : OUI (préciser le moyen : email support / écran "Mes informations")
- **Classification du contenu (IARC)** : questionnaire → résultat attendu "Tout public / PEGI 3"
- **Public cible** : 18+ (app professionnelle B2B)
- **Compte de démo pour la review Google** : `applereview@mesurechassis.com` / `AppleReview2026!` (le même que pour Apple)

## 7️⃣ Conformité paiements Google Play ✅ (déjà fait dans le code)
Google Play exige Google Play Billing pour les achats numériques in-app — même règle qu'Apple.
➡️ Le build Android masque désormais **tous les prix et CTA d'abonnement** (même stratégie que l'app iOS : gestion du compte hors application). Aucun flux d'achat dans l'app = pas d'obligation Play Billing.

## 8️⃣ Soumission
1. **Premier upload : MANUEL obligatoire** (règle Google) :
   - Play Console → Créer l'app → Production (ou Test fermé si compte personnel) → Importer l'AAB
   - **AAB prêt (v1.1.0, versionCode 27)** : https://expo.dev/artifacts/eas/v83v--DU_iqkw77oiluH0Yf2J5RcvUDA9M6lMwbYP9Y.aab
2. Uploads suivants automatisables via `eas submit -p android` (nécessite une clé de compte de service Google Cloud JSON)

---

## 📋 CHECKLIST FINALE AVANT SOUMISSION GOOGLE
- [ ] Compte Play Console créé et vérifié (organisation recommandé)
- [ ] AAB build téléchargé et uploadé
- [ ] Feature graphic 1024×500 créée
- [ ] 2+ captures d'écran téléphone
- [ ] URL politique de confidentialité publique
- [ ] Data Safety + IARC remplis
- [ ] Compte démo renseigné pour la review
