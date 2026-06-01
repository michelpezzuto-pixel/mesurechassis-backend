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
from datetime import datetime, timezone

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
        logger.info("Seeded %d demo chantiers", len(demos))
