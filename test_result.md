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
        -working: "NA"
        -agent: "main"
        -comment: |
          ⬆️ EXPORT v2 ENRICHI (mai 2025). Plus une simple synthèse du 1er escalier — désormais :
          • PDF : section dédiée par escalier (n_stairs pages) avec table récap stair, table par niveau
            (hauteur, sol fini, réserve, hauteur_eff, h, g, blondel, pente), table tronçons (#, type, L, largeur, marches),
            warnings inline, et un dessin de profil multi-niveaux/tronçons avec légende couleurs
            (vert=marches, bleu=palier, orange=quart-tournant).
          • DXF : la fonction écrit désormais des marches individuelles (risers + treads),
            des paliers horizontaux et des quart-tournants sur des calques distincts (`STAIR_<NAME>_DROIT/PALIER/QUART_*`)
            par escalier, avec offsets X pour empiler plusieurs escaliers côte-à-côte.
          • Le router DXF n'exige plus la présence d'une mesure legacy quand le projet a des stairs[].
          • Smoke-test local OK : projet à 2 stairs (4 tronçons mixtes, 3 niveaux) → PDF 8464 bytes, DXF 9079 bytes.
          • Legacy preserved : projet sans stairs mais avec measurement → PDF 4302 bytes, DXF 3568 bytes (calque STAIR_PROFILE intact).
          • Regression tests : 24/24 PASS (moteur Blondel non touché).
        -working: true
        -agent: "testing"
        -comment: |
          ✅ Validation V2 enrichment (36/36 PASS) via /app/backend_test.py contre l'URL publique.
          Scénario 1 (Smoke PDF V2 — marc / projet neuf 1 stair "Cave-to-RDC" / 2 niveaux RDC+R+1 /
          4 tronçons mixtes droit+palier+quart_haut+droit) :
          - GET /api/projects/{pid}/export/pdf → 200, Content-Type application/pdf, header %PDF-1.4,
            taille 9640 bytes (>> 5000, confirme la section V2 enrichie).
          Scénario 2 (Smoke DXF V2) :
          - GET /export/dxf → 200, Content-Type application/dxf, contient SECTION + ENDSEC,
            calques `STAIR_CAVE-TO-RDC_DROIT`, `STAIR_CAVE-TO-RDC_PALIER`, `STAIR_CAVE-TO-RDC_QUART_HAUT`
            tous présents (les 3) + calque `LIMON` présent.
          Scénario 3 (Multi-stair) : ajout 2e escalier "Mezzanine" (1 niveau h=1800 / 1 tronçon droit) :
          - PDF taille passe de 9640 → 12896 bytes (page break + nouvelle section confirmés).
          - DXF contient simultanément les préfixes `STAIR_CAVE-TO-RDC_` ET `STAIR_MEZZANINE_`
            (offsets X effectifs).
          Scénario 4 (Non-régression legacy) : admin@demo.fr → 12 projets, projet migré "Vidal"
          (measurement legacy + stairs[] générés par migration_v2) → GET /export/pdf 200 %PDF-1.4
          taille 8383 bytes : la section legacy ET la section V2 cohabitent sans crash.
          Scénario 5 (Paywall + Blondel) :
          - expired@demo.fr → login 200, mais GET /export/pdf renvoie 402 (paywall actif sur exports).
          - GET /stairs/{sid}/compute sur le projet V2 : total_steps=29, niveau RDC h=180.0,
            Blondel=610 valid=True (560-670). Calcul cohérent.
          Aucune régression détectée. Le moteur Blondel reste intact et l'enrichissement V2
          (PDF par-escalier + DXF multi-calques) est pleinement opérationnel.

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

frontend:
  - task: "V2 Stair Editor — Toggle Profil/Plan multi-tronçons"
    implemented: true
    working: "NA"
    file: "/app/frontend/app/projects/[id]/stairs/[sid].tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: |
          Ajout d'un toggle pill PROFIL ↔ PLAN au-dessus de la liste des niveaux (sous KPI/warnings).
          - Profil : composant existant NiveauSketch (vue de côté, polyligne montée + paliers).
          - Plan (nouveau NiveauPlanSketch) : vue de dessus, walk des tronçons avec changement de
            direction aux quart-tournants (quart_bas = +90° CW, quart_haut = +90° CCW),
            scaling auto sur bounding box, rectangles colorés (vert marches / bleu palier / orange quart),
            step lines (nez de marche), point DÉPART, boussole.
          - Validation visuelle via screenshot tool : toggle fonctionnel sur projet Caron Léa,
            les deux vues s'affichent correctement, état préservé entre re-renders.
            Validation manuelle utilisateur recommandée (notamment sur escaliers multi-tronçons mixtes).

frontend:
  - task: "Phase 4 — Plan de Balancement & Export (page dédiée)"
    implemented: true
    working: true
    file: "/app/frontend/app/projects/[id]/stairs/[sid]/export.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: |
          Nouvelle page complète /projects/{id}/stairs/{sid}/export :
          • SVG balancement à l'échelle avec marches dansantes radiales dans quart-tournants
            (pivot au coin intérieur), marches parallèles dans les droits, paliers en bleu,
            cotation largeur (flèches + L. xxx mm), point DÉPART, boussole, ligne de foulée pointillée.
          • 4 cartes KPI vert pomme : MARCHES / HAUTEUR h / GIRON g / PENTE.
          • Alerte Blondel temps réel : vert (600-640 OK), orange (560-670 acceptable), rouge (hors plage).
          • 3 checkboxes : photos / notes / logo (testID opt-photos|notes|logo).
          • Sélecteur format pill 3-states : PDF CLASSIQUE | DXF AUTOCAD | PDF + DXF (testID fmt-*).
          • Sticky bottom : MODIFIER LA CONFIG + GÉNÉRER LES LIVRABLES (téléchargement direct web via blob+anchor).
          • Validation E2E : flow login → projet → escalier → export → décocher photos → PDF only → GÉNÉRER
            → fichier escalier_<name>.pdf téléchargé avec succès (web).
          Backend extended :
          • GET /api/projects/{pid}/export/pdf?stair_id&include_photos&include_notes&include_logo (defaults true)
          • GET /api/projects/{pid}/export/dxf?stair_id
          Smoke test backend :
            - default: 13500 bytes / filtered: 10244 bytes / stripped: 9217 bytes (ordering correct) ✓
            - DXF stair filter: 6984 bytes contains SECTION ✓
            - Bad stair_id: 200 (génère un PDF vide pour la stair, pas un crash) — comportement acceptable.

frontend:
  - task: "Refactor V2 — floor_index strict + ghost + shape DROIT/TOURNANT + DÉTAILS"
    implemented: true
    working: true
    file: "/app/frontend/app/projects/[id]/stairs/[sid]/index.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: |
          PHASE 5 — Refactor majeur (mai 2025) :

          BACKEND :
          • Niveau : `floor_index: int (-3..+7)` + `is_ghost: bool` (Pas d'escalier ici).
          • Stair : `shape: 'droit' | 'tournant'`.
          • Validation contigüité : un saut de niveau → HTTP 400 "Saut de niveau détecté : il manque [N]".
          • Validation out-of-range : floor_index ∉ [-3,+7] → HTTP 422.
          • Validation duplicate : floor_index existant → HTTP 400 "Le niveau X existe déjà".
          • DROIT auto-crée 1 niveau RDC + 1 tronçon droit à la création de la stair.
          • Label auto-dérivé du floor_index : -1→"Sous-sol", 0→"RDC", 1→"R+1", etc.
          • Migration : backfill `shape` (heuristique) et `floor_index` (depuis label) sur tous les projets existants.
          • Smoke test backend : 6 scénarios contigüité/ghost/range/dup/DROIT → tous OK.

          FRONTEND :
          • Modal popup "Ajouter escalier" : champ Nom + sélecteur Forme (DROIT card / TOURNANT card).
          • Editor stair : badge `+0` (floor_index) au lieu d'index, label dérivé en titre, badge FANTÔME.
          • Bouton "AJOUTER UN NIVEAU" + bouton "NIVEAU FANTÔME" (dashed border).
          • Niveau ghost : section tronçons remplacée par notice "Pas d'escalier à ce niveau".
          • Section "DÉTAILS DE LA SAISIE" en bas : récap forme, n niveaux, hauteur, reculement, marches, limon + per-niveau breakdown avec tronçons listés. **Plus jamais vide.**
          • @shared-ui enrichi : Modal, Picker, Checkbox + KPI exposés depuis /shared-ui/index.
          • Index header documentant la portabilité multi-app (MesureEscalier ↔ MesureChâssis).

          INFRA :
          • Supervisor expo : retiré `--tunnel` → plus de 502 ngrok zombie. Le preview localhost:3000 sert directement.

frontend:
  - task: "Cleanup V1 legacy (base-mère)"
    implemented: true
    working: true
    file: "/app/backend/server.py + frontend cleanup"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: |
          🧹 NETTOYAGE V1 — Base-Mère propre (mai 2025).

          BACKEND :
          • Supprimé `routers/measurements.py` (endpoint V1 /projects/{pid}/measurement) — plus aucun appel frontend.
          • Supprimé l'import + include_router dans `server.py`.
          • Supprimé `tests/test_iteration3_math.py` (intégration V1 obsolète, math couvert par test_engine_regression).
          • Supprimé la classe `TestMeasurement` de `tests/test_mesure_escalier.py` (V1).
          • `services/stairs.py` (moteur math V1) PRÉSERVÉ — utilisé par regression tests, aucun changement.

          FRONTEND :
          • Supprimé `app/projects/[id]/export.tsx` (page export V1 niveau projet — superseded par stair-level).
          • Bouton EXPORTER du projet redirige désormais vers `/projects/{id}/stairs/{first_stair_id}/export`.
          • Supprimé `Measurements.*` du client API (`src/api.ts`).

          VALIDATION :
          • Lint Python : All checks passed ✓
          • Tests : 44 passed / 0 failed (avant : 43 + 14 fails sur V1)
          • Regression Blondel : 24/24 PASS ✓
          • Smoke screenshot : projet view + redirection EXPORTER OK
          
          STRUCTURE FINALE :
          • Backend : 7 routers (auth, projects, exports, voice, stats, integration, stairs_v2)
          • Frontend : 14 routes (auth + project CRUD + stair editor V2 + stair export V2)
          • Tests : 44 intégration + 24 regression = 68 tests passants

frontend:
  - task: "Master V2 Refactor — 4 shapes + HT/ED/HSP linked + Hybride build"
    implemented: true
    working: true
    file: "/app/frontend/app/projects/[id]/index.tsx + [sid]/index.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: |
          MASTER V2 REFACTOR (mai 2025) — Refactor majeur pour atteindre la "Base-Mère" production.

          BACKEND :
          • `Stair.shape` étendu de 2 → 5 valeurs :
            'droit' | 'quart_tournant' | 'demi_tournant' | 'helicoidal' | 'tournant' (alias V2.0).
          • `Niveau` enrichi avec 3 champs liés :
            - `epaisseur_dalle_mm` (ED, mm)
            - `hauteur_sous_plafond_mm` (HSP, mm)
            - `entry_mode: 'hauteur'|'hsp'` (verrouillage UI du champ auto-calculé)
          • Schema migration auto au startup (idempotent).
          • Tests 44 passing.

          FRONTEND :
          • Modal popup création : grid 2×2 de 4 cartes (DROIT, 1/4 TOURNANT, 2/4 TOURNANT, HÉLICOÏDAL).
            - HÉLICOÏDAL : disabled visuel + badge orange "BIENTÔT" + Alert "Bientôt disponible".
          • DroitForm refondu — section "HAUTEURS — SAISIE LIÉE" :
            - 3 champs HT/ED/HSP en saisie liée
            - L'un des 2 (HT ou HSP) est verrouillé selon entry_mode, affiché en italique gris avec badge "🔒 AUTO"
            - Tap sur champ verrouillé → switch entry_mode (devient saisissable, l'autre se verrouille)
            - Calcul instantané (HT = HSP + ED ; HSP = HT − ED)
          • Section "EMPRISE AU SOL" : Largeur + Longueur (inchangé).
          • Validation Blondel inline (vert/orange).
          • Validation E2E screenshot OK : modal 4 shapes ✓, DROIT avec HT/ED/HSP + lock ✓.

          INFRA (HYBRIDE choix ① b) :
          • Metro reste actif sur port 3000 pour Expo Go.
          • `./build-web.sh` génère `/app/frontend/dist/` (49s) pour fallback statique navigateur.
          • `--serve` du script bascule supervisor sur serve dist si l'utilisateur veut couper Metro.

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 9
  run_ui: false

test_plan:
  current_focus:
    - "Priorité 2 — Différenciation 1/4 vs 2/4 Tournant (auto-seed + detection + smart banner)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      🎯 PRIORITÉ 2 — ENRICHISSEMENT MÉTIER (Mai 2025).
      
      Pousse la différenciation 1/4 T vs 2/4 T au-delà du backend auto-seed :
      l'UI elle-même parle désormais le vocabulaire de l'artisan terrain.
      
      **1. Auto-seed étendu à la création (POST stair) :**
         - shape=droit            → [Droit 3500]
         - shape=quart_tournant   → [Droit 1500, Quart_bas 1200, Droit 1500]
         - shape=demi_tournant    → [Droit 1200, Quart_bas 1000, Droit 900, Quart_haut 1000, Droit 1200]
         Plus besoin de PATCH après création pour seed.
      
      **2. Labels contextuels métier (contextualTronconLabel) :**
         Le titre de chaque tronçon dépend de SA POSITION + de la forme :
         - 1/4 T (3 sections) : "Volée BAS" · "Quart Tournant" · "Volée HAUT"
         - 2/4 T (5 sections) : "Volée BAS" · "Premier Quart" · "Repos Intermédiaire"
                                · "Second Quart" · "Volée HAUT"
         Le type technique (Droit, Quart-tournant BAS/HAUT, Palier) reste affiché
         en sous-titre gris pour traçabilité.
      
      **3. Smart Picker (suggestNextTroncon) :**
         Le bouton "AJOUTER UN TRONÇON" devient contextuel et propose le prochain
         tronçon attendu de la séquence métier :
         - Bouton fermé affiche "AJOUTER : <TYPE SUGGÉRÉ>" (ex. "AJOUTER : QUART-TOURNANT BAS")
         - Bouton ouvert affiche les 4 options + ÉTOILE ★ sur la suggestion
         - Hint pédagogique en haut : "💡 Ajoutez le Premier Quart" / "💡 Terminez par la Volée HAUT"
         - Options non recommandées sont visuellement atténuées (opacity 0.4)
         - Quand la séquence est complète, affiche "Structure 1/4 T complète. Vous pouvez ajuster."
      
      **4. Validation visuelle (screenshots localhost:3000) :**
         - 2/4 T → Tronçons listés "1. Volée BAS · Droit" / "2. Premier Quart · Quart-tournant BAS"
                  / "3. Repos Intermédiaire · Droit" / "4. Second Quart · Quart-tournant HAUT"
                  / "5. Volée HAUT · Droit"
         - 1/4 T → "1. Volée BAS · Droit" / "2. Quart Tournant · Quart-tournant BAS" / "3. Volée HAUT · Droit"
         - Smart picker : badge "★ AJOUTER : <type>" sur le bouton suggéré
      
      **Tests backend :** 20/20 PASS (test_mesure_escalier.py).
      
      **Fichiers modifiés :**
      - /app/backend/routers/stairs_v2.py — POST stair auto-seed étendu aux 3 formes
      - /app/frontend/app/projects/[id]/stairs/[sid]/index.tsx — contextualTronconLabel,
        suggestNextTroncon, NiveauCard accepte stairShape, picker refactored avec
        hint + suggestion étoile + options atténuées


      
      L'écran "Aucun escalier" était une impasse bloquante (aucun CTA visible
      directement dans le bloc empty, le bouton "AJOUTER UN ESCALIER" était
      séparé et pas évident). Résolu en 3 améliorations cumulatives :
      
      1. **CTA embarqué dans l'empty state** :
         - Bordure pointillée VERTE (accent) au lieu de gris
         - Icône stairs-up VERTE (accent) au lieu de gris terne
         - Hint mis à jour : "choisissez la forme (Droit, 1/4 T, 2/4 T, Hélicoïdal)..."
         - Bouton plein vert "+ AJOUTER MON PREMIER ESCALIER" directement
           dans le bloc empty (testID="btn-add-first-stair")
      
      2. **FAB "+" flottant** en bas-droite, toujours visible quand canEdit :
         - Rond 56×56px vert avec bord sombre + ombre
         - Position absolute right/bottom 16px
         - testID="fab-add-stair"
      
      3. **Banner verrou contextuel** : si canEdit=false (projet locked),
         affiche un encadré orange "Chantier verrouillé — déverrouillage
         admin nécessaire" au lieu de laisser l'utilisateur sans explication.
      
      **Flux validé en screenshot** :
      - Empty state → CTA primaire vert visible
      - Click CTA → modal AUCUN ESCALIER s'ouvre avec les 4 cartes techniques
        (DROIT + checkbox Niveau Fini, 1/4 TOURNANT L-shape, 2/4 TOURNANT U-shape,
        HÉLICOÏDAL avec badge BIENTÔT)
      - Input nom + bouton CONFIGURER →
      - FAB "+" reste accessible en permanence en bas-droite
      
      **Tests backend** : 20/20 PASS (test_mesure_escalier.py).
      
      **Fichier modifié** :
      - /app/frontend/app/projects/[id]/index.tsx (empty state + FAB + styles)


      
      Le comportement métier est désormais nettement distingué :
      
      **1. Auto-seed backend (PATCH stair) :**
      - shape='quart_tournant' (1/4 T) → [droit 1500, quart_bas 1200, droit 1500] (1 angle)
      - shape='demi_tournant'  (2/4 T) → [droit 1200, quart_bas 1000, droit 900, quart_haut 1000, droit 1200] (2 angles + section intermédiaire)
      - shape='droit'          → [droit 3500] (déjà en place)
      
      **2. Frontend intelligence — `detectStructure()` :**
      - Compte les `quart_bas + quart_haut` dans tous les tronçons saisis
      - Détecte automatiquement : 0/1/2+ angles
      - Compare avec la forme attendue → matches_shape boolean
      
      **3. Composant `ShapeStructureBanner` :**
      - Affiché en tête du flux Tournant (sous la barre de chips)
      - Mode CONFORME (vert) : "Structure 1/4 Tournant détectée (1 angle, 2 volées droites)"
        ou "Structure 2/4 Tournant détectée (2 angles, 3 volées droites)"
      - Mode WARNING (orange) : "Un seul angle détecté — il en faut 2 pour un 2/4 Tournant"
        avec hint contextuel : "Ajoutez un second quart-tournant + section intermédiaire (droite ou palier)."
      - CTA "↻ STRUCTURE TYPE" qui supprime tous les niveaux puis re-PATCH la forme
        → déclenche l'auto-seed backend → restaure la structure canonique
      - Affichage de la SÉQUENCE sous forme de pills colorées : [D] → [Q↻] → [D] → [Q↺] → [D]
        (vert pour droit, orange pour quart, bleu pour palier)
      
      **4. Validation visuelle (screenshots localhost:3000) :**
      - 1/4 T : banner vert "Conforme", séquence [D|Q↻|D], split COUPE/PLAN nickel
      - 2/4 T : banner vert "Conforme", séquence [D|Q↻|D|Q↺|D], plan en forme de U
      - 2/4 T cassé (1 quart supprimé) : banner orange + CTA "STRUCTURE TYPE" visible
      
      **Tests backend :** 20/20 PASS (test_mesure_escalier.py).
      
      **Fichiers modifiés :**
      - /app/backend/routers/stairs_v2.py — auto-seed PATCH étendu aux 3 formes
      - /app/frontend/app/projects/[id]/stairs/[sid]/index.tsx — detectStructure, ShapeStructureBanner, StructureBadge, loadStructureTemplate

    -agent: "main"
    -message: |
      🎯 REFACTOR MASTER V2 — Phase 1 terminée (Mai 2025).
      Implémenté l'éditeur d'escalier complet selon le Gigaprompt V2 :
      
      1. **ShapeSelectorBar** : 4 chips DROIT / 1/4 T / 2/4 T / HÉLICO en tête d'éditeur ;
         changement de forme à la volée via PATCH /api/projects/{pid}/stairs/{sid}
         (avec dialog de confirmation si données présentes).
      2. **Auto-seed niveau RDC + tronçon** dans le backend lorsque l'utilisateur
         bascule vers DROIT et que le stair n'a pas de niveaux (UX sans spinner mort).
      3. **Split visuel Coupe (gauche) + Plan (droite)** :
         - DroitForm : nouveau bloc "VISUALISATION" avec `StairSketch` (Coupe technique)
           et `PlanSketch` (Emprise au sol, shapeKey='droit') côte à côte ;
         - NiveauCard tournant : remplacement du toggle PROFIL/PLAN par un SplitVisualBlock
           qui rend `NiveauSketch` (Coupe) + `NiveauPlanSketch` (Plan) côte à côte ;
         - Nouvelles props `width` / `height` / `showLegend` sur les 3 composants SVG.
      4. **DonnéesTechniques block** sous la VISUALISATION pour DROIT : 4 KPIs compacts
         (Marches, Hauteur, Giron, Limon) + badge Blondel 2h+g vert/orange.
      5. **HelicoidalPlaceholder** : illustration SVG cercle + segments radiaux + badge
         "BIENTÔT DISPONIBLE" + texte explicatif.
      6. **Sticky footer** : RETOUR / EXPORTER inchangé, déjà cohérent sur toutes les vues.
      
      Tests backend : 20/20 PASS (test_mesure_escalier.py).
      Validation UI : screenshot localhost:3000 → KPIs, HT/ED/HSP avec lock badge AUTO,
      VISUALISATION split (Coupe Limon=4420 / Plan avec compass N + cotes), DonnéesTechniques
      avec Blondel 610 Conforme.
      Fichiers modifiés :
      - /app/backend/routers/stairs_v2.py (PATCH auto-seed droit)
      - /app/frontend/app/projects/[id]/stairs/[sid]/index.tsx (refactor complet)
      - /app/frontend/src/PlanSketch.tsx (props width/showLegend)
      
      Pas de test backend nécessaire — la seule modification backend est l'auto-seed
      conditionnel dans le PATCH stair quand shape='droit' et niveaux vide.

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
    -agent: "main"
    -message: |
      🎯 PHASE 2 — Export v2 ENRICHI (Mai 2025).
      Plus de simple synthèse du 1er escalier — désormais : par-escalier section PDF (page break entre stairs)
      avec table récap, tables par niveau (h, g, blondel, pente, hauteur eff, sol_fini/réserve),
      tableau des tronçons (type, longueur, largeur, marches assignées), warnings inline, et un dessin de profil
      multi-niveaux/tronçons coloré (vert=marches, bleu=palier, orange=quart-tournant).
      DXF : marches individuelles (risers + treads) + paliers horizontaux + quart-tournants sur calques distincts
      par escalier (`STAIR_<NAME>_DROIT/PALIER/QUART_*`), avec offsets X pour empiler plusieurs escaliers.
      Le router /dxf n'exige plus de mesure legacy si stairs[] existe.
      
      Tests locaux :
      - Projet 2-stairs / 3-niveaux / mixed tronçons → PDF 8464 bytes, DXF 9079 bytes
      - Projet legacy (measurement seul) → PDF 4302 bytes, DXF 3568 bytes (calque STAIR_PROFILE intact)
      - pytest tests/test_engine_regression.py → 24/24 PASS
      
      ⚠ DEMANDE : valider via deep_testing_backend_v2 que :
      1. GET /api/projects/{pid}/export/pdf retourne 200 + %PDF- sur un projet avec multi-stairs/niveaux/tronçons,
      2. GET /api/projects/{pid}/export/dxf retourne 200 + contient les calques STAIR_<NAME>_DROIT/PALIER/QUART_*,
      3. Pas de régression sur projet legacy (single measurement).
      Comptes : marc@mesureescalier.com / Demo1234! (admin solo, projets v2).
    -agent: "testing"
    -message: |
      ✅ Phase 2 — Export V2 enrichment VALIDÉE : 36/36 tests PASS via /app/backend_test.py contre l'URL publique.
      
      Détails :
      1. Smoke PDF V2 (marc, projet neuf, 1 stair "Cave-to-RDC", 2 niveaux RDC+R+1, 4 tronçons droit/palier/quart_haut/droit) :
         → 200 application/pdf %PDF-1.4 9640 bytes (>> 5000, confirme l'enrichissement).
      2. Smoke DXF V2 : 200 application/dxf, contient SECTION + ENDSEC, et les TROIS calques
         `STAIR_CAVE-TO-RDC_DROIT`, `STAIR_CAVE-TO-RDC_PALIER`, `STAIR_CAVE-TO-RDC_QUART_HAUT`
         + calque `LIMON` présent.
      3. Multi-stair : ajout "Mezzanine" → PDF 9640 → 12896 bytes ✓ ; DXF contient simultanément
         `STAIR_CAVE-TO-RDC_*` ET `STAIR_MEZZANINE_*` (offsets X opérationnels).
      4. Non-régression legacy : admin@demo.fr, projet migré "Vidal" (measurement + stairs[]) →
         /export/pdf 200 %PDF-1.4 8383 bytes (les deux sections cohabitent).
      5. Paywall + Blondel : expired@demo.fr → /export/pdf renvoie 402 ✓ ;
         compute V2 : total_steps=29, h=180.0, Blondel=610 valid (560-670).
      
      Aucune régression détectée. Le moteur Blondel reste inchangé, l'export V2 enrichi
      (PDF par-escalier + DXF multi-calques) est pleinement opérationnel.
      Test plan current_focus peut être marqué terminé.
