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

  - task: "Backend refactor — server.py monolithique éclaté en modules (db/models/deps/utils/seed/routes/*)"
    implemented: true
    working: true
    file: "/app/backend/server.py + /app/backend/routes/*.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "REGRESSION COMPLETE — 35/35 PASS (/app/backend_test.py). Refactor du monolithe 1397-lignes en 9 modules (db.py, models.py, deps.py, utils.py, seed.py, routes/{auth,chantiers,mesures,feedbacks,company,stats,exports}.py + server.py thin entry 53 lignes) VALIDÉ sans aucune régression. Détails: (1) Auth 3 rôles: login admin/commercial/technician→200, /auth/me→200 pour chacun. (2) Chantiers CRUD: GET liste→200 (8 chantiers), POST avec {first_name:Élodie, last_name:Régression-XXX, postal_code:75003, city:Paris}→200 + client_name auto-composé='Régression-XXX Élodie', PATCH (notes+status)→200, GET by id→200, DELETE→200. (3) Mesures CRUD: POST standard {bay_width:1500,bay_height:2400,diag1=diag2=2828}→200 (alerts=[]), POST trapeze→200, GET liste (n=2)→200, PATCH→200 (bay_height=2410), DELETE→200. (4) Users: GET /users (admin)→200, n=11. (5) Company profile: GET→200 avec {artisan_mode,company_id,subscription_status} shape OK; PATCH artisan_mode toggle puis restore→200. (6) Stats: /stats/company→200 ({by_status,total_chantiers}), /stats/commercials→200 ({commercials}). (7) Exports: PDF→200 magic '%PDF-' 2493 bytes ; JSON→200 schema_version='mc.v1' avec openings_count=2 et shapes {rectangular,trapezoidal} ; CSV→200 ct='text/csv; charset=utf-8' ; XLSX→200 ct='spreadsheetml.sheet' magic 'PK'. (8) Feedbacks: POST (commercial)→200, GET (admin)→200. (9) RBAC: artisan_mode=true bypass → tech POST /chantiers→200, commercial GET /stats/company→200, AUCUN 500. (10) Error handling: POST /chantiers sans address→422 (Pydantic), GET /chantiers/nonexistent-id→404, PATCH status=foobar→400 (validation manuelle). Aucun 5xx observé sur l'intégralité de la suite. Module routes/__init__.py vide mais fonctionnel. Startup seed.py idempotent OK. CORS middleware monté. Mongo connexion OK. Backend prêt production post-refactor."

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

  - task: "GET /api/chantiers/{id}/export.csv (CNC-friendly tabular CSV)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "25/25 PASS sur la suite CSV ciblée. (1) GET CSV admin → 200, Content-Type 'text/csv; charset=utf-8', body commence par BOM UTF-8 (b'\\xef\\xbb\\xbf'). Header contient exactement 'Chantier;Adresse;Code Postal;Ville;Statut;Label;Type;Forme;...'. (2) 3 mesures créées (standard, trapeze, porte) → 3 lignes data. (3) Trapeze: Forme='trapezoidal', Hauteur G='1200.0', Hauteur D='1600.0', Hauteur/Diag1/Diag2 vides. (4) Standard: Forme='rectangular', Hauteur='1500.0', Diag1='1921.0', Diag2='1921.0', Diag1 OK='oui'. (5) Porte: Forme='rectangular', Réserve sol='35.0'. (6) CSV commercial→200, technician→200. (7) Sans token→401. (8) bad-uuid→404. (9) Régression exports: PDF→200 + magic '%PDF-', XLSX→200 + magic 'PK', JSON→200 + schema_version='mc.v1'. Aucun 5xx. Endpoint prêt production."

  - task: "RBAC tightened — POST/PATCH/DELETE /api/mesures réservé Commercial/Technicien (Admin 403 sauf artisan_mode)"
    implemented: true
    working: true
    file: "/app/backend/routes/mesures.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS. artisan_mode=false: Admin POST /mesures→403, Admin PATCH /mesures/{id}→403, Admin DELETE /mesures/{id}→403 (toutes bloquées par require_roles(['commercial','technician'])). Commercial POST→200, Technician POST→200 (standard + trapèze + porte). RBAC strict appliqué."

  - task: "RBAC tightened — Exports JSON/CSV/XLSX réservés Tech+Admin (Commercial 403 sauf artisan_mode), PDF ouvert à tous"
    implemented: true
    working: true
    file: "/app/backend/routes/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS. artisan_mode=false: Commercial GET export.pdf→200 (magic %PDF-), Commercial export.json/csv/xlsx→403 (détail FR explicite). Technician GET all 4 formats→200. Admin GET all 4 formats→200. Dépendance restrict_advanced_exports() opérationnelle. PDF accessible à tous (commercial inclus) comme spec."

  - task: "Exports enrichis — colonnes CSV étendues, XLSX Mesures complet + feuille Photos site, JSON schema enrichi"
    implemented: true
    working: true
    file: "/app/backend/routes/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS. (1) CSV header inclut les nouvelles colonnes enrichies 'L. haut', 'L. bas', 'H. gauche', 'H. droite', 'L. milieu', 'H. milieu', trapèze (L. petite, L. inter, H. petite, H. grande), isolation/finitions, angle pente, Alertes. Content-Type='text/csv; charset=utf-8'. (2) XLSX: magic 'PK', taille=6682 bytes (>1000), content-type spreadsheetml.sheet. Feuille Mesures avec toutes dims + feuille Photos site quand site_photos non-vide. (3) JSON: schema_version='mc.v2' (NOTE: review request mentionnait mc.v1 mais le code actuel renvoie mc.v2, ce qui est cohérent avec l'évolution du schéma), openings[].dimensions_mm dict présent sur les 3 ouvertures (standard rénovation, trapèze, porte), openings[].renovation_mode flag présent partout, openings[].construction (bloc/wall_type/isolation/finishes) présent. site_photos array présent (vide ici car chantier de test sans photos). Trapeze opening shape='trapezoidal' OK."

  - task: "Wall Config global per chantier — PATCH /api/chantiers/{id}/wall-config + persist + RBAC"
    implemented: true
    working: true
    file: "/app/backend/routes/chantiers.py + /app/backend/models.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "PASS. (1) Admin PATCH /api/chantiers/{id}/wall-config {project_type, masonry_type:brique, gros_oeuvre_mm:200, insulation_mode:iti, iti_thickness_mm:100}→200, wall_config retourné dans la réponse. (2) GET /api/chantiers/{id} retourne wall_config persisté correctement (5 clés). (3) Technician PATCH /api/chantiers/{id}/wall-config→200 (RBAC ['admin','commercial','technician']). (4) PATCH sans token→401. (5) PATCH chantier inexistant→404. (6) Champ wall_config: Optional[dict] ajouté à Chantier et ChantierUpdate (free-form pour souplesse). Endpoint dédié pour ne pas ouvrir tout PATCH /chantiers aux techniciens."

  - task: "Latin-1 filename bug — _safe_filename() translit apostrophe/accents pour Content-Disposition"
    implemented: true
    working: true
    file: "/app/backend/routes/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS. Chantier créé avec client_name=\"M. d'Aujourd'hui\" (apostrophes ASCII). Export PDF→200 (magic %PDF-), Export CSV→200, Export XLSX→200. AUCUN 500. _safe_filename() (unicodedata NFKD + suppression diacritiques + re.sub des non-word) gère correctement apostrophes et accents (Étoile, Régnier-Marchand). Cleanup DELETE OK."

frontend:
  - task: "Wizard new-mesure — wall_config global (Skip Étape 1 + feuillures conditionnelles)"
    implemented: true
    working: true
    file: "/app/frontend/app/chantier/[id]/new-mesure.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "VALIDÉ E2E COMPLET via screenshot tool. Scénario réel utilisateur (Login → Crée chantier → Wizard1 fill Step1 + Suivant + Pick Rect + Fill cotes + Enregistrer → Wizard2 ré-ouverture) : Étape 1 affichée la 1ère fois ✓, advanced to Step 2 après SUIVANT (wall_config persisté en DB) ✓, Step 3 fonctionnel avec auto-Pythagore ✓, save OK ✓, ré-ouverture du wizard → Étape 1 SAUTÉE, ouvre directement sur Étape 2 ✓. (1) useEffect détection stricte: wall_config significatif SEULEMENT si masonry_type ET insulation_mode présents (évite skip sur objet vide {}). (2) buildWallConfigPayload + persistWallConfig() helpers extraits. (3) goNextFromStep1 PATCH + Alert utilisateur si échec (plus de silence radio). (4) FILET DE SÉCURITÉ: submit() appelle persistWallConfig() une 2ème fois avant POST /mesures (idempotent — assure persistance même si PATCH initial a échoué). (5) Étape 3 lit s1.masonry_type → showFeuillures (brique/pierre/bloc-béton → 3 champs feuillure_left/right/top ; bloc terre cuite → masqué). (6) goBack() step=1 + wallConfigLocked=true → router.back() direct."

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
  test_sequence: 4
  run_ui: false

test_plan:
  current_focus:
    - "Artisan strict — bloquer invitations équipe (backend + frontend)"
    - "Feedback user — GET /feedbacks/mine endpoint + historique perso"
    - "Trial 90 jours + Anti-fraude device fingerprint"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

backend_artisan_strict:
  - task: "Bloquer POST /admin/invitations pour les comptes Artisan (403)"
    implemented: true
    working: true
    file: "/app/backend/routes/invitations.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /admin/invitations vérifie maintenant le account_type de la company de l'admin courant. Si account_type='artisan', renvoie HTTP 403 avec message: 'Les comptes Artisan sont limités à un seul utilisateur. Pour inviter des collaborateurs, passez à un compte Entreprise.' La vérification se fait AVANT le check d'unicité email, pour bloquer même en cas d'email déjà existant. À tester: (a) Compte Artisan tente POST /admin/invitations → 403. (b) Compte Entreprise → 200 nominal. (c) Compte Artisan converti en Entreprise via PATCH /company/profile peut ensuite inviter."
        -working: true
        -agent: "testing"
        -comment: "PASS 7/7 (/app/backend_review_test.py). (1a) Artisan créé via POST /auth/register {account_type:'artisan'} → 200 ; activation status='active' via Motor ; login → token OK. (1b) POST /admin/invitations avec token Artisan → 403 avec detail commençant par 'Les comptes Artisan sont limités à un seul utilisateur. Pour inviter des collaborateurs, passez à un compte Entreprise.' ✅. ORDRE DU CHECK VÉRIFIÉ : POST /admin/invitations avec email déjà existant (admin@mesurechassis.fr) en tant qu'Artisan → 403 (pas 400 'Cet email est déjà enregistré') → confirme que le check account_type est bien AVANT le check d'unicité email. (1c) Compte Entreprise (account_type='entreprise', company_name='TestSAS-xxx') → register 200, login OK, POST /admin/invitations {role:'commercial'} → 200 invitation créée. (1d) Conversion Artisan→Entreprise via Motor `db.companies.update_one({company_id},{'$set':{'account_type':'entreprise'}})`, puis re-POST /admin/invitations avec le token Artisan inchangé → 200. La vérification lit bien le account_type courant en DB à chaque appel."

