# 📱 Notification de mise à jour (v1.1.3+) — Guide d'exploitation

## Vue d'ensemble

À partir de v1.1.3, l'app MesureChâssis vérifie automatiquement la version
au démarrage (et toutes les 15 min) via l'endpoint public :
`GET /api/config/app-version`.

Selon la comparaison avec la version installée, l'utilisateur voit :

| Cas | Version installée | Comportement |
|---|---|---|
| ✅ À jour | `>= latest_version` | Rien |
| 🟢 Update dispo | `< latest_version` | **Bannière orange soft** en haut du dashboard (dismissable, revient à chaque nouvelle version) |
| 🔴 Update forcé | `< min_version` ET `force_update=true` | **Écran plein bloquant** → seule action : ouvrir App Store |

L'endpoint est **public (sans auth)** et **fail-safe** : si le backend est down, aucun blocage.

## Variables Railway à configurer

Sur Railway → service backend → **Variables** :

| Variable | Rôle | Exemple |
|---|---|---|
| `APP_LATEST_VERSION` | 🟢 Version la plus récente publiée | `1.1.3` |
| `APP_MIN_VERSION` | 🔴 Version minimale acceptée | `1.0.29` |
| `APP_FORCE_UPDATE` | Active l'écran bloquant si version < min | `false` (défaut) ou `true` |
| `APP_UPDATE_MESSAGE` | Message affiché dans banner + écran | Texte libre |
| `APP_UPDATE_HIGHLIGHTS` | Liste des nouveautés (séparées par `\|`) | `Import PDF corrigé\|Notifications de mise à jour` |

## Workflow standard pour une nouvelle release

### 1. Publier la nouvelle version (ex: 1.1.4)

- Bump `version` + `buildNumber` dans `/app/frontend/app.json`
- Click "Publish" via Emergent → build iOS + envoi App Store Connect
- Une fois **approuvée par Apple** :

### 2. Activer la notification côté Railway

Dans Railway dashboard → service backend → Variables :

```
APP_LATEST_VERSION=1.1.4
APP_MIN_VERSION=1.0.29             ← ne change PAS (sauf bug critique)
APP_FORCE_UPDATE=false             ← garde false (mise à jour recommandée, pas obligatoire)
APP_UPDATE_MESSAGE=Nouvelle version 1.1.4 disponible avec plusieurs améliorations
APP_UPDATE_HIGHLIGHTS=Nouveauté A|Nouveauté B|Nouveauté C
```

Puis clique **"Deploy"** — les variables sont prises en compte instantanément.

**Résultat** : dans les 15 minutes, tous les utilisateurs v1.1.3 voient la
bannière soft. Elle est dismissable une fois — mais reviendra à la prochaine
version encore plus récente.

### 3. Cas urgent : forcer la mise à jour (bug critique)

Si v1.1.4 corrige un bug bloquant et qu'il faut forcer :

```
APP_LATEST_VERSION=1.1.4
APP_MIN_VERSION=1.1.4              ← force minimum = latest
APP_FORCE_UPDATE=true              ← active blocage
APP_UPDATE_MESSAGE=Une correction critique nécessite la mise à jour immédiate.
```

⚠️ **À utiliser avec parcimonie** — bloque l'app pour toute personne qui n'a
pas mis à jour. À reset dès que la crise est passée.

## Tracking : voir qui utilise quelle version

À partir de v1.1.3, chaque requête envoie un entête `X-App-Version: 1.x.y`.
Le backend peut logger ou stocker cette info pour analyser la distribution
des versions dans MongoDB (à implémenter en v1.1.4 si besoin — see
`TODO_force_update.md` section "Job cron quotidien").

## Test rapide

### Simuler "update dispo" côté serveur

```bash
# Sur Railway, met APP_LATEST_VERSION plus haut que la version app actuelle
APP_LATEST_VERSION=99.0.0
# → tous les users voient la bannière orange
```

### Simuler "force update" côté serveur

```bash
APP_MIN_VERSION=99.0.0
APP_FORCE_UPDATE=true
# → tous les users voient l'écran bloquant plein écran
```

### Test API direct

```bash
curl "https://capable-gratitude-production-db51.up.railway.app/api/config/app-version" | jq
```

## Fichiers du code

- Backend : `/app/backend/routes/config.py`
- Service frontend : `/app/frontend/src/services/appVersion.ts`
- Composants : `/app/frontend/src/components/ForceUpdateScreen.tsx` +
  `/app/frontend/src/components/UpdateAvailableBanner.tsx`
- Wire : `/app/frontend/src/context/AuthContext.tsx` (priorité MAX)
- Banner display : `/app/frontend/app/dashboard.tsx`
