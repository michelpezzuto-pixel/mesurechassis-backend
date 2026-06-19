"""Assistant IA Yann — Backend route POST /api/yann/chat (Build 9 — juin 2026).

Contexte métier :
  Yann est un assistant intelligent intégré qui répond aux questions des
  menuisiers utilisateurs de MesureChâssis (workflow, exports, RBAC,
  formules, parrainage, prise de mesures…). Disponible en option à
  +5 €/mois sur Artisan Solo & Entreprise, et INCLUS dans Entreprise Pro.

Choix techniques :
  • Anthropic Claude Sonnet 4.5 (excellent rapport intelligence/coût,
    bon multilingue FR/NL/EN).
  • Utilise emergentintegrations.llm.chat (couche unifiée Emergent).
  • Historique de conversation stocké dans MongoDB collection
    `yann_conversations` (1 doc par session_id).
  • Pour le MVP : send_message() non-streaming. Streaming SSE pourra
    être ajouté en v2 si besoin UX.
  • Quota : 30 messages/jour/utilisateur en MVP (anti-abus).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import auth_user

load_dotenv()
logger = logging.getLogger("mesurechassis.yann")
router = APIRouter()

EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY", "")
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"
DAILY_MESSAGE_LIMIT = 30  # par utilisateur, anti-abus MVP

YANN_SYSTEM_PROMPT = """Tu es Yann, l'assistant IA officiel de MesureChâssis, l'application mobile de référence pour la prise de mesures terrain des menuisiers (fenêtres, portes, châssis).

# TON RÔLE
Répondre clairement, en français professionnel et chaleureux, aux questions des utilisateurs de l'application. Tu connais l'app sur le bout des doigts, tu connais aussi le métier de menuisier.

# CONNAISSANCE DE L'APP
- 3 rôles : Admin (patron), Commercial (relevé terrain), Technicien (validation atelier)
- Workflow : Devis à faire → À mesurer → À vérifier (par le technicien) → En fabrication (verrouillé) → Terminé
- Mode "Artisan solo" : l'utilisateur est seul, il a tous les droits
- Formes supportées : rectangle, carré, cintré (plein cintre, arc surbaissé), polygones (triangle, pentagone, hexagone, octogone), trapèze, angle 90°, bow-window, oval
- Exports : PDF, Excel, CSV, JSON (compatible CNC)
- Photos anti-litige rattachées aux mesures
- Mode hors-ligne avec synchronisation auto

# FORMULES (à mentionner si l'utilisateur demande les prix)
- Gratuit : 5 ouvertures/mois à vie
- Artisan Solo : 19,99 €/mois (1 user)
- Entreprise : 59,99 €/mois (équipe illimitée, pas de supplément)
- Entreprise Pro : 249 €/mois (tout inclus : toi Yann + devis auto + mesure photo IA + intégrations machines)
- Add-on Assistant IA Yann : +5 €/mois sur Solo et Entreprise (inclus dans Pro)

# PARRAINAGE
2 mois offerts par filleul actif, limite 10 filleuls = jusqu'à 20 mois cumulés.

# IOS (Apple Review)
Sur iPhone l'inscription et les prix ne sont pas affichés (Reader App). L'utilisateur doit aller sur mesurechassis.com ou Android pour s'abonner.

