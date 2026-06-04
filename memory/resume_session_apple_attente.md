# 🍎 SESSION EN ATTENTE — Apple Review

**Date** : 4 juin 2026
**Statut** : Apple examine Build 7 (1.0.0 / 7) — soumission iOS faite à 09h22

---

## 📍 OÙ ON EN EST

### ✅ FAIT en mode "live" (corrections appliquées dans le code mais pas dans Build 7)

#### Backend (`/app/backend/`)
1. `routes/chantiers.py` :
   - ✅ `assigned_to` **obligatoire** à la création en mode Entreprise (Admin)
   - ✅ Vérif que l'assignee existe dans la même company
   - ✅ Chantier démarre directement en `a_mesurer` (skip `devis_a_faire`) si Admin avec assigned_to
   - ✅ Transitions nouvelles :
     - `(a_verifier → a_mesurer)` : technician (renvoi commercial)
     - `(technique_a_valider → a_mesurer)` : technician
     - `(en_fabrication → a_verifier)` : technician (renvoi tardif)
     - `(en_fabrication → cloture)` : admin + technician (était tech seul)
     - `(a_verifier → cloture)` : admin uniquement
   - ✅ Email automatique Tech + Admin quand statut passe à `a_verifier` (send_ready_for_verification_email)
   - ✅ Nouveaux endpoints :
     - `POST /chantiers/{id}/mod-request` (commercial)
     - `POST /chantiers/{id}/mod-request/respond` (technician/admin)
2. `models.py` : champ `mod_request` exposé dans `Chantier`
3. `email_service.py` :
   - ✅ `send_verification_email` updated avec mention "Votre inscription a bien été enregistrée"
   - ✅ `send_ready_for_verification_email` nouvelle fonction

#### Frontend (`/app/frontend/app/`)
1. `dashboard.tsx` :
   - ✅ Sélecteur "Commercial à assigner" obligatoire à la création (mode Entreprise)
   - ✅ Fetch automatique de la liste via `/users` + refetch à ouverture du modal
   - ✅ Filtre insensible à la casse
   - ✅ Redirect dashboard auto pour Admin (pas vers le chantier créé)
2. `chantier/[id]/index.tsx` :
   - ✅ Cartes ouvertures cliquables pour TOUS les rôles (Admin ouvre en lecture seule)
   - ✅ Bouton "↩️ Demander au technicien de modifier" (Commercial sur a_verifier)
   - ✅ Bannière "📢 Demande de modification" + boutons Approuver/Refuser (Technicien)
   - ✅ Bouton "↩️ Renvoyer au commercial pour correction" (Technicien sur a_verifier)
3. `chantier/[id]/mesure/[mesure_id].tsx` (NOUVEAU FICHIER) :
   - ✅ Page de consultation lecture seule pour Admin/non-éditeurs
   - ✅ Bandeau jaune "Mode consultation"
4. `admin/team.tsx` :
   - ✅ Fix iOS autofill mot de passe : `textContentType="oneTimeCode"` + `autoComplete="off"`
5. `index.tsx` (login screen) :
   - ✅ Tentative fix clavier Samsung : `behavior={undefined}` sur Android

### 🧪 TESTS RÉALISÉS
- Backend 20/20 PASS (deep_testing_backend_v2)
- Email Tech+Admin testé E2E : OK
- Preview web (Chrome) : tout testé et fonctionnel
- iPhone (Build 7 TestFlight) : login OK, fonctionnalités de base OK, MAIS bugs identifiés présents (autofill iOS, pas de workflow Demande modif, pas de carte ouverture cliquable pour Admin)

---

## 📦 BUILD 8 — PRÊT MAIS PAS LANCÉ

Quand on relancera le build :
```powershell
cd C:\Users\micha\Downloads\mesurechassis-frontend  # le récupérer à jour d'abord
eas build --platform ios --profile production
```

Soumission auto via eas submit (clé API déjà enregistrée chez Expo).

---