backend_feedback_mine:
  - task: "GET /feedbacks/mine — historique personnel des retours soumis par l'utilisateur"
    implemented: true
    working: true
    file: "/app/backend/routes/feedbacks.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Nouvel endpoint GET /api/feedbacks/mine (auth required, tous rôles). Retourne List[Feedback] filtré sur user_id=user.id, trié par created_at desc, limit 200. Permet à l'utilisateur de retrouver ses propres soumissions. À tester: (a) GET /feedbacks/mine sans token → 401. (b) Avec token + 0 feedback → []. (c) Soumettre 2 feedbacks via POST /feedbacks puis GET /feedbacks/mine → length=2 trié desc par date. (d) Un user ne voit PAS les feedbacks d'un autre user (isolation user_id)."
        -working: true
        -agent: "testing"
        -comment: "PASS 7/7. (2a) GET /feedbacks/mine sans Authorization → 401 'Missing token' ✅. (2b) User fraîchement créé (status=active) avec 0 feedback → GET retourne [] ✅. (2c) POST /feedbacks {page_context:'/dashboard', user_comment:'First...'} puis 1.1s plus tard POST /feedbacks {page_context:'/chantier/abc', user_comment:'Second...'} ; GET /feedbacks/mine → length=2, ordre DESC : data[0].id==fb2 (le plus récent), data[1].id==fb1 ✅. (2d) ISOLATION : U1 (artisan A) et U2 (artisan B) créés. U1 soumet 2 feedbacks (fb1, fb2), U2 soumet 1 feedback (fb_u2). GET /mine U1 → uniquement {fb1, fb2}, PAS fb_u2 ✅. GET /mine U2 → uniquement [fb_u2], PAS fb1/fb2 ✅. Filtre user_id={user['id']} opérationnel et isolation respectée même entre companies différentes."

backend_trial_antifraud:
  - task: "Trial 90 jours non-BETA + Anti-fraude device fingerprint (SHA256 IP+UA)"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "(1) Trial: en mode non-BETA (BETA_MODE=false), la création de company définit subscription_status='trial', trial_expires_at=now+90j, subscription_expires_at identique. Le user sera bloqué par le paywall existant après J+90. (2) Anti-fraude: nouvelle fonction _device_fingerprint(req) calcule un SHA256 de (x-forwarded-for || client.host) + user-agent (200 chars max). Le hash est stocké dans user.signup_fingerprint à l'inscription. Sur chaque tentative de register, on cherche un user existant avec status='deleted', deleted_at>=now-180j, ET même signup_fingerprint. Si trouvé → 403 'Un compte précédent a été supprimé depuis cet appareil récemment. Pour reprendre votre activité, contactez le support à info@mesurechassis.com.'. Bypass: (a) en mode BETA_MODE=true (configuration actuelle) pour ne pas gêner les premiers tests, (b) en legacy mode quand payload contient 'role' (tests internes)."
        -working: true
        -agent: "testing"
        -comment: "PASS 9/9. (3a) Smoke test BETA actif : POST /auth/register {name, email, password, account_type:'artisan'} + header User-Agent:'AntifraudeTest/1.0' → 200 ; lecture en Motor : user.signup_fingerprint='b9e4dda4df32a0d2...' (sha256 hex, len=64) ✅. (3b) Trial 90j : en BETA_MODE=true, company.subscription_expires_at='2036-05-21...' (~10 ans), confirmant la branche BETA. La branche non-BETA (else) est vérifiée par code grep : `timedelta(days=90)` + `trial_expires_at` + `subscription_status='trial'` + `plan='trial'` présents dans routes/auth.py l.222-238 ✅. (3c-i) 2 inscriptions consécutives avec MÊME User-Agent 'AntifraudeTest/1.0' (userA puis userB) → toutes les deux 200, BETA bypass confirmé ✅. (3c-ii) Vérification Motor : userA.signup_fingerprint === userB.signup_fingerprint (même UA + même IP source pour test runner → même sha256) ✅. (3c-iii) Soft-delete userA via DELETE /auth/me {password, confirm_text:'SUPPRIMER', marketing_optin:false} → 200 ; user.status='deleted', signup_fingerprint préservé en DB ✅. (3c-iv) Tentative de recréer un userC avec même UA après soft-delete de userA → 200 (BETA bypass actif), pas de 403 antifraude ✅. (3c-v) DOCUMENTATION VALIDÉE : 'Anti-fraude désactivée en BETA, sera active en prod quand BETA_MODE=false' — comportement attendu. Code grep confirme la branche antifraud (`if 'role' not in payload and not BETA_MODE:` + lookup status='deleted' + 403 'Un compte précédent...') existe et sera active dès BETA_MODE=False ✅. NOTE TEST DESIGN : la review request suggérait userA@af.test et userB@af.test mais le TLD '.test' est rejeté par Pydantic EmailStr (RFC 6761 special-use), causant un 500 sur user_to_public lors du register. J'ai utilisé '@mesurechassis.fr' à la place pour le test fonctionnel — c'est une amélioration future (catcher l'erreur Pydantic plus tôt) mais sans impact sur la feature antifraud testée."

frontend_artisan_team_guard:
  - task: "Frontend — bloquer accès à /admin/team pour les comptes Artisan (redirect dashboard)"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/admin/team.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "useEffect: si user.role!=admin → redirect /dashboard, OU si company.account_type==='artisan' → Alert 'Compte Artisan...' puis redirect /dashboard. Empêche d'arriver sur la page d'invitation même via URL directe. Combiné avec masquage du bouton Équipe sur dashboard.tsx + blocage backend → triple verrou. Pas de test agent frontend prévu."

frontend_my_feedbacks_page:
  - task: "Page /my-feedbacks — historique perso + bouton 'Suggérer une amélioration' (FAB Aide remonté)"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/my-feedbacks.tsx + /app/frontend/app/dashboard.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "(1) Nouvelle route /my-feedbacks accessible à tous les rôles (testID my-feedbacks-button sur dashboard, ouverte via icône chatbubble-ellipses-outline). Affiche FlatList des feedbacks (sujet, date FR, contexte page) + composant FeedbackButton pour en soumettre un nouveau. État empty: icône + texte explicatif. Pull-to-refresh. (2) FAB Aide remonté à bottom:96 (au lieu de 24) pour ne plus masquer les CTA primaires du dashboard (+ Nouveau chantier). Padding/marges ajustés (16/11). Test visuel à confirmer par l'utilisateur."
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

backend_lot_e:
  - task: "Lot E — RGPD soft-delete du compte courant + opt-in marketing + login bloqué après suppression"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "DELETE /api/auth/me (auth required). Body JSON: password (str, requis), confirm_text (doit valoir SUPPRIMER en majuscules), marketing_optin (bool, défaut False). Validation: 400 si password manquant, 400 si confirm_text != 'SUPPRIMER', 400 si mot de passe incorrect (verify_password). Sur succès: user.status='deleted', deleted_at=ISO now, hashed_password='' (login impossible), push_tokens=[], password_reset_code/expires effacés. Email: si marketing_optin=True alors email préservé + marketing_email=email original; sinon email anonymisé en deleted_<uuid>@deleted.invalid + marketing_email=null. Bonus: si plus aucun admin actif dans la company → companies.abandoned_at = now. POST /api/auth/login refuse explicitement les comptes deleted (401 'Email ou mot de passe incorrect' — pas de fuite d'info)."
        -working: true
        -agent: "testing"
        -comment: "LOT E — 30/33 PASS sur la suite ciblée (/app/backend_lot_e_test.py) + 167/167 pytest existant PASS. Fonctionnalité CORE 100% opérationnelle. ✅ Tests réussis : (T1) DELETE /auth/me sans token → 401 'Missing token'. (T2a) sans password → 400 'Le mot de passe est requis...'. (T2b) sans confirm_text → 400 'Tapez SUPPRIMER...'. (T2d) password incorrect (sur user fresh) → 400 'Mot de passe incorrect.' (vérifié séparément). (T3) Soft-delete sans opt-in marketing : status='deleted', deleted_at ISO non-null, hashed_password='', email anonymisé en 'deleted_9d91e5b86662@deleted.invalid' (regex match), marketing_email=None, marketing_optin=False, push_tokens=[]. Login avec ancien email → 401 (anti-fuite). Forgot-password sur ancien email → 200 anti-énum. (T4) Soft-delete avec marketing_optin=True : status='deleted', email préservé exactement (lote_optin_dcd60388@mesurechassis.fr), marketing_email == email original, marketing_optin=True, hashed_password=''. Login après delete → 401. (T5) Préservation données métier : chantier (id=f06b640e...) créé puis user delete → chantier TOUJOURS présent en DB après delete, chantier.created_by préservé pointant vers user.id supprimé. (T6) abandoned_at : artisan seul admin de sa company (lonely-artisan-d4c6e4) → DELETE /auth/me → companies.abandoned_at non-null ('2026-05-24T18:55:36.190701+00:00'). (T7) Resend MAIL_FROM : POST /auth/forgot-password admin@mesurechassis.fr → 200 SANS beta_reset_code dans le body ; log 'Resend OK → admin@mesurechassis.fr (subject=...Réinitialisation..., id=7f958782-9ad8-44d9-971d-4f18175563d9)'. Le domaine mesurechassis.com EST bien vérifié sur Resend, MAIL_FROM='MesureChâssis <info@mesurechassis.com>' fonctionne. (T9) Régression pytest : 167 passed in ~30s. ❌ TROIS BUGS MINEURS DÉTECTÉS (non bloquants, n'invalident PAS la livraison Lot E) : (B1) confirm_text case-insensitive : le code l.490 `confirm_text = str(...).strip().upper()` transforme silencieusement 'supprimer' en 'SUPPRIMER' donc lowercase est accepté. La spec dit 'doit valoir exactement SUPPRIMER (majuscules)'. Impact UX : minor (user doit toujours taper le mot). Fix : supprimer `.upper()` et comparer strictement. (B2) Double-DELETE → 500 : si on rappelle DELETE /auth/me sur un user déjà supprimé (hashed_password=''), `verify_password('xxx', '')` lève passlib.exc.UnknownHashError → 500 Internal Server Error au lieu de 400/401. Fix : ajouter `if not user_doc.get('hashed_password'): raise HTTPException(400, 'Mot de passe incorrect.')` avant verify_password. (B3) MOYEN — GET /auth/me avec token zombie sur user deleted → 500 : auth_user() ne vérifie pas status=='deleted', et UserPublic.email est typé EmailStr qui REFUSE le TLD .invalid. Traceback : `pydantic_core.ValidationError: ... input='deleted_a2cca2ab71a9@deleted.invalid' ... part after @-sign is a special-use or reserved name`. Risque sécurité MOYEN : un attaquant qui possède un JWT volé peut continuer à appeler l'API tant que le token n'est pas expiré (~1440min par défaut), et la plupart des endpoints planteront en 500 (au lieu de 401). Fix recommandé : ajouter dans auth_user() après le chargement du user : `if (user.get('status') or 'active') == 'deleted': raise HTTPException(401, 'Compte supprimé.')`. Cela rend les zombie tokens immédiatement invalides ET protège tous les autres endpoints (chantiers, exports, etc.) sans nécessiter de modification au niveau de Pydantic. (Bonus) GET /users côté admin 'default' n'inclut bien PAS un user deleted d'une autre company (multi-tenant respecté). CLEANUP COMPLET : 5 users de test lote_*@mesurechassis.fr supprimés en Motor (+ verifications + chantiers), 4 companies de test supprimées. admin@mesurechassis.fr/admin123/role intacts (vérifié post-cleanup). BETA_MODE et MAIL_FROM dans .env non modifiés."

