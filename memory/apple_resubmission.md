# 🍎 RE-SOUMISSION APPLE — Build 9 (v1.1.0)

**Date** : 11 juin 2026
**Refus initial** : 5 juin 2026 — Build 1.0.0 (7) — Guidelines 2.2 (Beta) + 3.1.1 (Payments)
**Build correctif** : 1.1.0 (**9**) — EAS build ID `3d58849f-d360-4a96-81ef-0e0ac914b91e`

## 🚨 ATTENTION : NE PAS UTILISER LE BUILD 8 !
Le build 1.1.0 (8) contient un bug critique découvert après compilation : un `)}` parasite dans
`dashboard.tsx` qui fait **planter le Dashboard sur iOS** (texte brut dans une View). Corrigé dans le build 9.
➡️ Dans App Store Connect, sélectionner uniquement le build **1.1.0 (9)**.

---

## ✅ CORRECTIFS APPLIQUÉS DANS LE BUILD 9

### Guideline 3.1.1 (Payments) — tous les prix/CTA Stripe retirés d'iOS
| Écran | Avant (build 7) | Après (build 8, iOS uniquement) |
|---|---|---|
| Mon abonnement | Liste des 3 plans + prix + "Démarrer l'essai gratuit" → checkout Stripe | Bandeau neutre "Gestion du compte" sans prix, sans URL, sans CTA |
| Profil société | "Compte Entreprise — 54,99 €/mois", "PASSER EN COMPTE ARTISAN (24,99 €/mois)" | Mêmes libellés **sans aucun prix** |
| Modal changement de formule | Prix affichés | Prix masqués sur iOS |
| Équipe (siège supplémentaire) | "+4,99 €/mois" + encadré prix | Encadré prix masqué sur iOS |
| Parrainage | "Dès qu'il paie son abonnement… depuis mesurechassis.com" | "Dès l'activation de son abonnement" (aucune URL d'achat) |
| Inscription | Prix déjà masqués sur iOS (déjà OK build courant) | inchangé |

**Bonus build 9** : le masquage des prix s'applique désormais aussi sur **Android** (conformité Google Play Billing) — seul le web affiche les plans/prix Stripe.

### Guideline 2.2 (Beta) — tout le wording "beta/test" supprimé (toutes plateformes)
- Badge "BETA GRATUITE" → **"OFFRE DE LANCEMENT"** (FR) / "LAUNCH OFFER" (EN) / "LANCERINGSAANBOD" (NL)
- "pendant la phase de test. Aucun paiement n'est requis" → "offert pendant la période de lancement"
- Bannière dashboard "BETA · gratuit" → "OFFRE DE LANCEMENT"
- "(Bluetooth laser, à venir)" supprimé de l'écran d'inscription
- ⚠️ Note : le "Environnement de test" Stripe vu par Apple n'est plus atteignable depuis iOS (aucun checkout possible)

---

## 👤 COMPTE DÉMO POUR LES REVIEWERS (créé sur la prod Railway)

- **Email** : `applereview@mesurechassis.com`
- **Mot de passe** : `AppleReview2026!`
- Type : Artisan solo (accès complet immédiat, pas de config d'équipe requise)
- Données : 1 chantier de démo "Dupont Jean — 12 Avenue Louise, 1050 Bruxelles"
- ✅ Login vérifié sur `https://capable-gratitude-production-db51.up.railway.app`

À renseigner dans **App Store Connect → Version iOS → Informations sur la vérification de l'app → Connexion requise**.

---

## ✉️ RÉPONSE À ENVOYER À APPLE (copier-coller dans le fil de messages App Store Connect)

```
Hello,

Thank you for your detailed review. We have addressed both issues in a new build (version 1.1.0, build 9).

Guideline 3.1.1 — Payments:
MesureChâssis is a B2B SaaS tool for professional window-installation companies. In the new build, the iOS app no longer contains any subscription purchase flow, pricing information, or payment call-to-action of any kind. All purchasing UI has been removed from the iOS binary, and the app does not link out to any external payment mechanism. Subscriptions are sold separately, outside the app, and the iOS app is only used to access an existing account (multiplatform service, Guideline 3.1.3(b)).

Guideline 2.2 — Beta Testing:
The "free beta" badge shown in the previous build was misleading wording for a commercial launch offer, not an actual beta test. MesureChâssis is a complete, fully functional production product: project management, full measurement wizard, multilingual PDF/CSV exports, team roles, and email notifications are all fully implemented. We have removed all "beta/test" wording from the app.

A demo account with sample data is provided in the App Review Information section:
Email: applereview@mesurechassis.com
Password: AppleReview2026!

Suggested test flow: log in → open the demo project "Dupont Jean" → tap "+ Nouvelle mesure" to use the full measurement wizard → generate a PDF export from the project screen.

Thank you for your time and consideration.
```
(⚠️ Le texte mentionne "version 1.1.0, build 8" dans la 1ère phrase d'origine : dire **build 9**.)

---

## 📝 NOTES POUR "APP REVIEW INFORMATION" (champ Notes)

```
MesureChâssis is a B2B SaaS application for professional window-installation companies (joinery/carpentry). It is used by company admins, sales reps and technicians to record on-site window measurements, manage measurement projects, and export technical PDF/CSV documents for production.

The demo account provided is a solo "Artisan" account with full access and pre-loaded sample data. No purchase is required or possible inside the iOS app: subscriptions are handled entirely outside the app.

Test flow:
1. Log in with the provided credentials.
2. Open the sample project "Dupont Jean".
3. Tap "+ Nouvelle mesure" to launch the measurement wizard (window type, dimensions, options).
4. Back on the project screen, use "Export PDF" to generate the technical document.
```

---

## 🚀 ÉTAPES RESTANTES

1. ✅ Build 9 compilé sur EAS et soumission App Store Connect lancée (automatique)
   - Suivi : https://expo.dev/accounts/michelpezzuto/projects/mesurechassis/builds/3d58849f-d360-4a96-81ef-0e0ac914b91e
2. ⏳ Dans App Store Connect :
   - Sélectionner le build **1.1.0 (9)** sur la fiche version (PAS le 8 !)
   - Renseigner le compte démo dans App Review Information
   - Répondre au message d'Apple avec le texte ci-dessus (corriger "build 9")
   - "Soumettre à nouveau à l'équipe de vérification des apps"
3. 🤖 Android : build AAB en file d'attente EAS — `81fe2c95-aa4e-4288-bf71-8c3efc5f3593`
   - Fiche Play Store complète : `/app/memory/play_store_listing_fr.md`

## ⚠️ POINTS DE VIGILANCE POST-APPROBATION
- La clé Stripe backend est en mode TEST (`sk_test_…`) → basculer en clé LIVE avant la commercialisation web (sans impact Apple).
- `MC_AUTO_VERIFY_ON_REGISTER=1` (auto-vérification email active sur prod) — à durcir plus tard si besoin.