## 🎯 QUOI FAIRE QUAND APPLE RÉPOND

### Si ✅ approuvé :
1. Publier manuellement Build 7 sur l'App Store (depuis App Store Connect)
2. Préparer Build 8 EAS pour les fixes + nouvelles features
3. Soumettre Build 8 à la revue Apple en parallèle
4. Reprendre Google Play Store (12 testeurs)

### Si ❌ refusé (mineur) :
1. Capture de l'email Apple
2. Préparer Build 8 EAS qui contient déjà les fixes
3. Répondre via Resolution Center
4. Re-soumettre Build 8

### Si ❌ refus sérieux :
1. Analyser le motif
2. Discuter avec Apple via Resolution Center
3. Adapter le code si besoin avant Build 8

---

## 📝 CREDENTIALS À RETENIR

### Production (Railway + TestFlight)
- Email : `info@mesurechassis.com`
- Mot de passe : `admin1234`

### Preview Local (Emergent, pour tests dev)
- Admin : `admin@mesurechassis.fr` / `admin123`
- Commercial : `commercial@mesurechassis.fr` / `commercial123`
- Technicien : `tech@mesurechassis.fr` / `tech123`
- Artisan : `artisan@mesurechassis.fr` / `artisan123`

### Apple Developer
- Apple ID : `michelpezzuto@hotmail.com`
- Team : Michel Pezzuto (2AM7T2NRS3)
- ASC App ID : 6776357930
- Bundle ID : com.mesurechassis.escalier

### Expo
- Account : `michelpezzuto`
- Project ID : 12c32e71-eeb8-454b-b34d-5ab3f8bd6641

### Email Michel
- Personnel : `michelpezzuto@gmail.com` (Apple Dev notifs)
- Hotmail : `michelpezzuto@hotmail.com` (Apple Developer login)
- Pro : `info@mesurechassis.com` (production admin)

---

## 🔮 BACKLOG POUR APRÈS LE BUILD 8

### Priorité 1
- Reprendre Google Play Store : recruter 12 testeurs Gmail (Closed Testing, 14j)
- Vérifier que les emails de production sont bien envoyés (commercial, tech, admin)

### Priorité 2 (bugs/améliorations possibles)
- 🟡 Bug clavier Samsung (à valider une fois Build 8 installé sur Samsung)
- 🟠 Stripe webhook signature (paused, à reprendre quand abonnement activé)
- 🟢 Rate limiting backend (slowapi)
- 🟢 Sanitization HTML champs libres (bleach)

### Priorité 3 (futur)
- 🟢 i18n FR/EN/NL
- 🟢 Formes complexes Wizard V2 (Plein cintre, Arc surbaissé, Angle 90°, Bow-Window)
- 🟢 Mode sombre/clair
- 🟢 Notifications push complètes
- 🟢 Refactor `chantier/[id]/index.tsx` (2700+ lignes, trop gros)

---

## 💬 NOTES DE MICHEL

- Michel n'est pas développeur — toujours instructions claires, numérotées, copier-coller
- A "toute la nuit" et a fait un boulot exceptionnel : Build iOS depuis Windows, premier essai
- A bien validé la logique RBAC : Admin = observer, Commercial = mesures, Tech = vérif/fabrication
- A demandé option A (attendre Apple) — donc on est en pause
- Va revenir avec des questions au fil de l'eau et quand Apple répondra

---

## 🚦 ACTION IMMÉDIATE POUR LE NOUVEL AGENT

L'utilisateur va revenir avec :
- Des questions ponctuelles → répondre directement
- La réponse Apple (acceptation ou refus) → suivre le plan ci-dessus
- Demande de Build 8 → préparer le zip frontend (déjà créé hier : `/app/backend/public_downloads/mesurechassis-frontend.zip` — à regénérer avec le code à jour)

**NE PAS** annuler la soumission Apple en cours.
**NE PAS** toucher au backend production Railway.
**NE PAS** modifier la fiche App Store pendant la revue.
