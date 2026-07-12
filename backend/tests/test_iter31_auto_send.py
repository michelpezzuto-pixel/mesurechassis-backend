"""Tests iter31 — Auto-send scheduler + regression on /campaign endpoints.

Focus: verify the new automated daily email sending (/campaign/auto-send/status)
and confirm existing endpoints (stats, prospects, countdown) are not broken.

DO NOT trigger a real batch send (would cost Resend credits). We only:
- Verify status/config endpoints
- Verify DB state (prospects count, pending count, new imports source tag)
"""
import os
import re
from datetime import datetime, timedelta

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "artisan@mesurechassis.fr"
OWNER_PASS = "artisan123"


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASS},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


# ─── Auto-send status endpoint ──────────────────────────────────────────
class TestAutoSendStatus:
    def test_status_requires_auth(self):
        r = requests.get(f"{API}/campaign/auto-send/status", timeout=30)
        assert r.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {r.status_code}: {r.text}"
        )

    def test_status_with_owner(self, owner_headers):
        r = requests.get(
            f"{API}/campaign/auto-send/status", headers=owner_headers, timeout=30
        )
        assert r.status_code == 200, f"Status returned {r.status_code}: {r.text}"
        data = r.json()

        # Required fields
        assert data.get("enabled") is True, f"enabled should be True: {data}"
        assert data.get("schedule") == "16h30 Europe/Brussels (Mar-Ven)", (
            f"schedule wrong: {data.get('schedule')}"
        )
        assert "next_run_iso" in data, "next_run_iso missing"
        assert "last_run_date" in data
        assert "last_result" in data
        assert "last_scheduled" in data
        assert "last_started_at" in data

    def test_next_run_iso_is_valid_weekday_16h30_brussels(self, owner_headers):
        r = requests.get(
            f"{API}/campaign/auto-send/status", headers=owner_headers, timeout=30
        )
        data = r.json()
        next_run = data["next_run_iso"]
        # Parse ISO datetime
        dt = datetime.fromisoformat(next_run)
        assert dt.hour == 16 and dt.minute == 30, (
            f"next_run should be 16h30, got {dt.hour}h{dt.minute}"
        )
        assert dt.weekday() < 5, f"next_run should be a weekday, got weekday={dt.weekday()}"
        # UTC offset must be +01:00 (winter) or +02:00 (summer) — Brussels TZ
        offset = dt.utcoffset()
        assert offset in (timedelta(hours=1), timedelta(hours=2)), (
            f"tz offset should be Brussels (+01:00 or +02:00), got {offset}"
        )
        # Must be strictly in the future
        now = datetime.now(dt.tzinfo)
        assert dt > now, f"next_run should be in future: {dt} vs now {now}"


