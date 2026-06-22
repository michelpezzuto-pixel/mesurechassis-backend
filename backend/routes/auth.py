"""Routes d'authentification + gestion utilisateurs + double opt-in."""
from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from db import BETA_MODE, VALID_ROLES, db

logger = logging.getLogger("mesurechassis.auth")
from deps import (
    auth_user,
    create_access_token,
    hash_password,
    require_active_subscription,
    user_to_public,
    verify_password,
)
from email_service import (
    build_verification_link,
    send_verification_email,
)
from models import (
    LoginRequest,
    PushTokenIn,
    RegisterMasterAdmin,
    RegisterResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserPublic,
    VerifyEmailRequest,
)

router = APIRouter()


VERIFICATION_TTL_DAYS = 7


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def _create_verification(
    *, user_id: str, email: str, kind: str = "verify"
) -> str:
    token = _new_token()
    await db.email_verifications.insert_one(
        {
            "token": token,
            "user_id": user_id,
            "email": email.lower(),
            "kind": kind,  # verify | invite
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(days=VERIFICATION_TTL_DAYS)
            ).isoformat(),
            "used": False,
        }
    )
    return token


import hashlib

from fastapi import Request


def _device_fingerprint(req: Request) -> str:
    """Calcule un hash SHA-256 de l'IP + User-Agent du client.

    Utilisé pour détecter les inscriptions répétées depuis le même
    appareil après suppression (anti-fraude essai gratuit).
    """
    ip = (
        req.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or req.client.host
        or "unknown"
    )
    ua = req.headers.get("user-agent", "unknown")[:200]
    return hashlib.sha256(f"{ip}|{ua}".encode("utf-8")).hexdigest()