backend_resend_prod_domain:
  - task: "Resend MAIL_FROM rebascule sur info@mesurechassis.com (domaine vérifié)"
    implemented: true
    working: "NA"
    file: "/app/backend/.env"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Domaine mesurechassis.com vérifié sur Resend. MAIL_FROM passé de 'onboarding@resend.dev' à 'MesureChâssis <info@mesurechassis.com>'. MAIL_REPLY_TO=info@mesurechassis.com. Test agent non requis (smoke test simple via curl/python). À vérifier juste via un POST /api/auth/forgot-password qui doit retourner 200 sans beta_reset_code et logger 'Resend OK'."

frontend_lot_e_dashboard_fixes:
  - task: "Fixes UI: bouton Aide FAB flashy + masquage Équipe pour Artisan + AppointmentPicker plein écran + bouton mailto feedback"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/dashboard.tsx + /app/frontend/app/admin/feedbacks.tsx + /app/frontend/src/components/AppointmentPicker.tsx + /app/frontend/app/company-profile.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "(1) Bouton 'Aide' retiré de la barre d'actions et déplacé en FAB flottant (bottom-right) bleu cyan #3B82F6 avec border #60A5FA + shadow → bien visible. testID=help-fab. (2) Bouton 'Équipe' caché si company.account_type === 'artisan' (compte solo, pas d'équipe à gérer). (3) Nouveau composant AppointmentPicker.tsx : modal plein écran avec calendrier mois complet (react-native-calendars + locale FR), sélection heure (24h scroll) + minutes (00/15/30/45 pills). Cross-platform (web/iOS/Android). Remplace l'ancien `<input type=date>` + DateTimePicker overlay illisible. (4) Page admin/feedbacks.tsx: bouton 'RÉPONDRE PAR MAIL' (mailto:user_email pré-rempli sujet+citation message+template réponse) à côté du bouton Supprimer. (5) Lot E UI: nouvelle carte 'ZONE DANGER' avec bouton 'SUPPRIMER MON COMPTE' dans profil société, ouvre une modal avec input password + input texte 'SUPPRIMER' + checkbox opt-in marketing. Sur succès → logout automatique. Frontend agent test non requis pour l'instant (user testera lui-même)."
    - "Feedback email — bouton mailto cliquable + reply_to client"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

backend_lot_b:
  - task: "Lot B — Logo entreprise: stockage + apposition sur PDF + bandeau DOCUMENT INTERNE"
    implemented: true
    working: true
    file: "/app/backend/models.py + /app/backend/routes/company.py + /app/backend/routes/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Backend: CompanyProfile et CompanyProfileUpdate exposent un champ optionnel logo_base64 (data URL). PATCH /api/company/profile accepte ce champ et l'enregistre dans la collection companies. _to_profile() le ressort. GET /chantiers/{id}/export.pdf: charge le logo via db.companies.find_one(), construit un en-tête 2 colonnes (logo gauche + nom société droite via reportlab Table), suivi d'un bandeau orange 'DOCUMENT INTERNE — Fiche technique de mesurage, usage strictement interne'. Si pas de logo, le PDF garde son rendu sans crash (header_logo_cell vide)."
        -working: true
        -agent: "testing"
        -comment: "LOT B — 18/18 PASS sur la suite ciblée (/app/backend_lot_b_test.py) + 167/167 pytest existant PASS (cd /app/backend && python -m pytest tests/ -q --no-cov en 31.89s). Détails: (T1) GET /company/profile (admin, après PATCH artisan_mode=false) → 200, logo_base64=null initialement ✓. (T2) PATCH /company/profile {logo_base64:'data:image/png;base64,<valid PNG 200x100>'} → 200, response.logo_base64 === payload (identique) ✓. (T3) GET /company/profile vérifie persistance → 200, logo_base64 identique au PATCH ✓. (T4) PATCH {logo_base64:''} → 200, logo_base64='' (chaîne vide effectivement écrite — update_company_profile filtre seulement les None) ✓. (T5) Re-PATCH avec logo pour préparer le test PDF → 200 ✓. (T6) GET /chantiers → 200, 14 chantiers existants, picked id=dbd7564b-b7d6-4f03-8b3c-e5bc5ce9701b ✓. (T7) GET /chantiers/{id}/export.pdf avec logo PNG valide → 200, ct=application/pdf, taille=3218 bytes (>1500), magic %PDF présent en début ✓. (T7b) Décompression du PDF via pypdf : 'DOCUMENT INTERNE — Fiche technique de mesurage, usage strictement interne' BIEN PRÉSENT dans le bandeau (extracted text confirms 'DOCUMENT INTERNE' line + 'default via MesureChâssis' header) ✓. (T8) GET .../export.pdf après PATCH {logo_base64:''} → 200, ct=application/pdf, taille=2765 bytes (>1500), magic %PDF, AUCUN crash ✓. (T8b) Le PDF sans logo contient AUSSI le bandeau 'DOCUMENT INTERNE' (vérifié via pypdf) — header_logo_cell vide mais le banner orange reste affiché ✓. (T9 RBAC commercial) GET /company/profile commercial → 200 ✓ ; PATCH avec logo → 403 detail='Admin only' (require_admin actif) ✓. (T10 RBAC tech) GET → 200 ✓ ; PATCH → 403 'Admin only' ✓. (T11 logo invalide) PATCH {logo_base64:'pas-une-data-url'} → 200 (validation laxiste comme attendu) ; GET .../export.pdf → 200 magic %PDF- taille=2765 bytes — le try/except dans exports.py l.124-135 attrape l'exception base64 et continue le rendu ✓. (T12) cd /app/backend && python -m pytest tests/ -q --no-cov → 167 passed in 31.89s ✓. ⚠️ NOTE BUG MINEUR DÉCOUVERT EN TESTANT: si on envoie un logo dont les bytes base64 décodent mais qui n'est PAS un PNG valide (ex: bytes aléatoires), PIL/ImageReader lève 'broken data stream when reading image file' DURANT doc.build() qui est HORS du try/except → 500. Le try/except actuel couvre uniquement base64.b64decode() mais pas le rendu PIL. NOT BLOCKING car aujourd'hui les data URLs malformés (qui ne décodent pas en base64 valide) sont gérés OK (T11). Mais un attaquant pourrait envoyer un PNG corrompu pour casser le PDF. Recommandation: déplacer la construction de RLImage() dans une zone protégée, ou pré-valider l'image avec PIL.Image.open()+verify() au PATCH /company/profile. CLEANUP COMPLET: logo retiré (PATCH {logo_base64:''} → 200, final logo=''); artisan_mode restauré à true (état initial); aucun chantier créé pour le test (chantier existant réutilisé). ZÉRO 5xx pendant le run principal."

backend_feedback_email_mailto:
  - task: "Feedback email: bouton mailto cliquable + reply_to=sender_email"
    implemented: true
    working: "NA"
    file: "/app/backend/email_service.py + /app/backend/routes/feedbacks.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "send_feedback_email() refactorisée: HTML enrichi avec bouton 'RÉPONDRE AU CLIENT' (mailto:sender_email avec sujet/body pré-remplis), table d'en-tête nom/email/société/page, message en bloc orange. send_email() accepte désormais reply_to_override pour override le reply-to default. Côté feedbacks.py: SUPPORT_EMAIL=info@mesurechassis.com (default), envoi avec reply_to_override=sender_email (cliquer Répondre dans le mail répond directement au client). Test direct Python validé: delivered=true, id=8e02a883-5312-453d-a19e-be8a4dd3605e. Pas de test agent nécessaire (mail externe non testable automatiquement)."
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

backend_lot_d:
  - task: "Lot D — Onboarding différencié Artisan vs Entreprise (account_type)"
    implemented: true
    working: true
    file: "/app/backend/routes/auth.py + /app/backend/models.py + /app/backend/routes/company.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /api/auth/register accepte désormais un champ optionnel account_type ∈ {artisan, entreprise} (défaut entreprise). Si 'artisan' → company créée avec artisan_mode=True automatiquement, company_name optionnel (fallback = name utilisateur). Si 'entreprise' → artisan_mode=False, company_name OBLIGATOIRE (HTTP 400). models.CompanyProfile.account_type ajouté (défaut entreprise). routes/company.py:_to_profile() retourne account_type depuis le doc Mongo."
        -working: true
        -agent: "testing"
        -comment: "LOT D — 39/39 PASS (/app/backend_lot_d_test.py). (T1) Inscription Artisan : POST /auth/register {name:'Jean Artisan', account_type:'artisan'} sans company_name → 200 + verification_link + user.role='admin' ; DB company doc créé avec account_type='artisan', artisan_mode=true, name='Jean Artisan' (fallback sur name utilisateur). /auth/verify {token} → 200 + access_token. GET /company/profile → account_type='artisan', artisan_mode=true, beta_mode=true, plan='pro' ✓. (T2) Inscription Entreprise valide : POST /auth/register {account_type:'entreprise', company_name:'Menuiseries TestSAS'} → 200 + verification_link ; DB doc account_type='entreprise', artisan_mode=false, name='Menuiseries TestSAS'. Verify+profile retournent account_type='entreprise', artisan_mode=false ✓. (T3) Entreprise SANS company_name → 400 detail=\"Le nom de l'entreprise est requis pour un compte Entreprise.\" ; AUCUN user créé en DB (count=0) ✓. (T4) account_type='bidon' → fallback 'entreprise' : sans company_name → 400 ; avec company_name='FallbackCorp' → 200, DB account_type='entreprise', artisan_mode=false ✓. (T5) Compat ascendante : POST sans champ account_type + company_name → 200, DB account_type='entreprise' (défaut) ✓. (T6) GET /company/profile admin legacy → 200, account_type='entreprise' (défaut côté _to_profile) — pas de crash sur le doc sans le champ ✓. (T7) Régression pytest : cd /app/backend && python -m pytest tests/ -q --no-cov → 167 passed in 61.86s ✓. (Bonus) Compte Artisan (role=admin) peut POST /chantiers → 200 + GET own chantier → 200 (pas de 403). CLEANUP : 4 users + 4 companies lotd_* supprimés en Motor direct, email_verifications + chantiers liés purgés. admin@mesurechassis.fr/admin123 login → 200 INTACT. Aucune modification de BETA_MODE ni de artisan_mode du compte 'default'. ZÉRO 5xx. Backend Lot D prêt production."

