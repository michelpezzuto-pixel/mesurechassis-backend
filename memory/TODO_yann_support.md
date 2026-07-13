# 🤖 TODO — Yann Support (FAQ + fallback mail + apprentissage)

**Status** : En attente · **Décidé le** 12 juillet 2026 · **À déclencher** : sur demande explicite Michel (idéalement après le 12 août)
**Priorité** : P1 (améliore l'UX support et réduit les emails à Michel)
**Estimation** : ~4h dev + 1h tests

---

## 🎯 Objectif

Remplacer le bouton actuel « **POSER UNE QUESTION** » du centre d'aide (qui ouvre un simple `mailto:info@mesurechassis.com`) par un **chat plein écran avec Yann** — l'agent IA déjà utilisé pour les questions métier (DTU, EN 14351).

**Comportement demandé par Michel** :
1. L'utilisateur pose sa question → Yann répond avec le contexte "assistant support MesureChâssis"
2. Si Yann ne connaît pas la réponse, il **envoie automatiquement la question à Michel par mail**
3. Michel répond au mail
4. **Yann APPREND** cette réponse et la resservira automatiquement à la prochaine question similaire

---

## 🏗️ Architecture

### Backend (2 nouveaux endpoints + 2 collections)

#### Endpoints
1. `POST /api/help/ask` — Chat avec Yann Support
   ```json
   {
     "question": "Comment supprimer un chantier ?",
     "context": { "screen": "chantiers", "role": "admin", "account_type": "artisan" }
   }
   ```
   → Retourne `{ answer, escalated: bool, ticket_id?: str }`
   - Cherche d'abord dans `help_knowledge_base` (RAG basique par cosine similarity)
   - Si hit avec score > 0.85 → renvoie la réponse mémorisée
   - Sinon → génère une réponse via Emergent LLM key (Claude Sonnet 4.5)
   - Si Yann ne peut pas répondre → escalade auto + crée un `help_ticket` + envoie mail à Michel via Resend

2. `POST /api/help/tickets/{ticket_id}/answer` — Michel répond à un ticket
   ```json
   {"answer": "Pour supprimer un chantier, va sur..."}
   ```
   → Ajoute la Q/A dans `help_knowledge_base` (avec embedding vectoriel)
   → Envoie l'email de réponse à l'utilisateur qui avait posé la question
   → Marque le ticket comme `resolved`

#### Collections MongoDB nouvelles
- `help_knowledge_base` : `{id, question, answer, embedding, hits, created_at, updated_at}`
- `help_tickets` : `{id, user_id, user_email, question, ai_attempted_answer, status: "pending|resolved", michel_answer?, created_at, resolved_at?}`

### Frontend
- Nouvel écran `/app/frontend/app/help/chat.tsx` (~350 lignes)
  - Chat UI FlatList inversée
  - Input bas avec bouton envoi + indicateur "Yann écrit…"
  - Chaque message a un tag : `[Réponse instantanée]`, `[Escaladé au support]`, `[Réponse de Michel]`
  - Historique par utilisateur (dernières 20 messages) stocké local via AsyncStorage
- Nouvel écran admin `/app/frontend/app/admin/help-tickets.tsx` (~200 lignes)
  - Michel voit les tickets `pending`
  - Formulaire "Répondre" → POST /api/help/tickets/{id}/answer
- Modifs :
  - `/app/frontend/src/components/ChatHelp.tsx` : bouton "POSER UNE QUESTION" → navigate `/help/chat` au lieu de mailto
  - Dashboard : ajouter bouton "🎫 Tickets support" pour Michel (badge count des pending)

### Emergent LLM
- Utiliser Claude Sonnet 4.5 via Emergent LLM Key (déjà en place dans le projet)
- Prompt système :
  ```
  Tu es Yann, l'assistant support de MesureChâssis (app iOS/Android pour menuisiers).
  Voici les FAQ et fonctionnalités que tu connais : [inject knowledge_base slice]
  Réponds UNIQUEMENT sur des sujets liés à l'app. Si tu ne sais pas, réponds
  exactement : "ESCALADE_SUPPORT_REQUIRED" — un humain va prendre le relais.
  ```

---

## 📁 Fichiers à créer / modifier

| Fichier | Nature | Estim. LOC |
|---|---|---|
| `/app/backend/routes/help.py` | NEW — endpoints ask + tickets | ~250 |
| `/app/backend/services/help_kb.py` | NEW — recherche + embeddings | ~180 |
| `/app/backend/email_service.py` | ADD templates ticket escalade + réponse | ~40 |
| `/app/backend/server.py` | Wire new router | ~2 |
| `/app/frontend/app/help/chat.tsx` | NEW — chat plein écran | ~350 |
| `/app/frontend/app/admin/help-tickets.tsx` | NEW — vue tickets pour Michel | ~200 |
| `/app/frontend/src/components/ChatHelp.tsx` | Modif : redirect vers /help/chat | ~10 |
| `/app/frontend/app/dashboard.tsx` | ADD bouton "Tickets" pour platform owner | ~20 |
| `/app/frontend/app/_layout.tsx` | Register nouveaux screens | ~4 |

---

## 🧠 Décisions techniques

1. **Embeddings** : utiliser `text-embedding-3-small` (OpenAI via Emergent) pour la KB — 1536 dims, rapide, ~1000 questions gratuit. Stocké directement en Mongo comme `[float]`.
2. **Recherche** : cosine similarity Python (numpy) — <10 ms pour ~500 questions, pas besoin de Vector DB au début.
3. **Rate limit** : max 20 questions/jour par utilisateur pour éviter les coûts LLM explosifs.
4. **Prompt injection** : filtrer les questions >500 chars, refuser les questions contenant `system:` / `ignore previous`.

---

## 🚦 Comment reprendre

Quand Michel dit « **go Yann Support** » :

1. Relire ce fichier
2. Créer backend endpoints + KB service (~1h30)
3. Créer écran chat + admin tickets (~1h30)
4. Seeder la KB avec 20 Q/A initiales tirées des screenshots FAQ actuels (~30 min)
5. Tester end-to-end via testing_agent (~30 min)
6. Commit + finish

**Prérequis** : la TODO TVA Google (autre fichier) peut passer avant si Michel le souhaite — indépendante.