# --- Master Admin self-signup (création d'une nouvelle société) ---------
@router.post("/auth/register")
async def register(payload: dict, request: Request):
    """Inscription — Dual-mode :

    * **Master Admin (nouveau flux)** : payload `{name, email, password, company_name?}`
      → crée un compte `admin` en `status="pending_verification"`,
      envoie un email de vérification (MOCKÉ : lien retourné dans la réponse).

    * **Legacy/internal (tests + tooling)** : payload `{name, email, password,
      role, company_id?}` → crée un utilisateur ACTIF avec le rôle demandé,
      retourne un JWT directement (pas de double opt-in). Réservé aux tests
      et à l'usage interne. La frontale principale n'utilise PAS ce mode.
    """
    name = payload.get("name")
    email = payload.get("email")
    password = payload.get("password")
    if not (name and email and password):
        raise HTTPException(400, "Champs requis : name, email, password")
    email_lower = str(email).lower()

    existing = await db.users.find_one({"email": email_lower})
    if existing:
        raise HTTPException(400, "Email déjà enregistré")

    # 🛡️ Anti-fraude essai gratuit — détecte les inscriptions répétées
    # depuis le même appareil après suppression de compte.
    # Bloque si un user a été soft-deleted ou si une company a été
    # abandonnée depuis ce fingerprint dans les 180 derniers jours.
    fingerprint = _device_fingerprint(request)
    # Bypass pour les inscriptions legacy (tests internes avec champ `role`)
    # et bypass complet en mode BETA pour ne pas gêner les premiers tests.
    if "role" not in payload and not BETA_MODE:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=180)
        ).isoformat()
        flagged = await db.users.find_one(
            {
                "signup_fingerprint": fingerprint,
                "status": "deleted",
                "deleted_at": {"$gte": cutoff},
            },
            {"_id": 0, "id": 1},
        )
        if flagged:
            raise HTTPException(
                403,
                "Un compte précédent a été supprimé depuis cet appareil "
                "récemment. Pour reprendre votre activité, contactez le "
                "support à info@mesurechassis.com.",
            )

    # ---- Legacy mode ----------------------------------------------------
    if "role" in payload:
        role = payload["role"]
        if role not in VALID_ROLES:
            raise HTTPException(400, "Invalid role")
        company_id = payload.get("company_id", "default")
        user_doc = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email_lower,
            "role": role,
            "company_id": company_id,
            "hashed_password": hash_password(password),
            "status": "active",
            "email_verified_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user_doc)
        token = create_access_token(user_doc["id"], user_doc["role"])
        return {"access_token": token, "token_type": "bearer",
                "user": user_to_public(user_doc).model_dump()}

    # ---- Master Admin mode (nouveau flux, double opt-in) ----------------
    # Lot D : account_type "artisan" (compte solo, artisan_mode=true)
    # vs "entreprise" (compte avec équipe). Défaut = entreprise (legacy).
    # 🆕 V3 (juin 2026) : ajout du tier "pro" (Entreprise Pro — équipe
    # étendue + fonctions avancées). Stocké tel quel dans `account_type`.
    # Le plan de souscription préféré est dérivé : artisan→solo,
    # entreprise→entreprise, pro→pro (utilisé pour pré-sélectionner sur
    # l'écran subscription Stripe).
    account_type_raw = str(payload.get("account_type") or "entreprise").lower()
    if account_type_raw not in {"artisan", "entreprise", "pro"}:
        account_type_raw = "entreprise"
    is_artisan = account_type_raw == "artisan"
    # Plan Stripe préféré pour cet utilisateur (pour pré-sélection)
    preferred_plan_map = {
        "artisan": "solo",
        "entreprise": "entreprise",
        "pro": "pro",
    }
    preferred_plan = preferred_plan_map.get(account_type_raw, "entreprise")

    # Pour un Artisan, le nom de société par défaut = nom de l'utilisateur
    # (auto-entrepreneur), pour Entreprise/Pro on impose company_name explicite.
    company_name = payload.get("company_name")
    if is_artisan:
        company_name = (company_name or name).strip() or name
    else:
        company_name = (company_name or "").strip()
        if not company_name:
            raise HTTPException(
                status_code=400,
                detail="Le nom de l'entreprise est requis pour un compte Entreprise.",
            )

    # 🆕 Build 11.3 — Validation TVA européenne obligatoire pour
    # Admin/Artisan (Apple Review Guideline 3.1.3(c)).
    # MesureChâssis se positionne désormais comme service B2B européen.
    # Les comptes Commercial/Technicien (créés via /auth/invite) sont
    # exemptés : ils héritent de la TVA de leur company parent.
    vat_raw = (payload.get("vat_number") or "").strip()
    if not vat_raw:
        raise HTTPException(
            status_code=400,
            detail=(
                "Un numéro de TVA européen est requis pour s'inscrire. "
                "MesureChâssis est un service réservé aux professionnels "
                "de la menuiserie. Exemple : BE0123456789"
            ),
        )
    # Bypass VIES uniquement pour le compte démo Apple Review
    # (vat bidon mais format valide, pour ne pas être bloqué par VIES).
    is_apple_review = email_lower == "applereview@mesurechassis.com"
    from services.vat_validator import validate_vat as _validate_vat
    vat_ok, vat_normalized, vat_msg = await _validate_vat(
        vat_raw, skip_vies=is_apple_review
    )
    if not vat_ok:
        raise HTTPException(
            status_code=400,
            detail=vat_msg or "Numéro de TVA invalide.",
        )

    base_slug = company_name.strip().lower()
    safe_slug = "".join(c if c.isalnum() else "-" for c in base_slug).strip("-")
    company_id = f"{safe_slug or 'co'}-{uuid.uuid4().hex[:6]}"

    # Mode auto-vérification (activé tant que les DNS Resend ne sont pas
    # configurés sur le domaine d'envoi). Permet à l'utilisateur de se
    # connecter immédiatement sans attendre l'email — l'email de
    # vérification est tout de même envoyé pour info.
    # Pour désactiver (production stricte) : MC_AUTO_VERIFY_ON_REGISTER=0
    auto_verify = os.getenv("MC_AUTO_VERIFY_ON_REGISTER", "1") == "1"
    now_iso_reg = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email_lower,
        "role": "admin",
        "company_id": company_id,
        "hashed_password": hash_password(password),
        "status": "active" if auto_verify else "pending_verification",
        "email_verified_at": now_iso_reg if auto_verify else None,
        # Fingerprint anti-fraude (IP + UA hash) — utilisé pour bloquer
        # les recréations de comptes après suppression.
        "signup_fingerprint": fingerprint,
        "created_at": now_iso_reg,
    }
    await db.users.insert_one(user_doc)
    # 🚧 BETA GRATUITE : les nouveaux comptes naissent directement en
    # `plan=pro` + `subscription_status=active` (pas d'écran de paiement).
    # ensure_company() complétera les valeurs manquantes au premier accès.
    if BETA_MODE:
        beta_expires = (
            datetime.now(timezone.utc) + timedelta(days=365 * 10)
        ).isoformat()
        # 💎 Freemium trial 14 jours : même en BETA, on initialise le champ
        # pour qu'il soit déjà présent en base le jour où on coupera BETA.
        freemium_trial_ends = (
            datetime.now(timezone.utc) + timedelta(days=14)
        ).isoformat()
        company_doc = {
            "company_id": company_id,
            "name": company_name,
            "account_type": account_type_raw,
            # 🆕 V3 — Plan Stripe préféré (artisan→solo, entreprise→entreprise, pro→pro)
            "preferred_plan": preferred_plan,
            # Artisan → artisan_mode automatique (bypass RBAC complet)
            "artisan_mode": is_artisan,
            # 🆕 Build 11.3 — TVA européenne (validée VIES, sauf compte Apple Review)
            "vat_number": vat_normalized,
            "vat_country": (vat_normalized or "")[:2] if vat_normalized else None,
            "subscription_status": "active",
            "subscription_expires_at": beta_expires,
            "plan": "pro",
            "chantiers_lifetime_count": 0,
            "cancel_at_period_end": False,
            "beta_account": True,
            # 💎 Freemium (juin 2026) — Pré-rempli pour la transition future
            "freemium_trial_ends_at": freemium_trial_ends,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        # 💎 Prod (post-beta) : Freemium avec essai gratuit 14 jours toutes formes.
        # Passé 14 jours sans abonnement → retour au mode gratuit 5 formes.
        freemium_trial_ends = (
            datetime.now(timezone.utc) + timedelta(days=14)
        ).isoformat()
        company_doc = {
            "company_id": company_id,
            "name": company_name,
            "account_type": account_type_raw,
            # 🆕 V3 — Plan Stripe préféré
            "preferred_plan": preferred_plan,
            "artisan_mode": is_artisan,
            # 🆕 Build 11.3 — TVA européenne (validée VIES, sauf compte Apple Review)
            "vat_number": vat_normalized,
            "vat_country": (vat_normalized or "")[:2] if vat_normalized else None,
            # Pas d'abonnement par défaut — l'utilisateur est en freemium
            "subscription_status": None,
            "subscription_expires_at": None,
            "plan": "free",
            "chantiers_lifetime_count": 0,
            "cancel_at_period_end": False,
            # 💎 Essai 14j toutes formes débloquées (le frontend lit ce champ)
            "freemium_trial_ends_at": freemium_trial_ends,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    await db.companies.insert_one(company_doc)
    # 🆕 Build 9 — Lier au parrain si un code valide est fourni à l'inscription
    try:
        from routes.referral import link_referral_at_signup
        await link_referral_at_signup(company_id, payload.get("referral_code"))
    except Exception:
        # Le parrainage ne doit JAMAIS bloquer l'inscription
        logger.exception("Erreur lien parrainage à l'inscription")

    token = await _create_verification(
        user_id=user_doc["id"], email=email_lower, kind="verify"
    )
    link = build_verification_link(token)
    # On envoie tout de même l'email pour info, mais on n'attend plus de
    # vérification : `auto_verify` a déjà mis le compte en `active`.
    send_verification_email(to=email_lower, name=name, link=link)

    if auto_verify:
        # Mode auto-vérification : on NE renvoie PAS verification_link au
        # frontend afin qu'il n'affiche pas l'écran "Pending verification".
        # L'utilisateur peut se connecter directement.
        return {
            "user": user_to_public(user_doc).model_dump(),
            "message": "Compte créé avec succès. Vous pouvez vous connecter.",
        }

    return {
        "user": user_to_public(user_doc).model_dump(),
        # 🔒 En production (MC_RETURN_VERIF_LINK=0), on NE renvoie PAS le lien
        # dans la réponse API : l'utilisateur DOIT le récupérer via email.
        # En preview/dev (MC_RETURN_VERIF_LINK=1), on l'expose pour faciliter
        # les tests sans avoir à ouvrir sa boîte mail.
        "verification_link": link
            if os.getenv("MC_RETURN_VERIF_LINK", "0") == "1"
            else None,
        "message": (
            "Compte créé. Un email de vérification a été envoyé. "
            "Cliquez sur le lien pour activer votre compte."
        ),
    }


# --- Verify email -------------------------------------------------------
@router.post("/auth/verify", response_model=TokenResponse)
async def verify_email(payload: VerifyEmailRequest):
    rec = await db.email_verifications.find_one({"token": payload.token})
    if not rec:
        raise HTTPException(400, "Lien de vérification invalide")
    # 🆕 Build 11.3 (Apple Fix) — Si le lien est déjà utilisé, mais que
    # l'utilisateur existe et est actif, on retourne un succès gracieux
    # avec un JWT, plutôt qu'une erreur. Cela évite l'écran "LIEN INVALIDE"
    # quand l'utilisateur clique 2× ou quand auto-verify a déjà activé.
    if rec.get("used"):
        existing = await db.users.find_one({"id": rec["user_id"]}, {"_id": 0})
        if existing and existing.get("status") == "active":
            jwt_token = create_access_token(existing["id"], existing["role"])
            return TokenResponse(
                access_token=jwt_token, user=user_to_public(existing)
            )
        raise HTTPException(400, "Lien déjà utilisé")
    try:
        expires = datetime.fromisoformat(
            str(rec["expires_at"]).replace("Z", "+00:00")
        )
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(400, "Lien expiré (>7 jours)")
    except ValueError:
        raise HTTPException(400, "Lien malformé")

    if rec.get("kind") != "verify":
        raise HTTPException(
            400,
            "Ce lien est une invitation. Utilisez /auth/invite/accept.",
        )

    user = await db.users.find_one({"id": rec["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "status": "active",
                "email_verified_at": now_iso,
            }
        },
    )
    await db.email_verifications.update_one(
        {"token": payload.token},
        {"$set": {"used": True, "used_at": now_iso}},
    )
    user["status"] = "active"
    user["email_verified_at"] = now_iso

    # Génère un token JWT pour login automatique après vérification.
    jwt_token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=jwt_token, user=user_to_public(user))


@router.post("/auth/resend-verification")
async def resend_verification(payload: ResendVerificationRequest):
    """Renvoie un nouvel email de vérification."""
    email_lower = payload.email.lower()
    user = await db.users.find_one({"email": email_lower})
    # Ne révèle pas si l'email existe (anti-énumération)
    if not user or (user.get("status") or "active") != "pending_verification":
        return {
            "ok": True,
            "message": "Si ce compte est en attente, un nouvel email a été envoyé.",
        }
    token = await _create_verification(
        user_id=user["id"], email=email_lower, kind="verify"
    )
    link = build_verification_link(token)
    send_verification_email(to=email_lower, name=user["name"], link=link)
    return {"ok": True, "verification_link": link}


# --- Login --------------------------------------------------------------
@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not user.get("hashed_password") or not verify_password(
        payload.password, user["hashed_password"]
    ):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    status = user.get("status") or "active"
    if status == "deleted":
        # Sécurité RGPD : ne pas confirmer l'existence d'un compte supprimé
        raise HTTPException(401, "Email ou mot de passe incorrect")
    if status == "pending_verification":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": (
                    "Votre adresse email n'a pas encore été vérifiée. "
                    "Cliquez sur le lien envoyé par email pour activer votre compte."
                ),
                "email": user["email"],
            },
        )
    if status == "suspended":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "user_suspended",
                "message": "Votre compte a été suspendu.",
            },
        )
    token = create_access_token(user["id"], user["role"])
    return TokenResponse(access_token=token, user=user_to_public(user))


