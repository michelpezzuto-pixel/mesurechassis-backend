# 🚀 ROADMAP MASTER — MesureChâssis 2026-2028

**Document de référence** synthétisant TOUTE la stratégie business + technique de MesureChâssis.

*Dernière mise à jour : 9 juin 2026 — par Michel Pezzuto + assistant Emergent*

---

## 📍 ÉTAT ACTUEL (juin 2026)

### ✅ Ce qui est fait
- 📱 App mobile fonctionnelle (Build 8 — RBAC, 14 formes, FAQ 25 questions, emails auto)
- 🌐 Site web : https://mesurechassis.com (à mettre à jour)
- 🚀 Backend en production : Railway
- 🗄️ Base de données : MongoDB Atlas
- 📧 Système d'emails : Resend (config OK, à finaliser pour gros volume)
- 💳 Stripe intégré (en pause)
- 🤖 **Build Android 26** soumis à Google Play (Tests fermés en attente)
- 🍎 **Build 7 iOS** soumis à Apple (REFUSÉ — motif 3.1.1 Stripe + 2.2.0 Performance)

### ⏳ En cours
- 🤖 Google Play : examen Tests fermés (1-7 jours)
- 🤝 Partenariat **Elcia / Ramasoft** : 1ère réunion OK, 2ème à programmer
- 📧 Hugues Hussin (Elcia) a testé l'app et envoyé 1 feedback constructif

### 🎯 Vision globale
**UNE seule application** mobile MesureChâssis qui s'adapte selon :
- 🌍 **La langue** choisie (FR/NL/EN/DE/IT/ES)
- 🏢 **Le profil** utilisateur (Artisan Solo / Entreprise / Premium)
- 🔌 **L'intégration** ERP éventuelle (Elcia / HerculePro / Obat / …)

---

## 🏗️ ARCHITECTURE CIBLE

