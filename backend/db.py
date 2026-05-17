"""MongoDB connection + constantes globales.

Ce module est importé en premier — aucune dépendance circulaire avec
les routes ou modèles.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mesurechassis")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get(
    "JWT_SECRET", "change-me-mesurechassis-secret-key-dev-only"
)
JWT_ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 jours
PLATFORM_ADMIN_TOKEN = os.getenv("PLATFORM_ADMIN_TOKEN", "mc-platform-2026")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --- Constantes métier ---------------------------------------------------
VALID_ROLES = {"admin", "commercial", "technician"}
VALID_STATUSES = {
    "devis_a_faire",
    "technique_a_valider",
    "en_commande",
    "en_fabrication",
    "cloture",
}
CONVERTED_STATUSES = {"en_commande", "en_fabrication", "cloture"}
VALID_BLOCK_TYPES = {"standard", "coulissant", "porte", "trapeze"}
VALID_WALL_TYPES = {"ite", "iti", "brique_parement", "crepi_simple"}

# Endpoints accessibles même si l'abonnement est expiré
SUBSCRIPTION_OPEN_PATHS = {
    "/api/auth/me",
    "/api/company/profile",
    "/api/feedbacks",
}
