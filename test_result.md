user_problem_statement: |
  Phase 2-3 (partielle) — Centre de Pilotage interactif.
  Backend additif :
   - Nouveaux champs optionnels dans MeasurementInput : `forme_choisie` (Literal: droit/quart_bas/quart_haut/double_quart/helicoidal),
     `largeur_volee` (default 900), `jour_escalier` (default 100)
   - MeasurementResult expose désormais shape_key, largeur_volee, jour_escalier (echo)
   - Moteur honore forme_choisie en override (sans casser le calcul Blondel)
   - Le moteur math N'A PAS ÉTÉ MODIFIÉ dans sa logique de calcul des marches
  Frontend :
   - Nouvelle page /projects/[id]/result.tsx (Centre de Pilotage)
   - Toggle Profil/Plan + nouveau composant PlanSketch
   - Sélecteur de forme + Largeur volée + Jour escalier
   - KPIs temps réel via /preview (debouncé)
   - Sticky bottom : Modifier / Valider

backend:
  - task: "Nouveaux champs Trajectoire (forme_choisie, largeur_volee, jour_escalier)"
    implemented: true
    working: true
    file: "/app/backend/models/schemas.py + /app/backend/services/stairs.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          Champs optionnels ajoutés à MeasurementInput. Le compute_stair les fait écho dans MeasurementResult
          via shape_key, largeur_volee, jour_escalier. Si forme_choisie est fourni, il override la forme auto.
          24/24 tests baseline PASS — moteur math intact.
        -working: true
        -agent: "testing"
        -comment: |
          ✅ Phase 2 Trajectoire — 20/20 checks PASS via /app/backend_test.py (test_trajectoire_phase2).
          • C2 preview forme_choisie="quart_bas" / largeur_volee=1100 / jour_escalier=120 → 200
            - shape_key="quart_bas" ✅, largeur_volee=1100.0 ✅, jour_escalier=120.0 ✅
            - shape="Quart-tournant bas (choix utilisateur)" ✅
            - n_steps=15, h=180.0, g=270.0, blondel=630.0, valid_blondel=true ✅
          • C3 preview SANS les 3 nouveaux champs → 200
            - shape_key="quart_bas" (auto-détecté car recul_needed=3780 > recul_max=3500) ✅ défini
            - largeur_volee=900.0 (default) ✅, jour_escalier=100.0 (default) ✅
          • C4 preview forme_choisie="double_quart" largeur_volee=1000 → shape_key="double_quart" ✅
          • C5 preview forme_choisie="helicoidal" → shape_key="helicoidal" ✅
          • C6 POST /measurement (save) avec forme_choisie+largeur_volee+jour_escalier → 200
            - input echo: forme_choisie="double_quart", largeur_volee=1050, jour_escalier=110 ✅
            - result.shape_key="double_quart", result.largeur_volee=1050, result.jour_escalier=110 ✅
          • C7 GET /projects/{pid} → measurement persistée contient forme_choisie/largeur_volee/jour_escalier ✅
          
          NON-RÉGRESSION COMPLÈTE (Section B 19/19 PASS) :
          - Login admin/solo/technicien (is_locked=false, trial=90j) ✅
          - Login expired → is_locked=true, GET /projects → 402 ✅
          - CRUD projects (POST/GET/PUT/list) ✅
          - Preview standard h=2700/recul=3500 → n_steps=15, h=180.0, valid_blondel=true (identique) ✅
          - Save sans element_title → default "Escalier" ✅
          - Export PDF (%PDF- header, 73KB) et DXF (commence par "0\nSECTION") ✅
          - /api/stats admin ✅
          - PUT /auth/me company_logo_base64 ✅
          - Photos CRUD + limite 10 (11e rejetée HTTP 400) ✅
          
          Minor: 1 check de la suite A (recherche raw du texte "Escalier de cave" dans le PDF compressé)
          est en FAIL mais c'est un défaut de la méthode de test (ReportLab compresse les streams) ;
          la persistance element_title est déjà vérifiée par A2/A3 (PASS).
          Total : 46/47 checks PASS, aucun problème fonctionnel.

  - task: "Non-régression moteur math (baseline)"
    implemented: true
    working: true
    file: "/app/backend/tests/test_engine_regression.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "24 tests pytest figés. PASS local après l'ajout des nouveaux champs."

metadata:
  created_by: "main_agent"
  version: "1.7"
  test_sequence: 7
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Ajout 3 champs optionnels (forme_choisie, largeur_volee, jour_escalier) sur MeasurementInput + echo dans MeasurementResult.
    -agent: "testing"
    -message: |
      ✅ Phase 2 Trajectoire backend — 46/47 checks PASS (test_trajectoire_phase2 + non-régression complète).
      Tous les comportements demandés sont conformes :
       • forme_choisie override correctement shape_key (quart_bas/quart_haut/double_quart/helicoidal)
       • largeur_volee + jour_escalier sont echo dans MeasurementResult (et defaults 900/100 si omis)
       • Save + GET project → 3 champs persistés en MongoDB (input + result.shape_key)
       • Moteur math intact : h=2700/recul=3500 sans override → n_steps=15, h=180, blondel=630, valid_blondel=true
       • Login 3 comptes actifs + paywall expired (402) OK
       • Exports PDF/DXF, /stats, photos CRUD + limite 10, logo upload : tous OK
      
      Seul "FAIL" : recherche raw substring "Escalier de cave" dans PDF compressé (test A6) — limitation
      de la méthode de test (ReportLab compresse les streams). Le PDF est valide (200, %PDF-, 73KB) et
      la persistance element_title est déjà confirmée par A2/A3.
      
      Backend prêt pour validation utilisateur via Expo Go (frontend non testé ici, par design).
      
      Tests à valider (admin@demo.fr / Demo1234!) :
      
      1. POST /api/projects/{pid}/measurement/preview avec body incluant forme_choisie="quart_bas",
         largeur_volee=1100, jour_escalier=120 → 200
         - Réponse contient shape_key == "quart_bas"
         - Réponse contient largeur_volee == 1100, jour_escalier == 120
         - Le shape (string) commence par "Quart-tournant bas (choix utilisateur)"
      
      2. POST /api/projects/{pid}/measurement/preview SANS forme_choisie (les autres champs requis) → 200
         - shape_key est défini (par défaut "droit" ou auto-détecté)
         - largeur_volee == 900 par défaut, jour_escalier == 100 par défaut
      
      3. POST /api/projects/{pid}/measurement avec forme_choisie="double_quart", largeur_volee=1000 → 200, sauvegardé
      
      4. GET /api/projects/{pid} → measurement contient forme_choisie + largeur_volee + jour_escalier
      
      5. NON-RÉGRESSION : tous les endpoints standard fonctionnent
         - login 3 comptes actifs OK
         - cas standard h=2700 / recul=3500 SANS forme_choisie → n_steps=15, h=180, valid_blondel=true (comportement IDENTIQUE à avant)
         - exports PDF/DXF OK
         - paywall toujours actif (expired@demo.fr → 402)
         - element_title (Phase 1) toujours OK
         - photos CRUD toujours OK
         - logo upload toujours OK
