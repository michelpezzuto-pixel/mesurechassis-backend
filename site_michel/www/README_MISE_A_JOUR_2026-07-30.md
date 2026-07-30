# 📦 LIVRAISON SITE MESURECHÂSSIS — v2.1
### 30 juillet 2026 — Corrections critiques + Nouvelle page réservation WhatsApp

---

## 🎯 CE QUE TU DOIS UPLOADER (via FileZilla)

Dans le dossier `/www/` de ton hébergement Easyhost :

### ✏️ Fichiers à REMPLACER (2 fichiers)

| Fichier | Où le mettre | Ce qui change |
|---|---|---|
| **`index.html`** | `/www/index.html` | 6 corrections + footer avec réseaux sociaux |
| **`reserver.html`** | `/www/reserver.html` | ⭐ NOUVEAU — Page formulaire WhatsApp |

**C'est TOUT.** Aucune image, aucun CSS externe à modifier. Tout est intégré dans les fichiers.

---

## ✅ CE QUI A ÉTÉ CORRIGÉ SUR `index.html`

| # | Zone | Avant | Après |
|---|---|---|---|
| 1 | Bandeau haut | "🤖 Android en beta" | "🤖 Android prévu 2026" |
| 2 | Bouton CTA hero | Redirigeait vers Calendly 30min | Redirige vers `reserver.html` (formulaire filtré) |
| 3 | Texte CTA | "Réserver 15 min avec Michel" | "Réserver 15 min sur WhatsApp" |
| 4 | Sous-titre hero | "Rdv gratuit avec le fondateur" | "Appel WhatsApp gratuit avec le fondateur" |
| 5 | FAQ Q1 | Mensonge iOS + Android + web | "Dès maintenant sur iPhone/iPad, Android + web prévus 2026" |
| 6 | FAQ Q3 | "Artisan Pro, Entreprise Pro..." | Noms harmonisés : "Artisan Solo, Artisan MAX, Entreprise, Entreprise MAX" + limite 3 chantiers |
| 7 | CTA final | "Version Android bientôt" | "Version Android prévue 2026" |
| 8 | Footer | Pas de réseaux sociaux | ⭐ Nouvelle section avec LinkedIn, Facebook, Instagram, TikTok |

---

## 🆕 NOUVELLE PAGE `reserver.html`

### Ce qu'elle fait

1. Le prospect arrive depuis le bouton "Réserver 15 min sur WhatsApp"
2. Il remplit **7 questions** dans un formulaire (2-3 minutes)
3. **Filtres anti-bot / anti-démarcheur** appliqués automatiquement :
   - Honeypot invisible (bloque 95% des bots)
   - Validation format numéro WhatsApp
   - **Question métier obligatoire** : *"Qu'est-ce qu'une pareclose ?"* → seule la bonne réponse (baguette qui maintient le vitrage) permet de continuer
4. Si tout est OK → **redirection automatique vers Calendly** avec toutes ses infos pré-remplies
5. Sinon → message d'erreur affiché

### Les 7 questions

1. Nom complet
2. Nom entreprise
3. Taille équipe (solo / 2-5 / 6-15 / 15+)
4. Défi #1 (ressaisie / devis / erreurs / papier / autre)
5. Numéro WhatsApp (validation format international)
6. Email pro
7. 🔧 **Question métier pareclose** (4 choix, 1 seule bonne réponse)

---

## ⚙️ ACTION REQUISE DE TON CÔTÉ (5 minutes)

### 🔴 ÉTAPE 1 — Créer un event Calendly dédié WhatsApp

1. Va sur ton **Calendly** (compte michelpezzuto)
2. Clique **"Create" → "One-on-One"**
3. **Nom de l'event** : `Appel WhatsApp - 15 min`
4. **URL slug** : `appel-whatsapp-15min` (⚠️ **exactement ce nom** pour que le lien du formulaire fonctionne)
   → URL finale : `calendly.com/michelpezzuto/appel-whatsapp-15min`
