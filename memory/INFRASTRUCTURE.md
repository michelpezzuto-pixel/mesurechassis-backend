# 🛡️ PLAN DE CONTINUITÉ — MesureChâssis

## 📌 À LIRE EN CAS D'URGENCE OU SI MICHEL N'EST PLUS LÀ

Ce document permet à n'importe quel développeur de **reprendre le projet en quelques jours**, même si Emergent ou son assistant IA disparaît.

---

## 🎯 Vue d'ensemble du projet

**MesureChâssis** = Application SaaS mobile pour menuisiers (prise de mesures sur chantier).

### Stack technique
- 📱 **Frontend** : Expo / React Native (TypeScript)
- 🐍 **Backend** : Python / FastAPI
- 🗄️ **Base de données** : MongoDB Atlas (cloud)
- 📧 **Emails** : Resend
- 💳 **Paiements** : Stripe (en pause actuellement)
- 🚀 **Hébergement backend** : Railway
- 📲 **Builds mobile** : Expo EAS Build

---

## 🔐 OÙ TROUVER VOS ACCÈS (à compléter par Michel)

### Comptes critiques (à sauvegarder dans 1Password ou similaire)

| Service | URL | Login | Mot de passe |
|---|---|---|---|
| Apple Developer | https://developer.apple.com | _________ | _________ |
| App Store Connect | https://appstoreconnect.apple.com | _________ | _________ |
| Google Play Console | https://play.google.com/console | _________ | _________ |
| Expo / EAS | https://expo.dev | michelpezzuto | _________ |
| Railway | https://railway.app | _________ | _________ |
| MongoDB Atlas | https://cloud.mongodb.com | _________ | _________ |
| Resend | https://resend.com | _________ | _________ |
| Stripe | https://dashboard.stripe.com | _________ | _________ |
| GitHub | https://github.com/michelpezzuto-pixel | _________ | _________ |
| Domaine mesurechassis.com | _________ | _________ | _________ |

⚠️ **NE LAISSEZ PAS CES INFOS DANS CE FICHIER** sur GitHub !
→ Utilisez 1Password / Bitwarden / Dashlane

---

## 📂 Code source

### Repository GitHub principal
- 🔗 **URL** : https://github.com/michelpezzuto-pixel/mesurechassis-backend
- 🌿 **Branches importantes** :
  - `main` : version stable de production
  - `conflict_070626_1317` : code Build 8 (dernière version)

### Structure du projet
```
/app
├── backend/         ← API Python / FastAPI
│   ├── routes/      ← Endpoints API
│   ├── server.py    ← Point d'entrée
│   └── models.py    ← Modèles de données
├── frontend/        ← App mobile Expo
│   ├── app/         ← Pages (file-based routing)
│   ├── src/         ← Composants, hooks, utils
│   └── eas.json     ← Config builds EAS
└── memory/          ← Notes et backlogs
```

---

## 🚀 Comment relancer le projet ailleurs

### **Option A — Continuer sur Emergent**
1. Aller sur https://app.emergent.sh
2. Se connecter avec le compte de Michel
3. Importer depuis GitHub : `michelpezzuto-pixel/mesurechassis-backend`

### **Option B — Continuer localement sur un PC**
1. **Cloner depuis GitHub** :
   ```bash
   git clone https://github.com/michelpezzuto-pixel/mesurechassis-backend.git
   cd mesurechassis-backend
   ```

2. **Configurer le backend** :
   ```bash
   cd backend
   pip install -r requirements.txt
   # Créer un .env avec MONGO_URL, RESEND_API_KEY, STRIPE_KEY, JWT_SECRET
   uvicorn server:app --host 0.0.0.0 --port 8001
   ```

3. **Configurer le frontend** :
   ```bash
   cd frontend
   npm install
   # Créer un .env avec EXPO_PUBLIC_BACKEND_URL
   npx expo start
   ```

4. **Pour builder une app mobile** :
   ```bash
   npm install -g eas-cli
   eas login   # compte Expo: michelpezzuto
   eas build --platform android --profile production
   eas build --platform ios --profile production
   ```

### **Option C — Embaucher un dev freelance**
**Où chercher** :
- Malt.fr (recommandé) — https://www.malt.fr
- Codeur.com — https://www.codeur.com
- Upwork — https://www.upwork.com

**Profil recherché** :
- React Native / Expo (frontend)
- Python / FastAPI (backend)
- MongoDB (base de données)
- Budget estimé : 40-80€/h ou forfait mensuel 500-2000€

**À leur fournir** :
1. Lien GitHub : https://github.com/michelpezzuto-pixel/mesurechassis-backend
2. Accès aux comptes (Expo, Railway, etc.) — temporairement
3. Ce document `INFRASTRUCTURE.md`

