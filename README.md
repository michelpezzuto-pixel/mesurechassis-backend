# MesureChâssis - Backend

Backend FastAPI pour l'application mobile MesureChâssis (gestion de prise de mesures pour menuiseries).

## 🚀 Déploiement sur Railway

### Prérequis
- Compte Railway (https://railway.app)
- Compte MongoDB Atlas OU service MongoDB Railway
- Clé API Resend (envoi d'emails)
- Clé Emergent LLM (génération de PDF / analyse)

### Étapes de déploiement

1. **Créer une base MongoDB** sur Railway :
   - `+ New` → `Database` → `Add MongoDB`
   - Attendre que le service soit prêt
   - Copier la variable `MONGO_URL` (onglet Variables du service MongoDB)

2. **Créer le service backend** :
   - `+ New` → `GitHub Repo` → sélectionner ce dépôt
   - Settings :
     - Root Directory : `/`
     - Start Command : `uvicorn server:app --host 0.0.0.0 --port $PORT`
     - Python version : 3.11+

3. **Configurer les variables d'environnement** (onglet Variables) :
   ```
   MONGO_URL=<copier depuis le service MongoDB>
   DB_NAME=mesurechassis
   JWT_SECRET=<chaîne aléatoire de 32 caractères minimum>
   ACCESS_TOKEN_EXPIRE_MINUTES=43200
   RESEND_API_KEY=re_xxxxxxxxx
   EMERGENT_LLM_KEY=sk-emergent-xxxxxxxxx
   ```

4. **Activer un domaine public** :
   - Settings → Networking → `Generate Domain`
   - L'URL générée (format `xxx.up.railway.app`) sera l'URL du backend

5. **Tester** :
   - Visiter `https://votre-url.up.railway.app/api/health`
   - Devrait retourner `{"status": "ok"}`

## 🛠 Stack technique
- FastAPI (Python 3.11+)
- MongoDB (motor async)
- Resend (emails)
- JWT pour l'authentification
- Expo Push Notifications

## 📁 Structure
```
/
├── server.py          # Point d'entrée FastAPI
├── routes/            # Endpoints (auth, chantiers, mesures, ...)
├── models.py          # Modèles Pydantic
├── db.py              # Connexion MongoDB
├── deps.py            # Dépendances FastAPI (auth, RBAC)
├── email_service.py   # Envoi d'emails via Resend
├── utils.py           # Utilitaires (JWT, hash, ...)
├── requirements.txt   # Dépendances Python
├── Procfile           # Commande de démarrage (Railway/Heroku)
└── railway.json       # Configuration spécifique Railway
```
