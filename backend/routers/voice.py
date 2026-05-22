"""Whisper transcription endpoint (FR)."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openai import OpenAI

from core.config import EMERGENT_LLM_KEY, logger
from core.security import get_current_user

router = APIRouter()

openai_client = OpenAI(
    api_key=EMERGENT_LLM_KEY,
    base_url="https://integrations.emergentagent.com/llm",
)


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), user=Depends(get_current_user)):
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=503, detail="Clé LLM non configurée")
    try:
        content = await audio.read()
        buf = io.BytesIO(content)
        buf.name = audio.filename or "audio.m4a"
        resp = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="fr",
            response_format="json",
        )
        return {"text": getattr(resp, "text", "") or ""}
    except Exception as e:
        logger.exception("Whisper error")
        raise HTTPException(status_code=500, detail=f"Erreur transcription: {e}")
