"""Tests Build 11.3.1 — retest des 3 fixes appliqués par le main agent.

Fix 1 : VIES `valid=null` → fallback accept (return True, None)
Fix 2 : /auth/verify avec token déjà utilisé + user actif → 200 + JWT (au lieu de 400)
Fix 3 : Compte démo Apple Review (applereview@mesurechassis.com) avec
        companies.vat_number='BE0123456789' peut toujours se loguer normalement.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest
import requests

# Allow importing the validator module directly for unit-test of fallback.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

APPLE_EMAIL = "applereview@mesurechassis.com"
APPLE_PASSWORD = "AppleReview2026!"

COMMON_PAYLOAD = {
    "password": "TestPassword2026!",
    "name": "Jean Test",
    "account_type": "entreprise",
    "company_name": "Test SARL Build 11.3.1",
}


def _unique_email(tag: str = "vat") -> str:
    return f"test-{tag}-{int(time.time() * 1000)}@example.com"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 — VIES valid=null → fallback accept (unit test du validateur)
# ─────────────────────────────────────────────────────────────────────────────
def test_vies_fix_valid_null_returns_fallback_true(monkeypatch):
    """Force VIES à renvoyer HTTP 200 avec {valid: null} → doit retourner (True, None)."""
    from services import vat_validator

    class NullValidResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"valid": None, "name": None, "address": None}

    class NullValidClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return NullValidResponse()

    monkeypatch.setattr(vat_validator.httpx, "AsyncClient", NullValidClient)
    ok, name = asyncio.run(vat_validator.check_vat_vies("BE0428759497"))
    assert ok is True, "valid=null doit être traité comme fallback success"
    assert name is None


def test_vies_fix_valid_false_still_rejects(monkeypatch):
    """Sanity check : VIES réellement KO (valid=False explicite) → toujours refusé."""
    from services import vat_validator

    class FalseResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"valid": False, "name": None}

    class FalseClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return FalseResponse()

    monkeypatch.setattr(vat_validator.httpx, "AsyncClient", FalseClient)
    ok, name = asyncio.run(vat_validator.check_vat_vies("BE0000000000"))
    assert ok is False
    assert name is None


def test_vies_fix_valid_true_accepts(monkeypatch):
    """Sanity : valid=True + name → accepté avec le nom."""
    from services import vat_validator

    class OkResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"valid": True, "name": "TEST COMPANY SA"}

    class OkClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **kw):
            return OkResponse()

    monkeypatch.setattr(vat_validator.httpx, "AsyncClient", OkClient)
    ok, name = asyncio.run(vat_validator.check_vat_vies("BE0428759497"))
    assert ok is True
    assert name == "TEST COMPANY SA"


# ─────────────────────────────────────────────────────────────────────────────
# FIX 1 (E2E) — register BE0428759497 doit passer en 1 essai
# ─────────────────────────────────────────────────────────────────────────────
def test_register_be0428759497_first_try():
    """Reprise du scénario UPS Belgium — DOIT passer du premier coup grâce au fix
    `valid=null` → fallback. Pas de retry loop.
    """
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    email = _unique_email("be-ups-singleshot")
    payload = {**COMMON_PAYLOAD, "email": email, "vat_number": "BE0428759497"}
    r = sess.post(f"{API}/auth/register", json=payload, timeout=60)
    assert r.status_code == 200, (
        f"Fix VIES valid=null cassé. Statut={r.status_code} Body={r.text[:300]}"
    )
    body = r.json()
    assert "user" in body
    assert body["user"]["email"] == email.lower()

    # Cleanup
    import os as _os
    from motor.motor_asyncio import AsyncIOMotorClient

    async def _cleanup():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            u = await d.users.find_one({"email": email.lower()}, {"_id": 0})
            if u:
                await d.companies.delete_one({"company_id": u["company_id"]})
                await d.users.delete_one({"email": email.lower()})
        finally:
            client.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# FIX 2 — /auth/verify graceful sur token déjà utilisé + user actif
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def created_user_with_token():
    """Crée un user via /auth/register (auto-verify ON → user déjà active),
    récupère le token de vérification depuis db.email_verifications, et yield
    (email, token, user_id). Nettoie ensuite.
    """
    import os as _os
    from motor.motor_asyncio import AsyncIOMotorClient

    email = _unique_email("verify-twice")
    payload = {**COMMON_PAYLOAD, "email": email, "vat_number": "BE0428759497"}
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/register", json=payload, timeout=60)
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    user = r.json()["user"]

    # Aller chercher le token dans la DB
    state = {"email": email.lower(), "user_id": user["id"], "company_id": user["company_id"], "token": None}

    async def _get_token():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            rec = await d.email_verifications.find_one(
                {"user_id": state["user_id"], "kind": "verify"},
                {"_id": 0},
                sort=[("created_at", -1)],
            )
            assert rec is not None, "verification token not created"
            state["token"] = rec["token"]
        finally:
            client.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_get_token())
    finally:
        loop.close()

    yield state

    # Cleanup
    async def _cleanup():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            await d.email_verifications.delete_many({"user_id": state["user_id"]})
            await d.companies.delete_one({"company_id": state["company_id"]})
            await d.users.delete_one({"id": state["user_id"]})
        finally:
            client.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_cleanup())
    finally:
        loop.close()


def test_verify_first_call_returns_200_and_jwt(created_user_with_token):
    """1er appel /auth/verify → 200 + access_token (consomme le token)."""
    state = created_user_with_token
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/verify", json={"token": state["token"]}, timeout=30)
    assert r.status_code == 200, f"1st verify expected 200, got {r.status_code} {r.text}"
    body = r.json()
    assert "access_token" in body and body["access_token"]
    assert body["user"]["id"] == state["user_id"]
    assert body["user"]["status"] == "active"


def test_verify_second_call_graceful_still_200(created_user_with_token):
    """FIX 2 : 2ᵉ appel /auth/verify avec même token déjà utilisé + user actif
    → AVANT: 400 'Lien déjà utilisé', APRÈS: 200 + nouveau JWT.
    """
    state = created_user_with_token
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})

    # 1er appel — consomme le token (used=True)
    r1 = sess.post(f"{API}/auth/verify", json={"token": state["token"]}, timeout=30)
    assert r1.status_code == 200, f"1st verify failed: {r1.status_code} {r1.text}"
    jwt1 = r1.json()["access_token"]

    # 2ᵉ appel — token used=True ET user active → DOIT renvoyer 200 + JWT
    r2 = sess.post(f"{API}/auth/verify", json={"token": state["token"]}, timeout=30)
    assert r2.status_code == 200, (
        f"FIX 2 cassé. Le 2ᵉ verify devrait être gracieux (200) car user actif. "
        f"Got {r2.status_code} {r2.text}"
    )
    body = r2.json()
    assert "access_token" in body and body["access_token"]
    assert body["user"]["id"] == state["user_id"]
    assert body["user"]["status"] == "active"
    # 2 JWT différents (générés à 2 instants distincts) — pas obligatoire mais sain
    # (NB : peuvent être identiques si générés dans la même seconde, on ne l'asserte pas)


def test_verify_used_token_but_user_deleted_returns_400():
    """FIX 2 — cas non géré sciemment : si on supprime l'user après 1er verify,
    le 2ᵉ call doit retomber sur 400 'Lien déjà utilisé'.
    """
    import os as _os
    from motor.motor_asyncio import AsyncIOMotorClient

    email = _unique_email("verify-deleted")
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    payload = {**COMMON_PAYLOAD, "email": email, "vat_number": "BE0428759497"}
    r = sess.post(f"{API}/auth/register", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    user = r.json()["user"]

    state = {"user_id": user["id"], "company_id": user["company_id"], "token": None}

    async def _setup():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            rec = await d.email_verifications.find_one(
                {"user_id": state["user_id"], "kind": "verify"},
                sort=[("created_at", -1)],
            )
            state["token"] = rec["token"]
        finally:
            client.close()

    asyncio.new_event_loop().run_until_complete(_setup())

    # 1er verify pour marquer used=True
    r1 = sess.post(f"{API}/auth/verify", json={"token": state["token"]}, timeout=30)
    assert r1.status_code == 200, r1.text

    # On supprime l'user (hard delete pour ce test) — simule le cas "user inexistant"
    async def _delete_user():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            await d.users.delete_one({"id": state["user_id"]})
        finally:
            client.close()

    asyncio.new_event_loop().run_until_complete(_delete_user())

    # 2ᵉ verify : token used + user absent → 400 attendu
    r2 = sess.post(f"{API}/auth/verify", json={"token": state["token"]}, timeout=30)
    assert r2.status_code == 400, (
        f"Token used+user absent doit retourner 400. Got {r2.status_code} {r2.text}"
    )
    detail = r2.json().get("detail", "")
    assert "déjà utilisé" in detail or "utilisé" in detail.lower(), detail

    # Cleanup company + token
    async def _cleanup():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            await d.companies.delete_one({"company_id": state["company_id"]})
            await d.email_verifications.delete_many({"user_id": state["user_id"]})
        finally:
            client.close()

    asyncio.new_event_loop().run_until_complete(_cleanup())


def test_verify_invalid_token_returns_400():
    """Sanity : token inexistant → 400 'Lien de vérification invalide'."""
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/verify", json={"token": "totally-fake-token-zzz"}, timeout=15)
    assert r.status_code == 400
    detail = r.json().get("detail", "")
    assert "invalide" in detail.lower()


# ─────────────────────────────────────────────────────────────────────────────
# FIX 3 — Compte démo Apple Review login OK + vat_number persisté
# ─────────────────────────────────────────────────────────────────────────────
def test_apple_review_login_still_works(s):
    r = s.post(
        f"{API}/auth/login",
        json={"email": APPLE_EMAIL, "password": APPLE_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200, f"Apple Review login KO: {r.status_code} {r.text}"
    body = r.json()
    assert "access_token" in body and body["access_token"]
    assert body["user"]["email"] == APPLE_EMAIL
    assert body["user"]["role"] == "admin"
    assert body["user"]["status"] == "active"


def test_apple_review_company_has_vat_be0123456789(s):
    """Vérifie que companies.vat_number et vat_country sont bien renseignés
    pour le compte applereview@ (fix 3).
    """
    import os as _os
    from motor.motor_asyncio import AsyncIOMotorClient

    state = {}

    async def _check():
        client = AsyncIOMotorClient(_os.environ["MONGO_URL"])
        try:
            d = client[_os.environ["DB_NAME"]]
            u = await d.users.find_one({"email": APPLE_EMAIL}, {"_id": 0})
            assert u is not None, "applereview user introuvable"
            c = await d.companies.find_one({"company_id": u["company_id"]}, {"_id": 0})
            assert c is not None, "applereview company introuvable"
            state["vat_number"] = c.get("vat_number")
            state["vat_country"] = c.get("vat_country")
        finally:
            client.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_check())
    finally:
        loop.close()

    assert state["vat_number"] == "BE0123456789", (
        f"vat_number attendu BE0123456789, got {state['vat_number']!r}"
    )
    assert state["vat_country"] == "BE", (
        f"vat_country attendu BE, got {state['vat_country']!r}"
    )


def test_apple_review_can_call_authenticated_endpoint(s):
    """Bout-en-bout : login + GET /auth/me avec le JWT."""
    r = s.post(
        f"{API}/auth/login",
        json={"email": APPLE_EMAIL, "password": APPLE_PASSWORD},
        timeout=15,
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = s.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == APPLE_EMAIL
