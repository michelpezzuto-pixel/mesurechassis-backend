"""Seeding initial des utilisateurs et chantiers de démo."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db import db, logger
from deps import hash_password

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
    """Seed idempotent exécuté au démarrage du serveur."""
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
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        user_ids[u["role"]] = uid
        logger.info("Seeded user %s", u["email"])

    if await db.chantiers.count_documents({}) == 0:
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
        logger.info("Seeded %d demo chantiers", len(demos))

    # Backfill company_id sur les anciens documents
    await db.chantiers.update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": "default"}},
    )
    await db.feedbacks.update_many(
        {"company_id": {"$exists": False}},
        {"$set": {"company_id": "default"}},
    )