# RÈGLES DE RÉPONSE
1. Réponses courtes (3-5 phrases max sauf si question complexe).
2. Toujours en français sauf si l'utilisateur parle dans une autre langue.
3. Si tu ne sais pas : dis-le et oriente vers le formulaire de contact (/feedback) ou support@mesurechassis.com.
4. Tu ne dois PAS inventer de fonctionnalité qui n'existe pas. Les futures features (mesure par photo IA, intégrations machines) sont "à venir" — précise-le.
5. Ton style : direct, pédagogique, bienveillant. Comme un collègue qui prend le temps d'expliquer.
6. Si on te demande de faire autre chose que du support MesureChâssis (écrire un poème, du code, etc.), refuse poliment et recentre."""


# ════════════════════════════════════════════════════════════════════════════
# Modèles Pydantic
# ════════════════════════════════════════════════════════════════════════════
class ChatMessage(BaseModel):
    role: str = Field(..., description="user | assistant")
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # généré si absent (1 par conversation)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    quota_remaining: int


# ════════════════════════════════════════════════════════════════════════════
# Endpoints
# ════════════════════════════════════════════════════════════════════════════
@router.post("/yann/chat", response_model=ChatResponse)
async def chat_with_yann(payload: ChatRequest, user=Depends(auth_user)):
    """Envoie un message à Yann et retourne sa réponse.

    L'historique de la conversation est stocké côté serveur (Mongo)
    indexé par `session_id`. Le client n'a qu'à renvoyer le même
    session_id sur les messages suivants pour maintenir le contexte.
    """
    if not EMERGENT_LLM_KEY:
        raise HTTPException(503, "Assistant IA temporairement indisponible (clé manquante).")

    user_id = user.get("user_id") or user.get("id") or ""
    if not user_id:
        raise HTTPException(401, "Utilisateur non authentifié")

    message = (payload.message or "").strip()
    if not message:
        raise HTTPException(400, "Message vide")
    if len(message) > 2000:
        raise HTTPException(400, "Message trop long (max 2 000 caractères)")

    # ─── Quota journalier ─────────────────────────────────────────────
    today_iso = datetime.now(timezone.utc).date().isoformat()
    quota_doc = await db.yann_quota.find_one({"user_id": user_id, "date": today_iso})
    used_today = (quota_doc or {}).get("count", 0)
    if used_today >= DAILY_MESSAGE_LIMIT:
        raise HTTPException(
            429,
            f"Quota journalier atteint ({DAILY_MESSAGE_LIMIT} messages). Revenez demain ou contactez le support pour augmenter votre limite.",
        )

    # ─── Récupère / crée la session ───────────────────────────────────
    session_id = payload.session_id or f"yann_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
    conv = await db.yann_conversations.find_one({"session_id": session_id})
    if conv and conv.get("user_id") != user_id:
        # Sécurité : on ne partage pas les sessions entre utilisateurs
        raise HTTPException(403, "Session non autorisée")

    history: list[dict] = (conv or {}).get("messages", [])

    # ─── Appel LLM via emergentintegrations ───────────────────────────
    try:
        # Import à l'intérieur pour éviter de charger la lib si la route
        # n'est jamais appelée (réduit le boot time du backend).
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=YANN_SYSTEM_PROMPT,
        ).with_model(MODEL_PROVIDER, MODEL_NAME)

        # Ré-injecte l'historique (la lib n'a pas de mémoire persistante).
        # On reconstruit la conversation en envoyant tour par tour, mais
        # pour un MVP pragmatique on concatène l'historique récent dans
        # le user_message courant pour préserver le contexte.
        # NB : on garde seulement les 10 derniers tours (20 messages) pour
        # contenir les tokens.
        recent = history[-20:]
        context_block = ""
        if recent:
            lines = []
            for m in recent:
                role = "Utilisateur" if m.get("role") == "user" else "Yann"
                lines.append(f"{role} : {m.get('content', '')}")
            context_block = (
                "Historique récent de la conversation (pour contexte) :\n"
                + "\n".join(lines)
                + "\n\n---\nNouvelle question de l'utilisateur :\n"
            )

        user_msg = UserMessage(text=context_block + message)
        reply_text = await chat.send_message(user_msg)
    except Exception as e:  # noqa: BLE001
        logger.exception("Erreur LLM Yann pour user=%s session=%s", user_id, session_id)
        raise HTTPException(
            502,
            f"Yann n'a pas pu répondre cette fois — réessayez. ({type(e).__name__})",
        ) from e

    # ─── Persiste l'historique + incrémente le quota ──────────────────
    new_history = history + [
        {"role": "user", "content": message, "ts": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": reply_text, "ts": datetime.now(timezone.utc).isoformat()},
    ]
    await db.yann_conversations.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "session_id": session_id,
                "user_id": user_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "messages": new_history,
            },
            "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()},
        },
        upsert=True,
    )
    await db.yann_quota.update_one(
        {"user_id": user_id, "date": today_iso},
        {"$inc": {"count": 1}, "$setOnInsert": {"user_id": user_id, "date": today_iso}},
        upsert=True,
    )

    return ChatResponse(
        reply=reply_text,
        session_id=session_id,
        quota_remaining=max(0, DAILY_MESSAGE_LIMIT - used_today - 1),
    )


@router.get("/yann/history")
async def get_conversation_history(session_id: str, user=Depends(auth_user)):
    """Retourne l'historique d'une conversation Yann (pour reprise UI)."""
    user_id = user.get("user_id") or user.get("id") or ""
    conv = await db.yann_conversations.find_one({"session_id": session_id})
    if not conv:
        return {"session_id": session_id, "messages": []}
    if conv.get("user_id") != user_id:
        raise HTTPException(403, "Session non autorisée")
    return {"session_id": session_id, "messages": conv.get("messages", [])}


@router.get("/yann/quota")
async def get_daily_quota(user=Depends(auth_user)):
    """Retourne le quota Yann restant pour aujourd'hui."""
    user_id = user.get("user_id") or user.get("id") or ""
    today_iso = datetime.now(timezone.utc).date().isoformat()
    quota_doc = await db.yann_quota.find_one({"user_id": user_id, "date": today_iso})
    used = (quota_doc or {}).get("count", 0)
    return {
        "limit": DAILY_MESSAGE_LIMIT,
        "used": used,
        "remaining": max(0, DAILY_MESSAGE_LIMIT - used),
    }