5. **Durée** : `15 minutes` (ou 20 si tu préfères — change aussi dans l'app)
6. **Location / Lieu de la réunion** :
   - Choisis **"Custom"** (ou "Autre" en français)
   - Texte : `Michel vous appellera sur WhatsApp au numéro que vous avez fourni. Vérifiez que votre téléphone est disponible.`
7. **Description** :
   ```
   Appel WhatsApp gratuit avec Michel Pezzuto, fondateur MesureChâssis.
   Menuisier belge · 20 ans de terrain.
   
   On va parler de :
   • Ton défi actuel sur chantier
   • Comment MesureChâssis peut t'aider
   • Démo en direct si tu veux
   
   ⚠️ Cet appel est réservé aux menuisiers pros.
   Zéro démarchage, zéro pression commerciale.
   ```
8. **Questions personnalisées** (à ajouter à ton event) :
   - **Q1** (paragraphe, obligatoire) : `Informations pré-qualification`
     → Cette question recevra automatiquement toutes tes infos (entreprise, taille, défi) via l'URL
   - **Q2** (texte court, obligatoire) : `📱 Confirmez votre numéro WhatsApp (format +32...)`

### 🟠 ÉTAPE 2 — Si tu veux changer le slug Calendly

Si tu préfères un autre nom d'URL que `appel-whatsapp-15min`, tu dois :
1. Ouvrir `reserver.html` avec un éditeur texte (Notepad++, VS Code, ou Notepad simple)
2. Chercher la ligne (vers le bas du fichier) :
   ```javascript
   const CALENDLY_URL = "https://calendly.com/michelpezzuto/appel-whatsapp-15min";
   ```
3. Remplacer par ton URL exacte
4. Sauvegarder et réuploader

### 🟢 ÉTAPE 3 — Test après upload

1. Va sur `https://mesurechassis.com`
2. Clique sur **"📞 Réserver 15 min sur WhatsApp"** dans le hero
3. Remplis le formulaire (avec de faux infos pour tester)
4. Réponds à la question pareclose (bonne réponse = **B** : *la baguette qui maintient le vitrage*)
5. Tu dois être redirigé vers Calendly avec ton nom, email, et infos pré-remplis
6. Si oui → ✅ tout fonctionne. Si non → me le dire, on debug

---

## 🇧🇪 Réseaux sociaux intégrés dans le footer

Icônes cliquables dans le pied de page de toutes les pages qui incluent le footer :

- 💼 **LinkedIn** → `https://www.linkedin.com/in/michel-pezzuto-aa4797235`
- 📘 **Facebook** → `https://www.facebook.com/profile.php?id=61590909743900`
- 📸 **Instagram** → `https://www.instagram.com/mesurechassis/`
- 🎵 **TikTok** → `https://www.tiktok.com/@mesure.chssis`

*(YouTube à ajouter plus tard quand la chaîne sera créée)*

---

## 📊 TRACKING & CONVERSIONS

Les événements suivants sont trackés automatiquement dans Google Analytics :

| Événement | Déclenché quand |
|---|---|
| `reserver_click` | Clic sur le bouton "Réserver 15 min sur WhatsApp" (hero) |
| `reserver_form_submit` | Le formulaire a passé tous les filtres et redirige vers Calendly |

Tu pourras voir tes taux de conversion dans **Google Analytics → Événements** :
- Nombre de clics sur le bouton (intérêt)
- Nombre de soumissions réussies (leads qualifiés)
- Taux de conversion = leads / clics

---

## 🚨 EN CAS DE PROBLÈME

**Le formulaire ne s'ouvre pas quand je clique sur le bouton :**
- Vérifie que `reserver.html` est bien uploadé dans `/www/` (racine, pas dans un sous-dossier)

**La question pareclose refuse même la bonne réponse :**
- La bonne réponse doit être sélectionnée dans le menu déroulant (choix B)
- Si tu veux tester avec une autre bonne réponse, ouvre `reserver.html` et cherche `if (pareclose !== 'b')`

**Calendly affiche "page introuvable" :**
- Ton event Calendly n'a pas le slug `appel-whatsapp-15min`
- Solution : voir ÉTAPE 2 ci-dessus

**Les icônes réseaux sociaux ne s'affichent pas :**
- Vérifie que le nouveau `index.html` est bien uploadé (le nouveau CSS est intégré dedans)
- Vide le cache navigateur (Ctrl+F5)

---

## 📞 QUESTIONS ?

Reviens vers moi, je débloque en 2 minutes.

Bon upload !
