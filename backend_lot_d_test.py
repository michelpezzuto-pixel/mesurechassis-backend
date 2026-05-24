"""Lot D — Onboarding différencié Artisan vs Entreprise.

Backend tests via the public preview URL.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Optional

import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Backend URL — utilise l'env Expo (route ingress Kubernetes vers /api)
BASE = "https://window-field-app.preview.emergentagent.com"
API = f"{BASE}/api"

# Mongo direct (cleanup)
load_dotenv("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN_EMAIL = "admin@mesurechassis.fr"
ADMIN_PASSWORD = "admin123"

PASS = []
FAIL = []


def _log(ok: bool, label: str, detail: str = ""):
    rec = (label, detail)
    if ok:
        PASS.append(rec)
        print(f"  ✅ {label} {detail}")
    else:
        FAIL.append(rec)
        print(f"  ❌ {label} {detail}")


def post(path: str, json: dict, token: Optional[str] = None, timeout: int = 30):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(f"{API}{path}", json=json, headers=headers, timeout=timeout)


def get(path: str, token: Optional[str] = None, timeout: int = 30):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.get(f"{API}{path}", headers=headers, timeout=timeout)


def login(email: str, password: str) -> str:
    r = post("/auth/login", {"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


async def db_lookup_company_for_email(email: str) -> Optional[dict]:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    user = await db.users.find_one({"email": email.lower()})
    if not user:
        client.close()
        return None
    company = await db.companies.find_one({"company_id": user["company_id"]})
    client.close()
    return company


async def db_count_users_with_prefix(prefix: str) -> int:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    n = await db.users.count_documents({"email": {"$regex": f"^{prefix}"}})
    client.close()
    return n


async def cleanup_lot_d():
    """Supprime users + companies de test lotd_*@mesurechassis.fr."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    test_users = await db.users.find(
        {"email": {"$regex": r"^lotd_"}}
    ).to_list(1000)
    user_ids = [u["id"] for u in test_users]
    company_ids = list({u["company_id"] for u in test_users if u.get("company_id") not in (None, "default")})
    res_u = await db.users.delete_many({"email": {"$regex": r"^lotd_"}})
    res_c = await db.companies.delete_many({"company_id": {"$in": company_ids}}) if company_ids else None
    # nettoie aussi email_verifications & chantiers de ces user_ids
    await db.email_verifications.delete_many({"user_id": {"$in": user_ids}})
    await db.chantiers.delete_many({"created_by": {"$in": user_ids}})
    client.close()
    return {
        "users_deleted": res_u.deleted_count,
        "companies_deleted": res_c.deleted_count if res_c else 0,
        "user_ids": user_ids,
        "company_ids": company_ids,
    }