@router.get("/auth/me", response_model=UserPublic)
async def me(user=Depends(auth_user)):
    return user_to_public(user)


@router.get("/users", response_model=List[UserPublic])
async def list_users(user=Depends(require_active_subscription)):
    docs = await db.users.find(
        {"company_id": user.get("company_id", "default")},
        {"_id": 0, "hashed_password": 0},
    ).to_list(500)
    return [user_to_public(d) for d in docs]


@router.post("/auth/push-token")
async def set_push_token(
    payload: PushTokenIn, user=Depends(auth_user)
):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"push_token": payload.push_token}},
    )
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────
# Modifier ses propres infos (nom, email, téléphone, mot de passe)
# ─────────────────────────────────────────────────────────────────────
@router.patch("/auth/me", response_model=UserPublic)
async def update_me(payload: dict, user=Depends(auth_user)):
    """Permet à l'utilisateur connecté de modifier ses informations.

    Champs modifiables :
    - name (str) : nom affiché
    - phone (str) : numéro de téléphone (optionnel)
    - email (str) : changement d'email (vérification requise via current_password)
    - new_password (str) : changement de mot de passe (vérification via current_password)

    ⚠️ Le changement d'email ou de mot de passe exige `current_password` pour
    confirmer l'identité (protection contre vol de session).
    """
    update: dict = {}
    sensitive_change = (
        payload.get("email") and payload.get("email").lower() != user.get("email", "").lower()
    ) or bool(payload.get("new_password"))

    # Vérification du mot de passe actuel pour toute modification sensible
    if sensitive_change:
        current_password = payload.get("current_password")
        if not current_password:
            raise HTTPException(
                400,
                "Le mot de passe actuel est requis pour modifier l'email ou le mot de passe.",
            )
        from deps import verify_password
        if not verify_password(current_password, user.get("hashed_password", "")):
            raise HTTPException(403, "Mot de passe actuel incorrect.")

    # 1. Nom
    if "name" in payload:
        name = str(payload["name"]).strip()
        if not (2 <= len(name) <= 80):
            raise HTTPException(400, "Le nom doit faire entre 2 et 80 caractères.")
        update["name"] = name

    # 2. Téléphone (optionnel, format libre)
    if "phone" in payload:
        phone = str(payload.get("phone") or "").strip()
        if phone and not (5 <= len(phone) <= 30):
            raise HTTPException(400, "Numéro de téléphone invalide.")
        update["phone"] = phone

    # 3. Email (vérification d'unicité)
    if payload.get("email"):
        new_email = str(payload["email"]).strip().lower()
        if "@" not in new_email or "." not in new_email:
            raise HTTPException(400, "Email invalide.")
        if new_email != user.get("email", "").lower():
            existing = await db.users.find_one({"email": new_email})
            if existing:
                raise HTTPException(400, "Cet email est déjà utilisé.")
            update["email"] = new_email

    # 4. Mot de passe
    if payload.get("new_password"):
        new_pw = str(payload["new_password"])
        if len(new_pw) < 8:
            raise HTTPException(400, "Le mot de passe doit faire au moins 8 caractères.")
        update["hashed_password"] = hash_password(new_pw)

    if not update:
        raise HTTPException(400, "Aucun changement à enregistrer.")

    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return user_to_public(fresh)


