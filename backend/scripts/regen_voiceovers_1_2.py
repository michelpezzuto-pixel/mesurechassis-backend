"""
🎙️ Régénération des voix-off TikTok Scripts #1 et #2.

Modifications demandées par l'utilisateur :
  - Suppression de toute mention de prix (ex: "huit cents euros")
  - Remplacement par : "Viens la télécharger gratuitement. Lien en bio."
  - Voix féminine (Nova) conforme aux guidelines

Sorties :
  - /app/backend/static/promo/tiktok_script1/voiceover.mp3 (remplacé)
  - /app/backend/static/promo/tiktok_script2/voiceover.mp3 (remplacé)
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

API_KEY = os.getenv("EMERGENT_LLM_KEY")
if not API_KEY:
    print("❌ EMERGENT_LLM_KEY introuvable")
    sys.exit(1)

# ───────────────────────────────────────────────────────────
# NOUVEAUX TEXTES (sans prix, avec CTA gratuit)
# ───────────────────────────────────────────────────────────
SCRIPTS = {
    "tiktok_script1": (
        "POV : t'es menuisier alu, vingt-trois ans de métier, et tu mesures "
        "encore avec un carnet papier. Hauteur cent vingt-deux. Ou cent "
        "trente-deux ? Le deux est mal écrit. Diagonale ? T'as pas pris la "
        "peine. Photo ? Bah non, t'as oublié. Trois jours après, l'atelier "
        "appelle : « Les cotes correspondent pas, le châssis rentre pas. » "
        "Devine quoi ? Tu refais le chantier à tes frais. Femme : pas "
        "contente. Ou tu télécharges MesureChâssis. Tu mesures sur ton "
        "téléphone, tout est carré. L'atelier valide direct. Zéro retour. "
        "Viens la télécharger gratuitement. Lien en bio."
    ),
    "tiktok_script2": (
        "Trois fois. Trois fois que l'atelier te renvoie le châssis. Tu "
        "craques. Tu reprends la mesure. Diagonale numéro un : mille huit "
        "cent cinquante. Diagonale numéro deux : mille huit cent "
        "cinquante-huit. Huit millimètres d'écart. Le châssis est foutu. "
        "Avec MesureChâssis, ton téléphone te le dit avant. Tu rentres tes "
        "cotes, l'application calcule la diagonale automatiquement et te "
        "bloque si l'écart dépasse trois millimètres. Yann, l'assistant IA, "
        "te dit même quoi corriger. Zéro retour atelier. Zéro SAV. "
        "Viens la télécharger gratuitement. Lien en bio."
    ),
}


async def regen_voiceover(folder: str, text: str) -> bool:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=API_KEY,
        base_url="https://integrations.emergentagent.com/llm",
    )

    output_dir = Path(f"/app/backend/static/promo/{folder}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "voiceover.mp3"
    backup_path = output_dir / "voiceover_old.mp3"

    # Sauvegarde de l'ancien fichier au cas où
    if output_path.exists() and not backup_path.exists():
        shutil.copy(output_path, backup_path)
        print(f"   📦 Backup : {backup_path.name}")

    try:
        response = await client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",  # voix féminine claire, conforme aux guidelines
            input=text,
            speed=1.0,
            response_format="mp3",
        )
        output_path.write_bytes(response.content)
        print(
            f"   ✅ {folder}/voiceover.mp3 "
            f"({len(response.content) // 1024} KB)"
        )
        return True
    except Exception as e:
        print(f"   ❌ {folder} : {e}")
        return False


async def main():
    print("🎙️  Régénération des voix-off TikTok #1 et #2 (voix Nova)")
    print("    → Suppression des prix, ajout CTA gratuit\n")

    for folder, text in SCRIPTS.items():
        print(f"🎬 {folder}")
        print(f"   📝 Texte ({len(text)} car.) :")
        # Affichage tronqué pour vérification
        preview = text[:120] + "..." if len(text) > 120 else text
        print(f"      {preview}")
        await regen_voiceover(folder, text)
        print()

    print("✅ Terminé !")
    print("\n📥 URLs publiques :")
    print(
        "   https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script1/voiceover.mp3"
    )
    print(
        "   https://window-field-app.preview.emergentagent.com/"
        "api/promo/tiktok_script2/voiceover.mp3"
    )


if __name__ == "__main__":
    asyncio.run(main())
