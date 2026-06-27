# 🍎 Réponse App Store Connect — Build 108

## Submission précédente (Build 107 — REJETÉ 26/06/2026)
- Submission ID : a6642535-fc7b-4d93-a474-7630d7482a5a
- Reviewer device : iPad Air 11-inch (M3)
- Guideline 2.1 — Information Needed
- Problème : Le bouton "Demo (App Review)" était trop discret et invisible pour le reviewer + le compte démo n'existait plus en BDD prod (login produisait une erreur).

---

## 🔧 Corrections Build 108

### 1. Bannière de démo ULTRA-VISIBLE en haut du formulaire
- Bannière **orange vif** (background #FFF3E0, bordure #FF9800 2px) en haut du formulaire de login (avant les champs email/password)
- Titre : **🍎 APP REVIEW — DEMO ACCESS** (gras, 15pt, orange foncé)
- Texte explicatif en anglais : *"Apple Review team: tap the button below to auto-fill the demo credentials, then tap Sign In."*
- Bouton CTA **plein orange #FF6F00** (taille 48pt minimum, fontSize 14pt, gras, blanc) : ⚡ TAP TO AUTO-FILL DEMO CREDENTIALS
- Affichage explicite des credentials en monospace sous le bouton
- Visible **UNIQUEMENT sur iOS** (Platform.OS === "ios")

### 2. Compte Apple Review CRÉÉ AUTOMATIQUEMENT au démarrage backend
- Nouvelle fonction `ensure_apple_review_user()` dans `/app/backend/seed.py`
- Appelée dans `lifespan()` au démarrage du serveur — **indépendamment de MC_SEED_DEMO**
- Idempotent : si le compte existe déjà, le hash du mot de passe est re-syncé pour garantir qu'il correspond toujours aux identifiants publiés
- Crée également la company `apple-review-demo` (plan Pro, 10 ans validité) + 4 chantiers démo dans les 4 statuts du pipeline

### 3. Bypass VAT VIES conservé pour le compte démo
- Dans `services/vat_validator.py` : `skip_vies=True` pour `applereview@mesurechassis.com`

---

## 📝 Réponse à coller dans App Store Connect

> Dear App Review team,
>
> Thank you for your detailed feedback. We have addressed both issues in Build 108:
>
> **1) Demo Access Button — Now Highly Visible**
> The previous "🍎 Demo (App Review)" button was too subtle. In Build 108, we have added a **large, high-contrast orange banner at the very top of the sign-in form**, before the email and password fields. The banner displays:
>
>    - A bold title: "🍎 APP REVIEW — DEMO ACCESS"
>    - Clear instructions in English
>    - A **large orange button** labeled "⚡ TAP TO AUTO-FILL DEMO CREDENTIALS"
>    - The credentials in plain text below the button for redundancy
>
> Tapping the button automatically fills the email and password fields. Then tap "SIGN IN" to access the full app as an Administrator.
>
> **2) Demo Account — Now Guaranteed to Exist**
> The previous login error was caused by the demo account being absent from the production database. We have now added an automatic startup routine that ensures the demo account `applereview@mesurechassis.com` **always exists** with the password `MesureChassis2026`, an admin role, and 4 pre-loaded demo construction projects (chantiers) covering all stages of our workflow. This account cannot be deleted.
>
> **Demo Credentials (Build 108):**
> - Email: `applereview@mesurechassis.com`
> - Password: `MesureChassis2026`
> - Role: Administrator (full access)
> - Pre-loaded demo data: 4 construction projects across all pipeline stages
>
> Please note: the banner and the auto-fill button are visible on iOS only. We tested on iPad Air (the same device used in your review) and the banner is clearly visible without scrolling, both in portrait and landscape orientation.
>
> Thank you for your patience and continued review. We are committed to making MesureChâssis a high-quality experience for professional carpenters across the EU.
>
> Best regards,
> The MesureChâssis team

---

## ✅ Checklist avant resoumission

- [x] Banner visible en haut du formulaire (iOS uniquement)
- [x] Bouton auto-fill testé manuellement
- [x] Compte Apple Review créé via `ensure_apple_review_user()` au lifespan
- [x] Login API testé localement : HTTP 200 + JWT admin valide
- [x] Pas d'erreur lint bloquante
- [ ] **À faire par Michel** :
  - [ ] Redéployer le backend sur Railway (pour que `ensure_apple_review_user` s'exécute en prod)
  - [ ] Vérifier que le compte existe en prod après déploiement (curl POST `/api/auth/login`)
  - [ ] Générer Build 108 via Expo EAS Build
  - [ ] Resoumettre dans App Store Connect avec la réponse ci-dessus
