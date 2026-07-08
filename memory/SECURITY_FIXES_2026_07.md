# 🔐 Correctifs sécurité (audit juillet 2026) — APPLIQUÉS & VÉRIFIÉS

Suite à l'audit de sécurité (verdict FAIL). Toutes les failles corrigées le 08/07/2026.

## SEC-001 [CRITIQUE] — Effacement anonyme de toute la base ✅
- `routes/company.py::platform_db_cleanup` : ajout de `Depends(require_platform_owner)`
  (JWT propriétaire obligatoire) + comparaison du token en temps constant (`hmac.compare_digest`).
- `server.py` : suppression de la page publique `/_admin/cleanup-ui`.
- Vérifié : anonyme → 401, ancien token → 403, propriétaire+bon token+confirm invalide → 400 (pas de suppression).

## SEC-002 [CRITIQUE] — Secret JWT par défaut (tokens falsifiables) ✅
- `db.py` : `_require_strong_secret()` — fail-fast au boot si JWT_SECRET / PLATFORM_ADMIN_TOKEN
  absent, < 32 car., ou valeur par défaut connue.
- Secrets forts générés et ajoutés à `backend/.env` (JWT_SECRET, PLATFORM_ADMIN_TOKEN — 64 car. token_urlsafe).
- ⚠️ Changer JWT_SECRET a invalidé les sessions existantes (reconnexion requise — normal).
- ⚠️ En PROD (Railway/déploiement), il FAUT définir ces 2 variables d'env, sinon le backend refuse de démarrer.

## SEC-003 [ÉLEVÉE] — Code de reset renvoyé dans la réponse API ✅
- `routes/auth.py::forgot-password` : suppression du bloc `beta_reset_code`. Le code n'est
  transmis QUE par email. Vérifié : réponse = {ok, message} sans code.

## SEC-004 [ÉLEVÉE] — Code source téléchargeable sans auth ✅
- `server.py` : routes supprimées → `/_downloads/frontend-source`, `/_downloads/backend-railway`,
  `/_downloads/file/{which}`, `/_downloads/railway-update`, `/_downloads/railway-fix-stripe`.
  (backend-railway renvoie 404.) Vérifié : toutes → 404.
- Restent (bénins) : images/screenshots marketing, HTML site.

## SEC-005 [ÉLEVÉE] — Outils internes via auto-inscription email propriétaire ✅
- `routes/auth.py::register` : blocage 403 si l'email est dans `PLATFORM_OWNER_EMAILS`.
- Les comptes propriétaires doivent être provisionnés via seed (bypass l'endpoint register). Vérifié : 403.

## Hardening restant (P3, non bloquant)
- CORS `allow_origins=["*"]` : laissé tel quel (app en bearer token, pas de cookies) pour ne pas
  casser le preview Expo. À restreindre en prod si besoin.
- Rate limiting login/forgot-password/reset : à ajouter (throttling).
- vat_validator fail-open si VIES down : acceptable (inscription iOS désactivée).

## ⚠️ RAPPEL DÉPLOIEMENT PROD
Définir dans l'environnement du backend déployé :
  JWT_SECRET=<secret fort ≥32 car>
  PLATFORM_ADMIN_TOKEN=<secret fort ≥32 car>
Sinon le backend NE DÉMARRE PAS (fail-fast volontaire).
