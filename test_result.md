user_problem_statement: |
  Itération 4 — Ajout de 3 features majeures :
  1. Logo entreprise sur PDF (admin upload via Settings, injecté dans en-tête PDF)
  2. Photos de chantier (caméra/galerie, 10 max/projet, compression expo-image-manipulator, intégrées en fin de PDF)
  3. Paywall trial 90 jours (trial_start_date à l'inscription, blocage HTTP 402 sur routes critiques au-delà, écran de blocage frontend)
  Architecture: backend modularisé, shared-ui frontend, EAS Update configuré.

backend:
  - task: "Logo entreprise — upload via PUT /api/auth/me et injection PDF"
    implemented: true
    working: true
    file: "/app/backend/routers/auth.py + /app/backend/services/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "PUT /api/auth/me accepte company_logo_base64 (data URI ou raw). PDF en-tête (logo top-left + nom société + accent vert pomme + footer date/page) sur toutes les pages via SimpleDocTemplate onFirstPage/onLaterPages."
        -working: true
        -agent: "testing"
        -comment: |
          Tous les tests passent :
          - PUT /api/auth/me { company_logo_base64: "data:image/png;base64,..." } → 200, retour avec logo non vide.
          - GET /api/auth/me retourne bien le logo.
          - Création projet + sauvegarde mesure (via technicien Sophie car admin@demo.fr n'a pas solo_mode → 403 attendu pour POST measurement) + GET /export/pdf → 200 binaire débutant par `%PDF-` (5691 bytes).
          - PUT /api/auth/me { company_logo_base64: "" } → 200, et GET /auth/me confirme le logo vide.
          Note : L'attente "save measurement avec token admin@demo.fr" du brief échoue car cet admin n'a pas solo_mode et la route /measurement exige technician_powers → on a contourné en assignant Sophie. Le flow PDF avec logo fonctionne. C'est conforme à l'architecture (admin pur ne saisit pas les mesures).

  - task: "Photos de chantier — CRUD avec limite 10/projet"
    implemented: true
    working: true
    file: "/app/backend/routers/projects.py + /app/backend/models/schemas.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          Routes: GET /api/projects/{pid}/photos, POST (ajoute, max 10), PATCH /{photo_id} (caption), DELETE /{photo_id}.
          Stockage : array embarqué dans le document project { id, base64, caption, created_at }.
          Listing projects exclut photos (lean payload). PDF inclut section "Photos de chantier" en fin.
          ACL : admin (partout), solo, technicien assigné peuvent éditer ; autres seulement read via projet visible.
        -working: true
        -agent: "testing"
        -comment: |
          Tous les tests passent avec marc@mesureescalier.com (solo) :
          - GET /photos → 200 [].
          - POST /photos → 200 avec id, base64, caption "Test trémie", created_at.
          - 10 photos OK, 11ème → 400 detail="Limite atteinte (10 photos max par chantier)".
          - PATCH /photos/{id} { caption: "Mise à jour" } → 200.
          - GET /projects (liste) → champ `photos` absent (exclu). 
          - GET /projects/{pid} (détail) → photos array de 10 items présent.
          - DELETE /photos/{id} → 200.
          - Sécurité : Sophie (technicienne non assignée au projet de marc) POST /photos → 404 (projet non visible via project_visible_to → marc.id != null/sophie.id).

  - task: "Paywall trial 90 jours — compute_access_state + require_active_access"
    implemented: true
    working: true
    file: "/app/backend/core/security.py + /app/backend/core/config.py + /app/backend/services/seed.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          - TRIAL_DAYS=90 dans core/config.py.
          - Chaque user a trial_start_date (datetime). Calcul state: trial_days_remaining, is_trial_active, is_locked.
          - Register pose trial_start_date=now(). InviteUser hérite du trial_start de l'admin.
          - Dependency require_active_access() → 402 si locked. Appliqué à : projects, measurements, exports, voice, stats.
          - require_roles applique aussi le check paywall.
          - /api/auth/me reste accessible même locked (200) pour que le frontend voie l'état.
          - Seed : compte expired@demo.fr (trial_offset=100j) pour tester paywall sans attendre 90 jours.
        -working: true
        -agent: "testing"
        -comment: |
          Tous les comportements paywall vérifiés :
          - Login expired@demo.fr → 200 avec is_locked=true, trial_days_remaining=0, is_trial_active=false.
          - Login admin@demo.fr → 200 avec is_locked=false, trial_days_remaining=90 (exact).
          - Avec token expired : GET /auth/me → 200, PUT /auth/me {full_name} → 200 (édition profil OK).
          - Avec token expired : GET /projects → 402, POST /projects → 402, GET /stats → 402, POST /projects/<any>/measurement/preview → 402 (le paywall fire avant le 404).
          - Avec token admin actif : toutes ces routes → 200 (jamais 402). Preview sur projet inexistant → 200 car la route preview n'accède pas à la DB.

frontend:
  - task: "Settings — section LOGO ENTREPRISE (Admin only)"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/settings.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Pas dans le scope test (frontend testé seulement sur demande user)."

metadata:
  created_by: "main_agent"
  version: "1.6"
  test_sequence: 6
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Trois grosses features à valider backend uniquement (l'utilisateur testera le frontend lui-même sur Expo Go).

      Comptes seedés (tous mot de passe Demo1234!) :
      - admin@demo.fr (Admin)
      - marc@mesureescalier.com (Admin Solo)
      - sophie@mesureescaliee.com (Technicien)
      - expired@demo.fr (Admin Solo, trial expiré il y a 10 jours)

      Tests obligatoires : voir test_result.md backend (paywall, logo, photos) + régression.
    -agent: "testing"
    -message: |
      Itération 4 — Backend testing complet : 37/37 PASS, 0 FAIL.

      A. PAYWALL (11/11) :
        - expired@demo.fr : login OK avec is_locked=true, days=0, is_trial_active=false.
        - admin@demo.fr : login OK avec is_locked=false, days=90.
        - Token expired : GET/PUT /auth/me → 200. GET /projects, POST /projects, GET /stats, POST /projects/<any>/measurement/preview → 402.
        - Token admin actif : toutes ces routes → 200 (jamais 402).

      B. LOGO (8/8) :
        - PUT /auth/me { company_logo_base64 dataURI } → 200, GET le retourne.
        - Création projet + mesure (sauvée via Sophie technicienne car admin@demo.fr n'a pas solo_mode → l'API exige technician_powers pour POST /measurement, contournement par assign + tech token). 
        - GET /export/pdf → 200, binaire débutant par %PDF- (5691 bytes).
        - PUT /auth/me { company_logo_base64: "" } → 200, GET confirme vide.

      C. PHOTOS (9/9) :
        - CRUD complet avec marc@ (solo) sur son propre projet.
        - Limite 10 strictement appliquée (11ème → 400 "Limite atteinte (10 photos max par chantier)").
        - GET /projects (liste) exclut bien le champ photos ; GET /projects/{pid} (détail) le contient.
        - Sécurité : Sophie (non assignée) POST /photos sur projet de marc → 404 (project_visible_to filtre).

      D. NON-RÉGRESSION (10/10) :
        - Login admin/solo/tech OK.
        - CRUD project + measurement preview/save/validate OK (avec solo).
        - Export PDF → %PDF-, Export DXF → contient "SECTION".
        - GET /stats avec admin actif → 200 avec total_projects.

      Aucun bug, aucune régression. Backend prêt pour validation utilisateur du frontend sur Expo Go.
