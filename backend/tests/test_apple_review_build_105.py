"""
Build 105+ Apple Review credentials verification.

Tests:
1. PROD Railway login with NEW lowercase password -> 200 + admin JWT
2. PROD rejects OLD passwords -> 401
3. LOCAL backend login with NEW password -> 200
4. Authenticated endpoints work with the new token (/auth/me, /chantiers, /users)
"""
import os
import pytest
import requests

PROD_URL = "https://capable-gratitude-production-db51.up.railway.app"
LOCAL_URL = "http://localhost:8001"

EMAIL = "applereview@mesurechassis.com"
NEW_PASSWORD = "applereview2026"
OLD_PASSWORD_1 = "MesureChassis2026"
OLD_PASSWORD_2 = "AppleReview2026!"


def _login(base_url, email, password):
    return requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )


# ---------- PROD ----------
class TestProdAppleReviewLogin:
    def test_prod_login_new_password_success(self):
        r = _login(PROD_URL, EMAIL, NEW_PASSWORD)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        # JWT field can be 'access_token' or 'token'
        token = data.get("access_token") or data.get("token")
        assert token, f"No JWT token in response: {data}"
        assert len(token.split(".")) == 3, "Token does not look like a JWT"
        user = data.get("user") or {}
        assert user.get("email") == EMAIL
        assert user.get("role") == "admin", f"Expected role=admin, got {user.get('role')}"
        # cache token for downstream tests
        pytest.prod_token = token
        pytest.prod_user = user

    def test_prod_login_old_password_1_rejected(self):
        r = _login(PROD_URL, EMAIL, OLD_PASSWORD_1)
        assert r.status_code == 401, f"Expected 401 for old pwd '{OLD_PASSWORD_1}', got {r.status_code}: {r.text[:200]}"

    def test_prod_login_old_password_2_rejected(self):
        r = _login(PROD_URL, EMAIL, OLD_PASSWORD_2)
        assert r.status_code == 401, f"Expected 401 for old pwd '{OLD_PASSWORD_2}', got {r.status_code}: {r.text[:200]}"


# ---------- LOCAL ----------
class TestLocalAppleReviewLogin:
    def test_local_login_new_password_success(self):
        r = _login(LOCAL_URL, EMAIL, NEW_PASSWORD)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        token = data.get("access_token") or data.get("token")
        assert token, f"No token: {data}"
        pytest.local_token = token


# ---------- Authenticated endpoints on PROD ----------
class TestProdAuthenticatedAccess:
    def _auth_headers(self):
        token = getattr(pytest, "prod_token", None)
        if not token:
            pytest.skip("Prod login failed, skipping authenticated checks")
        return {"Authorization": f"Bearer {token}"}

    def test_auth_me(self):
        r = requests.get(f"{PROD_URL}/api/auth/me", headers=self._auth_headers(), timeout=20)
        assert r.status_code == 200, f"/auth/me failed: {r.status_code} {r.text[:200]}"
        me = r.json()
        assert me.get("email") == EMAIL
        assert me.get("email_verified_at") is not None, "email_verified_at should not be null"
        assert me.get("status") == "active", f"Expected status=active, got {me.get('status')}"

    def test_chantiers_list(self):
        r = requests.get(f"{PROD_URL}/api/chantiers", headers=self._auth_headers(), timeout=20)
        assert r.status_code == 200, f"/chantiers failed: {r.status_code} {r.text[:200]}"
        payload = r.json()
        # may be a list or {items:[...]} shape
        items = payload if isinstance(payload, list) else payload.get("items") or payload.get("chantiers") or []
        assert len(items) >= 3, f"Expected >=3 chantiers, got {len(items)}"

    def test_users_list_admin(self):
        r = requests.get(f"{PROD_URL}/api/users", headers=self._auth_headers(), timeout=20)
        assert r.status_code == 200, f"/users failed (admin): {r.status_code} {r.text[:200]}"
