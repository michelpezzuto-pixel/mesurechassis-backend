# 🍎 Réponse App Store Connect — Build 110

## Submission précédente (Build 109 — REJET PARTIEL 30/06/2026)
- ✅ **Progrès énorme** : reviewer a réussi à se connecter (auto-login fonctionne)
- ❌ 3 nouveaux points soulevés :
  - **5.1.1(ii)** : photo library purpose string trop générique
  - **3.1.1 + 3.1.3(c)** : Enterprise Services vs IAP — Apple voit des services qui pourraient être vendus aux particuliers
  - **2.1** : besoin d'un compte démo NON-admin pour tester les autres rôles

---

## ✅ Corrections Build 110

### 1. Purpose strings enrichis (5.1.1)
Mis à jour dans `/app/frontend/app.json` avec exemples concrets :

- **NSCameraUsageDescription** : "MesureChâssis utilise l'appareil photo pour permettre aux menuisiers professionnels de photographier les ouvertures (fenêtres, châssis, baies) lors de leurs prises de mesures sur chantier. Exemple : prendre une photo d'une fenêtre PVC à remplacer et l'attacher à la fiche de mesure du client pour validation atelier."
- **NSPhotoLibraryUsageDescription** : "MesureChâssis accède à votre photothèque pour permettre aux menuisiers professionnels d'attacher des photos existantes à leurs fiches de mesures de chantier. Exemple : sélectionner une photo prise précédemment d'une porte d'entrée à remplacer pour la joindre au dossier client lors de la création du devis."
- **NSPhotoLibraryAddUsageDescription** : "MesureChâssis enregistre les exports PDF de fiches de mesures dans votre photothèque pour partage et archivage. Exemple : sauvegarder le PDF récapitulatif d'un chantier de 5 châssis livrés au client dans vos photos pour le retrouver facilement."
- **NSMicrophoneUsageDescription** : "MesureChâssis utilise le microphone pour la dictée vocale des notes de chantier. Exemple : dicter à voix haute 'pose en applique côté rue, prévoir cale de 10mm' pendant la prise de mesures, sans avoir à taper au clavier les mains occupées par le mètre."

### 2. Compte démo TECHNICIEN ajouté (2.1)
- Email : `applereview-tech@mesurechassis.com`
- Password : `MesureChassis2026`
- Rôle : `technician` (pas Administrateur)
- Même company que l'admin (`apple-review-demo`) → permet de voir le RBAC en action
- Auto-créé via `ensure_apple_review_user()` au lifespan backend

### 3. Argumentation Enterprise Services (3.1.1 + 3.1.3(c))
Aucune modification de code (le code iOS est déjà strict B2B). Argumentation écrite dans la réponse Apple expliquant clairement le modèle :
- L'app iOS est **login-only** : pas d'inscription, pas d'achat in-app
- Les comptes sont **provisionnés par les entreprises clientes** via leur back-office web (sur mesurechassis.com)
- L'entreprise paie par facturation B2B (virement SEPA, Stripe Business)
- L'utilisateur iOS est un **employé** d'une entreprise — exactement le cas 3.1.3(c) Enterprise Services

---

## 📝 Réponse à coller dans App Store Connect — Reply to App Review