# ─── Campaign stats regression ──────────────────────────────────────────
class TestCampaignStats:
    def test_stats_requires_auth(self):
        r = requests.get(f"{API}/campaign/stats", timeout=30)
        assert r.status_code in (401, 403)

    def test_stats_owner_returns_expected_counts(self, owner_headers):
        r = requests.get(f"{API}/campaign/stats", headers=owner_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Required keys
        for k in [
            "pending", "sent", "failed", "sending",
            "sent_today", "daily_limit",
            "converted", "relance_due", "relances_sent", "unsubscribed",
        ]:
            assert k in data, f"missing key {k}: {data}"
        assert data["daily_limit"] == 40, (
            f"daily_limit should be 40 (per new spec), got {data['daily_limit']}"
        )
        # Sanity checks per review request:
        # sent should still be ~260, pending ~36
        assert data["sent"] >= 250, f"sent expected ~260, got {data['sent']}"
        assert data["pending"] >= 30, f"pending expected ~36, got {data['pending']}"
        # Save for cross-check
        print(f"\nSTATS: pending={data['pending']}, sent={data['sent']}, "
              f"failed={data['failed']}, unsubscribed={data['unsubscribed']}")


# ─── Prospects list regression + verify 35 new imports ─────────────────
class TestProspectsList:
    def test_list_requires_auth(self):
        r = requests.get(f"{API}/campaign/prospects", timeout=30)
        assert r.status_code in (401, 403)

    def test_list_contains_new_imports(self, owner_headers):
        r = requests.get(
            f"{API}/campaign/prospects", headers=owner_headers, timeout=30
        )
        assert r.status_code == 200, r.text
        data = r.json()
        prospects = data.get("prospects", [])
        assert isinstance(prospects, list)
        assert len(prospects) >= 250, f"Expected ~296 total, got {len(prospects)}"

        # Filter new imports
        excel_new = [
            p for p in prospects
            if p.get("source") == "excel_import_2026_07"
        ]
        print(f"\nPROSPECTS: total={len(prospects)}, "
              f"excel_import_2026_07={len(excel_new)}")
        assert len(excel_new) >= 30, (
            f"Expected ~35 new prospects with source=excel_import_2026_07, "
            f"got {len(excel_new)}"
        )
        # Verify structure of new imports
        for p in excel_new[:3]:
            assert p.get("country") == "be", f"country should be 'be': {p}"
            assert p.get("status") == "pending", f"status should be pending: {p}"


# ─── send-batch regression (do NOT actually send) ───────────────────────
class TestSendBatchStillWorks:
    """Verify the manual send-batch endpoint is not broken by the refactor.

    Note: we cannot avoid triggering emails if it succeeds. So we just check
    that the endpoint responds with a valid status code (200 ok, 429 quota,
    404 no prospect, or 423 weekend) — never a 500.
    HOWEVER, the review explicitly says not to trigger a full send.
    So we just check the endpoint's *auth* behavior (no body call).
    """
    def test_send_batch_requires_auth(self):
        r = requests.post(f"{API}/campaign/send-batch", timeout=30)
        assert r.status_code in (401, 403), (
            f"Expected 401/403 without auth, got {r.status_code}"
        )

    def test_send_batch_endpoint_exists(self, owner_headers):
        # We check via OPTIONS (or check auto-send status has last_result set
        # after auto-send may have run today). Actually we check code compiles
        # by hitting an OPTIONS - not reliable. Instead: rely on import test.
        from routes.campaign import send_batch, _collect_batch_items  # noqa: F401
        assert callable(send_batch)
        assert callable(_collect_batch_items)


# ─── Countdown regression (from previous iter) ──────────────────────────
class TestCountdownRegression:
    def test_list_requires_auth(self):
        r = requests.get(f"{API}/campaign/countdown/list", timeout=30)
        assert r.status_code in (401, 403)

    def test_list_owner(self, owner_headers):
        r = requests.get(
            f"{API}/campaign/countdown/list", headers=owner_headers, timeout=30
        )
        # 503 if not generated yet, 200 otherwise — both acceptable
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            d = r.json()
            assert "j_zero_date" in d
            assert "days" in d
            assert isinstance(d["days"], list)

    def test_visual_public_no_auth(self):
        r = requests.get(f"{API}/campaign/countdown/visual/15", timeout=30)
        # Public — 200 (PNG) or 404 if not built, but NEVER 401/403
        assert r.status_code in (200, 404, 503), (
            f"Public visual should not require auth, got {r.status_code}"
        )
        if r.status_code == 200:
            assert r.headers.get("content-type", "").startswith("image/")

    def test_visual_invalid_number(self):
        r = requests.get(f"{API}/campaign/countdown/visual/99", timeout=30)
        assert r.status_code == 404

    def test_zip_requires_auth(self):
        r = requests.get(f"{API}/campaign/countdown/zip", timeout=30)
        assert r.status_code in (401, 403)

    def test_zip_owner(self, owner_headers):
        r = requests.get(
            f"{API}/campaign/countdown/zip", headers=owner_headers, timeout=30,
            allow_redirects=False,
        )
        assert r.status_code in (200, 503), r.text
