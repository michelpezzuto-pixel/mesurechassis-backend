# 🍎 Apple Review — Réponse Build 112

**Date** : 01/07/2026  
**Rejection Build 111** : Guidelines 3.1.1 + 3.1.3(c) (Enterprise services + IAP)

---

## 🐛 CAUSE RACINE IDENTIFIÉE

Dans le code du Build 111, l'écran `/yann` (assistant IA) affichait **encore** ces mentions visibles sur iOS :
- "Yann est inclus dans la formule **Entreprise Pro**"
- "disponible en option à **5 €/mois** sur Artisan Solo et Entreprise"
- "**14 jours d'essai**"

Bien que les écrans `/subscription` et `/company-profile` masquaient déjà les prix sur iOS, le paywall Yann laissait fuiter :
1. Les noms de plans (Artisan Solo, Entreprise Pro)
2. Le prix (5 €/mois)
3. La mention d'essai gratuit

**Apple a interprété ces mentions comme la preuve que l'app propose les mêmes services (plans payants) aux particuliers/consommateurs sans passer par IAP.**

---

## ✅ CORRECTION BUILD 112

Fichier `frontend/app/yann.tsx` — Paywall Yann :

**Sur iOS uniquement** — texte remplacé par :
> "Votre assistant IA est disponible selon votre formule professionnelle. Contactez votre administrateur pour l'activer."
> 
> "L'activation de Yann se fait par votre administrateur depuis l'espace professionnel mesurechassis.com."

**Sur Android + Web** — texte inchangé (prix visibles, bouton "Voir les formules", etc.)

---

## 📝 RÉPONSE À ENVOYER DANS APP STORE CONNECT (Réviseur)

> Hello App Review Team,
> 
> Thank you for your feedback on Build 111. We have identified and fixed the issue you pointed out.
> 
> **Root cause found:** Our AI Assistant paywall screen was leaking pricing information (subscription plan names, monthly prices, and trial period) that could suggest we were selling to individual consumers. We have removed all such references from the iOS build.
> 
> **What Build 112 fixes:**
> 
> 1. **`/yann` (AI Assistant) paywall**: On iOS, all mentions of plan names, prices, and trial periods have been replaced with a neutral B2B message directing users to contact their organization administrator.
> 
> 2. **All previously B2C-looking screens are now fully neutralized on iOS:**
>    - `/subscription`: No plan list, no prices, no "start trial" buttons on iOS.
>    - `/company-profile`: No prices on iOS.
>    - `/index` (registration): iOS blocks the registration tab entirely. iOS is login-only.
>    - `/yann`: Now shows only a neutral B2B message on iOS.
>    - `/dashboard` (freemium limit alert): Neutral message on iOS, no "See subscription" button.
> 
> **How our business model is fully B2B:**
> 
> MesureChâssis is a professional SaaS tool exclusively for carpentry/window installation businesses. All user accounts are tied to a company (`company_id`) with a validated European VAT number (SIRET/BE VAT). The subscription and billing relationship is with the **company entity**, not individual users. Even the smallest plan ("Artisan Solo") requires:
>   - A valid VAT number at signup
>   - Business ownership certification
>   - A company profile with legal information
> 
> Individual consumers or families **cannot** subscribe:
>   - Registration requires a VAT number (validated server-side)
>   - iOS blocks registration entirely (must go through mesurechassis.com website with VAT validation)
>   - No family/personal use case is supported
> 
> **iOS access model:** The iOS app functions as a **Reader / Companion** app where an already-onboarded business user can log in and use the app's tools (measurement wizard, chantier management, PDF exports). Subscription management is deferred to the company administrator, who handles billing from the web portal on a desktop browser.
> 
> **Test accounts for review (unchanged):**
>   - Admin: applereview@mesurechassis.com / MesureChassis2026
>   - Technician: applereview-tech@mesurechassis.com / MesureChassis2026
> 
> Both accounts belong to the "Apple Review Demo Co." organization with a valid VAT number (BE0000000097) and an active Enterprise Pro subscription (10-year validity for review purposes).
> 
> Please let us know if any other mentions of pricing or trial slip through the review — we will happily patch them immediately.
> 
> Thank you for your patience and thoroughness.
> 
> Best regards,
> The MesureChâssis Team

---

## 🔍 CHECKLIST FINALE AVANT SOUMISSION BUILD 112

- [x] `yann.tsx` — paywall neutralisé sur iOS (aucun prix, aucun nom de plan)
- [x] `subscription.tsx` — plans + trial masqués sur iOS (déjà fait avant)
- [x] `company-profile.tsx` — prix masqués sur iOS (déjà fait avant)
- [x] `index.tsx` — inscription bloquée sur iOS (déjà fait avant)
- [x] `dashboard.tsx` — freemium alert neutralisée sur iOS (déjà fait avant)
- [ ] **Vérifier App Store Connect** : la description du produit et les screenshots ne mentionnent PAS les prix Solo/Entreprise/Pro (à faire manuellement dans App Store Connect)
- [ ] **Vérifier App Review Notes** : ajouter la mention "iOS is a companion app for business accounts. Subscription is B2B only, requires VAT validation done via website"
- [ ] Générer Build 112 avec Emergent Publish
- [ ] Soumettre à Apple

---

## 📌 POUR L'AVENIR

Toute nouvelle feature qui mentionne "plan", "prix", "abonnement", "essai" DOIT être wrappée dans `Platform.OS !== "ios"` OU proposer une version neutre pour iOS. Créer un utilitaire :

```tsx
// /app/frontend/src/utils/appStore.ts
import { Platform } from "react-native";

export const isIOS = Platform.OS === "ios";
export const canShowPricing = Platform.OS !== "ios";
export const canShowTrial = Platform.OS !== "ios";
```

Puis dans les composants :
```tsx
{canShowPricing && <PricingCard ... />}
```
