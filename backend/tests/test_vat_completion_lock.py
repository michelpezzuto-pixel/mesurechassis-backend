"""Tests Build 12 — Verrou TVA post-Google Sign-In.

Couvre:
  * POST /api/company/complete-signup (idempotence, VIES, validations)
  * GET  /api/auth/me → flag dynamique `vat_completion_required`
  * Régression : login artisan, register classique, validate-vat

Le compte "Google mock" n'est pas facilement simulable → on crée
directement en DB un user + company sans vat_number, et on fabrique
un JWT via create_access_token pour tester tous les cas.
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
from deps import create_access_token  # noqa: E402

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://window-field-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

_client = AsyncIOMotorClient(MONGO_URL)
_db = _client[DB_NAME]


# ─────────────────── Helpers ────────────────────
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _create_google_like_user(email: str, company_id: str) -> tuple[str, str]:
    """Crée un user + company sans vat_number, renvoie (user_id, jwt)."""
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())
    await _db.companies.insert_one({
        "company_id": company_id,
        "name": "TEST_Google_Signup",
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
        "name": "Test Google Signup",
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


@pytest.fixture(scope="module")
def google_user():
    """Fixture module : crée le user Google-like sans TVA."""
    email = f"test_google_{uuid.uuid4().hex[:8]}@test.mesurechassis.com"
    company_id = f"test-google-{uuid.uuid4().hex[:8]}"
    user_id, token = _run(_create_google_like_user(email, company_id))
    yield {"email": email, "company_id": company_id, "user_id": user_id, "token": token}
    _run(_cleanup(company_id, user_id))


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ═══════════════════════════════════════════════════════════════
# A. POST /api/company/complete-signup
# ═══════════════════════════════════════════════════════════════
class TestCompleteSignup:
    def test_a1_no_auth_returns_401(self, api):
        r = api.post(f"{API}/company/complete-signup", json={"vat_number": "BE0428759497"})
        assert r.status_code == 401, r.text

    def test_a2_empty_vat_returns_400(self, api, google_user):
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup", json={"vat_number": ""}, headers=h)
        assert r.status_code == 400
        assert "TVA" in r.text or "requis" in r.text.lower()

    def test_a3_invalid_vat_format_returns_400(self, api, google_user):
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup", json={"vat_number": "XX99"}, headers=h)
        assert r.status_code == 400, r.text

    def test_a4_company_name_too_short_returns_400(self, api, google_user):
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup",
                     json={"vat_number": "BE0428759497", "company_name": "A"},
                     headers=h)
        assert r.status_code == 400, r.text
        assert "2" in r.text or "120" in r.text or "caractères" in r.text

    def test_a5_company_name_too_long_returns_400(self, api, google_user):
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup",
                     json={"vat_number": "BE0428759497", "company_name": "X" * 200},
                     headers=h)
        assert r.status_code == 400, r.text

    def test_a6_valid_payload_returns_200(self, api, google_user):
        """Succès : TVA belge publique + nom société → 200"""
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup",
                     json={"vat_number": "BE0428759497",
                           "company_name": "TEST_Company_Complete"},
                     headers=h)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("vat_number") == "BE0428759497"
        assert data.get("company_name") == "TEST_Company_Complete"

    def test_a7_db_persistence_after_complete_signup(self, google_user):
        """Vérifie que la company en DB est bien à jour."""
        doc = _run(_db.companies.find_one({"company_id": google_user["company_id"]}))
        assert doc is not None
        assert doc.get("vat_number") == "BE0428759497"
        assert doc.get("vat_country") == "BE"
        assert doc.get("vat_verified_at") is not None
        assert doc.get("name") == "TEST_Company_Complete"

    def test_a8_replay_returns_400(self, api, google_user):
        """Rejeu → doit refuser (idempotence)."""
        h = {"Authorization": f"Bearer {google_user['token']}"}
        r = api.post(f"{API}/company/complete-signup",
                     json={"vat_number": "BE0428759497",
                           "company_name": "OtherName"},
                     headers=h)
        assert r.status_code == 400, r.text
        assert "déjà" in r.text.lower() or "already" in r.text.lower()


# ═══════════════════════════════════════════════════════════════
# B. GET /api/auth/me — flag vat_completion_required
# ═══════════════════════════════════════════════════════════════
class TestAuthMeVatFlag:
    def test_b1_user_with_vat_no_flag(self, api):
        """applereview@mesurechassis.com a une TVA (BE0000000097) → flag null/false.

        NB : le brief mentionnait artisan@mesurechassis.fr, mais en DB
        cette company (artisan-test-b14bf0) N'A PAS de vat_number. Elle
        renverra donc légitimement `vat_completion_required=True`.
        On utilise donc applereview qui possède réellement une TVA.
        """
        lr = api.post(f"{API}/auth/login",
                      json={"email": "applereview@mesurechassis.com",
                            "password": "MesureChassis2026"})
        assert lr.status_code == 200, lr.text
        token = lr.json()["access_token"]
        r = api.get(f"{API}/auth/me",
                    headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        flag = data.get("vat_completion_required")
        assert flag in (None, False), f"Expected null/false, got {flag}"

    def test_b2_user_without_vat_flag_true(self, api):
        """User dont la company n'a PAS de TVA → flag True."""
        # Créer un user "Google-like" jetable (indépendant du fixture module)
        email = f"test_flag_{uuid.uuid4().hex[:8]}@test.mesurechassis.com"
        company_id = f"test-flag-{uuid.uuid4().hex[:8]}"
        user_id, token = _run(_create_google_like_user(email, company_id))
        try:
            r = api.get(f"{API}/auth/me",
                        headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("vat_completion_required") is True, data
        finally:
            _run(_cleanup(company_id, user_id))

    def test_b3_flag_disappears_after_complete_signup(self, api):
        """Après complete-signup, /auth/me ne doit plus renvoyer True."""
        email = f"test_after_{uuid.uuid4().hex[:8]}@test.mesurechassis.com"
        company_id = f"test-after-{uuid.uuid4().hex[:8]}"
        user_id, token = _run(_create_google_like_user(email, company_id))
        try:
            h = {"Authorization": f"Bearer {token}"}
            # 1) Flag doit être true
            r0 = api.get(f"{API}/auth/me", headers=h).json()
            assert r0.get("vat_completion_required") is True
            # 2) Compléter
            rc = api.post(f"{API}/company/complete-signup",
                          json={"vat_number": "BE0428759497",
                                "company_name": "TEST_After"},
                          headers=h)
            assert rc.status_code == 200, rc.text
            # 3) Flag doit disparaître
            r1 = api.get(f"{API}/auth/me", headers=h).json()
            assert r1.get("vat_completion_required") in (None, False), r1
        finally:
            _run(_cleanup(company_id, user_id))


# ═══════════════════════════════════════════════════════════════
# C. Régression
# ═══════════════════════════════════════════════════════════════
class TestRegression:
    def test_c1_login_artisan(self, api):
        r = api.post(f"{API}/auth/login",
                     json={"email": "artisan@mesurechassis.fr",
                           "password": "artisan123"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == "artisan@mesurechassis.fr"

    def test_c2_validate_vat_endpoint(self, api):
        r = api.post(f"{API}/auth/validate-vat",
                     json={"vat_number": "BE0428759497"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("valid") is True
        assert data.get("normalized") == "BE0428759497"

    def test_c3_register_with_valid_vat(self, api):
        """Register classique avec TVA valide → 200 (comportement inchangé)."""
        email = f"test_reg_{uuid.uuid4().hex[:8]}@test.mesurechassis.com"
        payload = {
            "name": "Test Register",
            "email": email,
            "password": "TestPass123!",
            "company_name": "TEST_Register_Co",
            "account_type": "entreprise",
            "vat_number": "BE0428759497",
        }
        try:
            r = api.post(f"{API}/auth/register", json=payload)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data.get("user", {}).get("email") == email
        finally:
            # Cleanup
            _run(_db.users.delete_many({"email": email}))
            _run(_db.companies.delete_many({"name": "TEST_Register_Co"}))