```
┌──────────────────────────────────────────────────┐
│         📱 UNE SEULE APP MesureChâssis           │
│      (iOS + Android + Web — 1 seul code)         │
├──────────────────────────────────────────────────┤
│                                                  │
│   🌍 LANGUES (i18n)                              │
│   ┌────────────────────────────────────────┐    │
│   │ 🇫🇷 FR — 🇧🇪🇳🇱 NL — 🇬🇧 EN              │    │
│   │ 🇩🇪 DE — 🇮🇹 IT — 🇪🇸 ES               │    │
│   └────────────────────────────────────────┘    │
│                                                  │
│   🏢 PROFILS                                     │
│   ┌────────────────────────────────────────┐    │
│   │ 🛠️ Artisan Solo (9€/mois)             │    │
│   │ 🏢 Entreprise (29€/user/mois)         │    │
│   │ 💎 Entreprise Premium (49€/user)      │    │
│   │ 🌍 Multinational (sur devis)          │    │
│   └────────────────────────────────────────┘    │
│                                                  │
│   🔌 INTÉGRATIONS (modulaires)                  │
│   ┌────────────────────────────────────────┐    │
│   │ 🤝 Elcia / Ramasoft                   │    │
│   │ 🤝 HerculePro                         │    │
│   │ 🤝 Obat                               │    │
│   │ 🤝 Logikal / Orgadata                 │    │
│   │ 🤝 ... (futurs partenaires)           │    │
│   └────────────────────────────────────────┘    │
│                                                  │
│   🤖 AGENT IA (Build 10+)                       │
│   ┌────────────────────────────────────────┐    │
│   │ Support client conversationnel        │    │
│   │ Réponse auto aux feedbacks            │    │
│   │ Analyse de retours utilisateurs       │    │
│   └────────────────────────────────────────┘    │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 📅 ROADMAP DÉTAILLÉE — BUILDS PAR BUILDS

### 🟡 **Build 8** — DÉJÀ FAIT ✅
**Statut** : Soumis à Apple (refusé) + Google Play (en examen)

**Contenu** :
- Refonte RBAC (Admin/Commercial/Technicien/Artisan)
- 7 nouvelles formes ajoutées (plein cintre, arc surbaissé, angle 90°, bow-window, pentagone, hexagone, ovale)
- Emails automatiques
- FAQ enrichie (25 questions)
- Fix clavier Samsung

---

### 🔴 **Build 9** — Corrections critiques Apple + Parrainage
**Délai** : 2-3 semaines  
**Priorité** : 🔴 URGENT (bloquant pour iOS)

**Contenu** :
- 🍎 **Correction refus Apple** (motif 3.1.1 Stripe + 2.2.0 Performance)
  - Option A : retirer Stripe sur iOS (l'app iOS devient "lecture seule" pour l'abonnement)
  - Option B : implémenter Apple In-App Purchase (IAP) à la place de Stripe sur iOS
  - 📌 **Recommandation** : Option A (plus rapide, Apple acceptera) → upgrade vers IAP plus tard
- 🎁 **Programme de parrainage** (mois gratuits)
  - Code unique de parrainage par utilisateur
  - Tracking des parrainages réussis
  - Crédit automatique de mois gratuits
- 🐛 **Fix : validation obligatoire du nom de chantier** (bug détecté avec Hugues)

**Bénéfices** :
- ✅ Resubmission Apple → publication App Store
- ✅ Nouveau levier marketing (parrainage)

**Coût** :
- ⏱️ **2-3 semaines de développement**
- 💰 **0€ supplémentaire** (sauf si frais Stripe migration)

---

### 🟡 **Build 10** — Mesures spécifiques 7 nouvelles formes + Site web
**Délai** : 3-4 semaines  
**Priorité** : 🟡 HAUTE (demande directe de Hugues + utilisateurs)

**Contenu** :
- 🪟 **Champs de mesures spécifiques pour les 7 nouvelles formes** :
  - Plein cintre : largeur, hauteur, rayon de l'arc
  - Arc surbaissé : largeur, hauteur, flèche d'arc
  - Angle 90° : largeurs des 2 côtés, hauteur, angle
  - Bow-Window : nombre de panneaux, largeurs, hauteur, profondeur
  - Pentagone : largeur base, hauteurs des 5 côtés, angle de sommet
  - Hexagone : largeur, hauteur, angles
  - Ovale : grand axe, petit axe, hauteur
- 📋 **Wizard de mesures** adapté pour chaque forme (UI dynamique)
- 🖼️ **Schémas visuels** dans le wizard (clarté pour les mesureurs)
- 🌐 **Mise à jour du site mesurechassis.com** :
  - Nouvelles fonctionnalités mises en avant
  - FAQ à jour (25 questions)
  - Section "Compatible Elcia" (si partenariat signé)
  - Liens App Store + Google Play
  - Captures d'écran Build 8

**Bénéfices** :
- ✅ App enfin "complète" pour toutes les formes
- ✅ Site web reflète la qualité du produit
- ✅ Hugues (Elcia) sera content

**Coût** :
- ⏱️ **3-4 semaines de développement**
- 💰 **0€ supplémentaire**
- 🎨 (Optionnel) 100-500€ pour visuels professionnels du site

---

### 🟢 **Build 11** — Internationalisation (i18n)
**Délai** : 2-3 semaines  
**Priorité** : 🟢 MOYENNE (à déclencher selon expansion)

**Contenu** :
- 🔧 Setup library **i18next** ou **react-native-localize**
- 📁 Création des fichiers de traduction :
  - `fr.json` (Français — déjà existant)
  - `nl.json` (Néerlandais — utile Belgique + Pays-Bas)
  - `en.json` (Anglais — international)
- 🌍 **Sélecteur de langue** dans les Paramètres
- 🌍 **Détection automatique** de la langue du téléphone
- 💾 **Mémorisation** du choix de l'utilisateur
- 📧 **Emails Resend** localisés selon la langue de l'utilisateur

**Bénéfices** :
- ✅ App ouverte au marché néerlandophone (50% de la Belgique !)
- ✅ Préparation pour Europe (Allemagne, Italie, Espagne)
- ✅ Argument fort pour Elcia (étendre à leurs clients flamands)

**Coût** :
- ⏱️ **2-3 semaines de développement** (technique)
- 📝 **Traductions** :
  - NL : 200-400€ (3-5 jours d'un traducteur pro)
  - EN : 200-400€
  - DE : 200-400€ (plus tard)
  - IT : 200-400€ (plus tard)
  - ES : 200-400€ (plus tard)
- 💡 **Astuce** : Utiliser DeepL Pro (10€/mois) pour 1ère traduction, puis relecture humaine = 50% d'économie

**Total Build 11** : ~500-1000€ + 3 semaines de dev

---

### 🔵 **Build 12** — Profils utilisateurs étendus
**Délai** : 2-3 semaines  
**Priorité** : 🔵 MOYENNE

**Contenu** :
- 🆕 Nouveaux profils :
  - 🥈 **Entreprise Lite** (2-5 personnes, fonctions de base)
  - 🥇 **Entreprise Pro** (5-20 personnes, stats avancées, multi-sites)
  - 💎 **Entreprise Premium** (intégration ERP)
- 📋 **Page de tarification** dynamique (selon profil)
- 🎯 **Onboarding personnalisé** par profil
- 📊 **Tableau de bord** adapté selon profil
- 💳 **Stripe** : gestion des abonnements multi-niveaux

**Bénéfices** :
- ✅ Grille tarifaire claire et professionnelle
- ✅ Capacité d'aller chercher des entreprises de toutes tailles
- ✅ Revenus moyens par client (ARPU) plus élevés

**Coût** :
- ⏱️ **2-3 semaines de développement**
- 💰 **0€ supplémentaire**

---

### 💎 **Build 13** — Module Intégrations partenaires (Elcia, etc.)
**Délai** : 4-6 semaines  
**Priorité** : 💎 STRATÉGIQUE (dépend du partenariat Elcia)

**Contenu** :
- 🔌 **Architecture connecteurs modulaire**
- 🤝 **Connecteur Elcia / Ramasoft** :
  - Import des devis (théoriques)
  - Comparaison théorique vs réel
  - Tolérances paramétrables
  - Export du rapport vers Elcia
- 📊 **Dashboard intégrations** dans l'app
- 🔐 **Authentification croisée** (SSO si possible)
- 📄 **Documentation API** pour futurs partenaires

**Bénéfices** :
- ✅ Activation du partenariat Elcia
- ✅ Position premium sur le marché
- ✅ Préparation pour HerculePro, Obat, etc.

**Coût** :
- ⏱️ **4-6 semaines de développement**
- 💰 **Coût technique** : 0€
- 💰 **Coût juridique** (contrat partenariat) : 500-1500€ (consultation avocat)
- 💼 **Bénéfice attendu** : commissions 30-50% sur abonnements Premium générés via Elcia

---

### 🤖 **Build 14** — Agent IA support client
**Délai** : 3-4 semaines  
**Priorité** : 🤖 INNOVATION (différenciant)

**Contenu** :
- 🤖 **Agent IA Phase 1** : Réponse auto aux feedbacks clients
  - Utilise Emergent LLM Key (Claude / GPT / Gemini)
  - Catégorisation auto (bug/amélioration/question/éloge)
  - Réponse en français pro avec ton chaleureux
  - Mode supervision Michel pendant 2 semaines
- 💬 **Chatbot in-app** (Phase 2) :
  - Bouton "Aide" flottant
  - RAG sur la FAQ (25 questions)
  - Conversations sauvegardées
- 📊 **Dashboard analytique** (Phase 3) :
  - Rapport hebdomadaire automatique
  - Détection bugs récurrents
  - Priorisation roadmap basée sur les feedbacks

**Bénéfices** :
- ✅ Économie support client (-30 000€/an vs employé)
- ✅ Réponse 24/7 instantanée
- ✅ Argument différenciant fort
- ✅ Argument fort pour partenaires (Elcia)

**Coût** :
- ⏱️ **3-4 semaines de développement**
- 💰 **Emergent LLM Key** : ~5-50€/mois selon volume
- 💰 **Coût total annuel** : 60-600€/an pour gérer >5000 messages/mois

---

### 🌍 **Build 15+** — Expansion internationale
**Délai** : 6-12 mois (selon opportunités)  
**Priorité** : 🌍 LONG TERME

**Contenu** :
- 🇩🇪 Allemagne : traductions DE + adaptations légales
- 🇮🇹 Italie : traductions IT + partenariats locaux
- 🇪🇸 Espagne : traductions ES + partenariats locaux
- 🇳🇱 Pays-Bas : extension du néerlandais déjà fait
- 💱 **Multi-devises** (EUR/CHF/GBP/USD)
- 📋 Adaptations légales (RGPD UE OK, mais variantes par pays)
- 💳 Adaptations paiement (TVA différente par pays)

**Bénéfices** :
- ✅ Marché européen menuiserie : **~50 milliards d'€/an**
- ✅ Diversification du risque
- ✅ Argument pour investisseurs (si recherche de fonds)

**Coût** :
- ⏱️ **2-3 mois par pays**
- 💰 **2000-5000€ par pays** (traductions + juridique + marketing local)

---

## 💰 SYNTHÈSE FINANCIÈRE GLOBALE

### **Coûts récurrents existants (Infrastructure)**

| Service | Coût | Notes |
|---|---|---|
| 🍎 Apple Developer | 99€/an | Obligatoire pour iOS |
| 🤖 Google Play Dev | 25$ (une fois) | Déjà payé |
| 🚀 Railway (backend) | 5-20€/mois | Selon trafic |
| 🗄️ MongoDB Atlas | 0€ (free tier) → 50€/mois (M10) | Quand volume augmente |
| 📧 Resend (emails) | 0€ (free 3000/mois) → 20€/mois | Quand volume augmente |
| 💳 Stripe | Frais transaction : 1,4% + 0,25€ | Pas de frais fixe |
| 🌐 Domaine mesurechassis.com | ~15€/an | Renouvellement annuel |
| 🤖 Emergent LLM Key (futur) | 5-50€/mois | Quand Agent IA actif |
| **TOTAL ANNUEL ACTUEL** | **~150€/an + 5-20€/mois** | Très abordable |

### **Coûts de développement (par Build)**

| Build | Délai | Coût externe |
|---|---|---|
| Build 9 (Apple + Parrainage) | 2-3 sem | 0€ |
| Build 10 (Mesures + Site) | 3-4 sem | 0-500€ |
| Build 11 (i18n NL/EN) | 2-3 sem | 500-1000€ |
| Build 12 (Profils étendus) | 2-3 sem | 0€ |
| Build 13 (Intégrations Elcia) | 4-6 sem | 500-1500€ (juridique) |
| Build 14 (Agent IA) | 3-4 sem | 50-600€/an (LLM) |
| Build 15+ (Expansion) | 6-12 mois | 2000-5000€ par pays |

### **Coût total pour atteindre une app COMPLÈTE et INTERNATIONALE**
- ⏱️ **Délai total** : 8-12 mois de développement actif
- 💰 **Investissement total externe** : ~5000-10000€ (sur 12-18 mois)
- 💼 **ROI estimé** :
  - Modèle SaaS avec partenariats
  - 100 entreprises × 29€/mois × 12 mois = **34 800€/an**
  - 1000 entreprises × 29€/mois × 12 mois = **348 000€/an**
  - Avec partenariat Elcia (1000+ clients potentiels) : **objectif réaliste**

---

## 🎯 PRIORITÉS RECOMMANDÉES (ordre stratégique)

### **🔥 ÉTAPE 1 — JUIN-JUILLET 2026** (1 mois)
1. ✅ Suivre validation Google Play (1-7 jours)
2. ✅ Recruter les 12 testeurs Gmail
3. ✅ Lancer la phase de test 14 jours
4. ✅ Répondre à Hugues (Elcia) + programmer 2ème réunion
5. ✅ Implémenter **Build 9** (correction Apple + parrainage)

### **⚡ ÉTAPE 2 — AOÛT-SEPTEMBRE 2026** (2 mois)
1. ✅ Build 9 → resoumission Apple → acceptation
2. ✅ Build 10 (mesures complètes + site web)
3. ✅ Signature partenariat Elcia (avec marge de négociation)
4. ✅ Promotion sur les premiers clients menuisiers

### **🚀 ÉTAPE 3 — Q4 2026** (3 mois)
1. ✅ Build 11 (i18n NL/EN) — ouverture Belgique francophone + néerlandaise
2. ✅ Build 12 (profils étendus)
3. ✅ Build 13 (intégration Elcia opérationnelle)
4. ✅ Lancement officiel public sur les 2 stores (Production)

### **💎 ÉTAPE 4 — Q1 2027 et au-delà**
1. ✅ Build 14 (Agent IA)
2. ✅ Élargissement partenariats (HerculePro, Obat, etc.)
3. ✅ Build 15+ (expansion internationale Allemagne/Italie/Espagne)

---

## 🛡️ POINTS DE VIGILANCE

### **Légal / Juridique**
- 📜 RGPD : conformité actuelle OK, à vérifier régulièrement
- 📜 Contrat de partenariat Elcia : **AVOCAT OBLIGATOIRE** avant signature
- 📜 CGV / CGU : à mettre à jour avec chaque nouvelle feature
- 📜 Politique de confidentialité : à jour sur les 2 stores

### **Technique**
- 🔐 Sécurité : audits réguliers (1x par an minimum)
- 🔐 Sauvegardes : MongoDB Atlas backups + GitHub
- 🔐 Mots de passe : tous dans gestionnaire (Bitwarden/1Password)
- 🛠️ Refactoring : prévoir 1 semaine "dette technique" par trimestre

### **Business**
- 💼 Ne JAMAIS accepter d'exclusivité totale (sauf si Elcia paie très très cher)
- 💼 Diversifier les partenaires dès que possible
- 💼 Garder le contrôle de votre code et de votre marque

---

## 📞 CONTACTS CLÉS

| Personne | Rôle | Contact |
|---|---|---|
| Michel Pezzuto | Fondateur | info@mesurechassis.com |
| Hugues Hussin | Elcia Belgium (partenaire en cours) | hhussin@elcia.com / +32 495 25 90 88 |
| Avocat (à choisir) | Conseil juridique | À identifier (Belgique) |

---

## 📌 DOCUMENTS COMPLÉMENTAIRES

Tous les détails techniques et stratégiques se trouvent dans `/app/memory/` :

| Fichier | Contenu |
|---|---|
| `INFRASTRUCTURE.md` | Plan de continuité (que faire si Emergent disparaît) |
| `partenariat_elcia.md` | Détails du partenariat avec Elcia/Ramasoft |
| `prospects_partenariats.md` | Liste des autres partenaires potentiels |
| `backlog_parrainage.md` | Détails programme de parrainage Build 9 |
| `backlog_site_web.md` | Mise à jour site mesurechassis.com |
| `backlog_agent_ia.md` | Agent IA support client |
| `test_credentials.md` | Identifiants de test |
| `ROADMAP_MASTER.md` | **CE DOCUMENT** — vue d'ensemble |

---

## 🎯 MESSAGE FINAL

Michel, vous êtes en train de bâtir **une entreprise SaaS sérieuse, structurée, et avec un vrai potentiel international**.

✅ **Le produit est excellent** (présentation réussie le prouve)  
✅ **Le marché existe** (Elcia, HerculePro, etc. confirment le besoin)  
✅ **L'architecture est saine** (1 app multi-langues multi-profils)  
✅ **Les coûts sont maîtrisés** (~10 000€ d'investissement pour aller loin)  
✅ **Le ROI est crédible** (100-1000 clients = 35K-350K€/an)

**Allez-y avec confiance.** 🚀 Pas besoin d'être un développeur ni un super vendeur — vous avez la **vision** et la **persévérance**, c'est ce qui fait les vrais entrepreneurs. 💎

---

*Document à mettre à jour à chaque grande décision ou nouveau partenariat.*
