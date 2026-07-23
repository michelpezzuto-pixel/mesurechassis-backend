"""
📱 App Version Config — Endpoint public pour notifier les clients mobiles
d'une mise à jour disponible ou requise (style Revolut / Uber).

Piloté par 3 variables d'environnement Railway :
- APP_MIN_VERSION      : version minimum acceptée (ex: "1.0.29")
- APP_LATEST_VERSION   : dernière version publiée (ex: "1.1.3")
- APP_FORCE_UPDATE     : "true" pour BLOQUER les versions < min (défaut false)
- APP_UPDATE_MESSAGE   : message custom affiché à l'utilisateur
- APP_UPDATE_HIGHLIGHTS: "|"-séparé, liste des nouveautés (ex: "Fix PDF|Nouveaux exports")

Endpoint appelé au démarrage de l'app (avant login) → pas d'auth requise.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter(prefix="/config", tags=["config"])


APP_STORE_URL = (
    "https://apps.apple.com/fr/app/mesurech%C3%A2ssis/id6776357930"
)
PLAY_STORE_URL: str | None = None  # activer quand Android publié


@router.get("/app-version")
async def app_version_config():
    """Retourne la config des versions mobiles. Public + no-auth."""
    min_version = os.getenv("APP_MIN_VERSION", "1.0.29").strip() or "1.0.29"
    latest_version = os.getenv("APP_LATEST_VERSION", "1.1.3").strip() or "1.1.3"
    force_update = os.getenv("APP_FORCE_UPDATE", "false").lower() == "true"
    message = os.getenv(
        "APP_UPDATE_MESSAGE",
        "Une nouvelle version de MesureChâssis est disponible avec des "
        "améliorations importantes. Merci de mettre à jour.",
    ).strip()
    highlights_raw = os.getenv("APP_UPDATE_HIGHLIGHTS", "").strip()
    highlights = [h.strip() for h in highlights_raw.split("|") if h.strip()] if highlights_raw else []

    return {
        "min_version": min_version,
        "latest_version": latest_version,
        "force_update": force_update,
        "message": message,
        "highlights": highlights,
        "app_store_url": APP_STORE_URL,
        "play_store_url": PLAY_STORE_URL,
    }
