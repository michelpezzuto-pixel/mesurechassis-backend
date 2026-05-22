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

user_problem_statement: |
  MesureEscalier — Application mobile React Native (Expo Router) + FastAPI/MongoDB pour poseurs d'escaliers.
  Design system Dark #1A1E2A / Vert Pomme #8CC63F. Rôles Admin/Technicien + Solo Mode.
  Smart Measurement Engine (Blondel, Échappée, Limon), exports PDF + DXF, dictée Whisper.
  Dernière action : Modularisation backend server.py → core/, models/, services/, routers/.
  À VALIDER : refactor n'a rien cassé, toutes les routes fonctionnent.

backend:
  - task: "Modularisation backend (server.py → routers/core/services/models)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "server.py 1100+ lignes éclaté en core/{config,db,security}, models/schemas, services/{stairs,exports,seed}, routers/{auth,projects,measurements,exports,voice,stats,integration}. Backend démarre sans erreur d'import. À valider end-to-end."
        -working: true
        -agent: "testing"
        -comment: "Validation end-to-end OK. server.py inclut bien les 7 routers sous /api. Aucune régression détectée. 40 vérifications passées, 0 échec fonctionnel."

  - task: "Auth JWT (login, /me, update)"
    implemented: true
    working: true
    file: "/app/backend/routers/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Fonctionnait avant refactor. Comptes seedés: admin@demo.fr, marc@mesureescalier.com (solo), sophie@mesureescaliee.com — tous Demo1234!"
        -working: true
        -agent: "testing"
        -comment: "POST /api/auth/login OK pour les 3 comptes seedés (JWT renvoyé). GET /api/auth/me OK avec Bearer, 401 sans token. PUT /api/auth/me met à jour company_name (admin). PUT solo_mode bien refusé (403) pour technicien. Aucun problème."

  - task: "CRUD Projects + transmit"
    implemented: true
    working: true
    file: "/app/backend/routers/projects.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "À revalider après modularisation."
        -working: true
        -agent: "testing"
        -comment: "GET /api/projects (admin et tech, filtré), POST (admin), POST (solo) qui auto-locks + status=a_mesurer, GET/PUT/DELETE/{id}, POST /transmit qui passe le projet en a_mesurer + locked=True : TOUT OK. Forbidden pour tech sur POST/PUT renvoie bien 403."

  - task: "Measurement preview + validate (Blondel + Échappée + Limon)"
    implemented: true
    working: true
    file: "/app/backend/routers/measurements.py + /app/backend/services/stairs.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Math engine déplacée dans services/stairs.py. Inclut Blondel strict, échappée <2m warning, limon hypoténuse."
        -working: true
        -agent: "testing"
        -comment: "preview cas normal (h=2700, recul=3500, trémie=2400, dalle=200, plafond=2400) → n=15, h=180, g=270, 2h+g=630 (valid_blondel=true), limon=4645.3, échappée=1500. Cas critique échappée<2000 détecté. Cas Blondel impossible → shape='Double quart-tournant ou hélicoïdal' + is_tournant=true. POST sauvegarde mesure (tech), forbidden pour admin non-solo (403). POST /validate met status='valide'. Tous les champs requis présents (giron g, hauteur_marche h, echappee, limon_length, blondel_ok via valid_blondel)."

  - task: "Exports PDF (ReportLab) et DXF (ezdxf)"
    implemented: true
    working: true
    file: "/app/backend/routers/exports.py + /app/backend/services/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Doit toujours renvoyer base64 PDF + DXF texte."
        -working: true
        -agent: "testing"
        -comment: "Routes EXISTENT en GET (pas POST comme indiqué dans la review). GET /api/projects/{pid}/export/pdf → 200, content-type application/pdf, 5067 octets, header '%PDF-1.4' valide. GET /api/projects/{pid}/export/dxf → 200, contient 'SECTION'/'ENTITIES', header '0\\nSECTION\\n2\\nHEADER...' OK. NOTE: l'implémentation renvoie un StreamingResponse binaire (Content-Disposition attachment) plutôt qu'un JSON {pdf_base64, dxf_content}. Comportement identique à pré-refactor — pas une régression. POST renvoie 405 (route GET uniquement). Si le front consomme du base64, vérifier qu'il lit bien le corps binaire."

  - task: "Whisper transcription"
    implemented: true
    working: true
    file: "/app/backend/routers/voice.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Utilise EMERGENT_LLM_KEY pour OpenAI Whisper."
        -working: true
        -agent: "testing"
        -comment: "POST /api/transcribe vivant. Sans fichier → 422 (FastAPI validation). Sans Bearer → 401. Avec bytes factices → 500 (OpenAI rejette le format), preuve que la route exécute bien Whisper. Test Whisper réel non effectué (pas d'audio mp3/m4a disponible) comme demandé."

  - task: "Stats endpoint"
    implemented: true
    working: true
    file: "/app/backend/routers/stats.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "À revalider."
        -working: true
        -agent: "testing"
        -comment: "GET /api/stats (admin) → JSON complet avec total_projects, by_status (dict des 6 statuts), total_measurements, validated_measurements, average_steps, team_size. GET /api/stats (tech) → 200. Aucun champ manquant."

  - task: "Integration endpoint (futur sister apps)"
    implemented: true
    working: true
    file: "/app/backend/routers/integration.py"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "À revalider."
        -working: true
        -agent: "testing"
        -comment: "ATTENTION nommage : la review demandait GET /api/integration/projects, mais le code expose uniquement GET /api/integration/sites/{pid} (identique à pré-refactor — pas une régression). Cette route /sites/{pid} fonctionne : 200, payload {site_id, client, structure{material, true_height_mm, ..., echappee_mm, tremie}}, et exige bien un Bearer (401 sans token). Si une route 'liste projets pour sister apps' est attendue, elle n'a jamais été implémentée — décision produit à valider."

