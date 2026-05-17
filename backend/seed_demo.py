"""
Seed script for MesureChâssis demo data.
Generates 8 realistic chantiers across all statuses, with varied
mesures (standard rectangular, renovation mode with out-of-level
alerts, trapeze, porte, coulissant), plus site photos with captions.

Usage: python3 /app/backend/seed_demo.py
"""
import asyncio
import base64
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import uuid

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ.get("DB_NAME", "mesure_chassis")


# 1×1 PNG transparent (small, for thumbnails)
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8A"
    "AAAASUVORK5CYII="
)
SITE_PHOTO_URI = f"data:image/png;base64,{TINY_PNG_B64}"


CLIENTS = [
    {"first": "Marc",       "last": "Dubois",   "addr": "12 rue des Lilas",        "cp": "69003", "city": "Lyon"},
    {"first": "Sophie",     "last": "Laurent",  "addr": "5 avenue de la Gare",     "cp": "31000", "city": "Toulouse"},
    {"first": "Pierre",     "last": "Martin",   "addr": "44 boulevard Victor Hugo","cp": "13008", "city": "Marseille"},
    {"first": "Émilie",     "last": "Rousseau", "addr": "8 allée des Cèdres",      "cp": "44000", "city": "Nantes"},
    {"first": "Antoine",    "last": "Lefèvre",  "addr": "17 quai des Bateliers",   "cp": "67000", "city": "Strasbourg"},
    {"first": "Camille",    "last": "Bernard",  "addr": "3 impasse du Vieux Puits","cp": "33000", "city": "Bordeaux"},
    {"first": "Julien",     "last": "Petit",    "addr": "29 rue de la République", "cp": "59000", "city": "Lille"},
    {"first": "Aurélie",    "last": "Moreau",   "addr": "61 chemin des Vignes",    "cp": "21000", "city": "Dijon"},
]

# Pipeline 4-étapes :
#   Étape 1 – À mesurer (gris) : devis_a_faire (équivalent a_mesurer)
#   Étape 2 – À vérifier par le technicien (orange) : technique_a_valider
#   Étape 3 – En fabrication (bleu) : en_fabrication
#   Étape 4 – Terminé / Livré (vert) : cloture
STATUS_PLAN = [
    # 2 chantiers en étape 1 (À mesurer 🩶)
    "devis_a_faire",        # Marc Dubois
    "devis_a_faire",        # Sophie Laurent
    # 2 chantiers en étape 2 (À vérifier par le technicien 🟠)
    "technique_a_valider",  # Pierre Martin
    "technique_a_valider",  # Émilie Rousseau
    # 2 chantiers en étape 3 (En fabrication 🔵)
    "en_fabrication",       # Antoine Lefèvre
    "en_fabrication",       # Camille Bernard
    # 2 chantiers en étape 4 (Terminé / Livré 🟢)
    "cloture",              # Julien Petit
    "cloture",              # Aurélie Moreau
]