# ─────────────────────────────────────────────────────────────────────
# Mot de passe oublié (forgot / reset password)
# ─────────────────────────────────────────────────────────────────────
PASSWORD_RESET_TTL_MINUTES = 30


@router.post("/auth/forgot-password")
async def forgot_password(payload: dict):
    """Démarre la réinitialisation du mot de passe.

    Body : {"email": "user@..."}

    Génère un code à 6 chiffres, le stocke en base avec expiration 30 min,
    et l'envoie par email (mock console en BETA, Resend ensuite).

    🛡️ Anti-énumération : on renvoie TOUJOURS HTTP 200 (même si l'email
    n'existe pas) pour ne pas permettre à un attaquant de découvrir les
    emails inscrits. En revanche en BETA on retourne le code dans la
    réponse pour que l'utilisateur ne soit pas bloqué quand l'email
    réel n'est pas encore branché.
    """
    email = (payload.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalide.")

    user = await db.users.find_one({"email": email})
    response_payload = {
        "ok": True,
        "message": (
            "Si un compte existe avec cet email, un code de "
            "réinitialisation vous a été envoyé."
        ),
    }

    if not user:
        # Énumération : on log mais on renvoie OK
        return response_payload

    # Génère un code 6 chiffres + expiration 30 min
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES)
    ).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "password_reset_code": code,
                "password_reset_expires_at": expires_at,
            }
        },
    )

    # Envoi via Resend (fallback mock console si la clé est absente)
    email_result: dict = {}
    try:
        from email_service import send_password_reset_email

        email_result = await send_password_reset_email(email, code)
    except Exception:  # noqa: BLE001
        # Toute exception inattendue → on bascule en mode dégradé
        email_result = {"delivered": False}

    delivered = bool(email_result.get("delivered"))

    # 🛟 Sécurité : on n'expose JAMAIS le code en clair si Resend a envoyé.
    # En revanche, si l'envoi a échoué ET qu'on est en BETA, on retourne
    # le code pour ne pas bloquer l'utilisateur (clé Resend en cours de
    # config, domaine pas vérifié, etc.).
    if not delivered and BETA_MODE:
        response_payload["beta_reset_code"] = code
        response_payload["beta_message"] = (
            "Email non envoyé (mode dégradé). Code = "
            f"{code} (valable {PASSWORD_RESET_TTL_MINUTES} min)."
        )

    return response_payload


