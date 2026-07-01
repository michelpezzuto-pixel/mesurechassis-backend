# 🏗️ Roadmap Odoo + Devis Automatique — Post-Apple

**Statut** : ⏸️ À exécuter dès que Apple approuve MesureChâssis (Build 110+)  
**Créé le** : 01/07/2026  
**Contexte** : Analyse CDC "Application prise de cotes fenêtres synchronisée Odoo" + discussion pricing

---

## 📊 ÉTAT DES LIEUX — MesureChâssis vs CDC Odoo

### ✅ Déjà présent (et dépasse le CDC)
- Auth JWT + RBAC 4 rôles (admin, manager, technicien, commercial)
- Multi-tenant client/chantier
- Wizard N ouvertures par relevé
- Photos multiples par ouverture (base64)
- Notes/commentaires
- Checklist validation
- Diagonales automatiques
- Yann IA temps réel
- Import CDC PDF par IA (3 sec)
- Exports PDF/CSV/XLSX/JSON
- Freemium + Stripe
- Programme parrainage
- 3 plateformes (iOS + Android + Web)

### ❌ Manquant (à ajouter)
1. **🔴 Connecteur Odoo** — LE gap stratégique
2. **🟠 Mode offline + queue de sync** — critique pour terrain
3. **🟡 Compression photos automatique** — 1h de dev
4. **🟡 Signature client** — argument commercial
5. **🟡 Génération devis automatique** — transformation en mini-ERP

---

## 💰 PRICING DEVIS AUTOMATIQUE — 3 OPTIONS

### 🅰️ Option A — Prix dans Odoo (100% Odoo)
- Comptable configure prix dans produits Odoo (100€/m² etc.)
- MesureChâssis envoie dimensions → Odoo calcule
- ❌ Pas de prix visible offline

### 🅱️ Option B — Prix dans MesureChâssis
- Grille tarifaire dans l'app admin
- Prix visible en direct sur chantier
- ❌ 2 endroits à maintenir si Odoo aussi

### 🅾️ Option C — HYBRIDE ⭐ (RECO)
- Odoo = source de vérité prix
- MesureChâssis récupère grille au démarrage → cache local
- Prix affiché en direct sur chantier (offline OK)
- Re-validation Odoo à la sync
- ✅ Prix live + un seul point de config + offline

---

## 🏗️ ROADMAP DÉTAILLÉE (post-Apple)

### Sprint 1 (2-3j) — Enrichir wizard mesure
Ajouter champs manquants pour calcul prix :
- Type de vitrage (double / triple / acoustique)
- Couleur RAL (blanc / anthracite / RAL personnalisé)
- Type de profil (Schüco / Reynaers / Reho / autre)
- Options quincaillerie (crémone, seuil PMR, poignée)
- Fournisseur associé

### Sprint 2 (3-5j) — Module Odoo dédié
Créer module Python `mesurechassis_connector` avec 3 modèles :
- `x_mesurechassis.pricing` (grille tarifaire — comptable saisit ici)
- `x_mesurechassis.releve` (en-tête relevé)
- `x_mesurechassis.ouverture` (lignes ouvertures)

Relations :
- `releve` → `res.partner` (client)
- `releve` → `crm.lead` OU `project.project`
- `releve` → `sale.order` (devis auto-généré)

### Sprint 3 (2-3j) — API bidirectionnelle
Endpoints :
- `GET /api/odoo/pricing` — récupère grille tarifaire → cache local
- `GET /api/odoo/clients` — clients assignés
- `POST /api/odoo/releve` — envoie relevé (idempotent avec UUID)
- `POST /api/odoo/photos` — upload photos
- `GET /api/odoo/status/{uuid}` — vérifier statut sync

Règles :
- Idempotence stricte (UUID côté app)
- Retry automatique en cas d'erreur réseau
- Journal des synchros

### Sprint 4 (2j) — Mode offline robuste
- AsyncStorage queue de mesures en attente
- Sync auto quand réseau revient
- Indicateur "3 mesures à synchroniser" dans header
- Résolution conflits (last-write-wins)

### Sprint 5 (1j) — Compression photos
- `expo-image-manipulator` → resize 1920px max, quality 0.7
- Réduction 80% du poids sans perte visuelle

### Sprint 6 (2j) — Écran admin "Grille tarifaire"
- Affichage miroir de la grille Odoo (lecture seule)
- Refresh manuel + auto quotidien
- Prévisualisation prix "1200×1000 fixe blanc = 120€"

### Sprint 7 (1j) — Signature client
- `react-native-signature-canvas`
- Signature base64 → PDF devis + Odoo

---

## 💼 STRATÉGIE COMMERCIALE — 2 OFFRES

### Offre 1 — "MesureChâssis Standalone"
Pour clients SANS Odoo (majorité artisans indépendants) :
- Grille tarifaire native dans l'app
- Génération devis PDF directement depuis l'app
- Envoi email client
- Prix : 19€ (Solo) / 59€ (Entreprise) / 249€ (Pro)

### Offre 2 — "MesureChâssis + Odoo Sync"
Pour PME utilisant déjà Odoo :
- Tous les avantages Standalone
- + Module Odoo installé
- + Sync bidirectionnelle
- + Devis auto dans Odoo
- Prix : +30€/mois par entreprise
- Cible : 50% des PME menuisiers Belgique/France utilisent Odoo → **TAM énorme**

---

## 🎯 PRIORISATION APRÈS APPLE VALIDATION

| Priorité | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 🥇 P0 | Sécurité (JWT, admin token, ZIP) | 1j | Bloquant |
| 🥈 P1 | Enrichir wizard (vitrage, couleur, profil) | 2j | Prérequis |
| 🥉 P2 | Mode offline + queue | 3j | Critique terrain |
| P3 | Compression photos | 1h | UX |
| P4 | Module Odoo dédié | 5j | Différentiateur B2B |
| P5 | API sync Odoo | 3j | Différentiateur B2B |
| P6 | Écran grille tarifaire | 2j | UX admin |
| P7 | Signature client | 1j | Commercial |
| P8 | Génération devis PDF native | 3j | Offre Standalone |

**Total estimé** : ~4 semaines de dev focused pour passer de "app de mesure" à **"mini-ERP menuiserie SaaS"**.

---

## 📌 NOTES IMPORTANTES

- **Ne rien commencer avant Apple validation** (Build 110)
- Le connecteur Odoo est LA killer feature qui multiplie le TAM par 5
- 50% des PME menuisiers ont déjà Odoo → cible directe
- Odoo Community = gratuit, Odoo Enterprise = payant → notre module doit marcher sur les 2
- Utiliser la nomenclature Odoo standard (`res.partner`, `sale.order`) pour être compatible
- Prévoir une doc `INSTALL_ODOO_MODULE.md` pour les clients qui installent

---

**⏸️ NE RIEN LANCER TANT QUE APPLE N'A PAS VALIDÉ BUILD 110+**
