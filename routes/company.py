"""Routes Company Profile + endpoints plateforme (subscription)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from db import BETA_MODE, PLATFORM_ADMIN_TOKEN, VALID_PLANS, db
from deps import auth_user, ensure_company, require_admin
from models import CompanyProfile, CompanyProfileUpdate

router = APIRouter()


def _to_profile(doc: dict, company_id: str) -> CompanyProfile:
    return CompanyProfile(
        company_id=doc.get("company_id", company_id),
        name=doc.get("name") or company_id,
        artisan_mode=bool(doc.get("artisan_mode", False)),
        account_type=str(doc.get("account_type") or "entreprise"),
        logo_base64=doc.get("logo_base64"),
        subscription_status=doc.get("subscription_status", "trial"),
        subscription_expires_at=doc.get("subscription_expires_at"),
        plan=doc.get("plan", "trial"),
        chantiers_lifetime_count=int(doc.get("chantiers_lifetime_count", 0)),
        cancel_at_period_end=bool(doc.get("cancel_at_period_end", False)),
        cancelled_at=doc.get("cancelled_at"),
        beta_mode=BETA_MODE,
    )


@router.get("/company/profile", response_model=CompanyProfile)
async def get_company_profile(user=Depends(auth_user)):
    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


@router.patch("/company/profile", response_model=CompanyProfile)
async def update_company_profile(
    payload: CompanyProfileUpdate, user=Depends(require_admin)
):
    company_id = user.get("company_id", "default")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if update:
        update["company_id"] = company_id
        await db.companies.update_one(
            {"company_id": company_id},
            {"$set": update},
            upsert=True,
        )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


# --- C5 : Toggle Artisan ↔ Entreprise ----------------------------------
@router.post("/company/switch-account-type", response_model=CompanyProfile)
async def switch_account_type(
    payload: dict, user=Depends(require_admin)
):
    """Bascule entre Artisan (24.99€) et Entreprise (54.99€).

    - Artisan → Entreprise : passe le tarif et débloque la gestion d'équipe.
    - Entreprise → Artisan : retombe à 24.99€, bloque les équipes.
      Refuse le passage si des collaborateurs (commerciaux/techniciens)
      existent encore — l'Admin doit d'abord les supprimer.
    """
    target = (payload or {}).get("account_type", "").strip().lower()
    if target not in ("artisan", "entreprise"):
        raise HTTPException(400, "account_type doit valoir 'artisan' ou 'entreprise'")

    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    current = (doc.get("account_type") or "entreprise").lower()
    if current == target:
        return _to_profile(doc, company_id)

    # Entreprise → Artisan : vérifier qu'il n'y a pas de membres
    if target == "artisan":
        members_count = await db.users.count_documents({
            "company_id": company_id,
            "role": {"$in": ["commercial", "technician"]},
        })
        if members_count > 0:
            raise HTTPException(
                409,
                f"Impossible de basculer en Artisan : {members_count} collaborateur(s) "
                "encore actif(s). Supprimez-les d'abord depuis la page Équipe.",
            )

    new_plan = "artisan" if target == "artisan" else "entreprise"
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {
            "account_type": target,
            "artisan_mode": (target == "artisan"),
            "plan": new_plan,
        }},
        upsert=True,
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


# --- A3 : Créer un membre d'équipe avec mot de passe direct -----------
@router.post("/team/members")
async def create_team_member(payload: dict, user=Depends(require_admin)):
    """L'Admin crée directement un membre (Commercial ou Technicien) en
    fournissant nom + email + mot de passe. Pas d'invitation par email :
    l'Admin communique manuellement les identifiants au collaborateur.

    Réservé aux comptes Entreprise.
    """
    from datetime import datetime, timezone
    import uuid
    from deps import hash_password

    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    if (doc.get("account_type") or "entreprise").lower() == "artisan":
        raise HTTPException(403, "Gestion d'équipe non disponible en mode Artisan. Passez en Entreprise.")

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    role = (payload.get("role") or "").strip().lower()

    if not name:
        raise HTTPException(400, "Nom requis")
    if not email or "@" not in email:
        raise HTTPException(400, "Email valide requis")
    if not password or len(password) < 6:
        raise HTTPException(400, "Mot de passe : 6 caractères minimum")
    if role not in ("commercial", "technician"):
        raise HTTPException(400, "Rôle doit être 'commercial' ou 'technician'")

    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(409, "Un compte avec cet email existe déjà")

    # === Vérification de siège supplémentaire payant ============================
    # En compte Entreprise : 2 sièges gratuits inclus (1 Commercial + 1 Technicien).
    # Chaque utilisateur supplémentaire coûte 4,99 €/mois.
    # Si on dépasse, on renvoie HTTP 402 avec le détail. Le frontend affiche
    # alors une pop-up de confirmation et rejoue la requête avec
    # `confirm_extra_seat=true` pour valider l'ajout payant.
    FREE_SEATS = 2
    SEAT_PRICE_EUR = 4.99
    current_count = await db.users.count_documents(
        {"company_id": company_id, "role": {"$in": ["commercial", "technician"]}}
    )
    next_seat_index = current_count + 1
    extra_seat_billed = next_seat_index > FREE_SEATS
    extra_seats_total = max(0, next_seat_index - FREE_SEATS)
    extra_amount_eur = round(extra_seats_total * SEAT_PRICE_EUR, 2)
    confirm_extra = bool(payload.get("confirm_extra_seat") or False)
    if extra_seat_billed and not confirm_extra:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "EXTRA_SEAT_REQUIRED",
                "message": (
                    "Votre forfait Entreprise inclut 2 sièges gratuits ; "
                    f"chaque utilisateur supplémentaire coûte {SEAT_PRICE_EUR:.2f} €/mois."
                ),
                "free_seats": FREE_SEATS,
                "next_seat_index": next_seat_index,
                "current_team_size": current_count,
                "extra_seats_total": extra_seats_total,
                "seat_price_eur": SEAT_PRICE_EUR,
                "extra_amount_eur": extra_amount_eur,
            },
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "role": role,
        "company_id": company_id,
        "hashed_password": hash_password(password),
        "status": "active",
        "email_verified_at": now_iso,
        "created_by_admin": user["id"],
        "created_at": now_iso,
    }
    await db.users.insert_one(user_doc)
    return {
        "ok": True,
        "user": {
            "id": user_doc["id"],
            "name": name,
            "email": email,
            "role": role,
        },
        "message": "Collaborateur créé. Transmettez-lui ses identifiants.",
    }


@router.patch("/team/members/{member_id}/password")
async def reset_member_password(member_id: str, payload: dict, user=Depends(require_admin)):
    """L'Admin réinitialise le mot de passe d'un membre. Le membre sera
    automatiquement déconnecté (token invalidé via mise à jour password).
    """
    from deps import hash_password
    new_pw = payload.get("password") or ""
    if len(new_pw) < 6:
        raise HTTPException(400, "Mot de passe : 6 caractères minimum")
    company_id = user.get("company_id", "default")
    member = await db.users.find_one({"id": member_id, "company_id": company_id})
    if not member:
        raise HTTPException(404, "Membre introuvable")
    if member.get("role") == "admin":
        raise HTTPException(403, "Impossible de modifier le mot de passe d'un Admin")
    await db.users.update_one(
        {"id": member_id},
        {"$set": {"hashed_password": hash_password(new_pw)}},
    )
    return {"ok": True, "message": "Mot de passe mis à jour"}


@router.delete("/team/members/{member_id}")
async def delete_team_member(member_id: str, user=Depends(require_admin)):
    """L'Admin supprime un membre de l'équipe."""
    company_id = user.get("company_id", "default")
    member = await db.users.find_one({"id": member_id, "company_id": company_id})
    if not member:
        raise HTTPException(404, "Membre introuvable")
    if member.get("role") == "admin":
        raise HTTPException(403, "Impossible de supprimer un Admin")
    await db.users.delete_one({"id": member_id})
    return {"ok": True}


# --- M1 : Support contact endpoint ------------------------------------
def _send_support_email(*, to: str, subject: str, html: str) -> dict:
    from email_service import send_email
    return send_email(to=to, subject=subject, body="", html=html)


@router.post("/support/contact")
async def contact_support(payload: dict, user=Depends(auth_user)):
    """Reçoit un message de support et l'envoie via Resend à info@."""
    from datetime import datetime, timezone
    import uuid

    subject = (payload.get("subject") or "Demande de support").strip()[:200]
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "Message vide")

    ticket = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "user_email": user.get("email"),
        "user_name": user.get("name"),
        "subject": subject,
        "message": message[:5000],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
    }
    await db.support_tickets.insert_one(ticket)

    # Email vers info@mesurechassis.com
    try:
        _send_support_email(
            to="info@mesurechassis.com",
            subject=f"[Support MC] {subject}",
            html=(
                f"<h3>Nouvelle demande de support</h3>"
                f"<p><b>De :</b> {user.get('name')} &lt;{user.get('email')}&gt;</p>"
                f"<p><b>Sujet :</b> {subject}</p>"
                f"<hr/><pre style='white-space:pre-wrap'>{message[:5000]}</pre>"
            ),
        )
    except Exception:
        pass  # le ticket reste en DB même si l'email échoue

    return {"ok": True, "message": "Votre demande a bien été envoyée. Nous vous répondrons sous 24h."}


