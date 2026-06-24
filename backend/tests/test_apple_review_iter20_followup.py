"""
Iteration 20 — Apple Review follow-up (Safari View Controller + URL anti-404).

Backend regression scope:
  - PROD Railway /api/auth/login with the documented Apple Review credentials -> 200
  - LOCAL backend /api/auth/login with same creds -> 200
  - GET /api/auth/me with token -> 200, role=admin

Note: the review request mentions password 'MesureChassis2026' but
/app/memory/test_credentials.md (updated in iter 19) confirms the current
active password is the lowercase 'applereview2026'. We test the documented one
first and treat it as the canonical credential.

URL anti-404 sanity checks:
  - HEAD https://www.mesurechassis.com -> 200 / 301 / 302
  - HEAD https://www.mesurechassis.com/inscription -> 404 (expected — explains the URL change)
"""
import os
import pytest
import requests

PROD_URL = "https://capable-gratitude-production-db51.up.railway.app"
LOCAL_URL = "http://localhost:8001"
PUBLIC_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL",
    "https://window-field-app.preview.emergentagent.com",
).rstrip("/")

EMAIL = "applereview@mesurechassis.com"
# Password as specified in the review request (verified working on PROD/LOCAL today).
# NOTE: /app/memory/test_credentials.md currently says 'applereview2026' but that
# password is REJECTED by PROD/LOCAL — the doc is stale, see iteration_20 report.
PASSWORD = "MesureChassis2026"
# The previous lowercase password from the doc that no longer works.
LEGACY_DOC_PASSWORD = "applereview2026"


def _login(base_url, password=PASSWORD):
    return requests.post(
        f"{base_url}/api/auth/login",
        json={"email": EMAIL, "password": password},
        timeout=25,
    )


# ─── Backend login regression ──────────────────────────────────────────────
class TestBackendLoginRegression:
    def test_prod_login_returns_200(self):
        r = _login(PROD_URL)
        assert r.status_code == 200, f"PROD login failed: {r.status_code} {r.text[:200]}"
        data = r.json()
        token = data.get("access_token") or data.get("token")
        assert token, f"No JWT in PROD login response: {data}"
        user = data.get("user") or {}
        assert user.get("role") == "admin", f"role should be admin, got {user.get('role')}"
        pytest.prod_token = token

    def test_local_login_returns_200(self):
        r = _login(LOCAL_URL)
        assert r.status_code == 200, f"LOCAL login failed: {r.status_code} {r.text[:200]}"
        data = r.json()
        token = data.get("access_token") or data.get("token")
        assert token, f"No JWT in LOCAL login response: {data}"

    def test_public_url_login_returns_200(self):
        # End-to-end through Kubernetes ingress (what mobile app actually hits)
        r = _login(PUBLIC_URL)
        assert r.status_code == 200, f"PUBLIC login failed: {r.status_code} {r.text[:200]}"

    def test_prod_auth_me_admin(self):
        token = getattr(pytest, "prod_token", None)
        if not token:
            pytest.skip("Prod login failed earlier")
        r = requests.get(
            f"{PROD_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        assert r.status_code == 200, f"/auth/me failed: {r.status_code} {r.text[:200]}"
        me = r.json()
        assert me.get("email") == EMAIL
        assert me.get("role") == "admin", f"role should be admin, got {me.get('role')}"
        assert me.get("status") == "active"
        assert me.get("email_verified_at") is not None

    def test_prod_rejects_legacy_password_from_request(self):
        # The previous doc-listed lowercase password is the one that's now rejected.
        r = _login(PROD_URL, password=LEGACY_DOC_PASSWORD)
        assert r.status_code == 401, (
            f"Stale doc password 'applereview2026' should be rejected, "
            f"got {r.status_code}: {r.text[:200]}"
        )


# ─── URL anti-404 verification (Apple rejection root cause) ────────────────
class TestRegistrationWebsiteUrl:
    def test_new_url_is_reachable(self):
        r = requests.head(
            "https://www.mesurechassis.com",
            allow_redirects=False,
            timeout=15,
        )
        assert r.status_code in (200, 301, 302), (
            f"Landing page should be reachable, got {r.status_code}"
        )

    def test_old_inscription_url_still_404(self):
        # Documenting the root cause of Apple's 2.1(a) rejection.
        r = requests.head(
            "https://www.mesurechassis.com/inscription",
            allow_redirects=False,
            timeout=15,
        )
        assert r.status_code == 404, (
            f"Expected 404 on /inscription (this is why URL was changed), got {r.status_code}"
        )
