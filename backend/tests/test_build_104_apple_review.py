"""Apple Review Build 104 — Password reset verification.

Apple Review feedback (Build 103):
- 2.1: Could not log in with the test credentials (presumably difficult to type `!` on iOS keyboard)
- 3.1.1 / 3.1.3(c): Business-registration must not be exposed in iOS app

Fixes verified here (backend-side):
- Password of `applereview@mesurechassis.com` reset to `MesureChassis2026`
- Old password `AppleReview2026!` MUST be rejected
- Account remains fully usable (auth/me, chantiers, users)
- Both LOCAL (preview) and PRODUCTION Railway endpoints must accept new password
"""
from __future__ import annotations

import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
LOCAL_BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
LOCAL_API = f"{LOCAL_BASE}/api"

PROD_API = "https://capable-gratitude-production-db51.up.railway.app/api"

EMAIL = "applereview@mesurechassis.com"
NEW_PASSWORD = "MesureChassis2026"
OLD_PASSWORD = "AppleReview2026!"

TIMEOUT = 30


# ---------- LOCAL (preview) ----------------------------------------------
class TestLocalPasswordReset:
    """Verify password reset on the preview backend."""

    def test_login_with_new_password_returns_200(self):
        r = requests.post(
            f"{LOCAL_API}/auth/login",
            json={"email": EMAIL, "password": NEW_PASSWORD},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, (
            f"LOCAL: New password MUST work. Got {r.status_code} {r.text}"
        )
        data = r.json()
        assert "access_token" in data, f"Missing access_token: {data}"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 20
        assert data.get("user", {}).get("email") == EMAIL

    def test_login_with_old_password_returns_401(self):
        r = requests.post(
            f"{LOCAL_API}/auth/login",
            json={"email": EMAIL, "password": OLD_PASSWORD},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401, (
            f"LOCAL: Old password MUST be rejected (401). Got {r.status_code} {r.text}"
        )


# ---------- LOCAL — full app access via new password ---------------------
@pytest.fixture(scope="module")
def local_token():
    r = requests.post(
        f"{LOCAL_API}/auth/login",
        json={"email": EMAIL, "password": NEW_PASSWORD},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"Pre-req login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def local_headers(local_token):
    return {"Authorization": f"Bearer {local_token}"}


class TestLocalAppAccess:
    """After login with new pwd, the account must be fully usable."""

    def test_auth_me_returns_admin(self, local_headers):
        r = requests.get(f"{LOCAL_API}/auth/me", headers=local_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("email") == EMAIL
        assert data.get("role") == "admin", f"Expected role=admin, got {data.get('role')!r}"

    def test_chantiers_list_has_demo_data(self, local_headers):
        r = requests.get(f"{LOCAL_API}/chantiers", headers=local_headers, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        # Endpoint may return a list directly or wrapped under "chantiers"/"items"
        items = data if isinstance(data, list) else (
            data.get("chantiers") or data.get("items") or []
        )
        assert isinstance(items, list), f"Unexpected payload: {type(data)} {data!r}"
        assert len(items) >= 3, (
            f"Expected 3+ demo chantiers, got {len(items)}. Sample: {items[:1]}"
        )

    def test_users_list_admin_can_see(self, local_headers):
        r = requests.get(f"{LOCAL_API}/users", headers=local_headers, timeout=TIMEOUT)
        assert r.status_code == 200, (
            f"Admin must access /users. Got {r.status_code} {r.text}"
        )


# ---------- PRODUCTION Railway ------------------------------------------
class TestProductionPasswordReset:
    """Verify the new password also works on Railway production."""

    def _reach(self):
        try:
            r = requests.get(f"{PROD_API}/health", timeout=10)
            return r.status_code < 500
        except Exception:
            return False

    def test_prod_login_with_new_password(self):
        if not self._reach():
            pytest.skip("Production Railway endpoint not reachable from preview env.")
        r = requests.post(
            f"{PROD_API}/auth/login",
            json={"email": EMAIL, "password": NEW_PASSWORD},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, (
            f"PROD: New password MUST work on Railway. "
            f"Got {r.status_code} {r.text}"
        )
        data = r.json()
        assert "access_token" in data
        assert data.get("user", {}).get("email") == EMAIL

    def test_prod_login_with_old_password_rejected(self):
        if not self._reach():
            pytest.skip("Production Railway endpoint not reachable from preview env.")
        r = requests.post(
            f"{PROD_API}/auth/login",
            json={"email": EMAIL, "password": OLD_PASSWORD},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401, (
            f"PROD: Old password MUST be rejected. Got {r.status_code} {r.text}"
        )
