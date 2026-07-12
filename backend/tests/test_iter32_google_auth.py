"""Iter 32 — Emergent Google Sign-In endpoint + regression.

Scope (per review_request):
  1. POST /api/auth/google/session error-handling paths only
     (no happy path — needs real Emergent OAuth session_id)
     - empty/missing session_id → 400 "session_id requis"
     - invalid random session_id → 401 "Session Google invalide ou expirée"
     - extra fields silently ignored (Pydantic default)
  2. Regression:
     - POST /api/auth/login (artisan@mesurechassis.fr / artisan123)
     - GET  /api/auth/me
     - GET  /api/campaign/auto-send/status (owner)
     - GET  /api/_downloads/site-v2-4tiers (application/zip, ~1.6 MB)
"""
from __future__ import annotations

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api" if BASE_URL else "http://localhost:8001/api"

OWNER_EMAIL = "artisan@mesurechassis.fr"
OWNER_PASSWORD = "artisan123"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_token(http):
    r = http.post(
        f"{API}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"owner login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data
    return data["access_token"]


# ---------------------------------------------------------------------------
# 1. Google Sign-In endpoint — ERROR PATHS ONLY
# ---------------------------------------------------------------------------
class TestGoogleSessionErrorPaths:
    """POST /api/auth/google/session — error branches only.

    Happy path requires a real Emergent OAuth session_id (real Google browser
    flow), so is intentionally skipped.
    """

    def test_missing_body_returns_422(self, http):
        """No JSON body → FastAPI 422 (Pydantic missing required)."""
        r = http.post(f"{API}/auth/google/session", timeout=15)
        # Pydantic validation returns 422 when the body itself is empty.
        assert r.status_code == 422, (r.status_code, r.text)

    def test_missing_session_id_field_returns_422(self, http):
        """Body without `session_id` → 422 (Pydantic validation)."""
        r = http.post(f"{API}/auth/google/session", json={}, timeout=15)
        assert r.status_code == 422, (r.status_code, r.text)
        body = r.json()
        # Confirm the missing field points to session_id
        assert "session_id" in r.text

    def test_empty_string_session_id_returns_400(self, http):
        """Empty string after strip → HTTPException(400, 'session_id requis')."""
        r = http.post(
            f"{API}/auth/google/session",
            json={"session_id": ""},
            timeout=15,
        )
        assert r.status_code == 400, (r.status_code, r.text)
        assert r.json().get("detail") == "session_id requis"

    def test_whitespace_only_session_id_returns_400(self, http):
        """Whitespace-only → still 'session_id requis' after strip."""
        r = http.post(
            f"{API}/auth/google/session",
            json={"session_id": "   "},
            timeout=15,
        )
        assert r.status_code == 400, (r.status_code, r.text)
        assert r.json().get("detail") == "session_id requis"

    def test_invalid_random_session_id_returns_401(self, http):
        """Random session_id → Emergent rejects → 401.

        Emergent's /auth/v1/env/oauth/session-data returns non-200 for any
        unknown session_id, which the endpoint maps to
        HTTPException(401, 'Session Google invalide ou expirée. Réessayez.')
        """
        random_sid = f"invalid-{uuid.uuid4().hex}-{uuid.uuid4().hex}"
        r = http.post(
            f"{API}/auth/google/session",
            json={"session_id": random_sid},
            timeout=30,  # calls out to Emergent
        )
        # If Emergent is unreachable from this pod, endpoint would return 502
        # — still a valid guard, but not what we want to certify here.
        if r.status_code == 502:
            pytest.skip(
                "Emergent session API unreachable from test pod — "
                "cannot verify 401 path. Status: 502"
            )
        assert r.status_code == 401, (r.status_code, r.text)
        detail = r.json().get("detail", "")
        assert "invalide" in detail.lower() or "expirée" in detail.lower(), detail

    def test_extra_fields_are_silently_ignored(self, http):
        """Pydantic default = ignore extras. Extra keys must not 422."""
        random_sid = f"invalid-{uuid.uuid4().hex}"
        r = http.post(
            f"{API}/auth/google/session",
            json={
                "session_id": random_sid,
                "station_id": "no-such-station",
                "some_random_field": "should be ignored",
                "email": "attacker@evil.com",  # must NOT be honored
                "role": "admin",  # must NOT be honored
            },
            timeout=30,
        )
        # Should still reach the Emergent verification step and get 401
        # (not 422 for unexpected fields).
        if r.status_code == 502:
            pytest.skip("Emergent unreachable — 502")
        assert r.status_code == 401, (
            f"Extra fields should be ignored, expected 401, got "
            f"{r.status_code}: {r.text}"
        )

    def test_station_id_accepts_optional_string(self, http):
        """station_id is Optional[str] — providing it should not affect the
        error path (still 401 for invalid sid)."""
        r = http.post(
            f"{API}/auth/google/session",
            json={
                "session_id": f"invalid-{uuid.uuid4().hex}",
                "station_id": "f3ecaca4-a86c-482d-b0ac-21022fef2c8c",
            },
            timeout=30,
        )
        if r.status_code == 502:
            pytest.skip("Emergent unreachable — 502")
        assert r.status_code == 401, (r.status_code, r.text)

    def test_station_id_type_validation(self, http):
        """station_id must be a string; providing an int should 422."""
        r = http.post(
            f"{API}/auth/google/session",
            json={"session_id": "x" * 20, "station_id": 12345},
            timeout=15,
        )
        # Pydantic v2 may coerce int→str depending on config. We accept both
        # 422 (strict) or 401 (coerced then Emergent-rejected).
        assert r.status_code in (401, 422, 502), (r.status_code, r.text)


# ---------------------------------------------------------------------------
# 2. Regression — existing endpoints must still work
# ---------------------------------------------------------------------------
class TestRegressionAfterGoogleAuthAdd:
    """Ensure adding /auth/google/session did not break existing routes."""

    def test_login_owner_success(self, http):
        r = http.post(
            f"{API}/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
            timeout=30,
        )
        assert r.status_code == 200, (r.status_code, r.text)
        data = r.json()
        assert "access_token" in data
        assert data.get("token_type") == "bearer"
        assert "user" in data
        assert data["user"]["email"] == OWNER_EMAIL

    def test_auth_me(self, http, owner_token):
        r = http.get(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {owner_token}"},
            timeout=15,
        )
        assert r.status_code == 200, (r.status_code, r.text)
        me = r.json()
        assert me["email"] == OWNER_EMAIL
        assert me.get("role") == "admin"

    def test_campaign_auto_send_status_owner(self, http, owner_token):
        r = http.get(
            f"{API}/campaign/auto-send/status",
            headers={"Authorization": f"Bearer {owner_token}"},
            timeout=15,
        )
        assert r.status_code == 200, (r.status_code, r.text)
        payload = r.json()
        assert payload.get("enabled") is True, payload
        schedule = payload.get("schedule", "")
        # Per review_request the label should read "16h30 Europe/Brussels (Lun-Ven)"
        assert "16h30" in schedule, f"schedule missing time: {schedule!r}"
        assert "Europe/Brussels" in schedule, (
            f"schedule missing tz: {schedule!r}"
        )
        # Review_request expects "Lun-Ven" but current code (per iter31) may
        # still return "Mar-Ven". Report both cases.
        assert (
            "Lun-Ven" in schedule or "Mar-Ven" in schedule
        ), f"schedule missing day-range: {schedule!r}"
        # Flag if still Mar-Ven — regression review_request wants Lun-Ven.
        if "Mar-Ven" in schedule:
            pytest.fail(
                f"REGRESSION: schedule label still 'Mar-Ven' — review_request "
                f"expects 'Lun-Ven (Mon-Fri)'. Actual: {schedule!r}"
            )

    def test_downloads_site_v2_4tiers(self, http):
        # Do not follow-redirect: we want to see the actual FileResponse.
        r = http.get(f"{API}/_downloads/site-v2-4tiers", timeout=30)
        assert r.status_code == 200, (r.status_code, r.text[:200])
        ctype = r.headers.get("content-type", "").lower()
        assert "application/zip" in ctype or "application/octet-stream" in ctype, ctype
        # Content-Length ~ 1.6 MB — allow generous range 0.5 → 5 MB
        clen = int(r.headers.get("content-length", "0") or "0")
        assert clen > 100_000, f"zip suspiciously small: {clen} bytes"
        assert clen < 10 * 1024 * 1024, f"zip suspiciously large: {clen} bytes"
        # Sanity: first 2 bytes of a ZIP file are "PK"
        first_bytes = r.content[:2]
        assert first_bytes == b"PK", f"not a zip file, first bytes: {first_bytes!r}"
