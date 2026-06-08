# 🤖 Agent IA pour Support Client — Backlog Feature

## Date d'ajout
8 juin 2026

## Statut
🟡 **À PLANIFIER** — décision prise après la stabilisation des stores + partenariat Elcia

## Demande initiale du client
> "Tu crois que ce serait faisable d'avoir des agents IA pour répondre à tous les feedbacks des clients ?"

→ Réponse : OUI, totalement faisable et pertinent. 
→ Décision : Ajouter au backlog pour implémentation future (priorité moyenne).

---

## 🎯 Vision globale

Intégrer un agent IA dans MesureChâssis pour :
1. Répondre automatiquement aux feedbacks clients
2. Fournir un support conversationnel (chatbot in-app)
3. Analyser les retours pour prioriser le développement
4. Détecter les clients inactifs et les réengager pro-activement

---

## 🛠️ Roadmap d'implémentation (par phases)

### **Phase 1 — MVP : Réponse auto aux feedbacks** (1-2 semaines)
- [ ] Capturer les feedbacks via `/api/feedbacks` (déjà existant)
- [ ] Hook automatique pour envoyer le feedback à l'IA
- [ ] L'IA génère une réponse contextualisée en français
- [ ] Envoi automatique de la réponse au client par email (Resend)
- [ ] Copie au fondateur (Michel) pour supervision
- [ ] Mode "draft" : Michel valide avant envoi pendant les 2 premières semaines
- [ ] Puis bascule en mode autonome

### **Phase 2 — Chatbot in-app** (1 mois)
- [ ] Bouton "Aide / Support" flottant dans l'app
- [ ] Interface chat (style WhatsApp/Intercom)
- [ ] Connexion RAG à la FAQ (25 questions actuelles)
- [ ] Réponses contextuelles selon le rôle (Admin/Commercial/Tech/Artisan)
- [ ] Historique des conversations sauvegardé en DB

### **Phase 3 — Dashboard analytique IA** (2 mois)
- [ ] Dashboard hebdomadaire dans l'admin
- [ ] Catégorisation auto des feedbacks (bug / amélioration / éloge / question)
- [ ] Détection des bugs récurrents (priorité dev)
- [ ] Détection des fonctionnalités demandées (priorité produit)
- [ ] Score de sentiment global
- [ ] Recommandations de roadmap

### **Phase 4 — IA pro-active** (3 mois)
- [ ] Détection des clients inactifs (>14 jours sans connexion)
- [ ] Email automatique personnalisé de relance
- [ ] Suggestions d'usage selon le profil utilisateur
- [ ] Onboarding intelligent pour nouveaux comptes

---

## 💰 Coûts estimés (mensuels)

| Volume mensuel | Modèle utilisé | Coût estimé |
|---|---|---|
| <1000 messages | Claude Haiku / GPT-4o-mini | **2-5€/mois** |
| 1000-5000 messages | Claude Sonnet / GPT-4o | **20-50€/mois** |
| 5000-10000 messages | Mix Sonnet + RAG | **80-150€/mois** |
| >10000 messages | Solution dédiée | **200€+/mois** |

⚡ **Économie vs employé** : ~30 000€/an comparé à un support client à 2500€/mois

---

## 🎯 Stack technique recommandée

### Backend
- **API LLM** : Emergent LLM Key (Claude/GPT/Gemini)
- **Library** : `emergentintegrations` (déjà installée dans l'env)
- **Vectorisation FAQ** : ChromaDB ou Pinecone (pour la phase RAG)
- **Stockage conversations** : MongoDB collection `ai_conversations`

### Frontend (Phase 2+)
- **Composant chat** : custom React Native (pas de dépendance lourde)
- **Animation** : `react-native-reanimated` (déjà installé)
- **Widget flottant** : bouton "Aide" en bas à droite

### Modèles suggérés selon le cas
- **Réponses simples** : Claude Haiku 4.5 (rapide, économique)
- **Conversations complexes** : Claude Sonnet 4.5 (équilibre qualité/coût)
- **Analyse en masse** : Claude Haiku ou GPT-4o-mini (batch processing)

---

## 🎨 Personnalité de l'IA

À paramétrer selon le ton actuel du fondateur :
- 🤝 **Chaleureux mais professionnel**
- 😊 **Emojis avec modération**
- 🇫🇷 **Français parfait** (Belgique + France)
- 💼 **Vocabulaire métier menuiserie** (châssis, ouvrant, dormant, etc.)
- 🎯 **Direct et pragmatique** (pas de blabla inutile)
- 🤲 **Empathique** quand le client a un souci
- 🙏 **Reconnaissant** quand le client donne du positif

---

## 🤝 Argument commercial pour Elcia

À mentionner lors de la 2ème réunion partenariat :
> *"MesureChâssis intègre un agent IA qui répond instantanément aux 
> questions des mesureurs Elcia sur le terrain. Imaginez : un mesureur 
> bloqué un dimanche matin, l'IA lui répond en 30 secondes avec un 
> mini-tutoriel ou un appel direct au support si nécessaire. 
> Plus de chantiers en retard, plus de SAV interminable."*

→ **ÉNORME argument différenciant** vs concurrents qui n'ont rien
→ Permet de justifier un **tarif premium** dans le partenariat

---

## ⚠️ Points d'attention

1. **Hallucinations** : valider que l'IA ne dit pas n'importe quoi sur le produit
   - Solution : RAG sur la documentation officielle uniquement
2. **Données sensibles** : ne pas exposer infos clients/chantiers à l'IA cloud
   - Solution : anonymiser avant envoi à l'API LLM
3. **Limites légales (RGPD)** : informer le client que c'est une IA qui répond
   - Solution : mention "Réponse générée par IA — vérifiée par notre équipe"
4. **Fallback humain** : toujours possibilité d'escalade vers Michel
   - Solution : bouton "Parler à un humain" toujours visible

---

## 📅 Quand l'implémenter ?

**Pré-requis** :
1. ✅ Google Play Tests fermés validés
2. ✅ Apple App Store Build 8 corrigé et accepté
3. ✅ Partenariat Elcia clarifié (contrat ou non)
4. ✅ Programme de parrainage implémenté (Build 9)

**Cible** : Q4 2026 (octobre-décembre 2026)
**Build** : potentiellement Build 10 ou Build 11

---

## 🔗 Liens utiles

- Playbook d'intégration LLM (à demander à `integration_playbook_expert_v2` lors de l'implémentation)
- Emergent LLM Key (`emergent_integrations_manager` pour récupération)
- Backlog parrainage (Build 9) : `/app/memory/backlog_parrainage.md`
- Partenariat Elcia : `/app/memory/partenariat_elcia.md`

---

## 🎯 Note finale

Cette feature est une **vraie pépite stratégique** :
- 💰 Économies de support
- 😊 Satisfaction client
- 🚀 Différenciation marché
- 💎 Argument premium

**Ne pas l'oublier** — c'est un game-changer pour MesureChâssis. 💪