def main() -> int:
    print(f"=== Lot D Onboarding tests — base={API} ===\n")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # ---------------------------------------------------------------
    # TEST 1 — Inscription Artisan
    # ---------------------------------------------------------------
    print("[T1] Inscription Artisan (sans company_name)")
    artisan_email = f"lotd_artisan_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    artisan_name = "Jean Artisan"
    r = post("/auth/register", {
        "name": artisan_name,
        "email": artisan_email,
        "password": "TestArt1234!",
        "account_type": "artisan",
        # pas de company_name → fallback = name
    })
    _log(r.status_code == 200, "T1.1 register artisan 200",
         f"got={r.status_code} body={r.text[:200]}")
    vlink = None
    if r.status_code == 200:
        body = r.json()
        vlink = body.get("verification_link")
        _log(bool(vlink), "T1.2 verification_link présent", f"link={vlink}")
        _log(body.get("user", {}).get("role") == "admin",
             "T1.3 role=admin", f"role={body.get('user', {}).get('role')}")

    # Check DB
    company = loop.run_until_complete(db_lookup_company_for_email(artisan_email))
    _log(company is not None, "T1.4 company doc exists",
         f"keys={list(company.keys()) if company else None}")
    if company:
        _log(company.get("account_type") == "artisan",
             "T1.5 company.account_type=artisan",
             f"got={company.get('account_type')}")
        _log(company.get("artisan_mode") is True,
             "T1.6 company.artisan_mode=True",
             f"got={company.get('artisan_mode')}")
        _log(company.get("name") == artisan_name,
             "T1.7 company.name=user_name (fallback)",
             f"got={company.get('name')!r}")

    # Verify token → access_token
    artisan_token = None
    if vlink:
        # /verify?token=XXX
        token_val = vlink.split("token=", 1)[-1]
        rv = post("/auth/verify", {"token": token_val})
        _log(rv.status_code == 200, "T1.8 /auth/verify 200",
             f"got={rv.status_code} body={rv.text[:160]}")
        if rv.status_code == 200:
            artisan_token = rv.json().get("access_token")
            _log(bool(artisan_token), "T1.9 access_token returned",
                 f"present={bool(artisan_token)}")

    # GET /company/profile
    if artisan_token:
        rp = get("/company/profile", token=artisan_token)
        _log(rp.status_code == 200, "T1.10 GET /company/profile 200",
             f"got={rp.status_code}")
        if rp.status_code == 200:
            prof = rp.json()
            _log(prof.get("account_type") == "artisan",
                 "T1.11 profile.account_type=artisan", f"got={prof.get('account_type')}")
            _log(prof.get("artisan_mode") is True,
                 "T1.12 profile.artisan_mode=True", f"got={prof.get('artisan_mode')}")
            _log(prof.get("beta_mode") is True,
                 "T1.13 profile.beta_mode=True (BETA actif)", f"got={prof.get('beta_mode')}")
            _log(prof.get("plan") == "pro",
                 "T1.14 profile.plan=pro", f"got={prof.get('plan')}")

    # ---------------------------------------------------------------
    # TEST 2 — Inscription Entreprise valide
    # ---------------------------------------------------------------
    print("\n[T2] Inscription Entreprise valide")
    ent_email = f"lotd_ent_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = post("/auth/register", {
        "name": "Marc Patron",
        "email": ent_email,
        "password": "TestEnt1234!",
        "account_type": "entreprise",
        "company_name": "Menuiseries TestSAS",
    })
    _log(r.status_code == 200, "T2.1 register entreprise 200",
         f"got={r.status_code}")
    vlink2 = r.json().get("verification_link") if r.status_code == 200 else None
    _log(bool(vlink2), "T2.2 verification_link présent", f"link={vlink2}")
    company2 = loop.run_until_complete(db_lookup_company_for_email(ent_email))
    if company2:
        _log(company2.get("account_type") == "entreprise",
             "T2.3 company.account_type=entreprise",
             f"got={company2.get('account_type')}")
        _log(company2.get("artisan_mode") is False,
             "T2.4 company.artisan_mode=False",
             f"got={company2.get('artisan_mode')}")
        _log(company2.get("name") == "Menuiseries TestSAS",
             "T2.5 company.name=Menuiseries TestSAS",
             f"got={company2.get('name')!r}")

    ent_token = None
    if vlink2:
        token_val = vlink2.split("token=", 1)[-1]
        rv = post("/auth/verify", {"token": token_val})
        _log(rv.status_code == 200, "T2.6 verify 200", f"got={rv.status_code}")
        if rv.status_code == 200:
            ent_token = rv.json().get("access_token")
    if ent_token:
        rp = get("/company/profile", token=ent_token)
        if rp.status_code == 200:
            prof = rp.json()
            _log(prof.get("account_type") == "entreprise",
                 "T2.7 profile.account_type=entreprise", f"got={prof.get('account_type')}")
            _log(prof.get("artisan_mode") is False,
                 "T2.8 profile.artisan_mode=False", f"got={prof.get('artisan_mode')}")

    # ---------------------------------------------------------------
    # TEST 3 — Entreprise SANS company_name → 400
    # ---------------------------------------------------------------
    print("\n[T3] Entreprise sans company_name → 400")
    nocomp_email = f"lotd_nocomp_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = post("/auth/register", {
        "name": "X",
        "email": nocomp_email,
        "password": "X1234!",
        "account_type": "entreprise",
    })
    _log(r.status_code == 400, "T3.1 status=400", f"got={r.status_code} body={r.text[:200]}")
    if r.status_code == 400:
        detail = r.json().get("detail", "")
        _log("nom de l'entreprise" in detail.lower() or "entreprise" in detail.lower(),
             "T3.2 detail mentionne entreprise",
             f"detail={detail!r}")
    # vérifie qu'aucun user n'a été créé
    n = loop.run_until_complete(db_count_users_with_prefix(f"lotd_nocomp_"))
    _log(n == 0, "T3.3 aucun user créé en DB", f"count={n}")

    # ---------------------------------------------------------------
    # TEST 4 — account_type invalide ('bidon') → fallback "entreprise"
    # ---------------------------------------------------------------
    print("\n[T4] account_type='bidon' → fallback entreprise (donc 400 sans company_name)")
    bidon_email = f"lotd_bidon_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = post("/auth/register", {
        "name": "Bidon",
        "email": bidon_email,
        "password": "Bidon123!",
        "account_type": "bidon",
        # pas de company_name → comme entreprise → doit 400
    })
    _log(r.status_code == 400, "T4.1 fallback entreprise sans company_name → 400",
         f"got={r.status_code}")

    # Avec company_name → 200, account_type stocké = "entreprise"
    bidon_email2 = f"lotd_bidon_ok_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = post("/auth/register", {
        "name": "Bidon OK",
        "email": bidon_email2,
        "password": "Bidon123!",
        "account_type": "WHATEVER",
        "company_name": "FallbackCorp",
    })
    _log(r.status_code == 200, "T4.2 fallback avec company_name → 200",
         f"got={r.status_code}")
    cdoc = loop.run_until_complete(db_lookup_company_for_email(bidon_email2))
    if cdoc:
        _log(cdoc.get("account_type") == "entreprise",
             "T4.3 DB account_type=entreprise (fallback)",
             f"got={cdoc.get('account_type')}")
        _log(cdoc.get("artisan_mode") is False,
             "T4.4 DB artisan_mode=False",
             f"got={cdoc.get('artisan_mode')}")

    # ---------------------------------------------------------------
    # TEST 5 — Compatibilité ascendante : pas de account_type
    # ---------------------------------------------------------------
    print("\n[T5] Compat: account_type absent + company_name → entreprise par défaut")
    legacy_email = f"lotd_legacy_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = post("/auth/register", {
        "name": "Legacy User",
        "email": legacy_email,
        "password": "Legacy123!",
        "company_name": "LegacySAS",
    })
    _log(r.status_code == 200, "T5.1 register legacy 200", f"got={r.status_code}")
    cdoc = loop.run_until_complete(db_lookup_company_for_email(legacy_email))
    if cdoc:
        _log(cdoc.get("account_type") == "entreprise",
             "T5.2 account_type=entreprise default", f"got={cdoc.get('account_type')}")
        _log(cdoc.get("artisan_mode") is False,
             "T5.3 artisan_mode=False", f"got={cdoc.get('artisan_mode')}")

    # ---------------------------------------------------------------
    # TEST 6 — Compte legacy admin@mesurechassis.fr a un profile valide
    # ---------------------------------------------------------------
    print("\n[T6] GET /company/profile sur admin legacy")
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    rp = get("/company/profile", token=admin_token)
    _log(rp.status_code == 200, "T6.1 admin profile 200", f"got={rp.status_code}")
    if rp.status_code == 200:
        prof = rp.json()
        _log(prof.get("account_type") == "entreprise",
             "T6.2 default account_type=entreprise",
             f"got={prof.get('account_type')}")

    # ---------------------------------------------------------------
    # TEST 7 — pytest régression
    # ---------------------------------------------------------------
    print("\n[T7] Régression pytest /app/backend/tests")
    import subprocess
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q", "--no-cov"],
        cwd="/app/backend",
        capture_output=True,
        text=True,
        timeout=180,
    )
    out_tail = (proc.stdout or "")[-600:]
    ok_pytest = proc.returncode == 0
    _log(ok_pytest, "T7.1 pytest tests/ exit==0", f"rc={proc.returncode} tail={out_tail[-200:]!r}")
    # try to find "167 passed"
    import re
    m = re.search(r"(\d+) passed", proc.stdout or "")
    if m:
        n_pass = int(m.group(1))
        _log(n_pass >= 167, f"T7.2 >=167 tests passed", f"got={n_pass}")

    # ---------------------------------------------------------------
    # BONUS — Compte artisan peut POST /chantiers sans 403
    # ---------------------------------------------------------------
    print("\n[Bonus] Compte artisan POST /chantiers sans 403")
    if artisan_token:
        r = post("/chantiers", {
            "first_name": "Test",
            "last_name": "Artisan-Chantier",
            "address": "1 rue Test",
            "postal_code": "75001",
            "city": "Paris",
            "status": "devis_a_faire",
        }, token=artisan_token)
        _log(r.status_code == 200, "B.1 POST /chantiers artisan 200",
             f"got={r.status_code} body={r.text[:200]}")
        if r.status_code == 200:
            cid = r.json().get("id")
            rg = get(f"/chantiers/{cid}", token=artisan_token)
            _log(rg.status_code == 200, "B.2 GET own chantier 200",
                 f"got={rg.status_code}")

    # ---------------------------------------------------------------
    # CLEANUP (OBLIGATOIRE)
    # ---------------------------------------------------------------
    print("\n[CLEANUP] Suppression users + companies lotd_*")
    res = loop.run_until_complete(cleanup_lot_d())
    print(f"  → {res}")
    # Vérification que admin n'est pas touché
    r = post("/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    _log(r.status_code == 200, "CLEANUP.1 admin login encore OK", f"got={r.status_code}")

    loop.close()

    # ---------------------------------------------------------------
    print(f"\n=== RESULT: {len(PASS)} PASS / {len(FAIL)} FAIL ===")
    if FAIL:
        print("\nFAILS:")
        for label, detail in FAIL:
            print(f"  - {label}: {detail}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
