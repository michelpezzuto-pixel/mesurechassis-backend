"""
🎬 CRÉATION DES 4 COMPTES DÉMO sur Railway (base production iOS)

Objectif : permettre à Michel de faire des démos avec ses collègues en
montrant les 4 rôles (Admin / Commercial / Technicien / Artisan solo).

Tous les comptes utilisent le mot de passe : Demo2026!

Base cible : https://capable-gratitude-production-db51.up.railway.app
"""
import asyncio
import httpx

RAILWAY_BASE = "https://capable-gratitude-production-db51.up.railway.app"
PASSWORD = "Demo2026!"

# Tous les comptes "entreprise" (admin/commercial/tech) partagent la
# même company_id → ils forment une équipe.
COMPANY_ID_ENTREPRISE = "demo-menuiserie-michel"
COMPANY_ID_ARTISAN = "demo-artisan-solo"

ACCOUNTS = [
    {
        "name": "Démo Admin",
        "email": "demo.admin@mesurechassis.com",
        "password": PASSWORD,
        "role": "admin",
        "company_id": COMPANY_ID_ENTREPRISE,
    },
    {
        "name": "Démo Commercial",
        "email": "demo.commercial@mesurechassis.com",
        "password": PASSWORD,
        "role": "commercial",
        "company_id": COMPANY_ID_ENTREPRISE,
    },
    {
        "name": "Démo Technicien",
        "email": "demo.tech@mesurechassis.com",
        "password": PASSWORD,
        "role": "technician",
        "company_id": COMPANY_ID_ENTREPRISE,
    },
    {
        "name": "Démo Artisan Solo",
        "email": "demo.artisan@mesurechassis.com",
        "password": PASSWORD,
        "role": "admin",  # Artisan solo est admin de sa propre entreprise
        "company_id": COMPANY_ID_ARTISAN,
    },
]


async def register_one(client: httpx.AsyncClient, acc: dict) -> dict:
    """Crée le compte via /api/auth/register mode legacy (avec role)."""
    payload = {
        "name": acc["name"],
        "email": acc["email"],
        "password": acc["password"],
        "role": acc["role"],
        "company_id": acc["company_id"],
    }
    try:
        r = await client.post(
            f"{RAILWAY_BASE}/api/auth/register",
            json=payload,
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "ok": True,
                "email": acc["email"],
                "role": acc["role"],
                "company_id": acc["company_id"],
                "user_id": data.get("user", {}).get("id"),
                "token": data.get("access_token"),
            }
        elif r.status_code == 400 and "déjà enregistré" in r.text:
            return {
                "ok": True,
                "email": acc["email"],
                "role": acc["role"],
                "company_id": acc["company_id"],
                "note": "Déjà existant (on tente le login pour confirmer)",
            }
        else:
            return {
                "ok": False,
                "email": acc["email"],
                "http": r.status_code,
                "error": r.text[:200],
            }
    except Exception as e:
        return {"ok": False, "email": acc["email"], "error": str(e)}


async def login_one(client: httpx.AsyncClient, email: str) -> dict:
    """Vérifie que le compte est login-able avec le password fixé."""
    try:
        r = await client.post(
            f"{RAILWAY_BASE}/api/auth/login",
            json={"email": email, "password": PASSWORD},
            timeout=15,
        )
        if r.status_code == 200:
            d = r.json()
            return {
                "login_ok": True,
                "user_id": d.get("user", {}).get("id"),
                "role": d.get("user", {}).get("role"),
                "company_id": d.get("user", {}).get("company_id"),
                "status": d.get("user", {}).get("status"),
            }
        return {"login_ok": False, "http": r.status_code, "error": r.text[:200]}
    except Exception as e:
        return {"login_ok": False, "error": str(e)}


async def main():
    print("🎬 CRÉATION DES 4 COMPTES DÉMO sur Railway (prod iOS)")
    print(f"🎯 Cible : {RAILWAY_BASE}")
    print(f"🔑 Mot de passe commun : {PASSWORD}\n")

    async with httpx.AsyncClient() as client:
        # Phase 1 — création
        print("─" * 70)
        print("PHASE 1 — Création des comptes")
        print("─" * 70)
        creation_results = []
        for acc in ACCOUNTS:
            res = await register_one(client, acc)
            creation_results.append(res)
            if res.get("ok"):
                if res.get("note"):
                    print(f"⚠️  {acc['email']:45s} → {res['note']}")
                else:
                    print(f"✅ {acc['email']:45s} → créé ({acc['role']}, {acc['company_id']})")
            else:
                print(f"❌ {acc['email']:45s} → HTTP {res.get('http')} — {res.get('error')}")

        # Phase 2 — vérif login pour chaque
        print("\n" + "─" * 70)
        print("PHASE 2 — Vérification LOGIN sur Railway")
        print("─" * 70)
        for acc in ACCOUNTS:
            check = await login_one(client, acc["email"])
            if check.get("login_ok"):
                print(f"✅ {acc['email']:45s} → login OK ({check['role']} · status={check.get('status')})")
            else:
                print(f"❌ {acc['email']:45s} → login KO — {check.get('error')}")

    print("\n" + "=" * 70)
    print("📋 RÉCAP POUR MICHEL — À COPIER DANS UN NOTES DE DÉMO")
    print("=" * 70)
    print(f"Mot de passe pour TOUS : {PASSWORD}\n")
    print("👥 ÉQUIPE (même entreprise) — démo collaboration :")
    print("   • demo.admin@mesurechassis.com       (Admin patron)")
    print("   • demo.commercial@mesurechassis.com  (Commercial)")
    print("   • demo.tech@mesurechassis.com        (Technicien poseur)")
    print("\n🔧 ARTISAN SOLO (entreprise séparée) :")
    print("   • demo.artisan@mesurechassis.com     (Artisan/patron solo)")


if __name__ == "__main__":
    asyncio.run(main())
