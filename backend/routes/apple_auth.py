"""🍎 Sign in with Apple — Apple Guideline 4.8 compliance (juillet 2026).

Flux :
    1. Frontend iOS appelle expo-apple-authentication.signInAsync()
    2. Apple retourne un `identityToken` JWT signé RS256
    3. Frontend POST /api/auth/apple/session { identity_token, user_name? }
    4. Backend vérifie le JWT contre les JWKS Apple (iss/aud/exp/signature)
    5. On upsert l'utilisateur par `apple_sub` dans `users`, on émet
       NOTRE JWT habituel → RBAC, abonnements, etc. sans changement.

Règles :
    - `apple_sub` est LA clé primaire (email peut être private-relay ou null).
    - Nom + email envoyés UNIQUEMENT à la première connexion — persister immédiat.
    - Utilisateur existant (par apple_sub) → simple login, aucun doublon.
    - Nouvel utilisateur → société solo (artisan) BETA gratuit, comme Google.
    - Fallback : si Apple envoie un email valide déjà existant dans la base,
      on lie le compte existant (email login classique → +apple_linked=True).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from jwt import PyJWKClient
from pydantic import BaseModel

from db import BETA_MODE, db
from deps import create_access_token, user_to_public

logger = logging.getLogger("mesurechassis.apple_auth")
router = APIRouter()

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# Audiences autorisées — DOIT contenir le bundle iOS ET `host.exp.Exponent`
# pour supporter les tests via Expo Go pendant le développement.
_AUDIENCES_ENV = os.getenv(
    "APPLE_AUDIENCES",
    "com.mesurechassis.escalier,host.exp.Exponent",
).strip()
APPLE_AUDIENCES = {a.strip() for a in _AUDIENCES_ENV.split(",") if a.strip()}

# Cache JWKS 24h (les clés Apple tournent rarement)
_JWKS_CACHE_TTL = 24 * 3600
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(APPLE_JWKS_URL, cache_keys=True, lifespan=_JWKS_CACHE_TTL)
    return _jwks_client


class AppleSessionPayload(BaseModel):
    identity_token: str
    # Envoyé uniquement à la 1re connexion (Apple ne renvoie plus après)
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    # ☕ Priorité 4 — tag campagne station partenaire (QR code), optionnel
    station_id: Optional[str] = None


def _verify_apple_token(identity_token: str) -> dict:
    """Vérifie signature + iss + aud + exp de l'identity_token Apple.

    Retourne les claims décodés (sub, email éventuel, email_verified…).
    Lève HTTPException 401 si invalide.
    """
    if not identity_token or "." not in identity_token:
        raise HTTPException(401, "identity_token invalide")

    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(identity_token).key
    except (jwt.PyJWTError, ValueError, UnicodeDecodeError) as exc:
        # JWT décodage impossible (format invalide, header mal encodé…) → 401
        logger.warning("Apple identity_token undecodable: %s", exc)
        raise HTTPException(401, "Jeton Apple invalide (format)")
    except Exception as exc:  # noqa: BLE001
        # Erreur RÉSEAU vers Apple JWKS uniquement → 502
        logger.exception("Apple JWKS lookup failed: %s", exc)
        raise HTTPException(502, "Impossible de vérifier le jeton Apple (JWKS)")

    try:
        # PyJWT accepte plusieurs audiences en même temps
        claims = jwt.decode(
            identity_token,
            signing_key,
            algorithms=["RS256"],
            audience=list(APPLE_AUDIENCES),
            issuer=APPLE_ISSUER,
            options={"require": ["sub", "aud", "iss", "exp"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Jeton Apple expiré. Réessayez.")
    except jwt.InvalidAudienceError:
        logger.warning("Apple token audience rejected — expected one of %s", APPLE_AUDIENCES)
        raise HTTPException(401, "Jeton Apple invalide (audience)")
    except jwt.InvalidIssuerError:
        raise HTTPException(401, "Jeton Apple invalide (émetteur)")
    except jwt.PyJWTError as exc:
        logger.warning("Apple token validation failed: %s", exc)
        raise HTTPException(401, "Jeton Apple invalide")

    if not claims.get("sub"):
        raise HTTPException(401, "Jeton Apple sans identifiant utilisateur")

    return claims


@router.post("/auth/apple/session")
async def apple_session(payload: AppleSessionPayload, request: Request):
    """Échange un identity_token Apple contre notre JWT applicatif."""
    claims = _verify_apple_token(payload.identity_token.strip())

    apple_sub = str(claims["sub"])
    token_email = str(claims.get("email") or "").lower().strip()
    email_verified = claims.get("email_verified") in (True, "true")

    # 1) Recherche par apple_sub (clé primaire Apple) — puis fallback par email
    user_doc = await db.users.find_one({"apple_sub": apple_sub})

    linked_email = ""
    if not user_doc:
        # Fallback : si le premier login envoie un email connu (compte
        # existant classique login/password OU Google), on lie plutôt que de
        # créer un doublon.
        candidate_email = (payload.user_email or token_email or "").lower().strip()
        if candidate_email:
            existing = await db.users.find_one({"email": candidate_email})
            if existing and existing.get("status") != "deleted":
                await db.users.update_one(
                    {"id": existing["id"]},
                    {"$set": {"apple_sub": apple_sub, "apple_linked": True}},
                )
                user_doc = await db.users.find_one({"id": existing["id"]})
                linked_email = candidate_email
                logger.info(
                    "🍎 Apple LINK compte existant %s → apple_sub=%s",
                    candidate_email, apple_sub,
                )

    if user_doc:
        if user_doc.get("status") == "deleted":
            raise HTTPException(
                403,
                "Ce compte a été supprimé. Contactez le support à "
                "info@mesurechassis.com.",
            )
        # Un compte pending_verification devient actif (Apple garantit l'email)
        if user_doc.get("status") == "pending_verification":
            await db.users.update_one(
                {"id": user_doc["id"]},
                {"$set": {
                    "status": "active",
                    "email_verified_at": datetime.now(timezone.utc).isoformat(),
                    "apple_linked": True,
                }},
            )
            user_doc = await db.users.find_one({"id": user_doc["id"]})
        logger.info("🍎 Apple login (compte existant) %s", user_doc.get("email"))
    else:
        # 2) Nouveau compte Apple — société solo BETA gratuit.
        #    Nom/email fournis UNE SEULE FOIS par Apple → à persister maintenant.
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Nom : d'abord ce que l'appli envoie (Apple SDK), sinon fallback
        name = (payload.user_name or "").strip()
        if not name and token_email:
            name = token_email.split("@")[0]
        if not name:
            name = f"Utilisateur {apple_sub[:6]}"

        # Email : Apple → privaterelay ou vrai email (peut être vide)
        final_email = (payload.user_email or token_email or "").lower().strip()

        base_slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
        company_id = f"{base_slug or 'co'}-{uuid.uuid4().hex[:6]}"

        company_doc = {
            "company_id": company_id,
            "name": name,
            "account_type": "artisan",
            "preferred_plan": "solo",
            "artisan_mode": True,
            "vat_number": None,
            "vat_country": None,
            "subscription_status": "active" if BETA_MODE else None,
            "subscription_expires_at": (now + timedelta(days=3650)).isoformat()
            if BETA_MODE else None,
            "plan": "pro" if BETA_MODE else "free",
            "chantiers_lifetime_count": 0,
            "cancel_at_period_end": False,
            "beta_account": BETA_MODE,
            "freemium_trial_ends_at": (now + timedelta(days=14)).isoformat(),
            "created_at": now_iso,
        }
        await db.companies.insert_one(company_doc)

        user_doc = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": final_email or f"apple-{apple_sub[:12]}@privaterelay.mesurechassis.com",
            "role": "admin",
            "company_id": company_id,
            "hashed_password": None,      # pas de password → login Apple uniquement
            "apple_sub": apple_sub,
            "apple_linked": True,
            "apple_email_verified": bool(email_verified),
            "apple_original_email": final_email or None,
            "status": "active",
            "email_verified_at": now_iso if (email_verified or not final_email) else None,
            "created_at": now_iso,
        }

        # ☕ Priorité 4 — tag campagne Jeton Café (QR code station)
        station_id_raw = (payload.station_id or "").strip()
        if station_id_raw:
            station = await db.cafe_stations.find_one(
                {"id": station_id_raw, "active": True}, {"_id": 0, "id": 1}
            )
            if station:
                user_doc["campaign_station_id"] = station_id_raw

        # 🗺️ Géolocalisation approximative (ville) via IP — best-effort
        try:
            from services.geolocation import geolocate_from_request
            geo = await geolocate_from_request(request)
            if geo:
                user_doc["signup_geo"] = geo
        except Exception:
            pass

        await db.users.insert_one(user_doc)
        logger.info(
            "🍎 Apple signup (nouveau) sub=%s email=%s → %s",
            apple_sub, final_email or "N/A", company_id,
        )

    # 3) Émission de NOTRE JWT — identique au login classique
    token = create_access_token(user_doc["id"], user_doc["role"])
    user_public = user_to_public(user_doc).model_dump()

    # 🔒 Flag TVA à compléter (Apple 3.1.3(c) + Stripe UE) — comme Google.
    try:
        from deps import user_needs_vat_completion
        company_now = await db.companies.find_one(
            {"company_id": user_doc["company_id"]},
            {"_id": 0, "vat_number": 1, "business_id_value": 1},
        )
        if user_needs_vat_completion(user_doc, company_now):
            user_public["vat_completion_required"] = True
    except Exception:
        pass

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_public,
    }
