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


def _require_strong_secret(var_name: str, insecure_defaults: set[str]) -> str:
    """Charge un secret depuis l'env et refuse de démarrer s'il est absent,
    trop court, ou égal à une valeur par défaut connue (audit SEC-001/002)."""
    value = os.environ.get(var_name, "")
    if not value or value.strip() == "":
        raise RuntimeError(
            f"[SÉCURITÉ] {var_name} est requis et ne peut pas être vide. "
            f"Définissez-le dans l'environnement (secret aléatoire fort)."
        )
    if value in insecure_defaults:
        raise RuntimeError(
            f"[SÉCURITÉ] {var_name} utilise une valeur par défaut non sécurisée. "
            f"Générez un secret aléatoire (ex: python -c \"import secrets;"
            f"print(secrets.token_urlsafe(48))\")."
        )
    if len(value) < 32:
        raise RuntimeError(
            f"[SÉCURITÉ] {var_name} doit faire au moins 32 caractères."
        )
    return value


JWT_SECRET = _require_strong_secret(
    "JWT_SECRET",
    {"change-me-mesurechassis-secret-key-dev-only", "secret", "changeme"},
)
JWT_ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 jours
PLATFORM_ADMIN_TOKEN = _require_strong_secret(
    "PLATFORM_ADMIN_TOKEN",
    {"mc-platform-2026", "admin", "changeme", "default"},
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --- Constantes métier ---------------------------------------------------
VALID_ROLES = {"admin", "commercial", "technician"}
VALID_STATUSES = {
    "devis_a_faire",
    "a_mesurer",
    "technique_a_valider",
    "a_verifier",
    "en_commande",
    "en_fabrication",
    "cloture",
}
CONVERTED_STATUSES = {"en_commande", "en_fabrication", "cloture"}
VALID_BLOCK_TYPES = {"standard", "coulissant", "porte", "trapeze"}
VALID_WALL_TYPES = {"ite", "iti", "brique_parement", "crepi_simple"}

# ═══════════════════════════════════════════════════════════════════════
# 💰 Freemium tier — Limites du plan gratuit (juillet 2026)
# ═══════════════════════════════════════════════════════════════════════
# Après la fin de l'essai 14 jours (Artisan Pro) ou fallback Entreprise,
# les users basculent automatiquement vers un plan gratuit LIMITÉ.
#
# Fonctionnalités qualitatives QUI RESTENT gratuites :
#   ✅ Export PDF
#   ✅ Photos anti-litige
#   ✅ Wizard mesure + calcul auto (diagonales, feuillures, tolérances)
#   ✅ 14 formes de menuiseries (choix limité par le nombre d'ouvertures)
#
# Limites QUANTITATIVES du plan gratuit :
VALID_PLANS = {"free", "trial", "pro", "entreprise", "beta"}
FREE_PLAN_MAX_CHANTIERS = 3               # 3 chantiers max en gratuit
FREE_PLAN_MAX_OUVERTURES = 5              # 5 ouvertures max cumulées en gratuit
FREE_YANN_QUESTIONS_MONTHLY = 10          # 10 questions Yann / mois calendaire
FREE_IA_IMPORTS_MONTHLY = 3               # 3 imports IA cahier des charges / mois
FREE_EXPORT_FORMATS = {"pdf"}             # Export PDF uniquement (pas Excel/CSV/JSON)

# ═══════════════════════════════════════════════════════════════════════
# 🚧 BETA_MODE — Toggle global pour forcer tous les comptes en Pro illimité
# ═══════════════════════════════════════════════════════════════════════
# TRUE  → phase actuelle (tous les users ont accès Pro illimité gratos)
# FALSE → phase paiement activée (limites + trials appliquées)
#
# Pour désactiver sans redéployer le code : ajouter BETA_MODE=false dans
# le .env de production (Railway) puis redémarrer le backend.
BETA_MODE = os.getenv("BETA_MODE", "true").lower() in ("true", "1", "yes", "on")

# Durée de la période d'essai (Trial) — 14 jours pour Artisan Pro et
# Entreprise Pro. (Entreprise MAX aura 30 jours quand implémenté.)
TRIAL_DAYS = 14
TRIAL_DAYS_ENTREPRISE_MAX = 30  # Pour usage futur — pas encore actif

# Endpoints accessibles même si l'abonnement est expiré
SUBSCRIPTION_OPEN_PATHS = {
    "/api/auth/me",
    "/api/company/profile",
    "/api/feedbacks",
}
