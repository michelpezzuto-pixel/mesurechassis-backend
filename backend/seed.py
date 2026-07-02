"""Seeding initial — DÉSACTIVÉ en PRODUCTION.

Les comptes et chantiers de démonstration ne doivent EXISTER QUE
pendant le développement / la phase BETA interne. En production,
les utilisateurs créent leurs propres comptes via /auth/register
et chacun démarre avec un dashboard 100% vierge (isolation stricte
par `company_id`).

Pour réactiver le seed (dev local ou debug) : exporter la variable
d'environnement `MC_SEED_DEMO=1` dans `/app/backend/.env`.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from db import db, logger
from deps import hash_password

# ─────────────────────────────────────────────────────────────────────
# DEMO TOGGLE — vide en production ; activable via env MC_SEED_DEMO=1
# ─────────────────────────────────────────────────────────────────────
SEED_DEMO = os.getenv("MC_SEED_DEMO", "0").strip() == "1"

DEMO_USERS = [
    {
        "name": "Marc Dubois",
        "email": "admin@mesurechassis.fr",
        "password": "admin123",
        "role": "admin",
    },
    {
        "name": "Sophie Martin",
        "email": "commercial@mesurechassis.fr",
        "password": "commercial123",
        "role": "commercial",
    },
    {
        "name": "Lucas Petit",
        "email": "tech@mesurechassis.fr",
        "password": "tech123",
        "role": "technician",
    },
]


async def seed_data() -> None:
    """Seed idempotent — n'agit que si MC_SEED_DEMO=1.

    Ne supprime JAMAIS de données existantes ; en production le seed est
    simplement skip et la base reste telle quelle (les anciens comptes
    démo déjà créés en BETA peuvent rester ou être nettoyés manuellement).
    """
    # Backfill company_id sur les anciens documents (toujours utile, même prod)
    await db.chantiers.update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": "default"}},
    )
    await db.feedbacks.update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": "default"}},
    )
    await db.mesures.update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": "default"}},
    )

    if not SEED_DEMO:
        logger.info("Seed démo DÉSACTIVÉ (set MC_SEED_DEMO=1 pour activer)")
        return

    logger.info("Seed démo ACTIVÉ — création des comptes et chantiers de démo")

    user_ids: dict[str, str] = {}
    for u in DEMO_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            user_ids[u["role"]] = existing["id"]
            continue
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "id": uid,
                "name": u["name"],
                "email": u["email"],
                "role": u["role"],
                "company_id": "default",
                "hashed_password": hash_password(u["password"]),
                "status": "active",
                "email_verified_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        user_ids[u["role"]] = uid
        logger.info("Seeded user %s", u["email"])

    if await db.chantiers.count_documents({"company_id": "default"}) == 0:
        demos = [
            ("Famille Lefèvre", "12 rue de la Paix, 75002 Paris", "devis_a_faire"),
            ("Boulangerie Moreau", "45 av. Victor Hugo, 69006 Lyon", "devis_a_faire"),
            ("M. et Mme Bernard", "8 chemin des Vignes, 33000 Bordeaux", "technique_a_valider"),
            ("SCI Le Clos", "23 rue Nationale, 59000 Lille", "technique_a_valider"),
            ("Cabinet Dr. Rousseau", "5 place Bellecour, 69002 Lyon", "cloture"),
        ]
        for name, addr, status_v in demos:
            await db.chantiers.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "client_name": name,
                    "address": addr,
                    "status": status_v,
                    "created_by": user_ids.get("commercial", "system"),
                    "assigned_to": user_ids.get("technician"),
                    "company_id": "default",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
async def ensure_apple_review_user() -> None:
    """🍎 Ensure the Apple App Review demo account ALWAYS exists.

    This is NOT optional and does NOT depend on MC_SEED_DEMO. The Apple
    review team needs to be able to log in with these exact credentials
    every time they review the iOS app, otherwise the app is rejected.

    Idempotent: if the user already exists, only re-syncs the password
    hash to guarantee it matches the published credentials (in case the
    DB was edited or a stale hash was kept).
    """
    APPLE_EMAIL = "applereview@mesurechassis.com"
    APPLE_PASSWORD = "MesureChassis2026"
    APPLE_COMPANY_ID = "apple-review-demo"

    existing = await db.users.find_one({"email": APPLE_EMAIL})
    now_iso = datetime.now(timezone.utc).isoformat()
    fresh_hash = hash_password(APPLE_PASSWORD)

    if existing:
        # Re-sync password + active status (in case anything changed)
        await db.users.update_one(
            {"email": APPLE_EMAIL},
            {"$set": {
                "hashed_password": fresh_hash,
                "status": "active",
                "email_verified_at": existing.get("email_verified_at") or now_iso,
                "role": "admin",
                "company_id": APPLE_COMPANY_ID,
            }},
        )
        logger.info("🍎 Apple Review user re-synced (password reset to canonical)")
    else:
        user_doc = {
            "id": str(uuid.uuid4()),
            "name": "Apple App Review",
            "email": APPLE_EMAIL,
            "role": "admin",
            "company_id": APPLE_COMPANY_ID,
            "hashed_password": fresh_hash,
            "status": "active",
            "email_verified_at": now_iso,
            "created_at": now_iso,
        }
        await db.users.insert_one(user_doc)
        logger.info("🍎 Apple Review user CREATED in DB")

    # Ensure company exists for this demo account (full Pro plan)
    company_existing = await db.companies.find_one({"company_id": APPLE_COMPANY_ID})
    if not company_existing:
        ten_years_iso = (
            datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 10)
        ).isoformat()
        await db.companies.insert_one({
            "company_id": APPLE_COMPANY_ID,
            "name": "Apple Review Demo Co.",
            "account_type": "entreprise",
            "preferred_plan": "pro",
            "plan": "pro",
            "subscription_status": "active",
            "subscription_expires_at": ten_years_iso,
            "vat_number": "BE0000000097",
            "created_at": now_iso,
        })
        logger.info("🍎 Apple Review company CREATED (Pro plan, 10y)")

    # Seed a few demo chantiers so the reviewer can explore the app
    existing_chantiers = await db.chantiers.count_documents({"company_id": APPLE_COMPANY_ID})
    if existing_chantiers == 0:
        apple_demos = [
            ("Démo — Maison Dupont",  "12 rue Demo, 75001 Paris",        "devis_a_faire"),
            ("Démo — Villa Martin",   "8 av. Demo, 69001 Lyon",          "technique_a_valider"),
            ("Démo — Boutique Léa",   "5 place Demo, 33000 Bordeaux",    "en_fabrication"),
            ("Démo — Chantier livré", "23 rue Demo, 59000 Lille",        "cloture"),
        ]
        apple_user = await db.users.find_one({"email": APPLE_EMAIL})
        creator_id = apple_user["id"] if apple_user else "system"
        for name, addr, status_v in apple_demos:
            await db.chantiers.insert_one({
                "id": str(uuid.uuid4()),
                "client_name": name,
                "address": addr,
                "status": status_v,
                "created_by": creator_id,
                "assigned_to": creator_id,
                "company_id": APPLE_COMPANY_ID,
                "created_at": now_iso,
            })
        logger.info("🍎 Seeded %d demo chantiers for Apple Review", len(apple_demos))

    # 🍎 Build 110 — Apple a explicitement demandé un compte NON-Administrateur
    # pour pouvoir tester les autres rôles (Guideline 2.1).
    # Création d'un 2e compte Technicien dans la MÊME company que l'admin
    # (apple-review-demo), pour montrer le RBAC en action.
    APPLE_TECH_EMAIL = "applereview-tech@mesurechassis.com"
    APPLE_TECH_PASSWORD = "MesureChassis2026"
    existing_tech = await db.users.find_one({"email": APPLE_TECH_EMAIL})
    fresh_tech_hash = hash_password(APPLE_TECH_PASSWORD)
    if existing_tech:
        await db.users.update_one(
            {"email": APPLE_TECH_EMAIL},
            {"$set": {
                "hashed_password": fresh_tech_hash,
                "status": "active",
                "email_verified_at": existing_tech.get("email_verified_at") or now_iso,
                "role": "technician",
                "company_id": APPLE_COMPANY_ID,
            }},
        )
        logger.info("🍎 Apple Review TECHNICIAN user re-synced")
    else:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Apple Review Technician",
            "email": APPLE_TECH_EMAIL,
            "role": "technician",
            "company_id": APPLE_COMPANY_ID,
            "hashed_password": fresh_tech_hash,
            "status": "active",
            "email_verified_at": now_iso,
            "created_at": now_iso,
        })
        logger.info("🍎 Apple Review TECHNICIAN user CREATED")

    # ────────────────────────────────────────────────────────────────
    # 🍎 Build 113 — Apple a demandé (Guideline 2.1) un compte demo
    # AVEC ABONNEMENT EXPIRÉ pour tester le flux paywall / renouvellement.
    # Création d'une 2e entreprise (apple-review-expired) avec un
    # subscription_status="expired" et subscription_expires_at dans le passé.
    # Sur iOS, cet utilisateur verra le PaywallScreen NEUTRE (pas de prix,
    # juste "contactez support@mesurechassis.fr").
    # ────────────────────────────────────────────────────────────────
    APPLE_EXPIRED_EMAIL = "applereview-expired@mesurechassis.com"
    APPLE_EXPIRED_PASSWORD = "MesureChassis2026"
    APPLE_EXPIRED_COMPANY_ID = "apple-review-expired"

    existing_expired_user = await db.users.find_one({"email": APPLE_EXPIRED_EMAIL})
    fresh_expired_hash = hash_password(APPLE_EXPIRED_PASSWORD)

    if existing_expired_user:
        await db.users.update_one(
            {"email": APPLE_EXPIRED_EMAIL},
            {"$set": {
                "hashed_password": fresh_expired_hash,
                "status": "active",
                "email_verified_at": existing_expired_user.get("email_verified_at") or now_iso,
                "role": "admin",
                "company_id": APPLE_EXPIRED_COMPANY_ID,
            }},
        )
        logger.info("🍎 Apple Review EXPIRED user re-synced")
    else:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "name": "Apple Review Expired",
            "email": APPLE_EXPIRED_EMAIL,
            "role": "admin",
            "company_id": APPLE_EXPIRED_COMPANY_ID,
            "hashed_password": fresh_expired_hash,
            "status": "active",
            "email_verified_at": now_iso,
            "created_at": now_iso,
        })
        logger.info("🍎 Apple Review EXPIRED user CREATED")

    # Compagnie expirée (subscription_status=expired, expires_at dans le passé)
    expired_company = await db.companies.find_one({"company_id": APPLE_EXPIRED_COMPANY_ID})
    thirty_days_ago = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).isoformat()
    ninety_days_ago = (
        datetime.now(timezone.utc) - timedelta(days=90)
    ).isoformat()

    expired_company_doc = {
        "company_id": APPLE_EXPIRED_COMPANY_ID,
        "name": "Apple Review Expired Demo Co.",
        "account_type": "entreprise",
        "preferred_plan": "entreprise",
        "plan": "entreprise",
        "subscription_status": "expired",
        "subscription_expires_at": thirty_days_ago,
        "trial_started_at": ninety_days_ago,
        "trial_expires_at": thirty_days_ago,
        "vat_number": "BE0000000098",
        "created_at": now_iso,
    }
    if expired_company:
        await db.companies.update_one(
            {"company_id": APPLE_EXPIRED_COMPANY_ID},
            {"$set": expired_company_doc},
        )
        logger.info("🍎 Apple Review EXPIRED company re-synced (status=expired, 30d ago)")
    else:
        await db.companies.insert_one(expired_company_doc)
        logger.info("🍎 Apple Review EXPIRED company CREATED (status=expired, 30d ago)")

    # 1 seul chantier démo (l'utilisateur ne pourra de toute façon rien faire à cause du paywall)
    existing_expired_chantiers = await db.chantiers.count_documents(
        {"company_id": APPLE_EXPIRED_COMPANY_ID}
    )
    if existing_expired_chantiers == 0:
        expired_user = await db.users.find_one({"email": APPLE_EXPIRED_EMAIL})
        expired_creator_id = expired_user["id"] if expired_user else "system"
        await db.chantiers.insert_one({
            "id": str(uuid.uuid4()),
            "client_name": "Démo — Compte expiré (bloqué)",
            "address": "1 rue Demo, 75001 Paris",
            "status": "devis_a_faire",
            "created_by": expired_creator_id,
            "assigned_to": expired_creator_id,
            "company_id": APPLE_EXPIRED_COMPANY_ID,
            "created_at": ninety_days_ago,
        })
        logger.info("🍎 Seeded 1 demo chantier for Apple Review EXPIRED account")