"""Iteration 35 — Validation du BYPASS TVA pour comptes techniques.

Suite du Build 12 (iter34). Vérifie que:

  A. Bypass fonctionnel — les 3 comptes techniques (artisan owner,
     admin@mesurechassis.fr, applereview@mesurechassis.com) ont
     `vat_completion_required` == None sur /auth/me, MÊME sans
     vat_number en DB.

  B. Verrou toujours actif — un user hors exempt list voit toujours
     le flag à True, peut compléter via /company/complete-signup,
     puis le flag disparaît.

  C. Regression rapide — login artisan + /health + /company/profile.

VAT réelle utilisée : BE0428759497 (validée VIES en direct).
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from deps import create_access_token, VAT_CHECK_EXEMPT_EMAILS  # noqa: E402

BASE_URL = (
    os.environ.get("EXPO_BACKEND_URL")
    or os.environ.get("EXPO_PUBLIC_BACKEND_URL")
    or "https://window-field-app.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
assert MONGO_URL and DB_NAME, "MONGO_URL / DB_NAME are required"

_client = AsyncIOMotorClient(MONGO_URL)
_db = _client[DB_NAME]


# ─────────────────────── Helpers ───────────────────────
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login_and_me(api, email: str, password: str) -> dict:
    """Login + /auth/me, retourne le body de /auth/me.

    Skip le test si le login échoue (compte manquant en env test).
    """
    lr = api.post(f"{API}/auth/login", json={"email": email, "password": password})
    if lr.status_code != 200:
        pytest.skip(f"Login KO pour {email}: {lr.status_code} {lr.text[:120]}")
    token = lr.json()["access_token"]
    r = api.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return {"me": r.json(), "token": token}


# ═══════════════════════════════════════════════════════════════
# 0. Sanity — le set VAT_CHECK_EXEMPT_EMAILS contient bien les 3
# ═══════════════════════════════════════════════════════════════
class TestExemptSetContent:
    def test_0a_admin_email_in_exempt(self):
        assert "admin@mesurechassis.fr" in VAT_CHECK_EXEMPT_EMAILS

    def test_0b_applereview_email_in_exempt(self):
        assert "applereview@mesurechassis.com" in VAT_CHECK_EXEMPT_EMAILS

    def test_0c_artisan_owner_email_in_exempt(self):
        # artisan@mesurechassis.fr est membre PLATFORM_OWNER_EMAILS
        # (cf. test_credentials.md) → doit être inclus via l'union.
        assert "artisan@mesurechassis.fr" in VAT_CHECK_EXEMPT_EMAILS


# ═══════════════════════════════════════════════════════════════
# A. Bypass fonctionnel — comptes techniques → flag null
# ═══════════════════════════════════════════════════════════════
class TestBypassTechnicalAccounts:
    def test_a1_artisan_owner_bypass(self, api):
        """artisan@mesurechassis.fr (PLATFORM_OWNER) — pas de vat_number
        en DB (voir iter34), mais le bypass doit rendre le flag null."""
        r = _login_and_me(api, "artisan@mesurechassis.fr", "artisan123")
        flag = r["me"].get("vat_completion_required")
        assert flag in (None, False), (
            f"BYPASS KO pour artisan owner : flag={flag} "
            f"(attendu null/False). me={r['me']}"
        )
        # Sanity : vérifier que la company n'a effectivement pas de TVA
        # (sinon le test ne prouve rien — le bypass n'est pas sollicité).
        company_id = r["me"].get("company_id")
        if company_id:
            doc = _run(_db.companies.find_one({"company_id": company_id}))
            if doc and doc.get("vat_number"):
                pytest.skip(
                    f"Company {company_id} a désormais un vat_number "
                    f"({doc.get('vat_number')}) — le bypass n'est pas testé."
                )

    def test_a2_admin_mesurechassis_bypass(self, api):
        """admin@mesurechassis.fr — company 'default' sans vat_number
        (voir iter34), le bypass doit rendre le flag null."""
        r = _login_and_me(api, "admin@mesurechassis.fr", "admin123")
        flag = r["me"].get("vat_completion_required")
        assert flag in (None, False), (
            f"BYPASS KO pour admin@mesurechassis.fr : flag={flag}"
        )

    def test_a3_applereview_bypass(self, api):
        """applereview@mesurechassis.com — dans exempt list explicitement."""
        r = _login_and_me(api, "applereview@mesurechassis.com",
                          "MesureChassis2026")
        flag = r["me"].get("vat_completion_required")
        assert flag in (None, False), (
            f"BYPASS KO pour applereview : flag={flag}"
        )


# ═══════════════════════════════════════════════════════════════
# B. Verrou toujours actif pour les VRAIS clients
# ═══════════════════════════════════════════════════════════════
async def _create_non_exempt_user(email: str, company_id: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())
    await _db.companies.insert_one({
        "company_id": company_id,
        "name": "TEST_ITER35_Company",
        "account_type": "artisan",
        "artisan_mode": True,
        "vat_number": None,
        "vat_country": None,
        "subscription_status": "active",
        "plan": "pro",
        "created_at": now,
        "_TEST_": True,
    })
    await _db.users.insert_one({
        "id": user_id,
        "name": "TEST ITER35 Real Client",
        "email": email,
        "role": "admin",
        "company_id": company_id,
        "hashed_password": None,
        "status": "active",
        "email_verified_at": now,
        "google_linked": True,
        "created_at": now,
        "_TEST_": True,
    })
    token = create_access_token(user_id, "admin")
    return user_id, token


async def _cleanup(company_id: str, user_id: str):
    await _db.users.delete_many({"id": user_id})
    await _db.companies.delete_many({"company_id": company_id})


class TestLockStillActiveForRealClient:
    def test_b_full_flow(self, api):
        """Cycle complet : email hors exempt → flag True → complete-signup
        → flag disparaît → cleanup."""
        email = "test-vat-lock@fake.com"
        # Confirme que l'email n'est PAS dans l'exempt list
        assert email not in VAT_CHECK_EXEMPT_EMAILS

        company_id = f"test-iter35-{uuid.uuid4().hex[:8]}"
        user_id, token = _run(_create_non_exempt_user(email, company_id))
        h = {"Authorization": f"Bearer {token}"}
        try:
            # 1) /auth/me → flag True
            r1 = api.get(f"{API}/auth/me", headers=h)
            assert r1.status_code == 200, r1.text
            assert r1.json().get("vat_completion_required") is True, r1.json()

            # 2) POST /company/complete-signup avec VIES réel
            rc = api.post(
                f"{API}/company/complete-signup",
                json={"vat_number": "BE0428759497",
                      "company_name": "Test Company"},
                headers=h,
                timeout=30,  # VIES peut être lent
            )
            assert rc.status_code == 200, rc.text
            body = rc.json()
            assert body.get("ok") is True
            assert body.get("vat_number") == "BE0428759497"

            # 3) /auth/me → flag null/False
            r2 = api.get(f"{API}/auth/me", headers=h)
            assert r2.status_code == 200
            assert r2.json().get("vat_completion_required") in (None, False), r2.json()

            # 4) Persistance DB
            doc = _run(_db.companies.find_one({"company_id": company_id}))
            assert doc is not None
            assert doc.get("vat_number") == "BE0428759497"
            assert doc.get("vat_country") == "BE"
        finally:
            _run(_cleanup(company_id, user_id))


# ═══════════════════════════════════════════════════════════════
# C. Régression rapide — rien ne doit être cassé
# ═══════════════════════════════════════════════════════════════
class TestRegression:
    def test_c1_backend_reachable(self, api):
        """Backend joignable via /auth/validate-vat (endpoint public)."""
        r = api.post(f"{API}/auth/validate-vat",
                     json={"vat_number": "BE0428759497"})
        assert r.status_code == 200, r.text

    def test_c2_artisan_login_token_ok(self, api):
        r = api.post(f"{API}/auth/login",
                     json={"email": "artisan@mesurechassis.fr",
                           "password": "artisan123"})
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()

    def test_c3_company_profile_with_artisan_token(self, api):
        lr = api.post(f"{API}/auth/login",
                      json={"email": "artisan@mesurechassis.fr",
                            "password": "artisan123"})
        assert lr.status_code == 200
        token = lr.json()["access_token"]
        r = api.get(f"{API}/company/profile",
                    headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
