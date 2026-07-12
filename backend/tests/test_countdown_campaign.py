"""Tests for the 3 new "Jeton Café" countdown campaign endpoints.

Endpoints under test (see /app/backend/routes/campaign.py):
  - GET /api/campaign/countdown/list        (PROTECTED — require_platform_owner)
  - GET /api/campaign/countdown/visual/{n}  (PUBLIC — no auth)
  - GET /api/campaign/countdown/zip         (PROTECTED — require_platform_owner)
"""
import os
from datetime import date, timedelta

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://window-field-app.preview.emergentagent.com").rstrip("/")

OWNER_EMAIL = "artisan@mesurechassis.fr"
OWNER_PASSWORD = "artisan123"


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_token(api_client):
    """Login as platform owner and return access token."""
    resp = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
        timeout=30,
    )
    if resp.status_code != 200:
        pytest.skip(f"Owner login failed ({resp.status_code}): {resp.text[:300]}")
    body = resp.json()
    token = body.get("access_token") or body.get("token")
    assert token, f"No token in login response: {body}"
    return token


@pytest.fixture(scope="module")
def auth_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


# ────────────────────────────────────────────────────────────────────
# 1) GET /api/campaign/countdown/list
# ────────────────────────────────────────────────────────────────────
class TestCountdownList:
    def test_requires_auth_returns_401(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/list", timeout=30)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}: {r.text[:200]}"

    def test_returns_full_campaign_payload(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/campaign/countdown/list",
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:300]}"
        data = r.json()

        # Top-level shape
        assert data.get("j_zero_date") == "2026-08-12", f"j_zero_date wrong: {data.get('j_zero_date')}"
        assert isinstance(data.get("today"), str) and len(data["today"]) == 10
        # today_day int 0..30 or null
        td = data.get("today_day")
        assert td is None or (isinstance(td, int) and 0 <= td <= 30), f"today_day invalid: {td}"
        assert isinstance(data.get("campaign_active"), bool)
        # campaign_active should be consistent with today_day
        assert data["campaign_active"] == (td is not None)

        days = data.get("days")
        assert isinstance(days, list), "days must be an array"
        assert len(days) == 31, f"Expected 31 days, got {len(days)}"

    def test_days_structure_and_order(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/campaign/countdown/list",
            headers=auth_headers,
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        days = data["days"]

        # n=30 first, n=0 last (countdown order)
        assert days[0]["n"] == 30, f"First day n should be 30, got {days[0]['n']}"
        assert days[-1]["n"] == 0, f"Last day n should be 0, got {days[-1]['n']}"

        # Verify each day has all required fields + captions
        required_fields = {"n", "title", "publish_date", "visual_url", "captions", "status", "days_until_publish"}
        prev_date = None
        for d in days:
            missing = required_fields - set(d.keys())
            assert not missing, f"Day n={d.get('n')} missing fields: {missing}"

            assert isinstance(d["n"], int) and 0 <= d["n"] <= 30
            assert isinstance(d["title"], str) and d["title"]
            assert isinstance(d["publish_date"], str) and len(d["publish_date"]) == 10
            assert isinstance(d["visual_url"], str) and d["visual_url"]

            caps = d["captions"]
            assert isinstance(caps, dict)
            for platform in ("linkedin", "facebook", "instagram"):
                assert platform in caps, f"Missing caption {platform} for n={d['n']}"
                assert isinstance(caps[platform], str) and caps[platform].strip(), (
                    f"Empty {platform} caption for n={d['n']}"
                )

            assert d["status"] in ("past", "today", "future")
            assert isinstance(d["days_until_publish"], int)

            # Publish date strictly +1 day per entry (array goes n=30 → n=0,
            # i.e. earliest publish date first, up to j_zero last).
            # Equivalent: n strictly decreases by 1 per step.
            cur = date.fromisoformat(d["publish_date"])
            if prev_date is not None:
                assert (cur - prev_date).days == 1, (
                    f"Publish dates not strictly +1 day between {prev_date} and {cur} (n={d['n']})"
                )
            prev_date = cur

        # The last day (n=0) publish_date should equal j_zero_date
        assert days[-1]["publish_date"] == data["j_zero_date"], (
            f"n=0 publish_date {days[-1]['publish_date']} != j_zero {data['j_zero_date']}"
        )
        # And the first day (n=30) publish_date should be j_zero - 30 days
        expected_first = date.fromisoformat(data["j_zero_date"]) - timedelta(days=30)
        assert days[0]["publish_date"] == expected_first.isoformat()

    def test_today_day_consistency_with_status(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/campaign/countdown/list",
            headers=auth_headers,
            timeout=30,
        )
        data = r.json()
        today_iso = data["today"]
        today_day = data["today_day"]

        today_entries = [d for d in data["days"] if d["status"] == "today"]
        if today_day is None:
            # Outside window: no entry should have status "today"
            assert not today_entries, "today_day null but some day has status=today"
        else:
            # Exactly one entry should be "today" and it should match today_day
            assert len(today_entries) == 1, f"Expected 1 'today' entry, got {len(today_entries)}"
            assert today_entries[0]["n"] == today_day
            assert today_entries[0]["publish_date"] == today_iso


# ────────────────────────────────────────────────────────────────────
# 2) GET /api/campaign/countdown/visual/{n}  (PUBLIC)
# ────────────────────────────────────────────────────────────────────
class TestCountdownVisual:
    def test_valid_n_15_returns_png(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/visual/15", timeout=30)
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("image/png"), (
            f"Wrong content-type: {r.headers.get('content-type')}"
        )
        assert len(r.content) > 10_000, f"PNG too small: {len(r.content)} bytes"
        # PNG magic bytes
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG file"

    def test_boundary_n_0(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/visual/0", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert len(r.content) > 10_000

    def test_boundary_n_30(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/visual/30", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert len(r.content) > 10_000

    def test_invalid_n_99_returns_404(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/visual/99", timeout=30)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def test_public_no_auth_required(self, api_client):
        # Explicitly send no Authorization header
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/campaign/countdown/visual/10", timeout=30)
        assert r.status_code == 200


# ────────────────────────────────────────────────────────────────────
# 3) GET /api/campaign/countdown/zip
# ────────────────────────────────────────────────────────────────────
class TestCountdownZip:
    def test_requires_auth_returns_401(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/campaign/countdown/zip", timeout=60)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_returns_zip_with_auth(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/campaign/countdown/zip",
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith("application/zip"), (
            f"Wrong content-type: {r.headers.get('content-type')}"
        )
        assert len(r.content) > 500_000, f"ZIP too small: {len(r.content)} bytes"
        # ZIP magic bytes: PK\x03\x04
        assert r.content[:4] == b"PK\x03\x04", "Not a valid ZIP file"

    def test_zip_contains_31_png_and_captions(self, api_client, auth_headers):
        """Verify ZIP structure: 31 PNG files + captions.json"""
        import io
        import zipfile

        r = api_client.get(
            f"{BASE_URL}/api/campaign/countdown/zip",
            headers=auth_headers,
            timeout=60,
        )
        assert r.status_code == 200
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            names = z.namelist()
            pngs = [n for n in names if n.endswith(".png")]
            assert len(pngs) == 31, f"Expected 31 PNGs, got {len(pngs)}"
            has_captions = any(n.endswith("captions.json") for n in names)
            assert has_captions, f"captions.json missing from ZIP. Members: {names[:5]}..."
