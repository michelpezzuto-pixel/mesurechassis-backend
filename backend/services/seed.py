"""Seed demo users + run small data migrations on startup."""
from __future__ import annotations

import uuid
from datetime import timedelta

from core.config import logger
from core.db import db
from core.security import hash_password, now_utc

DEMO_USERS = [
    {
        "email": "admin@demo.fr", "full_name": "Marie Dubois",
        "company_name": "Escaliers Demo SARL", "role": "admin",
        "password": "Demo1234!", "solo_mode": False,
        # offset_days: how many days ago the trial started (negative = future, positive = past).
        # 0 means trial starts NOW (full 90 days available).
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    {
        "email": "marc@mesureescalier.com", "full_name": "Marc Artisan",
        "company_name": "Marc Escaliers Indépendant", "role": "admin",
        "password": "Demo1234!", "solo_mode": True,
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    {
        "email": "sophie@mesureescaliee.com", "full_name": "Sophie Technicienne",
        "company_name": "Escaliers Demo SARL", "role": "technicien",
        "password": "Demo1234!", "solo_mode": False,
        "trial_offset_days": 0,
        "subscription_active": False,
    },
    # Compte de test PAYWALL — trial expiré il y a 10 jours
    {
        "email": "expired@demo.fr", "full_name": "Patrick Bloqué",
        "company_name": "Escaliers Expiré SARL", "role": "admin",
        "password": "Demo1234!", "solo_mode": True,
        "trial_offset_days": 100,
        "subscription_active": False,
    },
]


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
            if updates:
                await db.users.update_one({"id": existing["id"]}, {"$set": updates})
                logger.info("Migrated demo user %s → %s", u["email"], list(updates.keys()))
            continue
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "full_name": u["full_name"],
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
