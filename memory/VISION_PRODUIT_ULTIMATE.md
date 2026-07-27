# 🎯 Vision produit ULTIMATE — MesureChâssis

**Source** : Message vocal de Michel Pezzuto — 27 juillet 2026 (en route pour un RDV menuisier)
**Statut** : Vision cible confirmée par le fondateur

---

## 🧩 La vision en 3 briques chaînées

```
┌─────────────────────────────────────────────────────────────┐
│  BRIQUE 1 — DEVIS AUTOMATIQUE                               │
│                                                              │
│  Inputs :                                                    │
│    • CDC (Cahier des charges) — PDF scanné/uploadé          │
│    • Bordereau fabricant — PDF prix / catalogue tarifaire   │
│    • Config client — marges, coefs, options (page dédiée)   │
│                                                              │
│  Traitement IA :                                             │
│    • Extraction dimensions, formes, quantités (déjà existant)│
│    • Extraction prix par référence, ml, accessoires (NEW)   │
│    • Croisement CDC × Bordereau × Marges client              │
│                                                              │
│  Output :                                                    │
│    • Devis PDF pro, brandé (logo client)                    │
│    • Prêt à envoyer au client final                         │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  BRIQUE 2 — INTÉGRATION COMPTABLE                           │
│                                                              │
│  Cibles :                                                    │
│    • Odoo (priorité #1)                                      │
│    • Sage, WinBooks, EBP, Ciel (à confirmer marché belge)   │
│                                                              │
│  Modes :                                                     │
│    • API push (Odoo natif)                                   │
│    • Export JSON / XML / CSV standardisé (fallback)         │
│                                                              │
│  Résultat :                                                  │
│    • Devis directement dans le CRM/facturation du client    │
│    • Suivi commande, facturation, paiement                  │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  BRIQUE 3 — BOUCLE QUALITÉ CHANTIER                         │
│                                                              │
│  Déclenchement : commande signée par client final           │
│                                                              │
│  Workflow :                                                  │
│    1. Menuisier reçoit "chantier à vérifier" dans l'app     │
│    2. App affiche mesures théoriques (extraites du CDC)     │
│    3. Menuisier saisit mesures réelles sur chantier          │
│    4. App compare théorique vs réel                          │
│    5. Alerte les écarts significatifs (> seuil configurable)│
│    6. Valide au bureau (RBAC Admin/Commercial)              │
│    7. Envoie ordre de fabrication SÉCURISÉ en atelier       │
│                                                              │
│  Objectif : zéro erreur en fabrication (anti-litige)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 État de l'existant (juillet 2026)

| Composant | Existe ? | Notes |
|-----------|:--------:|-------|
| Import IA CDC (OpenAI Vision) | ✅ | Fonctionnel |
| Mesures chantier 14 formes | ✅ | App mobile publiée |
| Exports PDF branded | ✅ | Basique — à améliorer pour devis |
| RBAC (Admin/Commercial/Tech) | ✅ | Fonctionnel |
| Yann IA (assistant) | ✅ | Fonctionnel |
| **Import IA bordereau fabricant** | ❌ | À construire |
| **Générateur devis PDF automatique** | ❌ | À construire (Entreprise MAX) |
| **Config prix / marges client (page dédiée)** | ❌ | À construire |
| **Connecteur Odoo** | ❌ | À construire |
| **Mode vérification chantier (compare CDC vs réel)** | ⚠️ | Partiel, à renforcer |

---

## ⏱️ Estimation dev (à partir du feu vert post-faillite)

| Brique | Effort estimé | Priorité |
|--------|:-------------:|:--------:|
| Import IA bordereau | 3-4 semaines | 🔴 P1 |
| Générateur devis PDF | 4-6 semaines | 🔴 P1 |
| Page config prix/marges client | 2-3 semaines | 🟠 P2 |
| Connecteur Odoo (API) | 1-2 semaines | 🟠 P2 |
| Renforcement mode vérif chantier | 2 semaines | 🟢 P3 |
| **TOTAL** | **~3-4 mois** | — |

---

## 💰 Alignement business

### Plan Entreprise MAX (299 €/mois) — vendu comme "bientôt disponible"
Cette vision est **exactement le contenu promis** du plan Entreprise MAX sur la landing :
- "Générateur de devis PDF instantanés générés à partir des mesures"
- "Automatisation totale"
- "Analyse IA avancée des 14 formes par photo"
- "Utilisateurs illimités"
- "Gestion anti-litige avec archivage photo systématique"

### Pricing potentiel
- Fabricants belges de menuiseries : ~50-100 sociétés cibles
- 50 fabricants × 299 €/mois = **~15 000 €/mois de MRR** juste sur ce segment
- Effet levier : si Elcia intègre → accès à **~1 000 fabricants francophones**

---

## 🤝 Argument-clé pour la négociation Elcia

**"Nous vous vendons le module métier terrain qui manque à votre suite ERP."**

Elcia a la partie chiffrage/gestion, MesureChâssis a la partie IA + mesures + devis + vérif chantier. Complémentarité parfaite. Zéro overlap concurrentiel.

---

## ⚠️ Pré-requis avant de construire

1. Faillite Garde-corps en kit CLÔTURÉE
2. Effacement dettes obtenu
3. Autorisation article 100 §2 (mutuelle MC)
4. Inscription indépendant Primostarter + BCE
5. Startup Boost 100k€ obtenu (pour financer 3-4 mois de dev intensif)

**Timeline globale** : Ces prérequis (2-3 mois) + dev (3-4 mois) = **v1.0 vision ULTIMATE prête pour Q1 2027**.

---

## 📌 À vérifier / valider au prochain RDV avec Michel

1. Le RDV menuisier du 27/07 valide-t-il la vision ? (feedback terrain)
2. Michel a-t-il déjà un bordereau fabricant type qu'on peut utiliser en test ?
3. Quel(s) CRM/facturation ses futurs clients utilisent-ils VRAIMENT ? (Odoo confirmé ou hypothèse ?)
4. La brique "vérification chantier" doit-elle bloquer la fabrication si écart > X% ?
5. Prix Entreprise MAX 299 €/mois : à confirmer une fois la vision livrée