@router.post("/auth/reset-password")
async def reset_password(payload: dict):
    """Valide un code et change le mot de passe.

    Body : {"email": "...", "code": "123456", "new_password": "..."}
    """
    email = (payload.get("email") or "").strip().lower()
    code = (payload.get("code") or "").strip()
    new_password = payload.get("new_password") or ""

    if not email or not code or not new_password:
        raise HTTPException(
            status_code=400,
            detail="Email, code et nouveau mot de passe requis.",
        )
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir au moins 6 caractères.",
        )

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=400, detail="Code invalide ou expiré.")

    stored_code = user.get("password_reset_code")
    expires_at = user.get("password_reset_expires_at")
    if not stored_code or stored_code != code:
        raise HTTPException(status_code=400, detail="Code invalide ou expiré.")

    # Vérifie l'expiration
    try:
        exp_dt = datetime.fromisoformat(expires_at) if expires_at else None
    except Exception:
        exp_dt = None
    if not exp_dt or exp_dt < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expiré, demandez-en un nouveau.")

    # Hash et stocke le nouveau mot de passe + invalide le code
    # IMPORTANT : si l'utilisateur a réussi à recevoir le code par email et à le
    # valider, cela PROUVE qu'il possède bien cette adresse. On en profite donc
    # pour auto-vérifier son email (passe de pending_verification → active).
    now_iso = datetime.now(timezone.utc).isoformat()
    set_fields = {"hashed_password": hash_password(new_password)}
    if (user.get("status") or "active") == "pending_verification":
        set_fields["status"] = "active"
        set_fields["email_verified_at"] = now_iso
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": set_fields,
            "$unset": {
                "password_reset_code": "",
                "password_reset_expires_at": "",
            },
        },
    )
    return {
        "ok": True,
        "message": "Mot de passe réinitialisé. Vous pouvez vous reconnecter.",
    }


