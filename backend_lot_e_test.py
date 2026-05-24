"""Suite ciblée — Lot E : Soft-delete RGPD DELETE /api/auth/me.

Tests :
1. DELETE sans token → 401
2. Validations payload (password manquant, confirm_text invalide, password incorrect)
3. Soft-delete sans opt-in marketing (email anonymisé)
4. Soft-delete avec opt-in marketing (email préservé + marketing_email)
5. Préservation des données métier (chantier conservé)
6. abandoned_at sur company (seul admin supprimé)
7. Smoke test Resend MAIL_FROM (forgot-password admin)
8. Régression pytest backend

Auth requise via /auth/register (mode Master Admin) puis /auth/verify pour activer.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import uuid
from typing import Optional

import httpx

# Force backend URL from frontend env
BASE = "https://window-field-app.preview.emergentagent.com"
API = f"{BASE}/api"

# Comptes seedés (admin@mesurechassis.fr est l'admin de la company 'default')
ADMIN_EMAIL = "admin@mesurechassis.fr"
ADMIN_PASSWORD = "admin123"

PASSED = []
FAILED = []


def log_pass(name: str, detail: str = ""):
    PASSED.append(name)
    print(f"✅ {name} {detail}")


def log_fail(name: str, detail: str):
    FAILED.append((name, detail))
    print(f"❌ {name} :: {detail}")


# ============================================================
# Helpers Motor (accès direct DB pour vérifications + cleanup)
# ============================================================
async def get_db():
    sys.path.insert(0, "/app/backend")
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    return client[db_name], client


async def cleanup_lote_data():
    """Cleanup tous users lote_*@mesurechassis.fr + companies + chantiers."""
    db, client = await get_db()
    # Trouve tous les users de test (qu'ils soient anonymisés ou non).
    users = await db.users.find(
        {"$or": [
            {"email": {"$regex": r"^lote_.*@mesurechassis\.fr$"}},
            {"marketing_email": {"$regex": r"^lote_.*@mesurechassis\.fr$"}},
        ]},
        {"_id": 0},
    ).to_list(1000)
    user_ids = [u["id"] for u in users]
    company_ids = list({u.get("company_id") for u in users if u.get("company_id")})
    # Filtre companies de test seulement (pas "default"!)
    test_companies = [cid for cid in company_ids if cid and cid != "default"]
    print(f"[cleanup] users found={len(users)} user_ids={len(user_ids)} companies={test_companies}")
    if user_ids:
        del_chantiers = await db.chantiers.delete_many({"created_by": {"$in": user_ids}})
        del_mesures = await db.mesures.delete_many({"created_by": {"$in": user_ids}}) if hasattr(db, "mesures") else None
        del_users = await db.users.delete_many({"id": {"$in": user_ids}})
        del_verif = await db.email_verifications.delete_many({"user_id": {"$in": user_ids}})
        print(f"[cleanup] chantiers={del_chantiers.deleted_count} users={del_users.deleted_count} verif={del_verif.deleted_count}")
    if test_companies:
        del_co = await db.companies.delete_many({"company_id": {"$in": test_companies}})
        # Purge aussi tous les chantiers/mesures rattachés
        await db.chantiers.delete_many({"company_id": {"$in": test_companies}})
        print(f"[cleanup] companies={del_co.deleted_count}")
    client.close()


# ============================================================
# HTTP helpers
# ============================================================
def api_post(path: str, json_body: dict, token: Optional[str] = None, timeout=20):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.post(f"{API}{path}", json=json_body, headers=headers, timeout=timeout)


def api_delete(path: str, json_body: Optional[dict] = None, token: Optional[str] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request("DELETE", f"{API}{path}", json=json_body, headers=headers, timeout=20)


def api_get(path: str, token: Optional[str] = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.get(f"{API}{path}", headers=headers, timeout=20)


def register_and_activate(email: str, password: str, name: str, account_type: str = "artisan") -> str:
    """Crée un user, le vérifie, et retourne un access_token JWT.

    On utilise le mode Master Admin /auth/register (sans 'role') → renvoie
    verification_link ; on extrait le token et on appelle /auth/verify.
    """
    body = {
        "email": email,
        "password": password,
        "name": name,
        "account_type": account_type,
    }
    if account_type == "entreprise":
        body["company_name"] = f"TestSAS-{uuid.uuid4().hex[:6]}"
    r = api_post("/auth/register", body)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    data = r.json()
    link = data.get("verification_link", "")
    m = re.search(r"token=([^&]+)", link)
    assert m, f"no token in link: {link}"
    token_v = m.group(1)
    r2 = api_post("/auth/verify", {"token": token_v})
    assert r2.status_code == 200, f"verify failed: {r2.status_code} {r2.text}"
    return r2.json()["access_token"]


# ============================================================
# TESTS
# ============================================================
async def test_1_delete_without_token():
    r = api_delete("/auth/me", {"password": "x", "confirm_text": "SUPPRIMER"})
    if r.status_code == 401:
        log_pass("T1 DELETE /auth/me sans token → 401", f"detail={r.text[:80]}")
    else:
        log_fail("T1 DELETE /auth/me sans token", f"expected 401, got {r.status_code} {r.text[:200]}")


async def test_2_validation_payload():
    email = f"lote_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "Lot E Test")

    # 2a. Sans password
    r = api_delete("/auth/me", {"confirm_text": "SUPPRIMER"}, token=token)
    if r.status_code == 400 and "mot de passe est requis" in r.text.lower():
        log_pass("T2a sans password → 400")
    else:
        log_fail("T2a sans password", f"got {r.status_code} {r.text[:200]}")

    # 2b. Sans confirm_text
    r = api_delete("/auth/me", {"password": pwd}, token=token)
    if r.status_code == 400 and "supprimer" in r.text.lower():
        log_pass("T2b sans confirm_text → 400")
    else:
        log_fail("T2b sans confirm_text", f"got {r.status_code} {r.text[:200]}")

    # 2c. confirm_text en minuscules (échec attendu)
    r = api_delete("/auth/me", {"password": pwd, "confirm_text": "supprimer"}, token=token)
    if r.status_code == 400 and "supprimer" in r.text.lower():
        log_pass("T2c confirm_text en minuscules → 400")
    else:
        log_fail("T2c confirm_text minuscule", f"got {r.status_code} {r.text[:200]}")

    # 2d. Password incorrect
    r = api_delete("/auth/me", {"password": "wrong-password", "confirm_text": "SUPPRIMER"}, token=token)
    if r.status_code == 400 and "incorrect" in r.text.lower():
        log_pass("T2d password incorrect → 400")
    else:
        log_fail("T2d password incorrect", f"got {r.status_code} {r.text[:200]}")


async def test_3_soft_delete_no_optin():
    email = f"lote_no_optin_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "NoOptin User")

    r = api_delete("/auth/me", {
        "password": pwd,
        "confirm_text": "SUPPRIMER",
        "marketing_optin": False,
    }, token=token)
    if r.status_code != 200:
        log_fail("T3 soft-delete no optin", f"DELETE failed: {r.status_code} {r.text[:200]}")
        return
    log_pass("T3 DELETE /auth/me no optin → 200")

    # Vérification DB
    db, client = await get_db()
    # On cherche par marketing_email (NULL) — mais le user n'a plus l'email original.
    # On le retrouve via marketing_email IS NULL + status=deleted + l'absence d'email
    # → on prend tous les deleted_*@deleted.invalid récents
    docs = await db.users.find({
        "email": {"$regex": r"^deleted_.*@deleted\.invalid$"},
        "status": "deleted",
    }, {"_id": 0}).sort("deleted_at", -1).to_list(20)
    # Le plus récent doit être le nôtre
    if not docs:
        log_fail("T3 DB user not found", "no deleted_*@deleted.invalid users in DB")
        client.close()
        return
    doc = docs[0]
    if doc.get("status") == "deleted":
        log_pass("T3.db status='deleted'")
    else:
        log_fail("T3.db status", f"got {doc.get('status')}")
    if doc.get("deleted_at"):
        log_pass("T3.db deleted_at present", doc.get("deleted_at"))
    else:
        log_fail("T3.db deleted_at", "missing")
    if doc.get("hashed_password") == "":
        log_pass("T3.db hashed_password=''")
    else:
        log_fail("T3.db hashed_password", f"got {doc.get('hashed_password')[:20]!r}")
    if re.match(r"^deleted_.*@deleted\.invalid$", doc.get("email", "")):
        log_pass("T3.db email anonymized", doc.get("email"))
    else:
        log_fail("T3.db email pattern", f"got {doc.get('email')!r}")
    if doc.get("marketing_email") is None:
        log_pass("T3.db marketing_email is None")
    else:
        log_fail("T3.db marketing_email", f"got {doc.get('marketing_email')!r}")
    if doc.get("marketing_optin") is False:
        log_pass("T3.db marketing_optin == False")
    else:
        log_fail("T3.db marketing_optin", f"got {doc.get('marketing_optin')!r}")
    if doc.get("push_tokens") == []:
        log_pass("T3.db push_tokens == []")
    else:
        log_fail("T3.db push_tokens", f"got {doc.get('push_tokens')!r}")

    client.close()

    # Login avec ancien email → 401
    r = api_post("/auth/login", {"email": email, "password": pwd})
    if r.status_code == 401:
        log_pass("T3 login avec ancien email → 401")
    else:
        log_fail("T3 login avec ancien email", f"expected 401, got {r.status_code} {r.text[:200]}")

    # Forgot-password avec ancien email → 200 (anti-énum)
    r = api_post("/auth/forgot-password", {"email": email})
    if r.status_code == 200:
        body = r.json()
        # Le user n'existe plus sous cet email → branche "user not found" → 200 sans beta_reset_code
        log_pass("T3 forgot-password ancien email → 200", f"ok={body.get('ok')}")
    else:
        log_fail("T3 forgot-password ancien email", f"got {r.status_code} {r.text[:200]}")


async def test_4_soft_delete_with_optin():
    email = f"lote_optin_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "Optin User")

    r = api_delete("/auth/me", {
        "password": pwd,
        "confirm_text": "SUPPRIMER",
        "marketing_optin": True,
    }, token=token)
    if r.status_code != 200:
        log_fail("T4 soft-delete with optin", f"DELETE failed: {r.status_code} {r.text[:200]}")
        return
    log_pass("T4 DELETE /auth/me with optin → 200")

    # Vérification DB
    db, client = await get_db()
    doc = await db.users.find_one({"email": email, "status": "deleted"}, {"_id": 0})
    if not doc:
        log_fail("T4 DB user not found", f"no deleted user with email={email}")
        client.close()
        return
    if doc.get("status") == "deleted":
        log_pass("T4.db status='deleted'")
    else:
        log_fail("T4.db status", f"got {doc.get('status')}")
    if doc.get("email") == email:
        log_pass("T4.db email préservé", doc.get("email"))
    else:
        log_fail("T4.db email", f"expected {email}, got {doc.get('email')}")
    if doc.get("marketing_email") == email:
        log_pass("T4.db marketing_email == email original")
    else:
        log_fail("T4.db marketing_email", f"got {doc.get('marketing_email')!r}")
    if doc.get("marketing_optin") is True:
        log_pass("T4.db marketing_optin == True")
    else:
        log_fail("T4.db marketing_optin", f"got {doc.get('marketing_optin')!r}")
    if doc.get("hashed_password") == "":
        log_pass("T4.db hashed_password=''")
    else:
        log_fail("T4.db hashed_password", f"non-empty: len={len(doc.get('hashed_password',''))}")
    client.close()

    # Login impossible → 401
    r = api_post("/auth/login", {"email": email, "password": pwd})
    if r.status_code == 401:
        log_pass("T4 login après delete → 401")
    else:
        log_fail("T4 login après delete", f"expected 401, got {r.status_code} {r.text[:200]}")


async def test_5_preservation_donnees_metier():
    email = f"lote_chantier_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "Chantier Owner", account_type="artisan")

    # Crée un chantier
    body = {
        "first_name": "Marie",
        "last_name": "Préservation",
        "address": "10 rue du Soft Delete",
        "postal_code": "75011",
        "city": "Paris",
        "status": "devis_a_faire",
    }
    r = api_post("/chantiers", body, token=token)
    if r.status_code != 200:
        log_fail("T5 POST /chantiers", f"got {r.status_code} {r.text[:200]}")
        return
    chantier_id = r.json()["id"]
    created_by = r.json()["created_by"]
    log_pass("T5 chantier créé", f"id={chantier_id}")

    # DELETE /auth/me
    r = api_delete("/auth/me", {
        "password": pwd,
        "confirm_text": "SUPPRIMER",
        "marketing_optin": False,
    }, token=token)
    if r.status_code != 200:
        log_fail("T5 DELETE /auth/me", f"got {r.status_code} {r.text[:200]}")
        return
    log_pass("T5 DELETE /auth/me → 200")

    # Vérifie chantier toujours en DB
    db, client = await get_db()
    chantier_doc = await db.chantiers.find_one({"id": chantier_id}, {"_id": 0})
    if chantier_doc:
        log_pass("T5.db chantier préservé après delete", f"id={chantier_id}")
        if chantier_doc.get("created_by") == created_by:
            log_pass("T5.db chantier.created_by préservé (pointe vers user supprimé)")
        else:
            log_fail("T5.db chantier.created_by", f"expected {created_by}, got {chantier_doc.get('created_by')}")
    else:
        log_fail("T5.db chantier disparu !", f"id={chantier_id} no longer in DB — soft-delete a effacé les données métier")
    client.close()


async def test_6_abandoned_at_company():
    email = f"lote_lonely_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "Lonely Artisan", account_type="artisan")

    # Récupère company_id via /auth/me
    r = api_get("/auth/me", token=token)
    if r.status_code != 200:
        log_fail("T6 /auth/me", f"got {r.status_code}")
        return
    company_id = r.json().get("company_id")
    log_pass("T6 lonely admin créé", f"company_id={company_id}")

    # DELETE /auth/me
    r = api_delete("/auth/me", {
        "password": pwd,
        "confirm_text": "SUPPRIMER",
        "marketing_optin": False,
    }, token=token)
    if r.status_code != 200:
        log_fail("T6 DELETE /auth/me", f"got {r.status_code} {r.text[:200]}")
        return

    # Vérifie company.abandoned_at non-null
    db, client = await get_db()
    co = await db.companies.find_one({"company_id": company_id}, {"_id": 0})
    if not co:
        log_fail("T6.db company introuvable", company_id)
        client.close()
        return
    if co.get("abandoned_at"):
        log_pass("T6.db company.abandoned_at non-null", co.get("abandoned_at"))
    else:
        log_fail("T6.db company.abandoned_at", f"missing or null — full doc keys={list(co.keys())}")
    client.close()


async def test_7_resend_smoke():
    # 1) Reset offset des logs
    log_path = "/var/log/supervisor/backend.err.log"
    try:
        start_size = os.path.getsize(log_path)
    except FileNotFoundError:
        start_size = 0

    r = api_post("/auth/forgot-password", {"email": ADMIN_EMAIL})
    if r.status_code != 200:
        log_fail("T7 forgot-password admin", f"got {r.status_code} {r.text[:200]}")
        return
    body = r.json()
    if "beta_reset_code" in body:
        log_fail(
            "T7 beta_reset_code présent",
            f"Resend a échoué → fallback BETA actif. Body contient beta_reset_code. Le domaine n'est probablement PAS vérifié sur Resend. Body={body}",
        )
    else:
        log_pass("T7 forgot-password admin → 200 sans beta_reset_code")

    # Donne un peu de temps pour que les logs s'écrivent
    await asyncio.sleep(2.0)

    # Inspecte les nouvelles lignes du log
    try:
        with open(log_path, "rb") as f:
            f.seek(start_size)
            new_logs = f.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        log_fail("T7 lecture log", f"{exc}")
        return

    if "Resend OK" in new_logs:
        # Cherche la ligne complète
        line = next((l for l in new_logs.splitlines() if "Resend OK" in l), "")
        log_pass("T7 log 'Resend OK' présent", line[:200])
    elif "Resend FAIL" in new_logs:
        line = next((l for l in new_logs.splitlines() if "Resend FAIL" in l), "")
        log_fail("T7 Resend FAIL dans logs", line[:300])
    else:
        # Recherche dans les 100 dernières lignes au cas où
        try:
            with open(log_path, "rb") as f:
                f.seek(max(0, os.path.getsize(log_path) - 16000))
                tail = f.read().decode("utf-8", errors="ignore")
            line_ok = next((l for l in tail.splitlines() if "Resend OK" in l), None)
            line_fail = next((l for l in tail.splitlines() if "Resend FAIL" in l), None)
            if line_ok:
                log_pass("T7 'Resend OK' présent (recherche étendue)", line_ok[:200])
            elif line_fail:
                log_fail("T7 'Resend FAIL' présent (étendu)", line_fail[:300])
            else:
                log_fail("T7 aucun marqueur Resend OK/FAIL dans logs", f"new_logs_size={len(new_logs)}; check tail")
        except Exception as exc:
            log_fail("T7 log tail", f"{exc}")


async def test_8_suspect_behaviors():
    """Comportements suspects : un compte deleted ne doit pas apparaître dans /users
    et un PATCH /company/profile depuis un user deleted doit échouer (le user n'a
    plus de hashed_password donc plus de login → couvert par T3/T4 login → 401.
    Mais le token JWT pourrait survivre quelques minutes : vérifions que /auth/me
    refuse un user en status=deleted.)
    """
    email = f"lote_suspect_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    pwd = "Test1234!"
    token = register_and_activate(email, pwd, "Suspect User", account_type="artisan")

    # Crée chantier pour vérifier list /users plus tard si applicable
    r_me = api_get("/auth/me", token=token)
    user_id_before = r_me.json()["id"] if r_me.status_code == 200 else None

    # Delete
    r = api_delete("/auth/me", {
        "password": pwd,
        "confirm_text": "SUPPRIMER",
        "marketing_optin": False,
    }, token=token)
    if r.status_code != 200:
        log_fail("T8 setup delete", f"{r.status_code} {r.text[:200]}")
        return

    # /auth/me avec le token zombie → on s'attend à 401 ou 403 (status=deleted)
    # Aujourd'hui auth_user() ne check PAS explicitement status=='deleted'.
    r = api_get("/auth/me", token=token)
    if r.status_code in (401, 403):
        log_pass("T8 /auth/me avec token zombie → " + str(r.status_code))
    else:
        log_fail(
            "T8 SUSPECT — /auth/me accepte un token zombie",
            f"User deleted mais /auth/me retourne {r.status_code}. Risque : un attaquant qui a volé le JWT peut continuer à utiliser l'API jusqu'à l'expiration du token. Body={r.text[:200]}",
        )

    # GET /users en tant qu'admin master : vérifie que le user deleted n'apparaît PAS
    r = api_post("/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code == 200:
        admin_token = r.json()["access_token"]
        r = api_get("/users", token=admin_token)
        if r.status_code == 200:
            users = r.json()
            # On filtre les emails qui matchent notre cobaye (le sien est anonymisé maintenant)
            zombie_in_list = any(u.get("id") == user_id_before for u in users)
            if zombie_in_list:
                # Note : c'est dans une autre company (default), donc le user ne doit
                # PAS être listé de toute façon, mais c'est intéressant à vérifier.
                log_fail(
                    "T8 SUSPECT — GET /users (admin default) liste un user d'une AUTRE company",
                    "Le user supprimé apparait dans /users de la company 'default' alors qu'il appartenait à sa propre company. Multi-tenant cassé ?",
                )
            else:
                log_pass("T8 GET /users (admin default) n'inclut pas le user zombie d'une autre company")


# ============================================================
# REGRESSION pytest
# ============================================================
def test_9_pytest_regression():
    import subprocess
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q", "--no-cov", "--tb=short"],
        cwd="/app/backend",
        capture_output=True,
        text=True,
        timeout=240,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tail = "\n".join(out.splitlines()[-25:])
    if proc.returncode == 0:
        # Cherche "167 passed" ou similaire
        m = re.search(r"(\d+) passed", out)
        if m:
            log_pass(f"T9 pytest régression → {m.group(0)}", "")
        else:
            log_pass("T9 pytest exit 0", "")
    else:
        log_fail("T9 pytest échec", f"exitcode={proc.returncode}\n{tail}")


# ============================================================
# MAIN
# ============================================================
async def main():
    print("=" * 80)
    print(f"Backend URL: {API}")
    print("=" * 80)
    # Cleanup initial (idempotent)
    await cleanup_lote_data()

    print("\n--- T1: DELETE sans token ---")
    await test_1_delete_without_token()
    print("\n--- T2: validations payload ---")
    await test_2_validation_payload()
    print("\n--- T3: soft-delete sans opt-in ---")
    await test_3_soft_delete_no_optin()
    print("\n--- T4: soft-delete avec opt-in ---")
    await test_4_soft_delete_with_optin()
    print("\n--- T5: préservation données métier ---")
    await test_5_preservation_donnees_metier()
    print("\n--- T6: abandoned_at company ---")
    await test_6_abandoned_at_company()
    print("\n--- T7: Resend MAIL_FROM smoke ---")
    await test_7_resend_smoke()
    print("\n--- T8: comportements suspects ---")
    await test_8_suspect_behaviors()
    print("\n--- T9: régression pytest ---")
    test_9_pytest_regression()

    print("\n" + "=" * 80)
    print(f"PASS: {len(PASSED)}")
    print(f"FAIL: {len(FAILED)}")
    for name, detail in FAILED:
        print(f"  ❌ {name} :: {detail}")
    print("=" * 80)

    # CLEANUP FINAL
    print("\n--- CLEANUP FINAL ---")
    await cleanup_lote_data()
    print("Cleanup done.")

    sys.exit(0 if not FAILED else 1)


if __name__ == "__main__":
    asyncio.run(main())
