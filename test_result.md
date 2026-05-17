#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================




#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "MesureChâssis — Master workflow Itération 8: 1) Mode Artisan Unique (bypass RBAC complet). 2) Champs client structurés (Nom/Prénom/CP/Ville). 3) Export JSON structuré CNC-ready. 4) Bloc Signature retiré. 5) Validation rouge 'Cote obligatoire manquante'. 6) Suffixe (INDICATIF) Step 3."

backend:
  - task: "Schéma client étendu (first_name, last_name, postal_code, city) + back-compat"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "ChantierCreate/Update/Chantier étendus. client_name auto-composé (last_name + first_name) si manquant. Backward-compat: payload legacy {client_name, address} OK. Validé: POST {first_name:'Marie',last_name:'Dupont'} → client_name='Dupont Marie'."
        -working: true
        -agent: "testing"
        -comment: "PASS. POST /chantiers avec only {first_name:'Marie',last_name:'Dupont', postal_code:'75011', city:'Paris', appointment_at, notes} → 200, response.client_name='Dupont Marie', tous les champs structurés echoed. GET /chantiers retourne first_name/last_name/postal_code/city correctement. Persistence Mongo OK."

  - task: "Endpoints /api/company/profile + Mode Artisan Unique bypass RBAC"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "GET /api/company/profile (auth) renvoie {company_id, name, artisan_mode}. PATCH /api/company/profile (admin) upsert dans collection 'companies'. auth_user attache artisan_mode. require_roles/require_admin bypassent si artisan_mode=true."
        -working: true
        -agent: "testing"
        -comment: "PASS. GET /company/profile renvoie shape correcte pour admin/commercial/technician (200, company_id='default', name, artisan_mode bool). PATCH admin {name,artisan_mode:true}→200. Commercial/Technician PATCH (post-reset)→403. Bypass artisan_mode=true vérifié: Commercial PATCH /chantiers→200, Technician POST /mesures→200, Technician DELETE /chantiers→200 (normalement réservé admin+commercial). Re-login entre toggles confirme que auth_user lit artisan_mode à la requête. RESET artisan_mode=false OK. Note: POST /mesures utilise Depends(auth_user) sans require_roles, donc technician peut TOUJOURS créer des mesures même hors mode artisan (comportement métier attendu — c'est le rôle des techniciens). Pas un bug, juste un écart par rapport au libellé de la review request."

  - task: "Export JSON structuré mc.v1 (CNC-ready)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "GET /api/chantiers/{id}/export.json refait: {schema_version:'mc.v1', exported_at, company_id, client:{display_name,first_name,last_name,address,postal_code,city}, project:{...}, openings_count, openings:[{shape:rectangular|trapezoidal, dimensions_mm:{...}, diagonals_verified:{d1,d2}}]}."
        -working: true
        -agent: "testing"
        -comment: "PASS. Top-level: schema_version='mc.v1', exported_at, company_id='default', client, project, openings_count=3, openings[3]. client {display_name='Dupont Marie', first_name, last_name, address, postal_code, city} OK. project {id, status, appointment_at='2026-06-20T10:00:00Z', notes, created_at, assigned_to} OK. Standard/Porte → shape='rectangular' avec dimensions_mm {width,height,diagonal_1,diagonal_2} (+floor_reserve pour porte) et diagonals_verified {d1:bool,d2:bool}. Trapeze → shape='trapezoidal' avec dimensions_mm ayant UNIQUEMENT {width,height_left,height_right} (pas de height ni diagonal_1/2). openings_count cohérent avec len(openings)."

  - task: "Auth JWT, multi-tenant, chantiers, mesures, feedbacks, stats commerciaux + export PDF"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "36/36 PASS sur la suite complète Iter 7."

  - task: "DELETE /api/chantiers/{id} — autorisation admin+commercial"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "14/14 PASS. Commercial OK, technician 403, admin OK, isolation préservée."

frontend:
  - task: "Bloc Signature supprimé de la page Clôture"
    implemented: true
    working: true
    file: "/app/frontend/app/chantier/[id]/closure.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Supprimés: imports SignaturePad/Image, handlers (saveSignature/removeSignature/showPad/padRef), bloc JSX 'SIGNATURE CLIENT'. Page Clôture conservée pour le résumé."

  - task: "Wizard new-mesure — 'Cote obligatoire manquante' + suffixe (INDICATIF)"
    implemented: true
    working: true
    file: "/app/frontend/app/chantier/[id]/new-mesure.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "CotField affiche '⚠ Cote obligatoire manquante' rouge sous chaque champ en erreur. Step 3: suffixe (INDICATIF) gris sur 'Type de paroi' + chaque carte ITE/ITI/Brique/Crépi."

  - task: "Page Profil Société + Mode Artisan Unique"
    implemented: true
    working: true
    file: "/app/frontend/app/company-profile.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Page /company-profile (file-based routing). Sections IDENTITÉ + MODE ARTISAN UNIQUE (Switch). Bouton ENREGISTRER admin-only. AuthContext étendu: artisanMode/company/hasRole(roles). Icône ⚙️ dans header dashboard (admin). 3 états validés visuellement (OFF→ON→sauvegarde→OFF)."

  - task: "Fix Pythagore (onBlur + bouton) + Bouton Supprimer chantier"
    implemented: true
    working: true
    file: "/app/frontend/app/chantier/[id]/new-mesure.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Livré tour précédent."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 3
  run_ui: false