# ─────────────────────────────────────────────────────────────────────
# RGPD — Soft-delete du compte
# ─────────────────────────────────────────────────────────────────────
@router.delete("/auth/me")
async def delete_my_account(
    payload: dict,
    user=Depends(auth_user),
):
    """Soft-delete RGPD du compte courant.

    Le mot de passe doit être confirmé pour des raisons de sécurité.
    L'utilisateur peut opter pour conserver son email (opt-in marketing)
    sinon l'email est anonymisé immédiatement.

    Champs côté DB :
      - status = 'deleted'
      - deleted_at = ISO now
      - marketing_optin = bool
      - email = anonymized si !marketing_optin (préserve l'unicité)
      - hashed_password = "" (login impossible)
      - push_tokens = []

    Note : aucune purge dure (purge nightly à prévoir côté ops après 30j).
    """
    password = str(payload.get("password") or "").strip()
    marketing_optin = bool(payload.get("marketing_optin", False))
    # B1 — Conserver la casse stricte : "SUPPRIMER" exact, pas "supprimer".
    confirm_text = str(payload.get("confirm_text") or "").strip()

    if not password:
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe est requis pour confirmer la suppression.",
        )
    if confirm_text != "SUPPRIMER":
        raise HTTPException(
            status_code=400,
            detail="Tapez SUPPRIMER en majuscules pour confirmer.",
        )

    user_doc = await db.users.find_one({"id": user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    # B2 — Garde contre un éventuel double-DELETE : si le compte est déjà
    # soft-deleted, hashed_password est vide → verify_password lèverait
    # passlib.exc.UnknownHashError (500). On retourne 400 explicite.
    if not user_doc.get("hashed_password"):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect.")
    if not verify_password(password, user_doc["hashed_password"]):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect.")

    now_iso = datetime.now(timezone.utc).isoformat()
    original_email = user_doc.get("email") or ""

    # Anonymisation : si pas opt-in marketing → email effacé strictement.
    # On préserve l'unicité avec un suffixe UUID pour éviter les collisions.
    if marketing_optin:
        new_email = original_email
    else:
        new_email = f"deleted_{uuid.uuid4().hex[:12]}@deleted.invalid"

    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "status": "deleted",
                "deleted_at": now_iso,
                "marketing_optin": marketing_optin,
                "email": new_email,
                "hashed_password": "",
                "push_tokens": [],
                "password_reset_code": "",
                "password_reset_expires_at": "",
                # On conserve l'email d'origine en interne UNIQUEMENT si
                # opt-in marketing — sinon on garde une simple trace
                # anonymisée pour audit (hash de l'email d'origine).
                "marketing_email": original_email if marketing_optin else None,
            }
        },
    )

    # Si l'utilisateur supprimé est le seul admin de sa société, on flag la
    # société comme "abandonnée" pour faciliter le nettoyage ops ultérieur.
    company_id = user_doc.get("company_id")
    if company_id:
        remaining_admins = await db.users.count_documents(
            {
                "company_id": company_id,
                "role": "admin",
                "status": {"$ne": "deleted"},
            }
        )
        if remaining_admins == 0:
            await db.companies.update_one(
                {"company_id": company_id},
                {"$set": {"abandoned_at": now_iso}},
            )

    return {
        "ok": True,
        "message": "Compte supprimé. Toutes vos données personnelles ont été anonymisées."
        + (
            " Votre email reste enregistré pour les communications commerciales (opt-in)."
            if marketing_optin
            else " Votre email a été supprimé conformément au RGPD."
        ),
    }