frontend:
  - task: "Login + Demo accounts"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/login.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Pas modifié dans cette itération. À tester si user le demande."

metadata:
  created_by: "main_agent"
  version: "1.4"
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus:
    - "Modularisation backend (server.py → routers/core/services/models)"
    - "Auth JWT (login, /me, update)"
    - "CRUD Projects + transmit"
    - "Measurement preview + validate (Blondel + Échappée + Limon)"
    - "Exports PDF (ReportLab) et DXF (ezdxf)"
    - "Whisper transcription"
    - "Stats endpoint"
    - "Integration endpoint (futur sister apps)"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Modularisation backend terminée. Backend redémarre proprement (logs OK, pas d'erreur d'import).
      Merci de valider TOUTES les routes API end-to-end avec les comptes seedés (admin@demo.fr / Demo1234! ; marc@mesureescalier.com / Demo1234! ; sophie@mesureescaliee.com / Demo1234!).
      Focus : 1) Auth login + /me, 2) CRUD projects, 3) measurement preview/validate avec calcul Blondel/Échappée/Limon, 4) export PDF + DXF (vérifier base64 non vide), 5) Whisper (peut être skip si pas de fichier audio sous main), 6) /api/stats, 7) /api/integration/*.
      Comportement attendu identique à avant modularisation. Tous les endpoints sous /api/*.
    -agent: "testing"
    -message: |
      VALIDATION POST-REFACTOR : OK — la modularisation N'A RIEN CASSÉ.
      40 vérifications exécutées via /app/backend_test.py contre l'URL publique (https://stair-pro.preview.emergentagent.com/api). Résumé :
        ✅ AUTH : login 3 comptes, /auth/me (200/401), PUT /auth/me (admin OK, solo_mode bloqué pour tech 403).
        ✅ PROJECTS : list (admin/tech), POST (admin OK, tech 403), POST solo (auto-lock+a_mesurer), GET/PUT/DELETE/{id}, /transmit.
        ✅ MEASUREMENTS : preview cas standard (h=2700, recul=3500, trémie=2400, dalle=200, plafond=2400) → n=15, h=180, g=270, 2h+g=630, limon=4645.3, échappée=1500, valid_blondel=true. Cas critique échappée<2000 détecté. Cas Blondel impossible → shape tournant/hélicoïdal. POST measurement OK pour tech, 403 admin non-solo. /validate met le projet à 'valide'.
        ✅ EXPORTS : GET /export/pdf renvoie binaire %PDF-1.4 (5067 octets). GET /export/dxf renvoie DXF text valide (header 0\\nSECTION\\n...). À noter : implémentation = StreamingResponse binaire avec Content-Disposition attachment, PAS un JSON {pdf_base64, dxf_content} comme évoqué dans la review — comportement IDENTIQUE à pré-refactor, pas une régression. Les routes sont en GET (POST renvoie 405).
        ✅ VOICE : POST /api/transcribe vivant. 422 sans fichier, 401 sans auth, 500 avec bytes factices (OpenAI rejette le format — preuve que la route exécute Whisper). Test Whisper réel non effectué (pas d'audio).
        ✅ STATS : GET /api/stats payload complet (total_projects, by_status, total_measurements, validated_measurements, average_steps, team_size).
        ⚠️ INTEGRATION : la review mentionnait GET /api/integration/projects mais cette route N'EXISTE PAS (et n'a jamais existé). Seule /api/integration/sites/{pid} est exposée — elle fonctionne (200 avec payload {site_id, client, structure}, 401 sans auth). Si une liste type 'integration/projects' était attendue côté sister apps, c'est une décision produit, pas une régression du refactor.
      Aucun stuck task. Aucune action backend requise. Le front continue de tomber sur des warnings expo (shadow*, expo-av), non bloquants — hors périmètre.