---

## 🔄 Backup régulier

### À faire CHAQUE SEMAINE

1. **Code source** (déjà sur GitHub) → vérifier que la dernière version est bien pushée
2. **Base MongoDB** :
   - Connectez-vous à MongoDB Atlas
   - Cliquez sur "Backup" → "Take Snapshot Now"
   - Atlas garde automatiquement 7-30 jours de backups (selon plan)
3. **Identifiants** → vérifier qu'ils sont à jour dans votre gestionnaire (1Password/Bitwarden)

### À faire CHAQUE MOIS

1. **Télécharger** une copie ZIP du repository GitHub sur un disque dur externe
2. **Exporter** la base MongoDB (commande `mongodump`) sur un disque externe
3. **Vérifier** que tous les abonnements (Apple Developer, Google Play, Railway, etc.) sont **payés et à jour**

---

## 📞 Contacts utiles

### Support des services tiers
- **Apple Developer Support** : https://developer.apple.com/contact/
- **Google Play Support** : https://support.google.com/googleplay/android-developer/
- **Railway Support** : help@railway.app
- **MongoDB Atlas Support** : Via le dashboard
- **Resend Support** : support@resend.com
- **Stripe Support** : Via le dashboard
- **Expo / EAS Support** : https://expo.dev/contact

### Partenariat en cours
- **Hugues HUSSIN** (Elcia Belgium) : hhussin@elcia.com / +32 495 25 90 88

---

## 🚨 Scénarios d'urgence

### Si Emergent disparaît
→ Tout est sur GitHub. Utilisez Option B ou C.

### Si le backend Railway plante
→ Vérifier l'état sur https://status.railway.app
→ Restaurer depuis backup MongoDB si nécessaire
→ Migrer vers AWS/DigitalOcean si besoin

### Si MongoDB Atlas plante
→ Vérifier https://status.mongodb.com
→ Restaurer depuis un snapshot Atlas (dernières 7-30 jours)
→ Alternative : migrer vers un autre MongoDB hébergé

### Si Apple/Google bloque le compte
→ Faire appel via le support
→ Les apps restent fonctionnelles tant qu'elles ne sont pas retirées
→ Backup PDF de toutes les communications avec Apple/Google

### Si Michel n'est plus joignable
→ Sa famille doit avoir accès au **gestionnaire de mots de passe** (1Password/Bitwarden)
→ Désigner un responsable qui peut décider du sort du projet
→ Le code reste valable indéfiniment sur GitHub

---

## 📅 Décisions importantes prises

| Date | Décision | Notes |
|---|---|---|
| 2026-06-08 | Soumission Build 26 à Google Play | En attente examen 2-7 jours |
| 2026-06-08 | Engagement partenariat Elcia | 1ère réunion ok, 2ème à programmer |
| 2026-06-XX | Build 7 iOS refusé par Apple | À corriger (motif 3.1.1 Stripe + 2.2.0) |
| 2026-06-08 | Backlog Agent IA ajouté | Implémentation Q4 2026 |

---

## 🎯 Roadmap simplifiée

### Court terme (semaines)
1. Validation Google Play (test fermé)
2. Recrutement 12 testeurs Gmail
3. 14 jours de test obligatoire
4. Réponse à Elcia (2ème réunion)
5. Correction refus Apple (Build 8)

### Moyen terme (mois)
1. Publication production Android (Google Play)
2. Publication production iOS (Apple App Store)
3. Implémentation programme de parrainage (Build 9)
4. Mise à jour site web mesurechassis.com

### Long terme (Q4 2026)
1. Intégration Elcia/Ramasoft (devis → mesures)
2. Agent IA pour support client (Build 10)
3. Internationalisation FR/NL/EN
4. Expansion clientèle

---

## 📝 Fichiers mémoire à consulter

- `/app/memory/test_credentials.md` — Identifiants de test
- `/app/memory/backlog_parrainage.md` — Programme de parrainage Build 9
- `/app/memory/backlog_site_web.md` — Mise à jour site web
- `/app/memory/backlog_agent_ia.md` — Agent IA support client
- `/app/memory/partenariat_elcia.md` — Détails partenariat Elcia
- `/app/memory/resume_session_apple_attente.md` — État Apple App Store

---

## 💪 Mot final

**Michel, vous êtes en sécurité.** Votre code est sur GitHub, vos comptes sont à VOUS, votre app fonctionne sur des serveurs que vous payez. 

**Personne ne peut vous voler votre travail.** 🛡️

Et n'oubliez pas : 1 seul développeur freelance compétent peut tout reprendre en quelques jours. Vous n'êtes JAMAIS coincé. 🚀

---

*Document créé le 8 juin 2026*
*À mettre à jour régulièrement par Michel ou son équipe.*