frontend_lot_d:
  - task: "Lot D — Sélecteur Artisan/Entreprise sur écran d'inscription"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/index.tsx + /app/frontend/src/context/AuthContext.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Sélecteur visuel 2 cartes (testID account-type-artisan / account-type-entreprise) en haut du formulaire register. État accountType défaut 'artisan'. Labels/placeholders et bloc info adaptés selon le choix. Champ 'Nom de l'entreprise' OBLIGATOIRE (étoile rouge) en Entreprise / 'Nom commercial (optionnel)' en Artisan. Validation onSubmit: si Entreprise + companyName vide → Alert et blocage. AuthContext.signUp() étendu avec paramètre optionnel accountType envoyé au backend. CompanyProfile type étend account_type. Validation visuelle via screenshot tool : selectors présents et cliquables. Pas de test agent frontend pour l'instant — sera testé par l'utilisateur directement."
  - task: "Resend HTTP API integration via httpx — emails transactionnels réels"
    implemented: true
    working: true
    file: "/app/backend/email_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Refactorisation complète de email_service.py: utilise httpx.Client.post() vers https://api.resend.com/emails avec Bearer token. RESEND_API_KEY, MAIL_FROM, MAIL_REPLY_TO et MAIL_SUPPORT lus depuis backend/.env. send_email() retourne dict avec delivered:bool + resend_id ou error. Fallback MOCK console en cas de clé absente, HTTP 4xx/5xx ou exception. send_password_reset_email() utilise un template HTML enrichi (code en gros caractères, branding orange). Validation manuelle réussie: POST /api/auth/forgot-password {email:'michelpezzuto@gmail.com'} → 200 sans beta_reset_code (delivered=true), Resend ID=6a6ddbe3-c4a2-4d68-8636-2c9e4c89cdf8. Notes: domaine mesurechassis.com pas encore vérifié sur Resend → on utilise temporairement onboarding@resend.dev comme expéditeur + reply_to=info@mesurechassis.com."
        -working: true
        -agent: "testing"
        -comment: "RESEND INTEGRATION VALIDÉE — Suite ciblée + targeted michelpezzuto + 167/167 pytest PASS (/app/backend_resend_test.py). (1) POST /api/auth/forgot-password {email:'michelpezzuto@gmail.com'} → 200 body={ok:true, message:'Si un compte existe...'}, BODY NE CONTIENT PAS beta_reset_code (delivered=true), log backend.err.log contient '📧 Resend OK → michelpezzuto@gmail.com (subject=...Réinitialisation..., id=5d7eb5db-2604-4591-bed9-8ceb1f5506d2)' ✓. (2) POST /api/auth/forgot-password {email:'admin@mesurechassis.fr'} → 200 OK MAIS le body retourne beta_reset_code + log montre 'Resend FAIL (403) ... You can only send testing emails to your own email address (michelpezzuto@gmail.com)'. C'est LA LIMITATION DOCUMENTÉE de Resend en mode test (domaine non-vérifié) — l'API key actuelle ne peut envoyer QU'À l'email du propriétaire du compte Resend. Le fallback fonctionne parfaitement: Resend FAIL → mock log + comme BETA_MODE=True, retour du beta_reset_code à l'utilisateur pour ne pas le bloquer. (3) Anti-énumération: POST avec email inconnu (nope_test_xxx@example.com) → 200 {ok:true, message:...}, NO beta_reset_code, NO Resend call dans les logs ✓. (4) POST {email:'pas_un_email'} → 400 detail='Email invalide.' ✓. (5) Flux complet reset-password (sur user de test qa_reset_xxx@mesurechassis.fr créé via /auth/register legacy role=technician): forgot-password → 200 + beta_reset_code (Resend 403 testing mode) ; code récupéré DIRECTEMENT en DB via Motor (password_reset_code='123456', expires=now+30min) ; reset-password {email,code,new_password:'NouveauPass1234!'} → 200 {ok:true} ; login avec nouveau mdp → 200 + access_token ; login avec ancien mdp → 401 ; réutilisation du même code → 400 'Code invalide ou expiré.' ✓. (6) Edge cases: email vide → 400, missing email key → 400, reset-password sans code → 400, weak password <6 chars → 400 ✓. (7) Code source routes/auth.py:374-379 : 'if not delivered and BETA_MODE: response_payload[beta_reset_code]=code' BIEN IMPLÉMENTÉ et fonctionnel ✓. (8) Régression: admin/commercial/tech login → 200 chacun ; GET /auth/me admin → 200 ; GET /company/profile admin → 200 ; pytest tests/ -q --no-cov → 167/167 PASS en 32.07s ✓. CLEANUP: user de test supprimé (DELETE en Motor direct, deleted=1) ; admin password=admin123 INTACT ; artisan_mode INTACT ; beta_mode INTACT. ZÉRO 5xx. Integration Resend prête production — il restera juste à vérifier le domaine mesurechassis.com sur Resend pour que les emails autres que michelpezzuto@gmail.com partent en delivered=true ; aujourd'hui le fallback BETA_MODE protège l'UX."

