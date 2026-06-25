# Apple Review Response — Build 107

## Texte à copier-coller dans la réponse Apple via App Store Connect

---

**Subject:** Build 107 — Both issues addressed

Hello App Review Team,

Thank you for your detailed feedback on Build 106. We have submitted Build 107 with both issues fully addressed.

**Guideline 2.1 — Login fix:**
We identified that the on-screen keyboard on iPad Pro may insert invisible characters (trailing space or auto-capitalization) into the password field, causing authentication to fail. In Build 107 we now:
1. Aggressively `.trim()` both the email and password inputs before submitting.
2. To make testing seamless, we have added a discrete "🍎 Demo (App Review)" button directly on the login screen. **One tap pre-fills the demo credentials** so the reviewer can sign in in 2 taps with zero typing.
3. All error messages on the login screen are now fully localized in EN / FR / NL (in Build 106 the error popup was hardcoded in French, which was confusing in the English-language test environment).

The demo account is verified working in production:
- Email: applereview@mesurechassis.com
- Password: MesureChassis2026

**Guideline 4 — External browser:**
In Build 106, we had implemented Safari View Controller (SFSafariViewController via `expo-web-browser`) for the registration link, but you indicated this was still considered a "default web browser" experience. We have therefore taken the most conservative approach in Build 107:

**We have completely removed any external link from the sign-in screen.** There is no longer any button or link that opens a webpage from the sign-in screen. The app is now a pure "sign-in only" experience consistent with our strict B2B positioning — accounts are created exclusively through our enterprise onboarding process, outside of the app.

To test:
1. Open the app
2. Tap the "🍎 Demo (App Review)" button at the bottom of the sign-in screen
3. Tap "SIGN IN"

You will be signed in as "Apple Reviewer" (Administrator role) with access to 3 sample projects (M. Lefèvre, Mme Dubois, Dr. Martin) and the full feature set of the app (measurement wizard, PDF exports, AI chatbot, team management, etc.).

Thank you for your patience and your thorough review. We hope Build 107 meets all guidelines.

Best regards,
The MesureChâssis Team

---

## Notes internes

### Fichiers modifiés Build 107
- `/app/frontend/app/index.tsx` :
  - Lignes 1-25 : suppression import `WebBrowser`
  - Lignes 86-92 : suppression bloc commentaire + fonction `openRegistrationWebsite()`
  - Lignes 209-275 : trim email/password + reorder if-chain pour i18n
  - Lignes 776-810 : suppression bloc iOS footer "Pas encore de compte ?"  + ajout bouton "🍎 Demo (App Review)"
  - Lignes 1530-1555 : nouveaux styles `demoBtn`/`demoText`
- `/app/frontend/src/i18n/locales/{fr,en,nl}.json` : ajout clés `auth.loginErrors.*` et `auth.demo.*`

### Tests validés (testing agent iteration 22 + 23)
- ✅ Backend : 7/7 PASS (login applereview → 200 admin, wrong → 401, regression admin/tech intact)
- ✅ Frontend EN : Alert "Error / Incorrect email or password."
- ✅ Frontend NL : Alert "Fout / Onjuist e-mailadres of wachtwoord."
- ✅ Frontend FR : Alert "Erreur / Email ou mot de passe incorrect."
- ✅ Success path : demo button → login → /dashboard avec 3 chantiers démo + role admin
- ✅ Aucun lien externe vers mesurechassis.com sur l'écran login (vérifié visuellement)

### À vérifier avant submission
1. Bumper `versionCode` Android dans `app.json` (auto-handled by EAS) et `buildNumber` iOS si nécessaire.
2. Le bandeau orange "Accès TOTAL GRATUIT" est déjà masqué sur iOS via `Platform.OS === "ios" return null` dans `FreebieCountdown.tsx` ligne 81 — pas d'action nécessaire.

### Backlog post-Apple-approval
- Voir `/app/memory/TODO_POST_APPLE_REVIEW.md` (expansion européenne, traductions, relance emails)
- Refactor `index.tsx` (1533 lignes) en sous-composants `LoginForm.tsx`/`RegisterForm.tsx`
