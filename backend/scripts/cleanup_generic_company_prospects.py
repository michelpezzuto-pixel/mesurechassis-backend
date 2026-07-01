"""
🧹 Nettoyage des prospects avec un company field qui est en fait un domaine email générique.

Avant :
  company = "Gmail", "Free", "Orange", "Hotmail", ...   ← domaine email, PAS une société
Après :
  company = ""                                          ← vide (l'UI affichera l'email)

Utilisation : python -m scripts.cleanup_generic_company_prospects
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")

# Domaines email génériques (matching case-insensitive)
GENERIC_DOMAINS = {
    "gmail", "googlemail",
    "yahoo", "yahoo.fr", "yahoo.com",
    "hotmail", "hotmail.fr", "hotmail.com",
    "outlook", "outlook.fr", "outlook.com",
    "live", "live.fr", "live.com",
    "orange", "orange.fr",
    "free", "free.fr",
    "wanadoo", "wanadoo.fr",
    "sfr", "sfr.fr",
    "laposte", "laposte.net",
    "bbox", "bouygtel",
    "aol", "aol.fr", "aol.com",
    "icloud", "me.com", "mac.com",
    "protonmail", "proton.me",
    "voila", "voila.fr",
    "numericable", "neuf.fr",
    "skynet", "skynet.be",
    "telenet", "telenet.be",
    "belgacom", "belgacom.be", "proximus.be",
    "gmx", "gmx.fr", "gmx.com",
    "mail", "mail.com", "mail.ru",
}


async def main():
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("❌ MONGO_URL introuvable dans .env")
        return

    client = AsyncIOMotorClient(mongo_url)
    db_name = os.getenv("DB_NAME", "test_database")
    db = client[db_name]

    print(f"📊 Base : {db_name}")
    print("🔎 Recherche des prospects avec un company field générique...\n")

    # Récupère tous les prospects
    all_prospects = await db.prospects.find({}, {"_id": 0, "id": 1, "email": 1, "company": 1}).to_list(None)
    print(f"   → {len(all_prospects)} prospects au total")

    # Filtre ceux dont le company est un domaine générique
    to_fix = []
    for p in all_prospects:
        c = (p.get("company") or "").strip()
        if not c:
            continue
        if c.lower() in GENERIC_DOMAINS:
            to_fix.append(p)

    print(f"   → {len(to_fix)} prospects à corriger\n")

    if not to_fix:
        print("✅ Aucun prospect à nettoyer, tout est propre !")
        return

    # Aperçu (max 15)
    print("📋 Aperçu :")
    for p in to_fix[:15]:
        print(f"   • {p['email']}  (company incorrect : « {p['company']} » → vidé)")
    if len(to_fix) > 15:
        print(f"   ... et {len(to_fix) - 15} autres")

    # Confirmation via env var pour éviter accident
    if os.getenv("CONFIRM_CLEANUP") != "yes":
        print(
            "\n⚠️  Aperçu seulement. Pour appliquer, relancez avec :"
            "\n   CONFIRM_CLEANUP=yes python -m scripts.cleanup_generic_company_prospects"
        )
        return

    # Mise à jour : company = ""
    ids = [p["id"] for p in to_fix]
    result = await db.prospects.update_many(
        {"id": {"$in": ids}},
        {"$set": {"company": ""}},
    )
    print(f"\n✅ {result.modified_count} prospects nettoyés dans la DB.")


if __name__ == "__main__":
    asyncio.run(main())
