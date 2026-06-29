"""Seed demo users + run small data migrations on startup."""
from __future__ import annotations

import uuid
from datetime import timedelta

from core.config import logger
from core.db import db
from core.security import hash_password, now_utc

# Deterministic company_ids for demo seed users so re-runs keep the same
# tenant boundaries across container restarts.
COMPANY_ID_DEMO_SARL    = "11111111-1111-4111-8111-111111111111"
COMPANY_ID_MARC         = "22222222-2222-4222-8222-222222222222"
COMPANY_ID_EXPIRED_SARL = "33333333-3333-4333-8333-333333333333"

DEMO_USERS = [
    {
        "email": "admin@demo.fr", "full_name": "Marie Dubois",
        "company_id": COMPANY_ID_DEMO_SARL,
        "company_name": "Escaliers Demo SARL", "role": "admin",
        "password": "Demo1234!", "solo_mode": False,
        # offset_days: how many days ago the trial started (negative = future, positive = past).
        # 0 means trial starts NOW (full 90 days available).
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    {
        "email": "marc@mesureescalier.com", "full_name": "Marc Artisan",
        "company_id": COMPANY_ID_MARC,
        "company_name": "Marc Escaliers Indépendant", "role": "admin",
        "password": "Demo1234!", "solo_mode": True,
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    {
        "email": "sophie@mesureescaliee.com", "full_name": "Sophie Technicienne",
        "company_id": COMPANY_ID_DEMO_SARL,  # same tenant as Marie
        "company_name": "Escaliers Demo SARL", "role": "technicien",
        "password": "Demo1234!", "solo_mode": False,
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    # Compte de test PAYWALL — trial expiré il y a 10 jours
    {
        "email": "expired@demo.fr", "full_name": "Patrick Bloqué",
        "company_id": COMPANY_ID_EXPIRED_SARL,
        "company_name": "Escaliers Expiré SARL", "role": "admin",
        "password": "Demo1234!", "solo_mode": True,
        "trial_offset_days": 100,
        "subscription_active": False,
    },
]


async def _backfill_company_ids():
    """SEC-002 migration: ensure every existing user/project has a company_id.

    Strategy:
    - Group existing users by company_name. Each group gets ONE company_id
      (reused from any member that already has one, else freshly generated).
    - Backfill missing company_id on users.
    - Backfill missing company_id on projects via their creator/commercial.
    - Users without a company_name get a unique per-user company_id (their
      own private tenant) so they remain isolated from everyone else.
    """
    # 1) Group users by company_name → resolve a stable company_id per group.
    users_missing = await db.users.find(
        {"company_id": {"$in": [None, ""]}}, {"_id": 0, "id": 1, "company_name": 1},
    ).to_list(10_000)
    users_missing += await db.users.find(
        {"company_id": {"$exists": False}}, {"_id": 0, "id": 1, "company_name": 1},
    ).to_list(10_000)

    if not users_missing:
        return

    # Build company_name → company_id map by re-using existing assignments first.
    name_to_cid: dict[str, str] = {}
    async for u in db.users.find(
        {"company_id": {"$nin": [None, ""]}},
        {"_id": 0, "company_name": 1, "company_id": 1},
    ):
        cn = (u.get("company_name") or "").strip()
        cid = u.get("company_id")
        if cn and cid and cn not in name_to_cid:
            name_to_cid[cn] = cid

    seen_user_ids: set[str] = set()
    for u in users_missing:
        if u["id"] in seen_user_ids:
            continue
        seen_user_ids.add(u["id"])
        cn = (u.get("company_name") or "").strip()
        if cn:
            cid = name_to_cid.setdefault(cn, str(uuid.uuid4()))
        else:
            # No company_name → isolated private tenant
            cid = str(uuid.uuid4())
        await db.users.update_one({"id": u["id"]}, {"$set": {"company_id": cid}})
    logger.info("SEC-002 migration: assigned company_id to %d users", len(seen_user_ids))

    # 2) Backfill projects: derive company_id from the project's creator.
    projects_missing_cursor = db.projects.find(
        {"$or": [{"company_id": {"$exists": False}}, {"company_id": {"$in": [None, ""]}}]},
        {"_id": 0, "id": 1, "creator_id": 1, "commercial_id": 1, "company_name": 1},
    )
    n_proj = 0
    async for p in projects_missing_cursor:
        owner_id = p.get("creator_id") or p.get("commercial_id")
        cid = None
        if owner_id:
            owner = await db.users.find_one({"id": owner_id}, {"_id": 0, "company_id": 1})
            cid = (owner or {}).get("company_id")
        if not cid:
            cn = (p.get("company_name") or "").strip()
            cid = name_to_cid.get(cn) if cn else None
        if not cid:
            # Orphan project (no owner, no company) → bind to a sentinel tenant
            # that no real user belongs to → effectively quarantined.
            cid = "00000000-0000-4000-8000-000000000000"
        await db.projects.update_one({"id": p["id"]}, {"$set": {"company_id": cid}})
        n_proj += 1
    if n_proj:
        logger.info("SEC-002 migration: assigned company_id to %d projects", n_proj)


async def seed_demo_users():
    now = now_utc()
    for u in DEMO_USERS:
        trial_start = now - timedelta(days=u["trial_offset_days"])
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            updates = {}
            if existing.get("role") == "commercial":
                updates["role"] = u["role"]
            if "solo_mode" not in existing:
                updates["solo_mode"] = u["solo_mode"]
            # Backfill trial_start_date if missing (existing accounts)
            if not existing.get("trial_start_date"):
                updates["trial_start_date"] = trial_start
            if "subscription_active" not in existing:
                updates["subscription_active"] = u["subscription_active"]
            # SEC-002: ensure demo users have a stable company_id
            if not existing.get("company_id"):
                updates["company_id"] = u["company_id"]
            if updates:
                await db.users.update_one({"id": existing["id"]}, {"$set": updates})
                logger.info("Migrated demo user %s → %s", u["email"], list(updates.keys()))
            continue
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "full_name": u["full_name"],
            "company_id": u["company_id"],
            "company_name": u["company_name"],
            "role": u["role"],
            "solo_mode": u["solo_mode"],
            "password_hash": hash_password(u["password"]),
            "created_at": now,
            "trial_start_date": trial_start,
            "subscription_active": u["subscription_active"],
        })
        logger.info("Seeded demo user %s (%s, solo=%s, trial_offset=%dd)",
                    u["email"], u["role"], u["solo_mode"], u["trial_offset_days"])

    res = await db.users.update_many({"role": "commercial"}, {"$set": {"role": "technicien"}})
    if res.modified_count:
        logger.info("Migrated %d commercial → technicien", res.modified_count)
    await db.users.update_many({"solo_mode": {"$exists": False}},
                               {"$set": {"solo_mode": False}})
    # Generic migration: set trial_start_date = created_at for users missing it
    async for u in db.users.find({"trial_start_date": {"$exists": False}}):
        await db.users.update_one(
            {"id": u["id"]},
            {"$set": {
                "trial_start_date": u.get("created_at") or now_utc(),
                "subscription_active": False,
            }},
        )

    # SEC-002 backfill — runs every startup, idempotent
    await _backfill_company_ids()
