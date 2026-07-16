# 🔴 TODO — Notification obligatoire de mise à jour (style Revolut)

**Status** : SPEC VALIDÉE — à implémenter dans le prochain build unifié.
**Priorité** : P1 (améliore la rétention et la compliance des versions)
**Date spec** : 15 juillet 2026
**Décidé par** : Michel

---

## 🎯 Objectif

Empêcher les utilisateurs de rester sur d'anciennes versions de l'app
(bugs, compliance Apple, features cassées). Comportement type Revolut :
- Nouvelle version disponible → bannière non-bloquante
- Version obsolète critique → écran bloquant + email de rappel

---

## Backend

### Nouvel endpoint `GET /api/config/app-version`

Public (pas d'auth requise — appelé au démarrage avant login).

```python
@router.get("/config/app-version")
async def app_version_config():
    return {
        "min_version": os.getenv("APP_MIN_VERSION", "1.0.29"),
        "latest_version": os.getenv("APP_LATEST_VERSION", "1.0.29"),
        "force_update": os.getenv("APP_FORCE_UPDATE", "false") == "true",
        "message": os.getenv(
            "APP_UPDATE_MESSAGE",
            "Une mise à jour est disponible pour continuer à profiter des dernières fonctionnalités.",
        ),
        "app_store_url": "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930",
        "play_store_url": None,  # À activer quand Android publié
    }
```

**Configurable via variables Railway** :
- `APP_MIN_VERSION` : version minimum acceptée (ex: `1.0.28`)
- `APP_LATEST_VERSION` : dernière version dispo
- `APP_FORCE_UPDATE` : `true` pour bloquer les versions < min_version
- `APP_UPDATE_MESSAGE` : message personnalisable

### Tracking version installée par user

Ajouter dans `/auth/me` un champ `X-App-Version` lu depuis header :
```python
@router.get("/auth/me")
async def me(user=Depends(auth_user), x_app_version: str = Header(None)):
    if x_app_version:
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {
                "last_app_version": x_app_version,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
    ...
```

### Job cron quotidien — Email Resend aux users obsolètes

```python
async def cron_notify_obsolete_users():
    """Envoie un email quotidien aux users < APP_MIN_VERSION."""
    min_version = os.getenv("APP_MIN_VERSION", "1.0.29")
    obsolete = db.users.find({
        "last_app_version": {"$lt": min_version},
        "status": "active",
        "notified_update_at": {"$not": {"$gte": last_7_days}},  # anti-spam
    })
    async for user in obsolete:
        send_update_email(user["email"], user["name"])
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"notified_update_at": now_iso}},
        )
```

Template email :
- Sujet : "MesureChâssis - Mise à jour importante disponible"
- Body : "Bonjour {name}, une nouvelle version de MesureChâssis est disponible sur l'App Store. Elle contient des améliorations importantes. Merci de mettre à jour pour continuer à profiter de toutes les fonctionnalités."
- CTA : Bouton "Mettre à jour maintenant" → App Store link

---

## Frontend (Expo)

### 1. Service `src/services/appVersion.ts`

```typescript
import Constants from "expo-constants";
import { api } from "./api";

export async function checkAppVersion() {
  const currentVersion = Constants.expoConfig?.version || "0.0.0";
  const { data } = await api.get("/config/app-version");

  const isBelow = (v1: string, v2: string) => {
    const p1 = v1.split(".").map(Number);
    const p2 = v2.split(".").map(Number);
    for (let i = 0; i < 3; i++) {
      if ((p1[i] || 0) < (p2[i] || 0)) return true;
      if ((p1[i] || 0) > (p2[i] || 0)) return false;
    }
    return false;
  };

  return {
    currentVersion,
    minVersion: data.min_version,
    latestVersion: data.latest_version,
    forceUpdate: data.force_update && isBelow(currentVersion, data.min_version),
    updateAvailable: isBelow(currentVersion, data.latest_version),
    message: data.message,
    appStoreUrl: data.app_store_url,
  };
}
```

### 2. Composant `src/components/ForceUpdateScreen.tsx`

Verrou plein écran, non fermable, style similaire à `PaywallScreen` :
- Icône : `arrow-up-circle` orange
- Titre : "Mise à jour requise"
- Message : le `message` renvoyé par le backend
- Bouton primary : "Ouvrir l'App Store" → `Linking.openURL(appStoreUrl)`
- Bouton secondary : "Voir ce qui est nouveau" → ouvre la page telecharger.html
- **Pas de bouton retour, pas de bouton "Plus tard"**

### 3. Composant `src/components/UpdateAvailableBanner.tsx`

Bannière dismissable en haut du dashboard :
- Fond orange semi-transparent
- "🚀 Nouvelle version disponible — Mettre à jour"
- Bouton close (persist "dismissed_version" dans AsyncStorage — remontre à chaque nouvelle version)

### 4. Wire dans `AuthContext.tsx`

Priorité de verrous :
1. `forceUpdate` (nouveau) — priorité MAX
2. `lock.expired` (paywall)
3. `user.vat_completion_required` (verrou TVA)
4. `validationLock.required`
5. `children` (app normale)

Check au boot + toutes les 5 min via `AppState` change.

### 5. Interceptor Axios — Header `X-App-Version`

Ajouter automatiquement à toutes les requêtes :
```typescript
api.interceptors.request.use((config) => {
  config.headers["X-App-Version"] = Constants.expoConfig?.version || "0.0.0";
  return config;
});
```

---

## 📊 Écran admin (bonus)

Route HTML `/admin/versions` → tableau récapitulatif :
- Nombre d'users par version installée
- % d'users < min_version
- Bouton "Envoyer email de rappel maintenant" (déclenche le cron manuellement)

---

## ✅ Checklist implémentation

- [ ] Endpoint `GET /api/config/app-version`
- [ ] Variables env Railway (`APP_MIN_VERSION`, etc.)
- [ ] Tracking `last_app_version` dans `/auth/me`
- [ ] Job cron `cron_notify_obsolete_users`
- [ ] Template email Resend
- [ ] Service `appVersion.ts`
- [ ] Composant `ForceUpdateScreen.tsx`
- [ ] Composant `UpdateAvailableBanner.tsx`
- [ ] Wire dans `AuthContext.tsx`
- [ ] Interceptor Axios `X-App-Version`
- [ ] Écran admin `/admin/versions` (HTML)
- [ ] Tests : version < min → écran bloquant · version < latest → bannière · version >= latest → rien
- [ ] Tests régression : `/auth/me` renvoie toujours user correctement
