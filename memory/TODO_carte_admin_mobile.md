# 🗺️ TODO — Carte des inscrits accessible dans l'app mobile

**Status** : SPEC VALIDÉE — à implémenter dans le prochain build unifié.
**Priorité** : P2 (visualisation admin, la carte HTML existe déjà)
**Date spec** : 15 juillet 2026
**Décidé par** : Michel

---

## 🎯 Objectif

Permettre à Michel de voir directement dans l'app mobile la carte
géographique des utilisateurs inscrits, sans avoir à taper une URL
avec un token dans son navigateur.

---

## ✅ Ce qui existe déjà (backend, en prod)

Endpoint `/api/admin/map` (dans `/app/backend/routes/admin_tools.py`) :
- Page HTML complète avec Leaflet + MarkerCluster + OpenStreetMap
- Aucune clé API requise (OSM gratuit)
- Filtres : "derniers X jours", "actifs uniquement"
- Popup au clic : email masqué, ville, pays, rôle, date d'inscription
- Auth : `PLATFORM_ADMIN_TOKEN` en query param `?token=XXX`
- Route sœur `/api/admin/map/data` : JSON brut (utilisable pour un
  écran natif React Native si on veut).

---

## 🎯 Solution retenue — Option A (rapide, ~30 min)

Ajouter un bouton "🗺️ Carte des inscrits" dans l'écran admin de l'app
mobile. Un clic ouvre la carte HTML dans le navigateur du téléphone via
`Linking.openURL()`.

### Backend

**Nouvel endpoint `POST /api/admin/map/access-link`** — génère une URL signée à durée courte.

```python
from datetime import datetime, timezone, timedelta
import jwt

@router.post("/admin/map/access-link")
async def admin_map_access_link(user=Depends(require_platform_owner)):
    """Génère un lien temporaire (5 min) vers la carte HTML.

    Le user doit être platform owner. On émet un token JWT signé,
    court-vécu, distinct du token principal — utilisable uniquement
    pour `/api/admin/map` et `/api/admin/map/data`.
    """
    payload = {
        "sub": user["id"],
        "scope": "admin_map",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    map_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    base_url = os.getenv("FRONTEND_URL", "https://mesurechassis.up.railway.app")
    return {
        "url": f"{base_url}/api/admin/map?jwt={map_token}",
        "expires_in": 300,
    }
```

**Modifier `_check_token()`** dans `admin_tools.py` pour accepter soit :
- Le classique `?token=PLATFORM_ADMIN_TOKEN`
- Soit `?jwt=<map_token>` (JWT scope=admin_map)

### Frontend (Expo)

**Ajouter dans l'écran admin dashboard** (ou nouvelle screen `/admin/map-launcher.tsx`) :

```typescript
import * as Linking from "expo-linking";
import { api } from "@/src/services/api";

const openMap = async () => {
  try {
    setLoading(true);
    const { data } = await api.post("/admin/map/access-link");
    await Linking.openURL(data.url);
  } catch (e) {
    Alert.alert("Erreur", "Impossible d'ouvrir la carte. Réessayez.");
  } finally {
    setLoading(false);
  }
};

<TouchableOpacity onPress={openMap} style={styles.mapBtn}>
  <Ionicons name="map" size={22} color="#FF5A00" />
  <Text>Carte des inscrits</Text>
</TouchableOpacity>
```

**Visibilité** : bouton visible uniquement pour les `PLATFORM_OWNER_EMAILS`
(à vérifier via un endpoint `/auth/me` enrichi avec un flag
`is_platform_owner`, ou via un check côté frontend sur l'email).

---

## 🅱️ Alternative : Écran natif (~2-3h) — REPORTÉ à plus tard

Si Michel veut plus tard une carte 100% native (pas de webview) :
- Installer `react-native-maps` (nécessite Google Maps API key pour Android,
  Apple Maps gratuit pour iOS)
- Créer un écran `/app/admin/map.tsx`
- Fetcher `/api/admin/map/data` (déjà en JSON)
- Afficher les `points` avec `<Marker>` + clustering via
  `react-native-map-clustering`

**Estim** : 2-3h dev + tests iOS/Android.

---

## ✅ Checklist implémentation (Option A)

- [ ] Endpoint `POST /api/admin/map/access-link` (JWT scope=admin_map, 5 min TTL)
- [ ] Modif `_check_token()` pour accepter `?jwt=...` en plus de `?token=...`
- [ ] Bouton "Carte des inscrits" dans l'écran admin
- [ ] Guard visibilité : seulement pour `PLATFORM_OWNER_EMAILS`
- [ ] Test : bouton → génère lien → ouvre navigateur → carte s'affiche
- [ ] Test : lien expiré (>5 min) → 403
- [ ] Test : user non-owner → 403 sur `access-link`

---

## 📌 Comment reprendre

Quand Michel dit "go carte admin" :
1. Relire ce fichier
2. Backend : ajouter les 2 endpoints (~20 min)
3. Frontend : ajouter le bouton dans admin (~10 min)
4. Test manuel + screenshot
5. Commit

Total : ~30 min max. Zéro dépendance externe.
