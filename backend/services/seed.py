"""Seed demo users + run small data migrations on startup."""
from __future__ import annotations

import uuid

from core.config import logger
from core.db import db
from core.security import hash_password, now_utc

DEMO_USERS = [
    {
        "email": "admin@demo.fr", "full_name": "Marie Dubois",
        "company_name": "Escaliers Demo SARL", "role": "admin",
        "password": "Demo1234!", "solo_mode": False,
    },
    {
        "email": "marc@mesureescalier.com", "full_name": "Marc Artisan",
        "company_name": "Marc Escaliers Indépendant", "role": "admin",
        "password": "Demo1234!", "solo_mode": True,
    },
    {
        "email": "sophie@mesureescaliee.com", "full_name": "Sophie Technicienne",
        "company_name": "Escaliers Demo SARL", "role": "technicien",
        "password": "Demo1234!", "solo_mode": False,
    },
]


async def seed_demo_users():
    for u in DEMO_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            updates = {}
            if existing.get("role") == "commercial":
                updates["role"] = u["role"]
            if "solo_mode" not in existing:
                updates["solo_mode"] = u["solo_mode"]
            if updates:
                await db.users.update_one({"id": existing["id"]}, {"$set": updates})
                logger.info("Migrated demo user %s → %s", u["email"], updates)
            continue
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "full_name": u["full_name"],
            "company_name": u["company_name"],
            "role": u["role"],
            "solo_mode": u["solo_mode"],
            "password_hash": hash_password(u["password"]),
            "created_at": now_utc(),
        })
        logger.info("Seeded demo user %s (%s, solo=%s)",
                    u["email"], u["role"], u["solo_mode"])

    res = await db.users.update_many({"role": "commercial"}, {"$set": {"role": "technicien"}})
    if res.modified_count:
        logger.info("Migrated %d commercial → technicien", res.modified_count)
    await db.users.update_many({"solo_mode": {"$exists": False}},
                               {"$set": {"solo_mode": False}})