```
Dear App Review team,

Thank you for the detailed feedback on Build 109. We are pleased
that the demo sign-in worked smoothly with our new one-tap banner.
We have addressed all three new issues in Build 110.

═══════════════════════════════════════════════════════════════
1) PURPOSE STRINGS — Updated with concrete examples (5.1.1)
═══════════════════════════════════════════════════════════════

All four purpose strings (Camera, Photo Library, Photo Library
Add, Microphone) have been rewritten with detailed explanations
and concrete usage examples relevant to our professional carpenter
workflow. Example for Photo Library:

"MesureChâssis accesses your photo library to allow professional
carpenters to attach existing photos to their on-site measurement
records. Example: select a previously taken photo of a front door
to be replaced, to attach it to the client file when creating the
quote."

═══════════════════════════════════════════════════════════════
2) NON-ADMINISTRATOR DEMO ACCOUNT (2.1)
═══════════════════════════════════════════════════════════════

We have added a second demo account with a TECHNICIAN role so
you can review the role-based access control (RBAC) of our app.

Primary demo account (Administrator):
  Email:    applereview@mesurechassis.com
  Password: MesureChassis2026
  Role:     Administrator (full access)

Secondary demo account (Technician — non-admin):
  Email:    applereview-tech@mesurechassis.com
  Password: MesureChassis2026
  Role:     Technician (field measurement only)

Both accounts belong to the same demo company and have access to
the same 4 demo construction projects. The Technician role has
restricted access (no team management, no statistics, no admin
features) — only project assignment and on-site measurements.

To switch accounts on the sign-in screen, sign out (top right
button in the dashboard) and use the credentials above.

═══════════════════════════════════════════════════════════════
3) ENTERPRISE SERVICES — B2B-ONLY MODEL (3.1.1 + 3.1.3(c))
═══════════════════════════════════════════════════════════════

MesureChâssis is an exclusively B2B Enterprise SaaS service for
professional carpentry companies, equivalent in business model
to Slack, Notion Enterprise, or Microsoft Teams for Business.

KEY POINTS ABOUT OUR BUSINESS MODEL:

  • The iOS app is LOGIN-ONLY. No registration is possible from
    iOS. The "Inscription" tab is HIDDEN on iOS.

  • User accounts are PROVISIONED EXCLUSIVELY BY BUSINESS
    CUSTOMERS (window/door manufacturing companies). A company
    administrator invites their employees (commercials and
    field technicians) through our web back-office at
    mesurechassis.com.

  • Subscriptions are sold to CARPENTRY COMPANIES, not to
    individual end-users. Billing is handled via standard B2B
    methods (SEPA bank transfer, Stripe Business invoicing,
    quarterly enterprise invoicing). NO individual consumer
    can purchase a subscription.

  • The end-user of the iOS app is always an EMPLOYEE acting
    on behalf of their employer. They never make a purchase
    decision — they are field technicians taking on-site
    measurements as part of their professional job.

  • The app is specifically designed for the European window
    and door manufacturing trade (B2B EU VAT-registered
    professionals only — we require a valid European VAT
    number for company registration).

This is precisely the use case described in Guideline 3.1.3(c)
"Enterprise Services": services sold to organizations whose
employees use the app to perform their work.

We do not market or sell to individual consumers, families,
or single users. The only entry point to our service is via
B2B contact with our sales team on mesurechassis.com. The
iOS app is a tool for employees of companies that have
already subscribed.

For your reference, this is the same model used by:
  • Slack (B2B SaaS, no IAP)
  • Notion Enterprise (B2B SaaS, no IAP)
  • Microsoft Teams for Business (B2B SaaS, no IAP)
  • Salesforce Mobile (B2B SaaS, no IAP)
  • Asana for Teams (B2B SaaS, no IAP)

═══════════════════════════════════════════════════════════════
SUMMARY OF BUILD 110 CHANGES
═══════════════════════════════════════════════════════════════

  ✓ All purpose strings rewritten with concrete examples
  ✓ Technician demo account added (non-admin)
  ✓ One-tap admin sign-in banner preserved from Build 109
  ✓ Login-only iOS workflow preserved (no in-app signup)
  ✓ No in-app purchases (B2B Enterprise Service)

Thank you for your continued patience and detailed review.

Best regards,
The MesureChâssis team
```

---

## 📝 Remarques (App Review Information → Notes)

```
DEMO ACCOUNTS for Build 110:

  Administrator (default — one-tap auto-login):
    Email:    applereview@mesurechassis.com
    Password: MesureChassis2026

  Technician (non-admin, restricted access):
    Email:    applereview-tech@mesurechassis.com
    Password: MesureChassis2026

ONE-TAP SIGN IN — A large orange banner is displayed at the top
of the sign-in form with a button "⚡ TAP TO SIGN IN AS APP
REVIEW" — one tap auto-signs you in as Administrator.

To test the Technician account: from the dashboard, tap the
sign-out icon (top right), then on the sign-in screen, manually
type the technician credentials.

BUSINESS MODEL: B2B Enterprise SaaS for professional carpentry
companies (Guideline 3.1.3(c)). The iOS app is LOGIN-ONLY — no
in-app registration, no in-app purchases. Accounts are
provisioned by carpentry companies for their employees via the
web back-office (mesurechassis.com). Subscriptions are billed
to companies via SEPA/Stripe Business invoicing. Same model as
Slack, Notion Enterprise, Microsoft Teams for Business.

Both accounts have full access to 4 pre-loaded demo
construction projects covering all pipeline stages.
```

---

## ✅ Checklist avant resoumission

- [x] Photo library purpose string enrichi avec exemple concret
- [x] Camera, Microphone, PhotoLibraryAdd purpose strings également enrichis
- [x] Compte technicien `applereview-tech@mesurechassis.com` créé en BDD
- [x] Login API testé : admin OK + technician OK
- [x] `ensure_apple_review_user()` mis à jour pour gérer les 2 comptes
- [x] buildNumber passé à 110
- [ ] **À faire par Michel** :
  - [ ] **Régénérer un build iOS** via Emergent (le bouton "Générer un nouveau build")
  - [ ] Vérifier sur TestFlight que les 2 comptes fonctionnent
  - [ ] Sélectionner Build 110 dans App Store Connect
  - [ ] Coller "Remarques" et "Reply to App Review" ci-dessus
  - [ ] Submit for Review
