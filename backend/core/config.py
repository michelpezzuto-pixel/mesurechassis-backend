"""Environment & app-wide settings."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mesure_escalier")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "168"))
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Subscription / Paywall
TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "90"))
