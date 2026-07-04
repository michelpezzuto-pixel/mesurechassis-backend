# 📄 CDC Scan — Exigences de capture EXHAUSTIVE

**Créé le** : 03/07/2026  
**Contexte** : Instruction utilisateur explicite pendant la conception du module Odoo/devis

---

## 🎯 RÈGLE ABSOLUE À RESPECTER

Quand l'app scanne un cahier des charges (fonction `Import CDC PDF` avec IA) :

> **Chaque élément spécifique mentionné dans le CDC DOIT être capturé dans l'application** — soit par extraction automatique dans les champs dédiés, soit par une remarque/note visible qui rappelle à l'utilisateur que le CDC l'exige.

**Aucune information critique du CDC ne doit disparaître dans le processus de scan.**

---

## 📋 EXEMPLES D'ÉLÉMENTS À CAPTURER OBLIGATOIREMENT

### 🔧 Techniques
- **Type de vitrage** (double, triple, acoustique, feuilleté, sécurit, opale, retardateur d'effraction RC2/RC3…)
- **Coefficient thermique Ug/Uw** (ex: Uw ≤ 1,3 W/m²K)
- **Coefficient acoustique Rw** (ex: Rw ≥ 32 dB)
- **Type de profil** (Schüco AWS 75.SI+, Reynaers CS 77, Kömmerling…)
- **Couleur RAL** (RAL 7016 anthracite, RAL 9016 blanc trafic…)
- **Type de pose** (applique intérieure/extérieure, tunnel, en tableau, en feuillure)
- **Sens d'ouverture** (OB gauche, OB droite, à la française, oscillo-battant, coulissant…)
- **Quincaillerie spécifique** (crémone Roto NT, poignée Secustik, sécurité anti-effraction WK2…)
- **Seuil PMR** / seuil réduit
- **Dimensions exactes** (tableau, baie, hors-tout)

### 📜 Normes & Certifications
- **CE Marking** (obligatoire EN 14351-1)
- **Norme française NF** (ex: NF DTU 36.5)
- **Certification Acotherm** (thermique + acoustique)
- **Label BEE** (Belgique)
- **CEBTP / CSTB** (rapports d'essai)
- **Résistance au vent A/B/C** (classification EN 12210)
- **Étanchéité à l'eau E** (classification EN 12208)
- **Perméabilité à l'air** (classe 4 EN 12207)
- **Résistance effraction RC1/RC2/RC3**

### 📅 Contraintes Contractuelles
- **Délai de livraison** (ex: 6 semaines après validation)
- **Pénalités de retard**
- **Modalités de paiement** (30% acompte, 60% livraison, 10% pose)
- **Garantie** (10 ans décennale, 2 ans quincaillerie, 30 ans vitrage)
- **Assurance chantier**

### 🏗️ Chantier
- **Adresse exacte** avec précision étage/accès
- **Contraintes d'accès** (rue étroite, monte-charge, permis urbain)
- **Horaires de chantier** (autorisation de bruit)
- **Coordination** avec autres corps de métier
- **Nettoyage / évacuation gravats**

### 🎨 Esthétique
- **Finition intérieure/extérieure** (bicolore, plaxé bois…)
- **Vitrage décoratif** (imprimé, dépoli, motif)
- **Petits bois** (structurels, appliqués, intégrés)
- **Store intégré**

---

## 🛠️ IMPLÉMENTATION TECHNIQUE À PRÉVOIR

### Option A — Extraction automatique dans champs dédiés
Pour chaque exigence connue du système, créer un champ dans le modèle `Ouverture` :
```python
class Ouverture(BaseModel):
    # ... champs existants ...
    vitrage_type: Optional[str]           # "double" | "triple" | "acoustique"
    coef_uw: Optional[float]              # 1.3
    coef_rw: Optional[int]                # 32
    profil_marque: Optional[str]          # "Schüco AWS 75.SI+"
    ral_couleur: Optional[str]            # "7016"
    type_pose: Optional[str]              # "applique_int" | "tunnel" | "tableau"
    normes_requises: list[str]            # ["CE", "NF DTU 36.5", "RC2"]
    certifications: list[str]             # ["Acotherm", "BEE"]
    quincaillerie: Optional[str]          # "Roto NT + Secustik"
    seuil_pmr: bool                       # True/False
    delai_semaines: Optional[int]         # 6
    penalites_retard: Optional[str]       # texte libre
    garanties: list[str]                  # ["10 ans décennale", ...]
```

### Option B — Section "Remarques CDC" incontournable
Toute exigence détectée dans le CDC mais qui ne rentre pas dans un champ structuré est ajoutée dans une **section "Remarques du cahier des charges"** de chaque ouverture, avec :
- 📌 Icône visuelle (attention/info)
- ✅ Case à cocher **obligatoire** "J'ai pris en compte cette exigence" avant de pouvoir valider l'ouverture
- 💾 Historique horodaté (quelle exigence, quand elle a été acceptée, par qui)

### Combinaison A + B (RECO)
- Extraction auto pour les champs connus
- Section remarques pour tout le reste
- Yann (IA) alerte si un champ critique manque : "Le CDC exige un Uw ≤ 1,3 mais tu n'as pas rempli ce champ — bloquant ?"

---

## 🚨 IMPACT SUR LE DEVIS AUTO

Chaque exigence non satisfaite doit :
1. **Bloquer la génération du devis** OU
2. **Générer une alerte visible** dans le devis final ("⚠️ Coef Uw non validé — vérifier")
3. **Impacter le prix** automatiquement si un critère demande un composant plus cher (triple vitrage = +50€/m², acoustique = +80€/m², RC2 = +120€/m²)

---

## 📌 PRIORITÉ

**P2 — À implémenter dans la roadmap POST-APPLE** (voir `roadmap_odoo_devis_post_apple.md`)

Sprint dédié : **Sprint 3bis — "Capture exhaustive CDC"**
- Enrichir le prompt IA de l'extraction PDF pour détecter systématiquement tous ces champs
- Créer les champs DB (backend/models.py `Ouverture`)
- Créer les inputs UI (wizard ouverture, écran remarques CDC)
- Créer la fonction de blocage/alerte sur exigence non satisfaite
- Ajouter tests unitaires sur 5 CDC types réels (fournis par utilisateur)

Effort estimé : 4-5 jours de dev.

---

**⏸️ NE PAS COMMENCER TANT QUE APPLE N'A PAS VALIDÉ**

---

## 🔔 ALERTES DATES D'EXÉCUTION — Email + Notifications Push

**Demande utilisateur ajoutée le 04/07/2026** :

Quand le CDC contient des **dates d'exécution** (délai de livraison, date de pose, jalons contractuels…), l'application doit **alerter automatiquement** l'utilisateur pour éviter les oublis et retards.

### 📅 Événements à alerter

| Événement CDC | Alerte prévue |
|---|---|
| **J-30 avant date de pose** | Rappel : "Commander le châssis chez le fournisseur" |
| **J-14 avant date de pose** | Rappel : "Vérifier la disponibilité du poseur + planifier" |
| **J-7 avant date de pose** | Rappel : "Prévenir client + confirmer accès chantier" |
| **J-3 avant date de pose** | Rappel : "Préparer outils + charger véhicule" |
| **Jour J** | Notification : "Chantier à poser aujourd'hui" |
| **J+1 après pose** | Rappel : "Envoyer PV réception + facture" |
| **J+7 après pose** | Rappel : "Appel de courtoisie client" |
| **Date échéance paiement** | Alerte : "Facture N° X impayée depuis Y jours" |
| **Fin garantie décennale J-30** | Rappel : "Renouveler assurance décennale" |

### 🛠️ Canaux d'alerte

**Canal 1 — Emails** (via Resend, déjà en place) :
- Envoi automatique à l'utilisateur assigné (poseur, commercial, admin)
- Sujet clair : "🔔 Chantier Dupont — Pose dans 3 jours"
- Corps : détails chantier + lien direct dans l'app
- Configuration par utilisateur : peut activer/désactiver chaque type d'alerte

**Canal 2 — Notifications Push** :
- Push in-app via **Emergent-managed push notifications**
- Nécessite intégration via `integration_playbook_expert_v2`
- Nécessite un build iOS/Android déployé (ne marche pas sur Expo Go)
- Configuration granulaire par utilisateur (badges, sons, quiet hours)

**Canal 3 — In-app** :
- Badge rouge sur l'icône de menu "Alertes"
- Bandeau en haut du dashboard : "🔔 3 chantiers à préparer cette semaine"
- Section dédiée avec liste chronologique

### 🎯 Personnalisation par rôle

- **Technicien poseur** → alertes J-3, jour J, J+1 (opérationnel)
- **Commercial** → alertes J-14, J+7, échéances paiement (relation client)
- **Admin/Manager** → tout + alertes escalade si J-3 pas confirmé
- **Utilisateur solo** → tout (pas de dispatch équipe)

### 🛠️ Implémentation technique

**Backend** :
- Modèle `Alerte` : `chantier_id`, `type`, `date_prevue`, `sent_email`, `sent_push`, `read_at`
- Job cron (APScheduler ou Celery Beat) exécuté toutes les heures :
  - Query chantiers avec date_pose comprise dans les prochains 30 jours
  - Génère les alertes correspondantes (J-30, J-14, J-7, J-3, J, J+1, J+7)
  - Idempotence stricte (une même alerte ne part qu'une fois)
- Endpoint `GET /api/alerts` : liste des alertes non lues de l'utilisateur
- Endpoint `PATCH /api/alerts/{id}/read` : marquer comme lu

**Frontend** :
- Section "Alertes" dans le menu principal
- Badge notification sur icône (React Native badge)
- Bandeau dashboard "Alertes actives (N)"
- Écran détails alerte → deep-link vers chantier concerné
- Écran Paramètres → toggles par type d'alerte + canaux (email/push/in-app)

### 📌 Priorité

**P2 — Post-Apple validation**

**Sprint dédié : Sprint 4bis — "Alertes intelligentes"**
- 2j : Backend (modèle Alerte, cron scheduler, endpoints)
- 1j : Frontend (écran alertes, badges, deep-links)
- 1j : Emails auto (templates Resend par type d'alerte)
- 1j : Push notifications (via integration_playbook_expert_v2 Emergent-managed)
- 1j : Paramètres user (activer/désactiver, quiet hours)
- 1j : Tests + refinement

**Total** : 7 jours de dev.

### 🔑 Points d'attention

- **Nécessite un build natif iOS + Android** (Emergent Publish) pour tester les push — ne fonctionnera pas en Expo Go
- **Google Play Console** : demander `google-services.json` à l'utilisateur si Firebase requis
- **Timezone** : respecter timezone de l'utilisateur (Europe/Paris, Europe/Brussels)
- **Quiet hours** : ne pas envoyer de push entre 20h et 8h
- **Anti-spam** : max 3 alertes par jour par utilisateur (agrégation intelligente)
- **RGPD** : consentement explicite à la première ouverture (opt-in)

---

**⏸️ NE PAS COMMENCER TANT QUE APPLE N'A PAS VALIDÉ**
