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

# ── JWT ───────────────────────────────────────────────────────────────────
# SEC-001 fix: refuse to boot with the historic placeholder secret or any
# obviously weak value. JWT_SECRET MUST be loaded from the deployment
# environment, NOT from a committed file.
_FORBIDDEN_JWT_SECRETS = {
    "mesure-escalier-super-secret-jwt-key-change-in-prod-2026",
    "CHANGE_ME_USE_python_secrets.token_hex_48",
    "change-me",
    "secret",
    "",
}
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if JWT_SECRET in _FORBIDDEN_JWT_SECRETS or len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET is missing, too short (<32 chars) or matches a known "
        "default. Generate a strong one with "
        "`python -c \"import secrets; print(secrets.token_hex(48))\"` "
        "and set it via the deployment environment."
    )
JWT_ALGO = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# ── Subscription / Paywall ────────────────────────────────────────────────
TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "90"))

# ── CORS ──────────────────────────────────────────────────────────────────
# Comma-separated list of origins. "*" only allowed in DEV. In prod, set a
# real list via the deployment environment. Empty value → wildcard (dev).
_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_raw:
    CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]
else:
    # Dev fallback: allow the Expo packager preview host + localhost.
    # NOT a wildcard — wildcards combined with allow_credentials are unsafe.
    CORS_ORIGINS = [
        "https://stair-pro.preview.emergentagent.com",
        "http://localhost:3000",
        "http://localhost:8081",
        "http://localhost:19006",
    ]

# ── Login rate-limit ──────────────────────────────────────────────────────
# Generous default (30 attempts / 5 min) — tightens significantly in
# production where each user has their own IP via mobile carrier NAT.
# In dev / Expo preview many test runs share one egress IP (ingress proxy)
# so a lower limit would impede legitimate testing.
LOGIN_RATE_LIMIT_MAX = int(os.environ.get("LOGIN_RATE_LIMIT_MAX", "30"))
LOGIN_RATE_LIMIT_WINDOW_SEC = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SEC", "300"))