OPENING_LABELS = ["Salon", "Chambre 1", "Cuisine", "SDB", "Bureau", "Entrée", "Couloir"]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Fetch users to assign work
    admin = await db.users.find_one({"email": "admin@mesurechassis.fr"})
    commercial = await db.users.find_one({"email": "commercial@mesurechassis.fr"})
    if not admin:
        print("❌ Admin user missing. Run server first to seed defaults.")
        sys.exit(1)
    company_id = admin.get("company_id", "default")

    # Clean previous demo (preserve test artisan ones we made earlier? we wipe all)
    print(f"🧹 Cleaning previous chantiers/mesures for company {company_id}...")
    await db.chantiers.delete_many({"company_id": company_id})
    await db.mesures.delete_many({})

    now = datetime.now(timezone.utc)

    for idx, (client_data, status) in enumerate(zip(CLIENTS, STATUS_PLAN)):
        ch_id = str(uuid.uuid4())
        created_at = (now - timedelta(days=random.randint(1, 30))).isoformat()
        appointment = (now + timedelta(days=random.randint(2, 25), hours=random.randint(8, 16))).isoformat() \
            if status in ("devis_a_faire", "technique_a_valider") else None
        assigned_to = commercial["id"] if (status != "cloture" and commercial) else None

        # Up to 2 site photos for ~30% of chantiers (anti-litige proof)
        site_photos = []
        if random.random() < 0.4:
            site_photos = [
                {"uri": SITE_PHOTO_URI, "caption": "Fissure linteau existante côté droit"},
            ]
            if random.random() < 0.5:
                site_photos.append({"uri": SITE_PHOTO_URI, "caption": "Trace humidité bas baie salon"})

        chantier_doc = {
            "id": ch_id,
            "client_name": f"{client_data['last']} {client_data['first']}",
            "first_name": client_data["first"],
            "last_name": client_data["last"],
            "address": client_data["addr"],
            "postal_code": client_data["cp"],
            "city": client_data["city"],
            "status": status,
            "created_by": admin["id"],
            "assigned_to": assigned_to,
            "appointment_at": appointment,
            "notes": f"Test demo — RDV terrain {'à programmer' if status == 'devis_a_faire' else 'effectué'}.",
            "company_id": company_id,
            "client_signature": None,
            "signed_at": None,
            "created_at": created_at,
            "site_photos": site_photos,
        }
        await db.chantiers.insert_one(chantier_doc)

        # Add 0-4 mesures depending on status
        if status == "devis_a_faire":
            n_mesures = 0  # not yet measured
        elif status == "technique_a_valider":
            n_mesures = random.randint(2, 4)
        else:
            n_mesures = random.randint(3, 5)

        for m_idx in range(n_mesures):
            label = random.choice(OPENING_LABELS)
            block_type = random.choices(
                ["standard", "coulissant", "porte", "trapeze"],
                weights=[55, 20, 15, 10],
                k=1,
            )[0]

            mesure: dict = {
                "id": str(uuid.uuid4()),
                "chantier_id": ch_id,
                "label": label,
                "block_type": block_type,
                "bloc_thickness": random.choice([200, 250, 300]),
                "wall_type": random.choice(["ite", "iti", "brique_parement", "crepi_simple"]),
                "insulation_thickness": random.choice([80, 100, 120, 140]),
                "finish_outer": random.choice([8, 10, 12]),
                "finish_inner": random.choice([10, 13, 15]),
                "created_at": (now - timedelta(days=random.randint(0, 20))).isoformat(),
                "alerts": [],
                "options": {},
                "photo_url": None,
                "slope_angle_deg": None,
            }

            if block_type == "trapeze":
                w = random.randint(1100, 2400)
                hl = random.randint(1500, 2400)
                # Trapeze: heights asymmetric by design (real architecture)
                hr = hl + random.choice([-300, -200, -150, 150, 200])
                mesure.update({
                    "bay_width": float(w),
                    "height_left": float(hl),
                    "height_right": float(hr),
                })
            else:
                # 40% chance of renovation mode (to showcase the alert feature)
                if random.random() < 0.4:
                    wt = random.randint(900, 2200)
                    # Inject deliberate deviations >10mm in ~60% to demo the alert
                    if random.random() < 0.6:
                        wb = wt + random.choice([-25, -18, -15, 12, 18, 22, 30])
                        hl_d = random.randint(1800, 2400)
                        hr_d = hl_d + random.choice([-22, -15, 14, 19, 28])
                    else:
                        wb = wt + random.choice([-3, 0, 4])
                        hl_d = random.randint(1800, 2400)
                        hr_d = hl_d + random.choice([-2, 0, 3])
                    mesure.update({
                        "renovation_mode": True,
                        "width_top": float(wt),
                        "width_bottom": float(wb),
                        "height_left": float(hl_d),
                        "height_right": float(hr_d),
                        # Provide averaged bay_width/bay_height for back-compat workshop
                        "bay_width": float(round((wt + wb) / 2)),
                        "bay_height": float(round((hl_d + hr_d) / 2)),
                    })
                else:
                    # Standard rectangular
                    w = random.randint(800, 2400)
                    h = random.randint(1100, 2500)
                    d = round((w * w + h * h) ** 0.5)
                    mesure.update({
                        "renovation_mode": False,
                        "bay_width": float(w),
                        "bay_height": float(h),
                        "bay_diagonal_1": float(d),
                        "bay_diagonal_2": float(d),
                        "diag_1_verified": True,
                        "diag_2_verified": True,
                    })

                if block_type in ("porte", "coulissant"):
                    mesure["floor_reserve"] = float(random.choice([25, 30, 40, 50]))

            await db.mesures.insert_one(mesure)

        print(f"✅ {client_data['last']:10s} ({status}, {n_mesures} mesures, {len(site_photos)} site photos)")

    # Make sure subscription is active (essai de 90 jours)
    from db import TRIAL_DAYS
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {
            "subscription_status": "active",
            "subscription_expires_at": (now + timedelta(days=TRIAL_DAYS)).isoformat(),
            "artisan_mode": True,  # keep current artisan state ON
        }},
        upsert=True,
    )
    print(f"\n🎯 Subscription active + artisan_mode ON for company '{company_id}'.")
    print(f"📊 Total chantiers: {await db.chantiers.count_documents({'company_id': company_id})}")
    print(f"📐 Total mesures: {await db.mesures.count_documents({})}")


if __name__ == "__main__":
    asyncio.run(main())
