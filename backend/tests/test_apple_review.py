"""Apple Review demo account verification — Build 102 submission.

Verifies the demo account `applereview@mesurechassis.com` is fully functional:
- Login returns JWT
- account_type=artisan and artisan_mode=true (iOS-compatible)
- subscription_status=trial with expiration in the future
- role=admin
- Yann access works
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "applereview@mesurechassis.com"
PASSWORD = "AppleReview2026!"


# ---- Module-scoped login -------------------------------------------------
@pytest.fixture(scope="module")
def login_response():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    return r


@pytest.fixture(scope="module")
def token(login_response):
    assert login_response.status_code == 200, (
        f"Login failed: {login_response.status_code} {login_response.text}"
    )
    data = login_response.json()
    tok = data.get("access_token")
    assert tok, f"No access_token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Test 1 : Login returns 200 + valid JWT ------------------------------
def test_login_returns_200_with_jwt(login_response):
    assert login_response.status_code == 200, (
        f"Apple Review login MUST work. Got {login_response.status_code} "
        f"{login_response.text}"
    )
    data = login_response.json()
    assert "access_token" in data, "Missing access_token"
    assert "user" in data, "Missing user object"
    assert data["user"]["email"] == EMAIL


# ---- Test 2 : Company profile is artisan_mode + account_type=artisan -----
def test_company_profile_is_artisan(auth_headers):
    r = requests.get(f"{API}/company/profile", headers=auth_headers, timeout=10)
    assert r.status_code == 200, f"Company profile failed: {r.text}"
    data = r.json()
    assert data.get("account_type") == "artisan", (
        f"account_type MUST be 'artisan' for Apple Review, got "
        f"{data.get('account_type')!r}"
    )
    assert data.get("artisan_mode") is True, (
        f"artisan_mode MUST be true for Apple Review, got "
        f"{data.get('artisan_mode')!r}"
    )


# ---- Test 3 : Subscription status = trial, expires in future -------------
# NB : subscription_status & subscription_expires_at are on the COMPANY doc,
# exposed via /api/company/profile (NOT /api/auth/me — UserPublic model
# does not carry them). The Apple Review spec is checked against that
# endpoint.
def test_subscription_status_trial(auth_headers):
    r = requests.get(f"{API}/company/profile", headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("subscription_status") == "trial", (
        f"subscription_status MUST be 'trial' (Apple Review spec), "
        f"got {data.get('subscription_status')!r}."
    )


def test_subscription_expires_in_future(auth_headers):
    r = requests.get(f"{API}/company/profile", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    exp = r.json().get("subscription_expires_at")
    assert exp, "subscription_expires_at is missing"
    exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
    assert exp_dt > datetime.now(timezone.utc), (
        f"Subscription must not be expired. exp={exp}"
    )
    assert exp_dt.year >= 2027, (
        f"Expected expiration in 2027, got {exp_dt.isoformat()}"
    )


# ---- Test 4 : Role admin ------------------------------------------------
def test_user_role_admin(auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("role") == "admin", (
        f"role MUST be 'admin' for Apple Review, got {data.get('role')!r}"
    )


# ---- Test 5 : Yann quota allowed --------------------------------------
def test_yann_quota_allowed(auth_headers):
    r = requests.get(f"{API}/yann/quota", headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("allowed") is True, (
        f"Yann quota MUST allow access (BETA_MODE=True). Response: {data}"
    )


# ---- Test 6 : Yann chat returns a valid LLM response ------------------
def test_yann_chat_returns_reply(auth_headers):
    r = requests.post(
        f"{API}/yann/chat",
        json={"message": "Hello"},
        headers={**auth_headers, "Content-Type": "application/json"},
        timeout=60,
    )
    assert r.status_code == 200, f"Yann chat failed: {r.status_code} {r.text}"
    data = r.json()
    assert "reply" in data
    assert isinstance(data["reply"], str) and len(data["reply"]) > 0, (
        f"Empty Yann reply: {data}"
    )