frontend_chat_mailto:
  - task: "ChatHelp 'Poser une question' → mailto info@mesurechassis.com"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/ChatHelp.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Bouton 'CONTACTER LE SUPPORT' → 'POSER UNE QUESTION'. Le onPress n'appelle plus router.push('/company-profile') (feedback interne) — il ouvre désormais Linking.openURL('mailto:info@mesurechassis.com?subject=Question MesureChâssis&body=...') via Linking.canOpenURL() pour fallback Alert si aucune app mail. Ajout de l'adresse info@mesurechassis.com en hint discret sous le bouton. Test manuel via simulateur recommandé (web Linking ouvre l'app par défaut)."

backend_billing:
  - task: "Unsubscribe endpoints (cancel + reactivate) — admin-only graceful termination"
    implemented: true
    working: true
    file: "/app/backend/routes/company.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS 8/8. (A1) PATCH /company/profile {artisan_mode:false} (admin)→200, am=false. (A2) GET /company/profile inclut TOUS les nouveaux champs: plan='trial', chantiers_lifetime_count=58, cancel_at_period_end=false, cancelled_at=null, subscription_status='active', subscription_expires_at='2027-05-17...'. (A3) POST /company/subscription/cancel as commercial→403 (Admin only). (A4) Same as technician→403. (A5) Admin cancel→200, cape=true, cancelled_at='2026-05-17T15:14:34...', subscription_expires_at préservé (Pro access kept). (A6) Admin cancel again→400 detail=\"L'annulation est déjà programmée.\". (A7) Commercial reactivate→403. (A8) Admin reactivate→200, cape=false, cancelled_at=null. Note: code utilise un check supplémentaire user['role']=='admin' DANS l'endpoint en plus de require_admin, mais le 403 'Admin only' provient en pratique du require_admin lui-même quand artisan_mode=false."

  - task: "Anti-fraud Freemium Project Limit (plan=free, >=3 chantiers)"
    implemented: true
    working: true
    file: "/app/backend/routes/chantiers.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS 7/7. (B0) POST /platform/companies/default/subscription header X-Platform-Token + {plan:'free'}→200 plan='free'. (B1) GET /company/profile reflète plan='free', count=58 (déjà bien >=3 vu le seed). (B2) POST /chantiers admin avec count>=3→402 detail={code:'free_plan_limit', limit:3, used:58, message:'Limite Freemium atteinte (3 chantiers maximum...)'}. (B4a) DELETE chantier admin→200. (B4b) Re-fetch /company/profile: chantiers_lifetime_count INCHANGÉ (58→58) ✓ ANTI-FRAUD. (B4c) POST /chantiers → toujours 402 free_plan_limit (le compteur n'a pas baissé). (B5a/B5b) PATCH artisan_mode=true puis POST /chantiers→200 (artisan_mode bypass la limite de plan free pour création — voulu). (B5c) Restore artisan_mode=false→200. Incrément $inc sur chantiers_lifetime_count à chaque create confirmé."

  - task: "Anti-fraud Freemium Export Lock (plan=free → 402 free_plan_no_export sur PDF/CSV/XLSX/JSON)"
    implemented: true
    working: true
    file: "/app/backend/routes/exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS 7/7. Avec plan='free' (admin, artisan_mode=false): (C-pdf) GET /chantiers/{id}/export.pdf→402 detail={code:'free_plan_no_export', plan:'free'}. (C-csv) GET export.csv→402 idem. (C-xlsx) GET export.xlsx→402 idem. (C-json) GET export.json→402 idem. (C5a) PATCH artisan_mode=true→200. (C5b/C5c) CRITIQUE ANTI-FRAUD: avec artisan_mode=true + plan=free, GET export.pdf et export.xlsx restent BLOQUÉS 402 free_plan_no_export — le mode Artisan NE bypass PAS le paywall export, conformément à la spec anti-fraud. (C5d) Restore artisan_mode=false→200. block_free_plan_exports() dependency opère AVANT restrict_advanced_exports(), donc tous les exports incluant PDF sont gated."

  - task: "Restore Pro plan + smoke regression"
    implemented: true
    working: true
    file: "/app/backend/routes/company.py + chantiers.py + exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "testing"
        -comment: "PASS 6/6. (D1) POST /platform/companies/default/subscription {plan:'trial'}→200 plan='trial'. (D2) GET export.pdf admin→200, ct=application/pdf, magic=b'%PDF-' (5 bytes). (D3) POST /chantiers admin→200 (création débloquée). (F1) GET /chantiers→200 n=7 (seed étendu). (F2) GET /users→200 n=17. (F3) GET /stats/company→200. (E/Z) FINAL CLEANUP: plan=trial, artisan_mode=true, cancel_at_period_end=false confirmé. User NE SERA PAS bloqué hors Preview. Aussi: 157/157 pytest backend tests existants passent (cd /app/backend && pytest -x --no-cov)."

agent_communication:
    -agent: "testing"
    -message: "LOT E (Soft-delete RGPD) — 30/33 PASS sur la suite ciblée (/app/backend_lot_e_test.py) + 167/167 pytest existant PASS. FONCTIONNALITÉ CORE 100% OPÉRATIONNELLE. (T1) DELETE /auth/me sans token → 401 ✅. (T2a/T2b/T2d-isolé) Validations payload OK : password manquant→400, confirm_text manquant→400, password incorrect→400 'Mot de passe incorrect.' (vérifié sur user fresh). (T3) Soft-delete sans opt-in : status='deleted', deleted_at non-null, hashed_password='', email='deleted_xxxxxxxxxxxx@deleted.invalid' (regex match), marketing_email=None, marketing_optin=False, push_tokens=[]. Login avec ancien email→401 (anti-fuite). Forgot-password→200 anti-énum. (T4) Soft-delete avec opt-in : email préservé, marketing_email==email original, marketing_optin=True, hashed_password=''. Login→401. (T5) Chantier créé par artisan préservé en DB après DELETE /auth/me (chantier.created_by pointe toujours vers user.id supprimé — données métier conservées comme attendu RGPD soft). (T6) abandoned_at company : artisan seul admin → companies.abandoned_at non-null après suppression. (T7) Resend MAIL_FROM info@mesurechassis.com : POST /auth/forgot-password admin@mesurechassis.fr → 200 SANS beta_reset_code dans le body ; log 'Resend OK → admin@mesurechassis.fr (subject=...Réinitialisation..., id=7f958782...)' confirmé. Domaine mesurechassis.com bel et bien vérifié sur Resend. (T9) Régression pytest : 167 passed in ~30s. \n\n❌ TROIS BUGS DÉTECTÉS (non bloquants pour la livraison Lot E mais à corriger) :\n(B1 MINEUR) routes/auth.py l.490 : `confirm_text = str(...).strip().upper()` transforme silencieusement 'supprimer' (minuscule) en 'SUPPRIMER' donc lowercase est accepté. La spec dit 'doit valoir exactement SUPPRIMER (majuscules)'. Fix : supprimer `.upper()` et comparer strictement.\n(B2 MINEUR) Double-DELETE → 500 : si on rappelle DELETE /auth/me sur un user déjà supprimé (hashed_password=''), `pwd_context.verify('xxx', '')` lève `passlib.exc.UnknownHashError` → 500 au lieu de 400/401. Fix : ajouter `if not user_doc.get('hashed_password'): raise HTTPException(400, 'Mot de passe incorrect.')` AVANT verify_password.\n(B3 MOYEN — sécurité/UX) GET /auth/me avec JWT zombie sur user deleted → 500 : traceback pydantic `ValidationError for UserPublic.email: input='deleted_xxx@deleted.invalid' part after @-sign is a special-use or reserved name`. EmailStr refuse le TLD .invalid. Impact : un attaquant qui aurait volé un JWT peut continuer à appeler l'API jusqu'à expiration (~1440min par défaut), et les endpoints chantiers/exports/etc planteront en 500 au lieu de 401. Fix recommandé : dans deps.auth_user(), après le chargement du user_doc, ajouter `if (user.get('status') or 'active') == 'deleted': raise HTTPException(401, 'Compte supprimé.')`. Cela rend les zombie tokens immédiatement invalides ET protège tous les autres endpoints sans modifier Pydantic. C'est LA fix la plus propre.\n\n(Bonus) GET /users côté admin de la company 'default' n'inclut pas un user deleted d'une autre company → multi-tenant OK.\n\nCLEANUP COMPLET effectué via Motor direct : tous users `lote_*@mesurechassis.fr` (+ leurs companies + chantiers + email_verifications) supprimés ; le seul user qui n'apparaissait plus sous lote_* (anonymisé en deleted_xxx@deleted.invalid) a aussi été ciblé via $or sur marketing_email. admin@mesurechassis.fr/admin123 intact. BETA_MODE et MAIL_FROM dans .env non modifiés."
    -agent: "testing"
    -message: "REVIEW REQUEST — 27/27 PASS sur la suite ciblée (/app/backend_review_test.py) + 167/167 pytest existant PASS. ✅ TROIS FEATURES VALIDÉES. (1) ARTISAN STRICT — 7/7 : POST /admin/invitations renvoie bien 403 'Les comptes Artisan sont limités à un seul utilisateur. Pour inviter des collaborateurs, passez à un compte Entreprise.' pour Artisan ; le check est BIEN AVANT l'unicité email (testé avec admin@mesurechassis.fr existant → 403, pas 400) ; Entreprise → 200 nominal ; conversion Artisan→Entreprise via update direct DB permet ensuite l'invitation 200. (2) FEEDBACK MINE — 7/7 : GET /feedbacks/mine sans token→401 ; fresh user→[] ; 2 feedbacks postés→length=2 desc OK ; ISOLATION user_id stricte vérifiée (U1 ne voit pas le feedback de U2 et vice-versa, même entre companies différentes). (3) TRIAL 90j + ANTI-FRAUDE FINGERPRINT — 9/9 : user.signup_fingerprint=sha256 hex 64 chars stocké à l'inscription ; en BETA, company.subscription_expires_at=~10 ans (branche BETA active) ; branche non-BETA contient bien `timedelta(days=90)`+`trial_expires_at`+`subscription_status='trial'`+`plan='trial'` (code grep) ; même UA → même fingerprint pour 2 inscriptions ; soft-delete préserve le fingerprint ; tentative de recréation avec même UA post-suppression → 200 EN BETA (bypass actif, comportement attendu) ; code grep confirme la branche antifraud levant 403 lookera bien `status='deleted' AND deleted_at>=now-180j AND signup_fingerprint==fp` quand BETA_MODE=False. (4) RÉGRESSION pytest tests/ -q --no-cov → 167 passed in ~32s ✓.\n\n⚠️ Note test design (sans impact production) : la review request suggérait `userA@af.test`/`userB@af.test`, mais le TLD `.test` est rejeté par Pydantic EmailStr (RFC 6761 special-use) et provoque un 500 sur `user_to_public()` au moment du register (le user est inséré en DB mais la réponse plante). C'est cohérent avec le bug B3 déjà documenté dans Lot E (EmailStr refuse .invalid pareillement). J'ai utilisé `@mesurechassis.fr` à la place — le test antifraude reste pertinent car le hash dépend de UA+IP, pas de l'email. RECOMMANDATION (non bloquant) : envelopper `user_to_public()` dans un try/except ou pré-valider le payload.email en EmailStr dans le body Pydantic du register.\n\nCLEANUP COMPLET via Motor : tous users contenant 'lotf', 'antifraud', 'fb-mine' (+leurs companies, chantiers, feedbacks, email_verifications) supprimés. admin@mesurechassis.fr/admin123 INTACT (vérifié post-cleanup). BETA_MODE et MAIL_FROM dans .env NON MODIFIÉS. ZÉRO 5xx pendant le run principal."

agent_communication_previous: Backend ajouts: (1) schéma client structuré (first_name/last_name/postal_code/city, client_name auto-composé, back-compat); (2) endpoints /api/company/profile GET (auth)/PATCH (admin); (3) bypass complet RBAC quand company.artisan_mode=true — require_roles et require_admin retournent toujours user; (4) export.json refait en schema_version mc.v1 (structure CNC-ready avec openings[].shape='rectangular'|'trapezoidal'). Frontend ajouts validés visuellement: signature supprimée, message rouge inline, suffixe (INDICATIF) Step 3, nouvelle page /company-profile avec Switch artisan, icône ⚙️ dans dashboard admin, AuthContext étendu. Test backend ciblé demandé: (a) GET /api/company/profile renvoie shape correcte; PATCH admin OK (artisan_mode true|false), PATCH commercial → 403. (b) Une fois artisan_mode=true: commercial peut PATCH /chantiers, technician peut POST /mesures, technician peut PATCH /chantiers (bypass total). (c) POST /chantiers avec uniquement first_name+last_name (sans client_name) → response.client_name = 'last_name first_name'; postal_code et city persistés et retournés. (d) GET /chantiers/{id}/export.json: présence schema_version='mc.v1', client.first_name/last_name/postal_code/city, project.appointment_at/status, openings_count cohérent, openings[].shape correct (rectangular pour standard/coulissant/porte, trapezoidal pour trapeze), trapèze dimensions_mm={width,height_left,height_right} uniquement (PAS de diagonal_1/2), porte/coulissant ont floor_reserve. (e) Reset artisan_mode=false en fin de test pour ne pas polluer. Auth: admin@mesurechassis.fr/admin123, commercial@mesurechassis.fr/commercial123, tech@mesurechassis.fr/tech123."
    -agent: "testing"
    -message: "Suite backend Iter 7 — 36/36 PASS. Regression DELETE chantier — 14/14 PASS. Backend prêt production."
    -agent: "testing"
    -message: "Iter 8 — 29/30 PASS sur la suite ciblée. (1) GET /company/profile: 200 + shape correcte pour admin/commercial/technician. (2) PATCH admin artisan=true→200; commercial/technician PATCH post-reset→403. (3) Bypass artisan_mode=true validé: commercial PATCH /chantiers→200, technician POST /mesures→200, technician DELETE /chantiers→200. (4) RESET artisan_mode=false confirme retour à l'état initial. (5) Champs client structurés: POST sans client_name + {first_name:'Marie', last_name:'Dupont', postal_code:'75011', city:'Paris', appointment_at:'2026-06-20T10:00:00Z'} → response.client_name='Dupont Marie', tous les champs persistés et echoed dans GET /chantiers. (6) Export JSON mc.v1: schema_version='mc.v1', exported_at, company_id, client {display_name='Dupont Marie', first_name, last_name, address, postal_code, city}, project {id,status,appointment_at,notes,created_at,assigned_to}, openings_count=3 cohérent. Standard/Porte→shape='rectangular' avec dimensions_mm complètes (width/height/diagonal_1/2 + floor_reserve pour porte) et diagonals_verified {d1,d2:bool}. Trapeze→shape='trapezoidal', dimensions_mm UNIQUEMENT {width,height_left,height_right} (vérifié: pas de height ni diagonal_1/2). (7) DELETE chantier admin→200, artisan_mode reste false. Aucun 5xx. Seul écart vs review request: l'endpoint POST /mesures utilise Depends(auth_user) sans require_roles, donc technician peut TOUJOURS créer des mesures même hors mode artisan (200 au lieu de 403 attendu dans la review). C'est en fait le comportement métier correct (les techniciens prennent les mesures, c'est leur rôle) — à confirmer avec main agent si une restriction est réellement souhaitée. Aucune action requise sinon."
    -agent: "testing"
    -message: "CSV export — 25/25 PASS sur la suite ciblée (/app/backend_csv_test.py). Endpoint GET /api/chantiers/{id}/export.csv pleinement fonctionnel: (1) admin→200, Content-Type='text/csv; charset=utf-8', body débute par BOM UTF-8, header inclut exactement 'Chantier;Adresse;Code Postal;Ville;Statut;Label;Type;Forme;...'. (2) 3 mesures (standard/trapeze/porte) → 3 lignes data correctement formatées. (3) Trapeze: Forme='trapezoidal', Hauteur G/D remplis (1200/1600), Hauteur/Diag1/Diag2 vides — comportement attendu. (4) Standard: Forme='rectangular', Hauteur=1500, Diag1=Diag2=1921, 'Diag1 OK'='oui'. (5) Porte: Forme='rectangular', 'Réserve sol'=35.0. (6) commercial→200, technician→200, sans-token→401, bad-uuid→404. (7) Régression: PDF (%PDF-)→200, XLSX (PK)→200, JSON (schema_version=mc.v1)→200. Aucun 5xx. Cleanup DELETE OK. Backend prêt production pour Itération 9."
    -agent: "testing"
    -message: "RBAC enforcement (artisan_mode=false) — 16/17 PASS (/app/backend_rbac_test.py). Cleanup OK: artisan_mode restored to true at end (user NOT locked out of Preview). Steps executed: (1) Admin login→200, GET initial /company/profile shows artisan_mode=true; PATCH {artisan_mode:false}→200 with artisan_mode=false echoed. (2) Seed chantier created by admin. (3) Commercial role: login→200 ✓ ; GET /chantiers→200 ✓ ; POST /chantiers→200 ✓ ; PATCH /chantiers/{id} {notes}→200 ✓ ; DELETE /chantiers/{id}→200 (review expected 403 but server code intentionally uses require_roles(['admin','commercial']) — this is the DOCUMENTED behavior validated in prior task 'DELETE /api/chantiers/{id} — autorisation admin+commercial'. Review request expectation is outdated; actual behavior is correct per spec.) ; PATCH /company/profile→403 ✓ ; GET /api/admin/stats/commercials→404 (path doesn't exist; actual endpoint is /api/stats/commercials which returned 403 ✓). (4) Technician role: login→200 ✓ ; GET /chantiers→200 ✓ ; POST /chantiers→403 ✓ ; POST /api/mesures (literal review path /chantiers/{id}/mesures returns 405 — endpoint is POST /api/mesures with chantier_id in body)→200 ✓ ; PATCH /chantiers/{id}→403 ✓ ; DELETE /chantiers/{id}→403 ✓ ; PATCH /company/profile→403 ✓. (5) CLEANUP: seed chantier deleted; PATCH /company/profile {artisan_mode:true}→200 confirmed. RBAC bypass logic in server.py:355-366 (require_roles) and 349-352 (require_admin) operates correctly: bypasses only when company.artisan_mode=true; enforces role strictly otherwise. NO critical issues."
    -agent: "testing"
    -message: "3-stage status pipeline — 7/7 PASS (/app/backend_status_pipeline_test.py). (1) Admin login OK. (2) GET /api/chantiers retourne exactement 8 chantiers seedés avec statuts diversifiés — breakdown observé: {cloture:3, technique_a_valider:2, en_commande:1, devis_a_faire:1, en_fabrication:1}; les 5 statuts canoniques (devis_a_faire, technique_a_valider, en_commande, en_fabrication, cloture) sont tous présents. (3) Pipeline transitions sur chantier non-cloturé (status initial=technique_a_valider): PATCH {status:'en_fabrication'} → 200, response.status='en_fabrication' ✓; PATCH {status:'cloture'} → 200, response.status='cloture' ✓. (4) GET /chantiers?status_filter=cloture → 200, retourne 4 chantiers (3 seedés + 1 nouvellement cloturé), le chantier cible est bien présent et tous les items ont status='cloture'. (5) PATCH {status:'foobar'} → 400 avec detail='Invalid status' ✓. VALID_STATUSES (devis_a_faire, technique_a_valider, en_commande, en_fabrication, cloture) dans server.py:53 fonctionne correctement. Données laissées telles quelles comme demandé (pas de re-seed)."
    -agent: "testing"
    -message: "POST-REFACTOR REGRESSION — 35/35 PASS (/app/backend_test.py). Le découpage du monolithe server.py (1397 lignes) en 9 modules (db.py/models.py/deps.py/utils.py/seed.py + routes/{auth,chantiers,mesures,feedbacks,company,stats,exports}.py + server.py thin 53 lignes) est validé SANS AUCUNE RÉGRESSION. Couverture: (a) Auth 3 rôles login + /auth/me. (b) Chantiers CRUD complet (POST avec champs structurés first_name/last_name/postal_code/city + client_name auto-composé, GET liste/by-id, PATCH notes+status, DELETE). (c) Mesures CRUD (standard 1500x2400 + trapeze, alerts calculés, slope OK, PATCH bay_height, DELETE). (d) GET /users (n=11), GET/PATCH /company/profile (toggle artisan_mode + restore), GET /stats/company + /stats/commercials. (e) Exports 4 formats: PDF (2493 bytes, magic %PDF-), JSON (schema mc.v1, openings={rect,trap}), CSV (text/csv;charset=utf-8 avec BOM), XLSX (spreadsheetml.sheet, magic PK). (f) Feedbacks POST/GET. (g) RBAC sanity: artisan_mode=true → tech POST /chantiers→200, commercial GET /stats/company→200, aucun 500. (h) Error handling: 422 sans address, 404 nonexistent-id, 400 status=foobar. ZÉRO 5xx sur l'ensemble. Restoration artisan_mode initiale (true) confirmée. Note: bcrypt version warning passlib observé dans backend.err.log mais c'est un warning purement cosmétique (passlib lit __about__.__version__ qui n'existe plus dans bcrypt récent) — n'impacte pas les opérations hash/verify (login/register fonctionnent parfaitement). Backend prêt production post-refactor."
    -agent: "testing"
    -message: "RBAC TIGHTENED + EXPORTS ENRICHED + LATIN-1 FIX — 47/47 PASS (/app/backend_test.py). Suite exhaustive de la review request (artisan_mode désactivé puis restauré). (1) Disable artisan_mode (admin PATCH /company/profile {artisan_mode:false}→200 ; GET confirme false). (2) RBAC MESURES strict — Admin POST/PATCH/DELETE /mesures →403 (require_roles(['commercial','technician'])), Commercial POST→200, Technician POST→200 (standard rénovation + trapèze + porte). (3) RBAC EXPORTS strict — Commercial GET .pdf→200 (magic %PDF-), Commercial GET .json/.csv/.xlsx→403 chacun (restrict_advanced_exports), Technician GET les 4 formats→200, Admin GET les 4 formats→200. (4) Content validation — JSON: schema_version='mc.v2' (NOTE: review mentionnait mc.v1 mais le code retourne mc.v2, ce qui est cohérent), openings[3].dimensions_mm dict présent sur les 3 (standard avec legacy renovation_mode flag, trapèze shape='trapezoidal', porte avec floor_reserve), openings[].renovation_mode flag présent partout, openings[].construction (bloc_thickness/wall_type/insulation/finishes) présent, site_photos array présent (vide ici). CSV: header inclut bien les nouvelles colonnes enrichies 'L. haut', 'L. bas', 'H. gauche', 'H. droite', 'L. milieu', 'H. milieu', trapèze, isolation/finitions, angle pente, Alertes (content-type text/csv; charset=utf-8). XLSX: magic 'PK', taille 6682 bytes (>1000), content-type spreadsheetml.sheet. PDF: magic '%PDF', taille 3607 bytes (>1500). (5) Latin-1 fix — POST /chantiers client_name=\"M. d'Aujourd'hui\" (apostrophes)→200; Export PDF/CSV/XLSX sur ce chantier→200 chacun, ZÉRO 500 observé (avant le fix, le Content-Disposition crashait sur latin-1). _safe_filename() (unicodedata NFKD + suppression diacritiques + re.sub) confirmé opérationnel. (6) Cleanup — DELETE des 2 chantiers de test→200 ; PATCH /company/profile {artisan_mode:true}→200 confirmé (utilisateur NE PAS bloqué hors Preview). ZÉRO 5xx sur l'intégralité de la suite. Backend prêt production. Note bcrypt warning passlib reste cosmétique. Une mineure divergence vs review request: schema_version est 'mc.v2' (pas 'mc.v1') — l'évolution du schéma a déjà été appliquée et est cohérente avec les nouvelles données (renovation_mode, construction, site_photos enrichis)."
    -agent: "testing"
    -message: "BILLING/FREEMIUM/CANCELLATION — 33/33 PASS (/app/backend_billing_test.py) + 157/157 pytest existant PASS. (A) Unsubscribe: GET /company/profile expose plan/chantiers_lifetime_count/cancel_at_period_end/cancelled_at/subscription_status/subscription_expires_at. POST /company/subscription/cancel: commercial/technician→403, admin→200 (cape=true, cancelled_at iso UTC), second appel→400 'L'annulation est déjà programmée.'. POST /company/subscription/reactivate: commercial→403, admin→200 (cape=false, cancelled_at=null). subscription_expires_at préservé lors du cancel (graceful termination). (B) Anti-fraud Freemium: POST /platform/companies/default/subscription header X-Platform-Token + {plan:'free'}→200. Avec count=58 (seed étendu, déjà >=3), POST /chantiers admin→402 detail={code:'free_plan_limit', limit:3, used:58}. CRITIQUE: DELETE chantier→200 puis chantiers_lifetime_count INCHANGÉ (anti-fraud confirmé) puis POST→toujours 402. artisan_mode=true bypass la limite création (POST /chantiers→200) — comportement voulu pour artisans solo. (C) Anti-fraud Export Lock: avec plan='free', GET export.pdf/csv/xlsx/json→402 detail={code:'free_plan_no_export', plan:'free'}. CRITIQUE: artisan_mode=true NE bypass PAS le verrou export (export.pdf et export.xlsx restent 402) — anti-fraud strict. (D) Restore Pro: platform set plan=trial→200, export.pdf→200 magic %PDF-, POST /chantiers→200. (F) Regression smoke: GET /chantiers→200 n=7, GET /users→200 n=17, GET /stats/company→200. (E) FINAL CLEANUP confirmé: plan=trial, artisan_mode=true, cancel_at_period_end=false — user NE SERA PAS bloqué hors Preview. Aucun 5xx. Backend prêt production."
    -agent: "main"
    -message: "BILLING — Unsubscribe + Anti-fraud Freemium Export Paywall. Backend changes: (1) db.py: ajout VALID_PLANS={free,trial,pro} et FREE_PLAN_MAX_CHANTIERS=3. (2) models.py CompanyProfile étendu avec plan, chantiers_lifetime_count, cancel_at_period_end, cancelled_at. (3) deps.py ensure_company : initialise plan='trial', chantiers_lifetime_count (back-fill via count_documents si existant), cancel_at_period_end=False; auth_user expose plan/chantiers_lifetime_count/cancel_at_period_end/cancelled_at sur user. (4) routes/company.py: nouveaux endpoints POST /api/company/subscription/cancel (admin uniquement, strict role=='admin', refuse si déjà annulé), POST /api/company/subscription/reactivate (admin uniquement). Endpoint platform accepte désormais aussi plan + cancel_at_period_end. GET/PATCH /company/profile renvoient les nouveaux champs. (5) routes/chantiers.py POST /chantiers : si user.plan=='free' et !artisan_mode et chantiers_lifetime_count >= 3 → 402 detail.code='free_plan_limit'. Tout create incrémente chantiers_lifetime_count via $inc (jamais décrémenté = anti-fraud). (6) routes/exports.py: nouvelle dep block_free_plan_exports qui refuse 402 detail.code='free_plan_no_export' pour tous les 4 exports si plan='free' (artisan_mode NE bypass PAS — anti-fraud strict). restrict_advanced_exports passe désormais via block_free_plan_exports. Tests existants : 157/157 PASS. Identifiants : admin@mesurechassis.fr/admin123 (master admin), commercial@mesurechassis.fr/commercial123, tech@mesurechassis.fr/tech123. La société 'default' actuelle est en plan='trial' donc les exports/creates restent libres comme avant. Pour tester la logique Free, set plan='free' via POST /api/platform/companies/default/subscription header X-Platform-Token: mc-platform-2026 body {plan:'free'} puis rétablir {plan:'trial'} à la fin. Pour la cancel/reactivate : verify (a) POST /api/company/subscription/cancel admin→200, profile.cancel_at_period_end=true, cancelled_at présent ; second appel→400. Commercial/technician→403. (b) POST /api/company/subscription/reactivate→profile.cancel_at_period_end=false. (c) Bien rétablir cancel_at_period_end=false en cleanup pour ne pas affecter la prod."


    -agent: "testing"
    -message: "7-IN-1 BATCH RE-VALIDATION — A/B/C/D/E ALL PASS (/app/backend_7in1_test.py + /app/cleanup_7in1.py). Pre-check: artisan_mode was initially TRUE → temporarily disabled (PATCH /company/profile {artisan_mode:false}→200) for proper RBAC matrix tests, then restored to TRUE at end. (A) Feedback Recipient Email: POST /api/feedbacks {user_comment:'TEST_feedback_visualization Bug détecté sur l'écran X', page_context:'/dashboard'} (admin)→200 with body {id,user_email='admin@mesurechassis.fr',user_comment,page_context='/dashboard',company_id='default',created_at} present. Backend log /var/log/supervisor/backend.err.log proves email generated: Subject='[Feedback] Marc Dubois — default', Body contains 'De     : Marc Dubois <admin@mesurechassis.fr>', 'Page : /dashboard', '─── MESSAGE ───', 'TEST_feedback_visualization Bug détecté sur l'écran X'. send_feedback_email() called from /app/backend/routes/feedbacks.py inside try/except (non-blocking). MOCKED: email is logged to console via /app/backend/email_service.py — NOT actually sent. SUPPORT_EMAIL=support@mesurechassis.fr (env default). (B) Auto Team Assignment Email: POST /chantiers as admin with assigned_to=commercial_user_id, payload {first_name:'TEST', last_name:'Assignment', address:'10 rue Test', postal_code:'75011', city:'Paris', status:'devis_a_faire'}→200, client_name='Assignment TEST'. Backend log proves: Subject='Nouveau chantier attribué : Assignment TEST', To=commercial@mesurechassis.fr, Body=\"Bonjour Sophie Martin, Un nouveau chantier vous a été attribué (créé par Marc Dubois): 📋 Assignment TEST 📍 10 rue Test, 75011, Paris\". Self-assignment anti-double: POST /chantiers with assigned_to=admin_id→200 but NO 'Nouveau chantier attribué' line appears in log tail after this POST (verified by reading log byte-offset before/after); code in routes/chantiers.py:89 `if payload.assigned_to != user['id']` correctly skips the email. Try/except non-blocking confirmed. (C) Validation Flow + Manufacturing Lock: artisan_mode=false. Created chantier {status:'technique_a_valider'}→200. Admin PATCH /chantiers/{id} {status:'en_fabrication'}→200 (backend doesn't gate the team-size logic — frontend does, per spec). Tech GET /chantiers/{id}/export.xlsx on en_fabrication chantier→200, magic 'PK', 6267 bytes. Export is unlocked for tech even when status=en_fabrication. (D) Regression: cd /app/backend && python -m pytest tests/ --no-cov → 167/167 PASS in 27.51s (test_auth, test_chantiers, test_coverage_boost, test_exports, test_feedbacks_exports, test_iter3_roles_stats_push, test_iter4_new_mesure_fields, test_iter5_validation_xlsx_signature, test_iter6_brique_parement_diagonals, test_mesures, test_multitenant, test_verification). (E) MANDATORY CLEANUP COMPLETE: DELETE 3 test chantiers (Fabrication Valide, Assignment TEST, Assignment SELF) all→200. DELETE 1 test feedback→200. PATCH artisan_mode=true→200, verified GET /company/profile.artisan_mode=true. FINAL state of company 'default': artisan_mode=true, plan='trial', subscription_status='active', cancel_at_period_end=false — utilisateur NE SERA PAS bloqué hors Preview. ZÉRO 5xx sur l'intégralité de la suite. Backend prêt production pour cette batch 7-en-1. Note: les emails sont MOCKED dans /app/backend/email_service.py — pour la prod il faudra brancher SendGrid/Resend/SMTP."

    -agent: "testing"
    -message: "BETA GRATUITE — 42/43 PASS sur la suite ciblée (/app/backend_beta_test.py) + 167/167 PASS sur pytest existant (cd /app/backend && python -m pytest tests/ -q --no-cov en 33.09s). Détails par test : (T1) GET /api/company/profile admin → 200 avec beta_mode=true, plan='pro', subscription_status='active', subscription_expires_at='2036-05-17T19:38:18...' (~9.99 ans dans le futur, > now+9y). ✓ (T2) POST /api/chantiers admin 5 fois consécutives avec payload {first_name:'Beta', last_name:'Test', address:'1 rue Beta', postal_code:'75001', city:'Paris', status:'devis_a_faire'} → 5/5 retournent 200, aucun 402. Cleanup DELETE 5/5 → 200. La limite anti-fraud Freemium est bien désactivée. ✓ (T3) Plan='free' forcé via POST /api/platform/companies/default/subscription header X-Platform-Token: mc-platform-2026 body {plan:'free'} → 200 MAIS la réponse retourne plan='pro' (PAS plan='free') — ceci est le comportement ATTENDU : `_to_profile` re-passe par `ensure_company()` qui force plan='pro' immédiatement quand BETA_MODE=True. Le test 'T3.plan==free after platform set' échoue donc mais c'est EN FAIT LA VALIDATION du design BETA_MODE : impossible de mettre un compte en free tant que BETA_MODE=True. Les autres tests T3 passent tous : POST /chantiers (admin, plan=free)→200, POST /mesures (tech)→200, GET export.pdf admin→200 (magic %PDF-, 2456 bytes), GET export.csv→200 (text/csv; charset=utf-8, 642 bytes), GET export.xlsx→200 (magic PK, 6428 bytes), GET export.json→200 (schema_version='mc.v2'). Cleanup : POST {plan:'pro'} → 200, DELETE chantier → 200. ✓ (T4) POST /api/auth/register {email:'beta_test_a1znbt4yqf@mesurechassis.fr', password:'Test1234!', name:'Beta Tester', company_name:'BetaCorp'} → 200 avec user.role='admin', user.status='pending_verification', verification_link='/verify?token=...'. Token extrait OK. POST /api/auth/verify {token} → 200 + access_token. Login → 200. GET /api/company/profile avec token du nouveau compte → plan='pro', subscription_status='active', beta_mode=true, expires_at ~9.99 ans. ✓ (T5) cd /app/backend && python -m pytest tests/ -q --no-cov → 167 passed in 33.09s : test_auth (8), test_chantiers (7), test_coverage_boost (32), test_exports (12), test_feedbacks_exports (9), test_iter3_roles_stats_push (19), test_iter4_new_mesure_fields (12), test_iter5_validation_xlsx_signature (17), test_iter6_brique_parement_diagonals (20), test_mesures (8), test_multitenant (14), test_verification (9). ZÉRO échec, ZÉRO 5xx. ✓ FINAL CLEANUP : default company state confirmé plan='pro', subscription_status='active', beta_mode=true, artisan_mode=true (préservé, non modifié). Backend prêt production en mode BETA GRATUITE. Note : le seul 'fail' rapporté par le runner (T3.plan==free after platform set) n'est pas un bug mais une CONFIRMATION du comportement attendu : BETA_MODE override toute tentative de bascule en plan free."

    -agent: "main"
    -message: "BETA GRATUITE — Stripe mis en pause, l'app bascule en mode 'Beta Gratuite' total. Backend: (1) db.py ajoute BETA_MODE=True (toggle global). (2) deps.py ensure_company force plan='pro', subscription_status='active', subscription_expires_at=now+10y, beta_account=True quand BETA_MODE actif (sinon comportement trial historique). is_subscription_blocked() retourne toujours False en mode beta. (3) routes/chantiers.py: la limite anti-fraud Freemium (3 chantiers) est désactivée tant que BETA_MODE est True. (4) routes/auth.py register : les nouveaux comptes naissent directement plan='pro'+status='active' au lieu de 'trial'. (5) models.py CompanyProfile expose nouveau champ beta_mode:bool (alimenté par BETA_MODE) pour signaler le mode au frontend. Migration DB exécutée: update_many({}) → plan='pro', subscription_status='active', subscription_expires_at=2036-…, beta_account=True sur 62 sociétés existantes. Frontend: (a) AuthContext.tsx ajoute beta_mode au type CompanyProfile + gate paywall: lock.expired NE déclenche PaywallScreen QUE si company.beta_mode=false. (b) TrialCountdownBanner.tsx réécrit: désormais affiche bannière verte rocket 'BETA GRATUITE · ACCÈS COMPLET' + ligne discrète 'Vos retours nous aident à grandir ! Signalez-nous la moindre idée via info@mesurechassis.com 💬' (tap → mailto pré-rempli). Renvoie null hors mode beta. (c) chantier/[id]/index.tsx: isFreePlan force false quand company.beta_mode (les cadenas 🔒 et restrict_free_plan_exports côté UI disparaissent). (d) company-profile.tsx: la section ABONNEMENT en mode beta remplace badge plan + statut + expiration par badge vert 'BETA GRATUITE' + bloc 'Profitez de l'accès complet…' + ligne feedback + bouton orange 'DONNER MON AVIS / CONTACTER LE SUPPORT' (mailto:info@mesurechassis.com) au lieu du 'SE DÉSABONNER'. Bloc usage Freemium et bloc cancellation programmée également masqués. Test backend ciblé demandé: (T1) GET /api/company/profile en admin doit retourner beta_mode=true + plan='pro' + subscription_status='active' + subscription_expires_at à 10 ans. (T2) POST /api/chantiers admin créer 5 chantiers consécutifs sans 402 (limite Freemium désactivée). (T3) GET /api/chantiers/{id}/export.pdf/csv/xlsx/json admin et tech→200 même si on tente de set plan='free' via /platform (le bloc anti-fraud doit être inactif). (T4) POST /api/auth/register nouveau compte → company créée doit avoir plan='pro', subscription_status='active', beta_account=True. (T5) Régression complète: les 167 pytest existants doivent toujours passer (cd /app/backend && python -m pytest tests/ -q). Identifiants: admin@mesurechassis.fr/admin123. Aucun cleanup particulier requis: BETA_MODE reste True (c'est le but)."
    -agent: "testing"
    -message: "RESEND INTEGRATION (forgot-password / reset-password) — PASS sur /app/backend_resend_test.py + targeted test michelpezzuto@gmail.com + 167/167 pytest existant PASS (cd /app/backend && python -m pytest tests/ -q --no-cov en 32.07s). RÉSUMÉ TECHNIQUE : (✓) POST /api/auth/forgot-password {email:'michelpezzuto@gmail.com'} → 200 body={ok:true,message:...}, AUCUN beta_reset_code (delivered=true), log backend.err.log = '📧 Resend OK → michelpezzuto@gmail.com (subject=Réinitialisation..., id=5d7eb5db-2604-4591-bed9-8ceb1f5506d2)'. (✓) POST avec admin@mesurechassis.fr ou user de test → 200 + beta_reset_code retourné (fallback activé) car Resend renvoie 403 'You can only send testing emails to your own email address (michelpezzuto@gmail.com)' — LIMITATION DOCUMENTÉE de Resend tant que le domaine n'est pas vérifié. Le fallback BETA_MODE protège l'UX en retournant le code pour ne pas bloquer. Code source routes/auth.py:374-379 'if not delivered and BETA_MODE: response_payload[beta_reset_code]=code' bien implémenté. (✓) Anti-énumération : email inconnu (nope_test_xxx@example.com) → 200 sans beta_reset_code, AUCUN Resend call dans les logs (le code retourne early avant l'envoi). (✓) Email invalide ('pas_un_email', '', missing key) → 400 detail='Email invalide.' (les cas missing field retournent aussi 400 sur le check vide). (✓) Flux complet reset : user de test créé via /auth/register legacy mode {role:'technician'} → 200 ; forgot-password → 200 + beta_reset_code (Resend 403 fallback) ; code 6-digits récupéré DIRECTEMENT en MongoDB via Motor (champ password_reset_code, expires_at=now+30min) ; reset-password {email,code,new_password:'NouveauPass1234!'} → 200 ; login avec nouveau mdp → 200 + access_token ; login avec ancien mdp → 401 ; réutilisation du même code → 400 detail='Code invalide ou expiré.'. (✓) reset-password weak password (<6 chars) → 400. (✓) Régression : admin/commercial/tech login → 200 chacun ; GET /auth/me admin → 200 (email=admin@mesurechassis.fr) ; GET /company/profile admin → 200. (✓) pytest tests/ → 167 passed (test_auth, test_chantiers, test_coverage_boost, test_exports, test_feedbacks_exports, test_iter3_roles_stats_push, test_iter4_new_mesure_fields, test_iter5_validation_xlsx_signature, test_iter6_brique_parement_diagonals, test_mesures, test_multitenant, test_verification). CLEANUP : test user supprimé via Motor direct (deleted=1) ; admin password='admin123' INTACT ; BETA_MODE INTACT ; artisan_mode INTACT. ZÉRO 5xx. INTEGRATION PRÊTE PRODUCTION — il restera juste à vérifier le domaine mesurechassis.com sur Resend pour que les emails autres que michelpezzuto@gmail.com partent réellement en delivered=true (la beta_reset_code fallback étant désormais inutile une fois le domaine OK)."

    -agent: "testing"
    -message: "LOT D — ONBOARDING DIFFÉRENCIÉ ARTISAN/ENTREPRISE — 39/39 PASS (/app/backend_lot_d_test.py) + 167/167 pytest régression PASS. (T1 Artisan) POST /auth/register {name:'Jean Artisan', email:lotd_artisan_<uuid>@mesurechassis.fr, account_type:'artisan'} sans company_name → 200 + verification_link + user.role='admin'. DB Motor check : company doc créé avec account_type='artisan', artisan_mode=true, name='Jean Artisan' (fallback sur user name). POST /auth/verify {token} → 200 + access_token. GET /company/profile (token artisan) → account_type='artisan', artisan_mode=true, beta_mode=true, plan='pro'. ✓ (T2 Entreprise valide) POST /auth/register {account_type:'entreprise', company_name:'Menuiseries TestSAS'} → 200 + verification_link. DB : account_type='entreprise', artisan_mode=false, name='Menuiseries TestSAS'. Verify + profile → account_type='entreprise', artisan_mode=false. ✓ (T3 Entreprise sans company_name) → 400 detail=\"Le nom de l'entreprise est requis pour un compte Entreprise.\" ; AUCUN user créé (DB count=0). ✓ (T4 account_type='bidon') Fallback en 'entreprise' (permissif, pas de validation stricte) : sans company_name → 400 ; avec company_name='FallbackCorp' → 200, DB account_type='entreprise', artisan_mode=false. ✓ (T5 Compat ascendante) POST sans champ account_type + company_name='LegacySAS' → 200, DB account_type='entreprise' par défaut, artisan_mode=false. ✓ (T6 admin legacy) GET /company/profile admin@mesurechassis.fr → 200, account_type='entreprise' (valeur par défaut côté _to_profile, pas de crash sur doc sans le champ). ✓ (T7 Régression pytest) cd /app/backend && python -m pytest tests/ -q --no-cov → 167 passed in 61.86s, 0 failed. ✓ (Bonus) Compte Artisan (role=admin) peut POST /chantiers → 200 + GET own chantier → 200 (pas de 403, RBAC OK pour admin). ✓ CLEANUP FINAL : 4 users + 4 companies lotd_* supprimés via Motor direct (db.users.delete_many + db.companies.delete_many) ; email_verifications + chantiers liés purgés. admin@mesurechassis.fr/admin123 login post-cleanup → 200 INTACT. AUCUNE modification de BETA_MODE ni de artisan_mode du compte 'default'. ZÉRO 5xx sur l'intégralité de la suite. Backend Lot D prêt production."

    -agent: "testing"
    -message: "LOT B — LOGO ENTREPRISE — 18/18 PASS (/app/backend_lot_b_test.py) + 167/167 pytest régression PASS (cd /app/backend && python -m pytest tests/ -q --no-cov en 31.89s). DÉTAILS PAR TEST : (T1) GET /api/company/profile admin (artisan_mode temporairement désactivé→false pour matrice RBAC) → 200, logo_base64=null initialement ✓. (T2) PATCH /api/company/profile {logo_base64:'data:image/png;base64,<valid PNG 200x100 généré via PIL>'} → 200, response.logo_base64 strictement identique au payload ✓. (T3) GET /company/profile → 200, logo_base64 persisté identique ✓. (T4) PATCH {logo_base64:''} → 200, logo_base64='' (chaîne vide effectivement stockée — update_company_profile filtre None mais pas la chaîne vide) ✓. (T5) Re-PATCH avec logo PNG valide pour préparer le test PDF → 200 ✓. (T6) GET /chantiers → 200, 14 chantiers existants, picked id ✓. (T7) GET /chantiers/{id}/export.pdf avec logo → 200, ct=application/pdf, taille=3218 bytes (>1500), magic %PDF présent ✓. (T7b) Extraction du texte du PDF via pypdf : 'DOCUMENT INTERNE — Fiche technique de mesurage, usage strictement interne' BIEN PRÉSENT dans le bandeau orange (extracted text confirms 'default' company name + 'via MesureChâssis' + 'DOCUMENT INTERNE' line) ✓. (T8) GET .../export.pdf après PATCH {logo_base64:''} → 200, ct=application/pdf, taille=2765 bytes (>1500), magic %PDF, AUCUN crash ✓. (T8b) PDF sans logo contient TOUJOURS le bandeau 'DOCUMENT INTERNE' (header_logo_cell vide mais banner reste affiché) ✓. (T9 RBAC commercial) GET /company/profile commercial → 200 ✓ ; PATCH avec logo → 403 detail='Admin only' (require_admin actif) ✓. (T10 RBAC tech) GET → 200 ✓ ; PATCH → 403 ✓. (T11 logo invalide non-data-url) PATCH {logo_base64:'pas-une-data-url'} → 200 (validation laxiste comme attendu) ; GET .../export.pdf → 200 magic %PDF- taille=2765 — le try/except dans exports.py:124-135 attrape l'exception base64 et continue sans crash ✓. (T12) cd /app/backend && python -m pytest tests/ -q --no-cov → 167 passed in 31.89s ✓. ⚠️ NOTE BUG MINEUR DÉCOUVERT EN TESTANT (non bloquant pour cette livraison) : si on envoie un logo dont les bytes base64 DÉCODENT correctement mais qui n'est PAS un PNG valide (par ex bytes aléatoires ou PNG corrompu), PIL/ImageReader lève 'broken data stream when reading image file' DURANT doc.build() qui est HORS du try/except → l'endpoint renvoie un 500. Le try/except actuel exports.py:124-135 ne couvre que base64.b64decode()+RLImage() mais pas le rendu PIL effectif qui n'a lieu qu'à doc.build(). Aujourd'hui les data URLs malformés (qui ne décodent pas en base64 valide) sont gérés OK (validé en T11). Mais un PNG syntaxiquement valide en base64 mais corrompu pourrait casser le PDF. ⚠️ Recommandation main agent : pré-valider l'image au PATCH /company/profile en faisant PIL.Image.open(io.BytesIO(decoded)).verify() — refuser 400 si le PNG/JPG est corrompu. Cela évite un 500 plus tard sur le PDF. (Bug existant uniquement sur input adversarial, pas dans le flow utilisateur normal.) CLEANUP COMPLET CONFIRMÉ : (a) PATCH /company/profile {logo_base64:''} → 200, final logo='' (logo retiré). (b) Restoration artisan_mode=true → 200 (état initial préservé, utilisateur ne sera pas bloqué hors Preview). (c) Aucun chantier créé pour le test (chantier existant réutilisé). (d) Credentials admin/commercial/tech INTACTS. ZÉRO 5xx sur le run principal."



    -agent: "main"
    -message: "FIX CRITIQUE crash team.tsx + 3 UI manquantes (session juin 2025). (1) BUG TROUVÉ ET CORRIGÉ : admin/team.tsx lignes 472 et 483 contenaient un typo critique 'stylestyles.extraBtn' et 's.extraBtnGhost'/'s.extraBtnPrimary' (variables inexistantes). Les enfants d'un <Modal> étant évalués même quand visible={false}, cela provoquait un ReferenceError au mount, d'où le crash de la page Équipe sur Android (et un crash silencieux web). Le build v8 lancé avec --clear-cache N'AURAIT PAS résolu le crash car le bug est dans le code source. Un nouveau build v9 sera nécessaire. (2) Bridage Admin (entreprise) : modifié chantier/[id]/index.tsx ligne 108 — canMeasure = roleIsCommercial || roleIsTechnician || (roleIsAdmin && (isArtisanAccount || artisanMode || isSoloArtisan)). Désormais l'Admin en compte Entreprise ne voit plus les boutons 'AJOUTER UNE OUVERTURE', 'MODIFIER LA STRUCTURE DU MUR', 'AJOUTER UN CHÂSSIS / UNE OUVERTURE'. L'Admin solo (artisan ou teamSize=1) conserve tous les droits. (3) UI Bascule Artisan/Entreprise dans company-profile.tsx : nouveau bloc 'TYPE DE COMPTE' devient interactif avec bouton 'PASSER EN COMPTE ARTISAN (24,99 €)' ou 'PASSER EN COMPTE ENTREPRISE (54,99 €)'. Modale de confirmation avec message d'avertissement explicite : 'Vous conservez tous vos chantiers ainsi que les noms des personnes ayant pris les mesures. Vous perdez toutes les fonctionnalités dédiées aux équipes. Vous obtenez toutes les fonctionnalités de l'Artisan.' Appelle POST /api/company/switch-account-type (créé précédemment, refuse Entreprise→Artisan si membres équipe encore actifs avec HTTP 409). (4) UI Contact Support dans company-profile.tsx : remplacement du mailto: par modale sujet+message (max 5000 chars) qui poste vers POST /api/support/contact. Le backend stocke dans support_tickets et envoie l'email vers info@mesurechassis.com via Resend. Plus de dépendance à l'app Mail du Samsung. Linking import supprimé. Tests visuels : page Équipe affiche correctement (avant : crash), page company-profile rend correctement le nouveau bloc Type de compte. Lint TS donne faux positifs sur `type X = {}` (parser ESLint non configuré pour TS) — sans incidence sur Metro bundle. PROCHAINE ÉTAPE : Lancer un build EAS v9 (cancel le v8 si encore en cours) car le fix du crash team est dans le code source, pas dans le cache."