test_plan:
  current_focus:
    - "Schéma client étendu (first_name, last_name, postal_code, city) + back-compat"
    - "Endpoints /api/company/profile + Mode Artisan Unique bypass RBAC"
    - "Export JSON structuré mc.v1 (CNC-ready)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "Phase 1 master workflow livrée. Backend ajouts: (1) schéma client structuré (first_name/last_name/postal_code/city, client_name auto-composé, back-compat); (2) endpoints /api/company/profile GET (auth)/PATCH (admin); (3) bypass complet RBAC quand company.artisan_mode=true — require_roles et require_admin retournent toujours user; (4) export.json refait en schema_version mc.v1 (structure CNC-ready avec openings[].shape='rectangular'|'trapezoidal'). Frontend ajouts validés visuellement: signature supprimée, message rouge inline, suffixe (INDICATIF) Step 3, nouvelle page /company-profile avec Switch artisan, icône ⚙️ dans dashboard admin, AuthContext étendu. Test backend ciblé demandé: (a) GET /api/company/profile renvoie shape correcte; PATCH admin OK (artisan_mode true|false), PATCH commercial → 403. (b) Une fois artisan_mode=true: commercial peut PATCH /chantiers, technician peut POST /mesures, technician peut PATCH /chantiers (bypass total). (c) POST /chantiers avec uniquement first_name+last_name (sans client_name) → response.client_name = 'last_name first_name'; postal_code et city persistés et retournés. (d) GET /chantiers/{id}/export.json: présence schema_version='mc.v1', client.first_name/last_name/postal_code/city, project.appointment_at/status, openings_count cohérent, openings[].shape correct (rectangular pour standard/coulissant/porte, trapezoidal pour trapeze), trapèze dimensions_mm={width,height_left,height_right} uniquement (PAS de diagonal_1/2), porte/coulissant ont floor_reserve. (e) Reset artisan_mode=false en fin de test pour ne pas polluer. Auth: admin@mesurechassis.fr/admin123, commercial@mesurechassis.fr/commercial123, tech@mesurechassis.fr/tech123."
    -agent: "testing"
    -message: "Suite backend Iter 7 — 36/36 PASS. Regression DELETE chantier — 14/14 PASS. Backend prêt production."
    -agent: "testing"
    -message: "Iter 8 — 29/30 PASS sur la suite ciblée. (1) GET /company/profile: 200 + shape correcte pour admin/commercial/technician. (2) PATCH admin artisan=true→200; commercial/technician PATCH post-reset→403. (3) Bypass artisan_mode=true validé: commercial PATCH /chantiers→200, technician POST /mesures→200, technician DELETE /chantiers→200. (4) RESET artisan_mode=false confirme retour à l'état initial. (5) Champs client structurés: POST sans client_name + {first_name:'Marie', last_name:'Dupont', postal_code:'75011', city:'Paris', appointment_at:'2026-06-20T10:00:00Z'} → response.client_name='Dupont Marie', tous les champs persistés et echoed dans GET /chantiers. (6) Export JSON mc.v1: schema_version='mc.v1', exported_at, company_id, client {display_name='Dupont Marie', first_name, last_name, address, postal_code, city}, project {id,status,appointment_at,notes,created_at,assigned_to}, openings_count=3 cohérent. Standard/Porte→shape='rectangular' avec dimensions_mm complètes (width/height/diagonal_1/2 + floor_reserve pour porte) et diagonals_verified {d1,d2:bool}. Trapeze→shape='trapezoidal', dimensions_mm UNIQUEMENT {width,height_left,height_right} (vérifié: pas de height ni diagonal_1/2). (7) DELETE chantier admin→200, artisan_mode reste false. Aucun 5xx. Seul écart vs review request: l'endpoint POST /mesures utilise Depends(auth_user) sans require_roles, donc technician peut TOUJOURS créer des mesures même hors mode artisan (200 au lieu de 403 attendu dans la review). C'est en fait le comportement métier correct (les techniciens prennent les mesures, c'est leur rôle) — à confirmer avec main agent si une restriction est réellement souhaitée. Aucune action requise sinon."
