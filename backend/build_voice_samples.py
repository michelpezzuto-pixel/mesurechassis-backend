"""
Génère 4 échantillons voix OpenAI TTS pour que Michel choisisse son style.
Texte : celui affiché dans sa vidéo Runway (~5-6 s de voix par échantillon).

Sortie : /app/backend/public_downloads/voice-samples/*.mp3
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

TEXT = (
    "Après les mesures, je partage directement avec mon designer ou mon technicien."
)

VOICES = {
    "onyx":   "Masculine grave et autoritaire (B2B pro)",
    "echo":   "Masculine chaleureuse et amicale (storytelling)",
    "fable":  "Masculine narrative et posée (tutoriel)",
    "nova":   "Féminine dynamique et énergique (accroche)",
    "alloy":  "Neutre et équilibrée (multi-usage)",
    "shimmer":"Féminine douce et posée (contenu éducatif)",
}

OUT_DIR = Path("/app/backend/public_downloads/voice-samples")
API_KEY = os.getenv("EMERGENT_LLM_KEY", "").strip()
BASE_URL = "https://integrations.emergentagent.com/llm"


async def gen_sample(voice: str, description: str) -> None:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        r = await client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input=TEXT,
            speed=1.0,
            response_format="mp3",
        )
        out_path = OUT_DIR / f"sample-{voice}.mp3"
        out_path.write_bytes(r.content)
        size_kb = len(r.content) // 1024
        print(f"✅ {voice:8s} ({size_kb:3d} Ko) — {description}")
    except Exception as e:
        print(f"❌ {voice:8s} — {str(e)[:100]}")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not API_KEY:
        print("❌ EMERGENT_LLM_KEY manquante")
        return
    print(f"Texte : « {TEXT} »\n")
    for voice, desc in VOICES.items():
        await gen_sample(voice, desc)


if __name__ == "__main__":
    asyncio.run(main())
