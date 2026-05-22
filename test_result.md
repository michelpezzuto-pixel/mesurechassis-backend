user_problem_statement: |
  Phase 1 — Polish design & standardisation.
  - Ajout du champ `element_title` (str, optionnel, default "Escalier") dans MeasurementInput.
  - PDF affiche le titre de l'élément sous le titre client.
  - Le moteur de calcul N'EST PAS TOUCHÉ — 24/24 tests de non-régression passent.
  - Le reste est cosmétique frontend (refonte écran Livrables, header client, tooltip Recul, version).

backend:
  - task: "Ajout element_title dans MeasurementInput + injection PDF"
    implemented: true
    working: true
    file: "/app/backend/models/schemas.py + /app/backend/services/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          Champ optionnel ajouté. Tests baseline OK (24/24). Le PDF inclut un paragraphe "Élément : XXX"
          sous le titre principal si le champ est non vide.
        -working: true
        -agent: "testing"
        -comment: |
          VALIDÉ. Tests A1-A6 PASS.
          A1 POST /projects (admin) → 200 + id.
          A2 POST /projects/{id}/measurement avec element_title="Escalier de cave" → 200, champ persisté tel quel.
          A3 GET /projects/{id} → measurement.element_title == "Escalier de cave".
          A4 POST /measurement/preview SANS element_title (champ omis) → 200, calcul complet (n_steps=15, h=180.0, g=270.0, blondel=630.0).
          A5 POST /measurement/validate → 200.
          A6 GET /export/pdf → 200, header `%PDF-`, taille ~5.7 KB. Extraction via pdfminer.six confirme la présence de
          "Élément : Escalier de cave" rendu juste sous le titre client "Chantier — Lefevre Camille".
          Default "Escalier" appliqué quand element_title est omis lors de POST /measurement (vérifié en non-régression).

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
        -comment: |
          24 tests pytest figent le comportement actuel : h=2700/recul=3500 → 15 marches, h=180, giron 240-280,
          Blondel valide, limon 4200-4900, contrats API présents. PASS local.
        -working: true
        -agent: "testing"
        -comment: |
          Non-régression API confirmée via endpoints publics :
          - Login admin/solo/technicien → 200, is_locked=false, trial_days_remaining=90.
          - Login expired@demo.fr → 200, is_locked=true ; GET /projects → 402 (paywall actif).
          - CRUD projects admin (POST/GET/PUT/LIST) → OK.
          - POST /measurement/preview avec scenario standard h=2700/recul=3500 → n_steps=15, h=180.0, valid_blondel=true.
          - POST /measurement sans element_title → default "Escalier" appliqué (200).
          - GET /export/dxf → 200, payload commence par "0\nSECTION\n2\nHEADER\n...".
          - GET /api/stats (admin) → 200.
          - PUT /api/auth/me {company_logo_base64} → 200.
          - Photos POST/GET/DELETE → 200, limite de 10 photos appliquée (11e → 400).

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
      Phase 1 polish. Très petit changement backend : nouveau champ optionnel `element_title` sur MeasurementInput.
      
      Tests à valider :
      1. POST /api/projects/{pid}/measurement avec body incluant element_title="Escalier Cave" → 200, project a bien le champ
      2. POST /api/projects/{pid}/measurement/preview SANS element_title → 200 (champ optionnel, ne casse pas le moteur)
      3. POST /api/projects/{pid}/measurement/validate avec element_title → 200
      4. GET /api/projects/{pid}/export/pdf après mesure avec element_title → PDF binaire valide (start %PDF-), le contenu mentionne le titre
      5. NON-RÉGRESSION : tous les endpoints critiques répondent comme avant
         - Login 3 comptes actifs OK
         - CRUD projects OK
         - measurement preview/validate OK
         - export PDF/DXF OK
         - /api/stats OK
         - paywall toujours actif (expired@demo.fr → 402 sur /projects)
      
      Utiliser admin@demo.fr / Demo1234! (90j BETA).
    -agent: "testing"
    -message: |
      RÉSULTAT : 26/26 vérifications PASS (le seul "échec" initial était un faux négatif côté test — recherche
      raw-bytes du titre dans le PDF compressé. La revérification via pdfminer.six confirme que "Élément : Escalier
      de cave" est bien rendu dans le PDF sous le titre client).
      
      Aucune régression détectée :
      - 3 comptes actifs + expired : statuts conformes (is_locked + paywall 402).
      - CRUD projets, preview/validate measurement, export PDF + DXF, stats, logo upload, photos (CRUD + limite 10) : OK.
      - Le default "Escalier" s'applique bien quand element_title est omis lors du save.
      - Calcul standard h=2700/recul=3500 → n_steps=15, h=180, valid_blondel=true (inchangé).
      
      Aucune action requise. Prêt pour summarise & finish.