# --- Subscription cancellation (Master Admin) ---------------------------
@router.post("/company/subscription/cancel", response_model=CompanyProfile)
async def cancel_subscription(user=Depends(require_admin)):
    """Désabonnement gracieux : l'accès Pro est conservé jusqu'à
    `subscription_expires_at`, puis le verrou paywall s'active automatiquement.

    Réservé au Master Admin (role == "admin"). Le Mode Artisan ne bypass pas
    cette action — uniquement les administrateurs déclarés peuvent annuler.
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur peut annuler l'abonnement.",
        )
    company_id = user.get("company_id", "default")
    doc = await ensure_company(company_id)
    if doc.get("cancel_at_period_end"):
        raise HTTPException(
            status_code=400,
            detail="L'annulation est déjà programmée.",
        )
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.companies.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "cancel_at_period_end": True,
                "cancelled_at": now_iso,
            }
        },
        upsert=True,
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


@router.post("/company/subscription/reactivate", response_model=CompanyProfile)
async def reactivate_subscription(user=Depends(require_admin)):
    """Réactive l'abonnement avant la fin de la période payée."""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Seul l'administrateur peut réactiver l'abonnement.",
        )
    company_id = user.get("company_id", "default")
    await db.companies.update_one(
        {"company_id": company_id},
        {
            "$set": {
                "cancel_at_period_end": False,
                "cancelled_at": None,
            }
        },
        upsert=True,
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)


