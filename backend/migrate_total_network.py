"""🚀 Migration Priorité 5 — Création réseau « Total » + auto-tag.

Exécution manuelle (une seule fois) :
    docker exec -it <backend> python /app/backend/migrate_total_network.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import db  # noqa: E402


NETWORK_ID = "total-be"
NETWORK_NAME = "Total"
NETWORK_COUNTRY = "BE"
# Logo officiel Total (SVG hébergé Wikipedia commons — libre)
NETWORK_LOGO = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    "b/b0/Logo_TotalEnergies.svg/512px-Logo_TotalEnergies.svg.png"
)

TEST_USER_EMAILS = ["artisan@mesurechassis.fr"]  # comptes de test à rattacher


async def main() -> None:
    now = datetime.now(timezone.utc).isoformat()

    # ═════════ 1. Créer le réseau Total-BE ═════════
    existing_net = await db.cafe_networks.find_one({"id": NETWORK_ID})
    if existing_net:
        print(f"✅ Réseau '{NETWORK_ID}' existe déjà")
    else:
        await db.cafe_networks.insert_one(
            {
                "id": NETWORK_ID,
                "name": NETWORK_NAME,
                "country": NETWORK_COUNTRY,
                "logo_url": NETWORK_LOGO,
                "active": True,
                "created_at": now,
                "created_by": "migration",
            }
        )
        print(f"✅ Réseau '{NETWORK_ID}' créé")

    # ═════════ 2. Rattacher station 'Total Wavre TEST' au réseau ═════════
    r = await db.cafe_stations.update_many(
        {"network_id": {"$in": [None, ""]}, "name": {"$regex": "^Total", "$options": "i"}},
        {"$set": {"network_id": NETWORK_ID}},
    )
    print(f"✅ {r.modified_count} station(s) existante(s) rattachée(s) à '{NETWORK_ID}'")

    # Créer 'Total Wavre TEST' si aucune Total n'existe encore
    if await db.cafe_stations.count_documents({"network_id": NETWORK_ID}) == 0:
        await db.cafe_stations.insert_one(
            {
                "id": str(uuid.uuid4()),
                "name": "Total Wavre TEST",
                "city": "Wavre",
                "address": "Chaussée de Bruxelles 105, 1300 Wavre",
                "pin": "1234",
                "monthly_objective": 20,
                "network_id": NETWORK_ID,
                "contact_name": "",
                "contact_phone": "",
                "contact_email": "",
                "coffee_price": 2.50,
                "active": True,
                "created_at": now,
                "created_by": "migration",
            }
        )
        print("✅ Station 'Total Wavre TEST' créée (PIN 1234)")

    # ═════════ 3. Auto-tag comptes existants (backfill) ═════════
    r_users = await db.users.update_many(
        {
            "campaign_network_id": {"$in": [None, ""]},
            "campaign_station_id": {"$in": [None, ""]},
            "status": {"$ne": "deleted"},
        },
        {"$set": {"campaign_network_id": NETWORK_ID}},
    )
    print(f"✅ {r_users.modified_count} utilisateur(s) rétroactivement tagué(s) sur '{NETWORK_ID}'")

    # ═════════ 4. Tag explicite des comptes de test ═════════
    for email in TEST_USER_EMAILS:
        r_test = await db.users.update_one(
            {"email": email},
            {"$set": {"campaign_network_id": NETWORK_ID}},
        )
        if r_test.matched_count:
            print(f"✅ Compte {email} rattaché à '{NETWORK_ID}'")

    # ═════════ 5. Récap final ═════════
    stations = await db.cafe_stations.count_documents({"network_id": NETWORK_ID, "active": True})
    users = await db.users.count_documents({"campaign_network_id": NETWORK_ID})
    print("\n🎯 Réseau Total-BE prêt :")
    print(f"    - {stations} station(s) participante(s)")
    print(f"    - {users} utilisateur(s) tagué(s)")
    print("\n💡 Ajoute cette ligne au .env backend pour auto-tagger les futurs signups :")
    print(f"    ACTIVE_CAMPAIGN_NETWORK={NETWORK_ID}")


if __name__ == "__main__":
    asyncio.run(main())
