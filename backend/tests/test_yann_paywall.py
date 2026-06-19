"""Tests for the NEW Yann paywall logic (iteration 11).

Covers:
  • Unit tests for services.yann_access.is_yann_allowed — all 6 branches.
  • Integration tests for GET /api/yann/quota — allowed/access_reason fields.
  • Integration test against the live server confirming BETA_MODE=True path
    returns allowed=true with access_reason="beta".
  • Integration tests for POST /api/yann/chat 402 paywall response
    (BETA_MODE=False patched), without invoking the LLM.

NOTE: Most paywall-with-BETA_MODE=False tests use the in-process ASGI
client (httpx.ASGITransport) so we can monkey-patch BETA_MODE in both
`services.yann_access` and `deps` modules.  This avoids burning real
LLM credits, since blocked requests return 402 BEFORE hitting the LLM,
and we only call POST /yann/chat for the BLOCKED case.  For ALLOWED
states (trial / pro / addon) we verify via GET /api/yann/quota which
does NOT invoke the LLM but exposes `allowed` + `access_reason`.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import requests
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from pymongo import MongoClient

# Allow `import db / deps / services.yann_access` from the test file.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from db import db as async_db  # noqa: E402  (motor)
import db as db_module  # noqa: E402
import deps as deps_module  # noqa: E402
from services import yann_access as ya_module  # noqa: E402
from services.yann_access import is_yann_allowed  # noqa: E402
from server import app  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
_sync_client = MongoClient(MONGO_URL)
sync_db = _sync_client[DB_NAME]

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/") or (
    "https://window-field-app.preview.emergentagent.com"
)
API = f"{BASE_URL}/api"

EMAIL = "cousin.admin@test.mesurechassis.com"
PASSWORD = "Cousin2026!"


# ════════════════════════════════════════════════════════════════════════
# UNIT TESTS — is_yann_allowed(user, company_doc) — all 6 branches
# ════════════════════════════════════════════════════════════════════════
class TestIsYannAllowedUnit:
    """Pure unit tests; no DB/HTTP. Patches BETA_MODE in services.yann_access."""

    def _patch_beta(self, monkeypatch, value: bool):
        monkeypatch.setattr(ya_module, "BETA_MODE", value, raising=True)

    # ─── Branch 1: BETA_MODE=True ───────────────────────────────────────
    def test_beta_mode_always_allowed(self, monkeypatch):
        self._patch_beta(monkeypatch, True)
        # Even a "junk" user / company should be allowed
        allowed, reason = is_yann_allowed(
            {"subscription_status": "suspended", "plan": "free"},
            {"yann_addon_active": False},
        )
        assert allowed is True
        assert reason == "beta"

    # ─── Branch 2: trial + future expiry ────────────────────────────────
    def test_trial_future_expiry_allowed(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        allowed, reason = is_yann_allowed(
            {"subscription_status": "trial", "subscription_expires_at": future, "plan": "trial"},
            {},
        )
        assert allowed is True
        assert reason == "trial"

    def test_trial_expired_blocked(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        allowed, reason = is_yann_allowed(
            {"subscription_status": "trial", "subscription_expires_at": past, "plan": "trial"},
            {},
        )
        assert allowed is False
        assert reason == "expired"

    # ─── Branch 3: suspended → no_subscription ──────────────────────────
    def test_suspended_blocked_no_subscription(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        allowed, reason = is_yann_allowed(
            {"subscription_status": "suspended", "plan": "pro"},
            {"yann_addon_active": True},
        )
        # suspended should short-circuit before plan / addon
        assert allowed is False
        assert reason == "no_subscription"

    # ─── Branch 4: plan=pro → allowed ───────────────────────────────────
    def test_pro_plan_allowed(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        allowed, reason = is_yann_allowed(
            {"subscription_status": "active", "plan": "pro"},
            {},
        )
        assert allowed is True
        assert reason == "pro"

    # ─── Branch 5: yann_addon_active=True → allowed ─────────────────────
    def test_addon_allowed(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        allowed, reason = is_yann_allowed(
            {"subscription_status": "active", "plan": "trial"},
            {"yann_addon_active": True},
        )
        assert allowed is True
        assert reason == "addon"

    # ─── Branch 6: otherwise → plan_too_low ─────────────────────────────
    def test_low_plan_blocked(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        allowed, reason = is_yann_allowed(
            {"subscription_status": "active", "plan": "trial"},
            {"yann_addon_active": False},
        )
        assert allowed is False
        assert reason == "plan_too_low"

    def test_low_plan_no_company_doc_blocked(self, monkeypatch):
        self._patch_beta(monkeypatch, False)
        # company_doc=None defaults to {} → yann_addon_active falsy
        allowed, reason = is_yann_allowed(
            {"subscription_status": "active", "plan": "free"}, None
        )
        assert allowed is False
        assert reason == "plan_too_low"


# ════════════════════════════════════════════════════════════════════════
# LIVE-SERVER smoke (BETA_MODE=True path, default state)
# ════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def live_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=20,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def test_live_quota_returns_allowed_beta(live_token):
    """BETA_MODE=True on live server → allowed=true, access_reason='beta'."""
    r = requests.get(
        f"{API}/yann/quota",
        headers={"Authorization": f"Bearer {live_token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("allowed") is True, f"Expected allowed=True, got {data}"
    assert data.get("access_reason") == "beta", f"Expected reason=beta, got {data}"
    assert data["limit"] == 30
    assert "used" in data and "remaining" in data


# ════════════════════════════════════════════════════════════════════════
# IN-PROCESS ASGI tests with BETA_MODE=False patched
# ════════════════════════════════════════════════════════════════════════
@pytest_asyncio.fixture
async def asgi_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def asgi_token(asgi_client):
    r = await asgi_client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def disable_beta_mode(monkeypatch):
    """Patch BETA_MODE=False in BOTH services.yann_access and deps modules.

    `deps.ensure_company` would otherwise force the company back to plan=pro
    and subscription_status=active on every auth, masking our test state.
    """
    monkeypatch.setattr(ya_module, "BETA_MODE", False, raising=True)
    monkeypatch.setattr(deps_module, "BETA_MODE", False, raising=True)
    # We don't touch db_module.BETA_MODE because the constant is re-imported
    # into the two modules above; the source-of-truth read points are there.
    yield
    # monkeypatch auto-restores on teardown


@pytest.fixture
def cousin_company_id():
    user = sync_db.users.find_one(
        {"email": EMAIL}, {"_id": 0, "company_id": 1}
    )
    assert user, f"Test user {EMAIL} missing"
    return user["company_id"]


@pytest.fixture
def snapshot_and_restore_company(cousin_company_id):
    """Snapshot the company doc before the test, restore at teardown."""
    cid = cousin_company_id
    original = sync_db.companies.find_one({"company_id": cid}, {"_id": 0})
    assert original, f"Company {cid} not found"
    yield cid
    # Restore — replace_one to avoid leaving stray test fields
    sync_db.companies.replace_one({"company_id": cid}, original, upsert=True)


def _set_company(cid: str, **fields):
    sync_db.companies.update_one({"company_id": cid}, {"$set": fields})


# ─── Scenario A: BETA_MODE=False + suspended → 402 no_subscription ──────
@pytest.mark.asyncio
async def test_paywall_blocks_suspended(
    asgi_client, asgi_token, disable_beta_mode, snapshot_and_restore_company
):
    cid = snapshot_and_restore_company
    _set_company(cid, subscription_status="suspended", plan="trial",
                 yann_addon_active=False)

    headers = {"Authorization": f"Bearer {asgi_token}"}

    # Quota endpoint shows allowed=False with reason "no_subscription"
    rq = await asgi_client.get("/api/yann/quota", headers=headers)
    assert rq.status_code == 200, rq.text
    qdata = rq.json()
    assert qdata["allowed"] is False, qdata
    assert qdata["access_reason"] == "no_subscription", qdata

    # Chat endpoint returns 402 with structured detail
    rc = await asgi_client.post(
        "/api/yann/chat", headers=headers, json={"message": "Hi"}
    )
    assert rc.status_code == 402, rc.text
    detail = rc.json().get("detail", {})
    assert detail.get("code") == "yann_paywall", detail
    assert detail.get("reason") == "no_subscription", detail
    assert "message" in detail


# ─── Scenario B: trial path (future expiry) → quota shows allowed=trial ─
@pytest.mark.asyncio
async def test_paywall_allows_trial(
    asgi_client, asgi_token, disable_beta_mode, snapshot_and_restore_company
):
    cid = snapshot_and_restore_company
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    _set_company(
        cid,
        subscription_status="trial",
        subscription_expires_at=future,
        plan="trial",
        yann_addon_active=False,
    )
    headers = {"Authorization": f"Bearer {asgi_token}"}
    rq = await asgi_client.get("/api/yann/quota", headers=headers)
    assert rq.status_code == 200, rq.text
    data = rq.json()
    assert data["allowed"] is True, data
    assert data["access_reason"] == "trial", data


# ─── Scenario C: pro plan path ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_paywall_allows_pro(
    asgi_client, asgi_token, disable_beta_mode, snapshot_and_restore_company
):
    cid = snapshot_and_restore_company
    _set_company(
        cid,
        plan="pro",
        subscription_status="active",
        yann_addon_active=False,
    )
    headers = {"Authorization": f"Bearer {asgi_token}"}
    rq = await asgi_client.get("/api/yann/quota", headers=headers)
    assert rq.status_code == 200, rq.text
    data = rq.json()
    assert data["allowed"] is True, data
    assert data["access_reason"] == "pro", data


# ─── Scenario D: addon path ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_paywall_allows_addon(
    asgi_client, asgi_token, disable_beta_mode, snapshot_and_restore_company
):
    cid = snapshot_and_restore_company
    _set_company(
        cid,
        plan="trial",
        subscription_status="active",
        yann_addon_active=True,
    )
    headers = {"Authorization": f"Bearer {asgi_token}"}
    rq = await asgi_client.get("/api/yann/quota", headers=headers)
    assert rq.status_code == 200, rq.text
    data = rq.json()
    assert data["allowed"] is True, data
    assert data["access_reason"] == "addon", data


# ─── Scenario E: low plan + no addon → 402 plan_too_low ─────────────────
@pytest.mark.asyncio
async def test_paywall_blocks_plan_too_low(
    asgi_client, asgi_token, disable_beta_mode, snapshot_and_restore_company
):
    cid = snapshot_and_restore_company
    _set_company(
        cid,
        plan="trial",
        subscription_status="active",
        yann_addon_active=False,
    )
    headers = {"Authorization": f"Bearer {asgi_token}"}

    rq = await asgi_client.get("/api/yann/quota", headers=headers)
    assert rq.status_code == 200, rq.text
    qdata = rq.json()
    assert qdata["allowed"] is False, qdata
    assert qdata["access_reason"] == "plan_too_low", qdata

    rc = await asgi_client.post(
        "/api/yann/chat", headers=headers, json={"message": "Hi"}
    )
    assert rc.status_code == 402, rc.text
    detail = rc.json().get("detail", {})
    assert detail.get("code") == "yann_paywall", detail
    assert detail.get("reason") == "plan_too_low", detail
