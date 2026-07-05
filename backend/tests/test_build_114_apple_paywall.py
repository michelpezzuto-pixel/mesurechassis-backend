"""Build 114 — Apple Guideline 2.1a paywall fix verification.

Vérifie que :
  * /api/company/profile renvoie `beta_mode=false` pour apple-review-expired
    et `beta_mode=true` pour apple-review-demo (compte actif).
  * /api/chantiers renvoie HTTP 402 avec code=subscription_expired pour
    le compte expiré, et 200 pour le compte actif.
"""
import os
import pytest
import requests

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") if os.environ.get("EXPO_PUBLIC_BACKEND_URL") else None

# Fallback : read from frontend/.env
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("EXPO_PUBLIC_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

PASSWORD = "MesureChassis2026"
EMAIL_EXPIRED = "applereview-expired@mesurechassis.com"
EMAIL_ACTIVE = "applereview@mesurechassis.com"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password},
                      timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def token_expired():
    return _login(EMAIL_EXPIRED, PASSWORD)


@pytest.fixture(scope="module")
def token_active():
    return _login(EMAIL_ACTIVE, PASSWORD)


# ── company/profile beta_mode ────────────────────────────────────────
def test_company_profile_expired_beta_mode_false(token_expired):
    r = requests.get(f"{BASE_URL}/api/company/profile",
                     headers={"Authorization": f"Bearer {token_expired}"},
                     timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["company_id"] == "apple-review-expired"
    # 🎯 CRITICAL : must be False for the paywall to display
    assert data["beta_mode"] is False, \
        f"expired company must NOT be in beta_mode, got: {data.get('beta_mode')}"
    assert data.get("subscription_status") in ("suspended", "expired") \
        or (data.get("subscription_expires_at") is not None), \
        f"expired account should have suspended/expired status; got {data.get('subscription_status')}"


def test_company_profile_active_beta_mode_true(token_active):
    r = requests.get(f"{BASE_URL}/api/company/profile",
                     headers={"Authorization": f"Bearer {token_active}"},
                     timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["company_id"] == "apple-review-demo"
    # ⚠️ Note: beta_mode dépend de BETA_MODE env var. Selon spec du bugfix,
    # doit être True pour toutes sauf apple-review-expired.
    assert data["beta_mode"] is True, \
        f"active demo company should be in beta_mode, got: {data.get('beta_mode')}"


# ── chantiers 402 ────────────────────────────────────────────────────
def test_chantiers_expired_returns_402(token_expired):
    r = requests.get(f"{BASE_URL}/api/chantiers",
                     headers={"Authorization": f"Bearer {token_expired}"},
                     timeout=20)
    assert r.status_code == 402, \
        f"expected 402 for expired account, got {r.status_code}: {r.text[:200]}"
    detail = r.json().get("detail", {})
    assert detail.get("code") == "subscription_expired", \
        f"expected code=subscription_expired, got {detail}"


def test_chantiers_active_returns_200(token_active):
    r = requests.get(f"{BASE_URL}/api/chantiers",
                     headers={"Authorization": f"Bearer {token_active}"},
                     timeout=20)
    assert r.status_code == 200, \
        f"expected 200 for active account, got {r.status_code}: {r.text[:200]}"
    assert isinstance(r.json(), list)


# ── auth/me works for both (should NOT be blocked by paywall) ─────────
def test_auth_me_expired_returns_200(token_expired):
    r = requests.get(f"{BASE_URL}/api/auth/me",
                     headers={"Authorization": f"Bearer {token_expired}"},
                     timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL_EXPIRED