# --- Platform admin: régulariser un abonnement (out-of-band) ------------
@router.post("/platform/companies/{company_id}/subscription")
async def platform_set_subscription(
    company_id: str,
    payload: dict,
    x_platform_token: Optional[str] = Header(None),
):
    if x_platform_token != PLATFORM_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid platform token")
    update: dict = {}
    if "subscription_status" in payload:
        if payload["subscription_status"] not in (
            "trial", "active", "suspended",
        ):
            raise HTTPException(400, "Invalid subscription_status")
        update["subscription_status"] = payload["subscription_status"]
    if "plan" in payload:
        if payload["plan"] not in VALID_PLANS:
            raise HTTPException(
                400, f"plan must be one of {sorted(VALID_PLANS)}"
            )
        update["plan"] = payload["plan"]
        # Lorsqu'on passe en Pro : on remet à zéro l'annulation programmée.
        if payload["plan"] == "pro":
            update["cancel_at_period_end"] = False
            update["cancelled_at"] = None
    if "extend_days" in payload:
        try:
            days = int(payload["extend_days"])
        except (TypeError, ValueError):
            raise HTTPException(400, "extend_days must be int")
        new_dt = datetime.now(timezone.utc) + timedelta(days=days)
        update["subscription_expires_at"] = new_dt.isoformat()
    if (
        "subscription_expires_at" in payload
        and "extend_days" not in payload
    ):
        update["subscription_expires_at"] = payload["subscription_expires_at"]
    if "cancel_at_period_end" in payload:
        update["cancel_at_period_end"] = bool(payload["cancel_at_period_end"])
    if not update:
        raise HTTPException(400, "Nothing to update")
    update["company_id"] = company_id
    await db.companies.update_one(
        {"company_id": company_id}, {"$set": update}, upsert=True
    )
    doc = await ensure_company(company_id)
    return _to_profile(doc, company_id)
