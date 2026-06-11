# 🍎 RE-SOUMISSION APPLE — Build 8 (v1.1.0)

**Date** : 11 juin 2026
**Refus initial** : 5 juin 2026 — Build 1.0.0 (7) — Guidelines 2.2 (Beta) + 3.1.1 (Payments)
**Build correctif** : 1.1.0 (8) — EAS build ID `f20c9b28-be44-4fe2-8c8b-ba0c6dbcc037`

---

## ✅ CORRECTIFS APPLIQUÉS DANS LE BUILD 8

### Guideline 3.1.1 (Payments) — tous les prix/CTA Stripe retirés d'iOS
| Écran | Avant (build 7) | Après (build 8, iOS uniquement) |
|---|---|---|
| Mon abonnement | Liste des 3 plans + prix + "Démarrer l'essai gratuit" → checkout Stripe | Bandeau neutre "Gestion du compte" sans prix, sans URL, sans CTA |
| Profil société | "Compte Entreprise — 54,99 €/mois", "PASSER EN COMPTE ARTISAN (24,99 €/mois)" | Mêmes libellés **sans aucun prix** |
| Modal changement de formule | Prix affichés | Prix masqués sur iOS |
| Équipe (siège supplémentaire) | "+4,99 €/mois" + encadré prix | Encadré prix masqué sur iOS |
| Parrainage | "Dès qu'il paie son abonnement… depuis mesurechassis.com" | "Dès l'activation de son abonnement" (aucune URL d'achat) |
| Inscription | Prix déjà masqués sur iOS (déjà OK build courant) | inchangé |

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

Thank you for your detailed review. We have addressed both issues in a new build (version 1.1.0, build 8).

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

1. ✅ Build 8 lancé sur EAS (auto-incrément 7→8, certificats existants réutilisés)
   - Suivi : https://expo.dev/accounts/michelpezzuto/projects/mesurechassis/builds/f20c9b28-be44-4fe2-8c8b-ba0c6dbcc037
2. ⏳ Quand le build est terminé : soumission TestFlight
   - Il manque l'`ascAppId` (Apple ID numérique de l'app) dans `eas.json` → demandé au client
   - Commande : `eas submit --platform ios --id f20c9b28-be44-4fe2-8c8b-ba0c6dbcc037`
3. ⏳ Dans App Store Connect :
   - Sélectionner le build 1.1.0 (8) sur la fiche version
   - Renseigner le compte démo dans App Review Information
   - Répondre au message d'Apple avec le texte ci-dessus
   - "Soumettre à nouveau à l'équipe de vérification des apps"

## ⚠️ POINTS DE VIGILANCE POST-APPROBATION
- La clé Stripe backend est en mode TEST (`sk_test_…`) → basculer en clé LIVE avant la commercialisation web (sans impact Apple).
- `MC_AUTO_VERIFY_ON_REGISTER=1` (auto-vérification email active sur prod) — à durcir plus tard si besoin.
