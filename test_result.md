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
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

backend_resend:
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
    -agent: "main"
    -message: "Phase 1 master workflow livrée. Backend ajouts: (1) schéma client structuré (first_name/last_name/postal_code/city, client_name auto-composé, back-compat); (2) endpoints /api/company/profile GET (auth)/PATCH (admin); (3) bypass complet RBAC quand company.artisan_mode=true — require_roles et require_admin retournent toujours user; (4) export.json refait en schema_version mc.v1 (structure CNC-ready avec openings[].shape='rectangular'|'trapezoidal'). Frontend ajouts validés visuellement: signature supprimée, message rouge inline, suffixe (INDICATIF) Step 3, nouvelle page /company-profile avec Switch artisan, icône ⚙️ dans dashboard admin, AuthContext étendu. Test backend ciblé demandé: (a) GET /api/company/profile renvoie shape correcte; PATCH admin OK (artisan_mode true|false), PATCH commercial → 403. (b) Une fois artisan_mode=true: commercial peut PATCH /chantiers, technician peut POST /mesures, technician peut PATCH /chantiers (bypass total). (c) POST /chantiers avec uniquement first_name+last_name (sans client_name) → response.client_name = 'last_name first_name'; postal_code et city persistés et retournés. (d) GET /chantiers/{id}/export.json: présence schema_version='mc.v1', client.first_name/last_name/postal_code/city, project.appointment_at/status, openings_count cohérent, openings[].shape correct (rectangular pour standard/coulissant/porte, trapezoidal pour trapeze), trapèze dimensions_mm={width,height_left,height_right} uniquement (PAS de diagonal_1/2), porte/coulissant ont floor_reserve. (e) Reset artisan_mode=false en fin de test pour ne pas polluer. Auth: admin@mesurechassis.fr/admin123, commercial@mesurechassis.fr/commercial123, tech@mesurechassis.fr/tech123."
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


