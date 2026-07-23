# 🍎 Sign in with Apple — Guide d'exploitation v1.1.3

## Vue d'ensemble

- Backend : `POST /api/auth/apple/session` — vérifie le identity_token contre les JWKS Apple, upsert user par `apple_sub`, retourne notre JWT.
- Frontend : bouton natif `AppleSignInButton` visible UNIQUEMENT sur iOS (via `expo-apple-authentication.isAvailableAsync()`).
- Compliance : Apple Guideline 4.8 (obligatoire dès qu'un login tiers comme Google est actif).

## Variables Railway à définir

Sur Railway → service backend → Variables :

```
APPLE_AUDIENCES=com.mesurechassis.escalier,host.exp.Exponent
```

Si non défini, la valeur par défaut ci-dessus s'applique (le bundle iOS actuel + Expo Go).

⚠️ Si tu changes le bundle iOS un jour, mets aussi à jour cette variable.

## Configuration Apple Developer (si pas déjà fait)

1. Va sur https://developer.apple.com/account
2. Certificates, IDs & Profiles → Identifiers
3. Clique sur ton App ID `com.mesurechassis.escalier`
4. Coche `Sign In with Apple` (Capabilities)
5. Save (Apple regenerate provisioning profile automatiquement)

**Note** : `usesAppleSignIn: true` dans `/app/frontend/app.json` fait automatiquement
cette activation lors du build EAS via Emergent Publish.

## Flow utilisateur (iOS)

1. Ouvre l'app → écran Login/Register
2. Voit le bouton natif noir "Sign in with Apple" sous Google
3. Clique → sheet Apple native → Face ID / mot de passe
4. Choisit "Share my email" ou "Hide my email" (private relay)
5. Retour direct dans l'app connecté 🎉

## Cas particuliers

### Utilisateur déjà inscrit avec le même email (ex: Google)

Le backend fait un **lookup par email de fallback** :
- Si l'email retourné par Apple correspond à un compte existant → **LINK au lieu de dupliquer**.
- L'utilisateur peut ensuite se connecter indifféremment via Google OU Apple.

### Utilisateur choisit "Hide my email"

- Apple crée un email `xxxxx@privaterelay.appleid.com`
- Le backend stocke cet email dans `apple_original_email`
- Un email de fallback interne `apple-{sub}@privaterelay.mesurechassis.com` est stocké dans `email` pour cohérence DB

### Utilisateur supprime son compte Apple sur l'iPhone

- Le compte MesureChâssis reste actif (pas de webhook Apple pour ça)
- L'utilisateur devra utiliser un autre moyen de login (Google, email/password s'il en a créé un)

## Test rapide

### Simuler le format token

Utilise un vrai token depuis un test device — impossible à faire sans un iPhone connecté.

### Test backend seul

```bash
# Doit retourner 401
curl -X POST https://window-field-app.preview.emergentagent.com/api/auth/apple/session \
  -H "Content-Type: application/json" \
  -d '{"identity_token":"fake.token.here"}'
```

## Fichiers du code

- Backend : `/app/backend/routes/apple_auth.py`
- Service frontend : `/app/frontend/src/services/appleAuth.ts`
- Bouton : `/app/frontend/src/components/AppleSignInButton.tsx`
- Wire login/register : `/app/frontend/app/index.tsx`
- Method AuthContext : `signInWithApple(identityToken, userName?, userEmail?, stationId?)`
- Config : `/app/frontend/app.json` (`expo.ios.usesAppleSignIn: true`)
