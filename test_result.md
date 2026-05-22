user_problem_statement: |
  REFONTE MAJEURE v2 — Multi-stairs (Niveaux > Tronçons).
  - Backend : nouveaux modèles Stair / Niveau / Troncon + CRUD complet + endpoint /compute
  - Service stairs_v2 : calcule h, g, Blondel par niveau et répartit les marches par tronçon
  - Migration auto au démarrage (services/migration_v2.py) : 6 projets legacy migrés vers stairs[]
  - Export PDF/DXF : fallback synthétique depuis stairs[] si pas de mesure legacy
  - Suppression matériau (acier/bois/béton) → plus utilisé dans le wizard (champ legacy gardé optionnel default "bois")
  - Frontend : nouvelle page Project Detail (liste d'escaliers + bouton AJOUTER UN ESCALIER + modal nommage)
  - Nouvelle page /projects/[id]/stairs/[sid] : niveaux pliables + tronçons CRUD + croquis pédagogique SVG
  - Le moteur math legacy (compute_stair) reste INTACT — 24/24 baseline tests PASS

backend:
  - task: "Multi-stairs v2 — CRUD Stair + Niveau + Troncon"
    implemented: true
    working: true
    file: "/app/backend/routers/stairs_v2.py + /app/backend/services/stairs_v2.py + /app/backend/models/schemas.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          15+ endpoints créés sous /api/projects/{pid}/stairs/*.
          Test manuel OK : créer stair → niveau → tronçon droit → /compute renvoie n_steps, h, g, blondel.
        -working: true
        -agent: "testing"
        -comment: |
          Scénario A complet exécuté (20 sous-tests PASS) :
          - POST /projects → POST /stairs ("Cave-to-RDC") → GET list → PATCH name ("Cave-Rénovée") OK
          - POST 2 niveaux (RDC h=2700 sol_fini=true, R+1 h=2500 sol_fini=false reserve=50) OK
          - POST tronçons (droit 3500x900, palier 1000, quart_bas 2800) OK
          - GET /compute : total_height=5150.0 ✓, total_steps=29 ✓, total_reculement=7300.0 ✓, limon_length=8933.8 ✓
          - niveaux_calc[0] RDC : n_steps=15, h=180.0, g=250.0, blondel=610 valid=true, droit=15 marches palier=0 ✓
          - niveaux_calc[1] R+1 : hauteur_effective=2450 (2500-50 reserve), n=14, h=175, blondel=580 valid=true ✓
          - PATCH troncon longueur_mm=4000 ✓, DELETE troncon/niveau/stair tous OK
          Tous les calculs Blondel et la répartition marches/tronçons sont cohérents.

  - task: "Migration v2 idempotente au startup"
    implemented: true
    working: true
    file: "/app/backend/services/migration_v2.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: |
          6 projets legacy migrés vers stairs[] au démarrage (1 escalier "Escalier Principal" / 1 niveau / 1 tronçon droit).
          Log : "Migration v2 : 6 projet(s) migré(s) vers stairs[]". Idempotente : ne re-traite pas les projets déjà migrés.
        -working: true
        -agent: "testing"
        -comment: |
          Scénario B validé :
          - Log backend confirmé : "Migration v2 : 6 projet(s) migré(s) vers stairs[]"
          - GET /projects (admin) → 8 projets, 7/8 ont au moins 1 escalier migré (le 8e est un projet créé après migration)
          - GET /projects/{pid}/stairs/{sid} → structure complète (1 niveau "Niveau 1" + 1 tronçon droit) ✓
          - GET /compute sur projet migré : total_steps=15 / total_height=2700 (cohérent avec mesure legacy h=2700/recul=3500) ✓
          - Migration est idempotente (filter $or: [stairs:{$exists:false}, stairs:[]]) ; aucun re-traitement.

  - task: "Export PDF v2 — fallback synthétique depuis stairs[]"
    implemented: true
    working: true
    file: "/app/backend/routers/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          Si pas de mesure legacy mais des stairs[], on synthétise un measurement depuis le 1er escalier
          pour ne pas casser le PDF/DXF historiques.
        -working: true
        -agent: "testing"
        -comment: |
          Scénario C validé sur projet v2 frais (aucun measurement legacy, uniquement stairs[]) :
          - GET /export/pdf → HTTP 200, content-type application/pdf, header binaire %PDF-1.4 (4432 bytes) ✓
          - GET /export/dxf → HTTP 200, contient "SECTION" (3574 bytes) ✓
          _synthesize_measurement_from_stairs() reconstruit correctement les champs material/hauteur_brute/result.* depuis compute_v2.

  - task: "Non-régression moteur math baseline"
    implemented: true
    working: true
    file: "/app/backend/tests/test_engine_regression.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "24 tests PASS après tous les ajouts v2 — le moteur Blondel original n'a pas été modifié."
        -working: true
        -agent: "testing"
        -comment: |
          Confirmé via test live : POST /api/projects/{pid}/measurement/preview avec
          h=2700/recul=3500 → n_steps=15, h=180.0 (identique baseline). Aucune régression.

  - task: "Paywall + RBAC sur endpoints v2"
    implemented: true
    working: true
    file: "/app/backend/routers/stairs_v2.py + /app/backend/core/security.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: |
          Scénario D validé :
          - expired@demo.fr → POST /projects/{pid}/stairs renvoie 402 "Période d'essai terminée..." ✓
          - sophie (technicien Escaliers Demo SARL) → GET /projects/{marc-pid}/stairs renvoie 404 (project_visible_to filter) ✓
          - Tous les endpoints write v2 sont sous require_active_access (paywall), reads sous get_current_user ✓
          - GET /projects expired → 402 ✓

  - task: "Non-régression CRUD complète (photos, logo, element_title)"
    implemented: true
    working: true
    file: "/app/backend/routers/projects.py + /app/backend/routers/auth.py + /app/backend/routers/measurements.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: |
          Scénario E validé :
          - Login admin/solo/tech : 3/3 actifs (is_locked=False, trial_days=90) ✓
          - Photos CRUD (POST/GET/PATCH/DELETE) OK ✓
          - Logo upload PUT /auth/me {company_logo_base64} OK (data URI persisté) ✓
          - element_title legacy : POST /measurement persiste, GET /projects/{pid} le ressort dans measurement.element_title ✓
          - Paywall actif partout (expired → 402 sur /projects, /stairs, etc.)

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 9
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      REFONTE v2 majeure. Tests focus sur les 15+ nouveaux endpoints + migration auto + fallback PDF.
      Comptes (Demo1234!) :
      - admin@demo.fr (Admin)
      - marc@mesureescalier.com (Admin Solo) — recommandé pour les tests v2
      - expired@demo.fr (paywall → 402 sur stairs/*)
    -agent: "testing"
    -message: |
      ✅ Tous les scénarios v2 PASSENT (54/54 tests automatisés exécutés via /app/backend_test_v2.py).
      
      RÉSULTATS :
      - Section A — CRUD stairs/niveaux/troncons + compute v2 : 20/20 PASS
        * compute renvoie total_height=5150, total_steps=29, niveaux_calc avec h/g/blondel cohérents
        * RDC (h=2700, sol_fini=true) → 15 marches, h=180.0, g=250.0, blondel=610 valid
        * R+1 (h=2500, sol_fini=false, reserve=50) → hauteur_effective=2450, 14 marches, h=175, blondel=580 valid
        * Répartition marches par tronçon correcte (palier = 0 marches)
        * PATCH/DELETE troncons/niveaux/stairs fonctionnent
      - Section B — Migration v2 idempotente : 6/6 PASS
        * 6 projets legacy migrés au boot (log confirmé)
        * Structure migrée : 1 stair "Escalier Principal" + 1 niveau "Niveau 1" + 1 tronçon droit reconstruit depuis measurement legacy
        * compute sur projet migré cohérent (total_steps=15 pour h=2700)
      - Section C — Export PDF/DXF v2 fallback : 4/4 PASS
        * GET /export/pdf sur projet v2 sans measurement legacy : 200 %PDF- binaire ✓
        * GET /export/dxf : 200 contient SECTION ✓
      - Section D — Paywall + RBAC : 3/3 PASS
        * expired → POST /stairs = 402 ✓
        * sophie (tech différente société) → GET /stairs autre admin = 404 ✓
      - Section E — Non-régression complète : 13/13 PASS
        * login 3 comptes actifs, measurement legacy /preview 15 marches h=180, photos CRUD, logo upload, element_title persisté, paywall partout
      
      AUCUNE RÉGRESSION DÉTECTÉE. Migration v2, CRUD v2, compute v2 et fallback PDF/DXF prêts pour production.
      Le moteur math legacy (services/stairs.py) n'a pas été touché — comportement strictement identique.
