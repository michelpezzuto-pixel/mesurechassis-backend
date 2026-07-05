# Build 115 — Correctif rejet Apple Guideline 2.1(a) (Build 114)

## Rejet Apple (04/07/2026, iPad Air 11" M3, iPadOS 26.5.2)
« An error message appeared when we signed in with the provided expired demo account. »
→ Alerte « Erreur — Chargement impossible. » par-dessus le dashboard au lieu du PaywallScreen.

## Cause racine (triple bug)
1. **Backend** `routes/company.py::_to_profile` renvoyait `beta_mode=BETA_MODE` (true) pour TOUTES
   les sociétés, y compris `apple-review-expired` → le frontend masquait le paywall
   (condition `!company?.beta_mode` dans AuthContext.tsx).
2. **Frontend race** `src/services/api.ts` : l'intercepteur axios effaçait le verrou paywall à
   CHAQUE réponse réussie (ex: push token, /auth/me) → le paywall se démontait, le dashboard
   se montait, `/chantiers` renvoyait 402 → alerte générique.
3. **Frontend** `app/dashboard.tsx` + `app/admin/stats.tsx` : alerte générique « Chargement
   impossible » affichée même sur HTTP 402.

## Correctifs appliqués (05/07/2026)
- `backend/routes/company.py` : `beta_mode=BETA_MODE and company_id != "apple-review-expired"`.
- `frontend/src/services/api.ts` : suppression du « success clears lock » — le verrou n'est levé
  que par `fetchCompany()` (AuthContext) ou `signOut()`.
- `frontend/app/dashboard.tsx` + `frontend/app/admin/stats.tsx` : pas d'alerte si status 402.

## Validation (testing_agent, iteration_24.json)
- Backend 5/5 pytest : beta_mode=false (expiré) / true (actif), 402 subscription_expired, 200 actif.
- Frontend : paywall « ACCÈS BLOQUÉ » immédiat, 0 alerte, stable 10s, logout OK, compte actif sans régression.
- Tests créés : `/app/backend/tests/test_build_114_apple_paywall.py`.

## Statut
- Build 115 SOUMIS à Apple le 05/07/2026 (16e soumission). EN ATTENTE de review.
- ⚠️ L'utilisateur doit avoir republié le backend en prod pour que le fix beta_mode soit actif.
