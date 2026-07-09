"""🔑 Google Sign-In — via Emergent-managed Google Auth (juillet 2026).

Flux :
    1. Le frontend redirige vers https://auth.emergentagent.com/?redirect=<app>
    2. Google authentifie l'utilisateur → retour app avec `session_id`
    3. Le frontend appelle POST /api/auth/google/session {session_id}
    4. On vérifie le session_id auprès de l'API Emergent, on upsert
       l'utilisateur par email dans la collection `users` existante,
       puis on émet NOTRE JWT habituel → le reste de l'app (RBAC,
       abonnements, etc.) fonctionne sans aucun changement.

Règles :
    - Utilisateur existant (email/password OU Google) → simple connexion,
      AUCUN doublon créé (upsert par email).
    - Nouvel utilisateur → création société solo (artisan, BETA pro
      gratuit) sans numéro de TVA (complété plus tard si besoin).
    - Tag campagne ☕ Jeton Café supporté (station_id optionnel).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import BETA_MODE, db
from deps import create_access_token, user_to_public

logger = logging.getLogger("mesurechassis.google_auth")
router = APIRouter()

EMERGENT_SESSION_API = (
    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)


class GoogleSessionPayload(BaseModel):
    session_id: str
    # ☕ Priorité 4 — tag campagne station partenaire (QR code), optionnel
    station_id: Optional[str] = None


@router.post("/auth/google/session")
async def google_session(payload: GoogleSessionPayload):
    """Échange un `session_id` Emergent contre notre JWT applicatif."""
    session_id = (payload.session_id or "").strip()
    if not session_id:
        raise HTTPException(400, "session_id requis")

    # 1) Vérification du session_id auprès d'Emergent
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                EMERGENT_SESSION_API, headers={"X-Session-ID": session_id}
            )
    except httpx.HTTPError:
        logger.exception("Google auth : API session Emergent injoignable")
        raise HTTPException(502, "Service d'authentification indisponible. Réessayez.")
    if resp.status_code != 200:
        raise HTTPException(401, "Session Google invalide ou expirée. Réessayez.")

    data = resp.json()
    email = str(data.get("email") or "").lower().strip()
    name = str(data.get("name") or "").strip() or email.split("@")[0]
    picture = data.get("picture")
    if not email:
        raise HTTPException(401, "Impossible de récupérer l'email Google.")

    # 2) Upsert par email — JAMAIS de doublon
    user_doc = await db.users.find_one({"email": email})
    if user_doc:
        if user_doc.get("status") == "deleted":
            raise HTTPException(
                403,
                "Ce compte a été supprimé. Contactez le support à "
                "info@mesurechassis.com.",
            )
        updates = {"google_linked": True}
        if picture and not user_doc.get("picture"):
            updates["picture"] = picture
        # Un compte en attente de vérification email est validé de fait :
        # Google a déjà vérifié la propriété de l'adresse.
        if user_doc.get("status") == "pending_verification":
            updates["status"] = "active"
            updates["email_verified_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one({"id": user_doc["id"]}, {"$set": updates})
        user_doc = await db.users.find_one({"id": user_doc["id"]})
        logger.info("🔑 Google login (compte existant) %s", email)
    else:
        # 3) Nouveau compte — société solo (artisan) en BETA gratuite.
        #    Pas de TVA à l'inscription Google (complétée plus tard).
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
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
            if BETA_MODE
            else None,
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
            "email": email,
            "role": "admin",
            "company_id": company_id,
            # Pas de mot de passe — connexion Google uniquement (l'utilisateur
            # peut en définir un plus tard via « Mot de passe oublié ? »).
            "hashed_password": None,
            "status": "active",
            "email_verified_at": now_iso,
            "google_linked": True,
            "picture": picture,
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
        await db.users.insert_one(user_doc)
        logger.info("🔑 Google signup (nouveau compte) %s → %s", email, company_id)

    # 4) Émission de NOTRE JWT — identique au login classique
    token = create_access_token(user_doc["id"], user_doc["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_to_public(user_doc).model_dump(),
    }
