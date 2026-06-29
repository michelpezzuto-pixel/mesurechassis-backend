"""
Security audit regression suite — SEC-001 (JWT), SEC-002 (tenant isolation),
P3 hardening (rate-limit, security headers, password policy) + general regression.

Run order is alphabetical: the rate-limit test is intentionally named
test_z_rate_limit so it executes LAST (it floods the per-IP login bucket).
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL") or os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL"
) or "https://stair-pro.preview.emergentagent.com"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

# Demo credentials (per /app/memory/test_credentials.md + services/seed.py)
ADMIN_DEMO = ("admin@demo.fr", "Demo1234!")              # tenant Escaliers Demo SARL
SOPHIE_TECH = ("sophie@mesureescaliee.com", "Demo1234!")  # same tenant as Marie
MARC_SOLO = ("marc@mesureescalier.com", "Demo1234!")     # tenant Marc Escaliers Indépendant


# ─────────────────────────── helpers ───────────────────────────
def _login(email: str, password: str):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    return r


def _login_token(email: str, password: str) -> str:
    r = _login(email, password)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ─────────────── shared session-scoped tokens ───────────────
@pytest.fixture(scope="session")
def admin_demo_token():
    return _login_token(*ADMIN_DEMO)


@pytest.fixture(scope="session")
def sophie_token():
    return _login_token(*SOPHIE_TECH)


@pytest.fixture(scope="session")
def marc_token():
    return _login_token(*MARC_SOLO)


# Two fresh admins in 2 different freshly-created companies for SEC-002 cross-tenant test.
@pytest.fixture(scope="session")
def two_new_tenants():
    sfx = uuid.uuid4().hex[:8]
    email_a = f"test_admin_a_{sfx}@example.com"
    email_b = f"test_admin_b_{sfx}@example.com"
    pwd = "Strong1234"

    ra = requests.post(
        f"{API}/auth/register",
        json={
            "full_name": "Admin A",
            "email": email_a,
            "password": pwd,
            "company_name": f"Company A {sfx}",
        },
        timeout=15,
    )
    assert ra.status_code == 200, f"register A failed: {ra.status_code} {ra.text}"
    a = ra.json()
    rb = requests.post(
        f"{API}/auth/register",
        json={
            "full_name": "Admin B",
            "email": email_b,
            "password": pwd,
            "company_name": f"Company B {sfx}",
        },
        timeout=15,
    )
    assert rb.status_code == 200, f"register B failed: {rb.status_code} {rb.text}"
    b = rb.json()
    return {
        "a": {"token": a["token"], "user": a["user"], "email": email_a},
        "b": {"token": b["token"], "user": b["user"], "email": email_b},
    }


# ═════════════════════════════════════════════════════════════════
# A. SEC-001 — boot guard + admin demo login still works (bcrypt OK
#    with new JWT_SECRET)
# ═════════════════════════════════════════════════════════════════
class TestSec001JwtSecret:
    def test_a_admin_demo_login_succeeds(self):
        r = _login(*ADMIN_DEMO)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "token" in body and len(body["token"]) > 20
        assert body["user"]["email"] == ADMIN_DEMO[0]
        assert body["user"]["role"] == "admin"
        assert body["user"]["company_id"]  # must be set

    def test_b_wrong_password_returns_401(self):
        r = _login(ADMIN_DEMO[0], "WrongPass123")
        assert r.status_code == 401


# ═════════════════════════════════════════════════════════════════
# B. P3 — Security headers
# ═════════════════════════════════════════════════════════════════
class TestSecurityHeaders:
    def test_root_has_security_headers(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        h = {k.lower(): v for k, v in r.headers.items()}
        assert h.get("x-content-type-options") == "nosniff"
        assert h.get("x-frame-options") == "DENY"
        assert h.get("referrer-policy") == "no-referrer"


# ═════════════════════════════════════════════════════════════════
# C. P3 — Password policy
# ═════════════════════════════════════════════════════════════════
class TestPasswordPolicy:
    @pytest.mark.parametrize(
        "pwd,label",
        [
            ("shortpw", "too short"),
            ("abcdefgh", "no digit"),
            ("12345678", "no letter"),
        ],
    )
    def test_weak_password_rejected_422(self, pwd, label):
        sfx = uuid.uuid4().hex[:6]
        r = requests.post(
            f"{API}/auth/register",
            json={
                "full_name": "Weak",
                "email": f"weak_{sfx}@example.com",
                "password": pwd,
                "company_name": "Weak Co",
            },
            timeout=15,
        )
        assert r.status_code == 422, f"[{label}] expected 422 got {r.status_code}: {r.text}"

    def test_strong_password_accepted(self):
        sfx = uuid.uuid4().hex[:6]
        email = f"strong_{sfx}@example.com"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "full_name": "Strong",
                "email": email,
                "password": "Strong1234",
                "company_name": "Strong Co",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        # cleanup happens implicitly — these test users are isolated tenants


# ═════════════════════════════════════════════════════════════════
# D. SEC-002 — Cross-tenant isolation (two FRESH admins)
# ═════════════════════════════════════════════════════════════════
class TestSec002CrossTenantIsolation:
    def test_a_admin_b_cannot_see_admin_a_project(self, two_new_tenants):
        tok_a = two_new_tenants["a"]["token"]
        tok_b = two_new_tenants["b"]["token"]

        # A creates a project
        payload = {
            "client_nom": "Client_A_TEST",
            "client_prenom": "X",
            "address": "1 rue A",
            "postal_code": "75001",
            "city": "Paris",
        }
        r = requests.post(f"{API}/projects", json=payload, headers=_auth(tok_a), timeout=15)
        assert r.status_code == 200, r.text
        proj_a_id = r.json()["id"]
        two_new_tenants["project_a_id"] = proj_a_id  # stash for next tests

        # B listing must NOT contain A's project
        r = requests.get(f"{API}/projects", headers=_auth(tok_b), timeout=15)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert proj_a_id not in ids, "TENANT LEAK: Admin B can SEE Admin A's project in list"

        # A also confirms it sees its own project (sanity)
        r = requests.get(f"{API}/projects", headers=_auth(tok_a), timeout=15)
        assert r.status_code == 200
        assert proj_a_id in [p["id"] for p in r.json()]

    def test_b_admin_b_direct_get_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.get(f"{API}/projects/{pid}", headers=_auth(two_new_tenants["b"]["token"]), timeout=15)
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text}"

    def test_c_admin_b_put_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.put(
            f"{API}/projects/{pid}",
            json={"city": "Hacked"},
            headers=_auth(two_new_tenants["b"]["token"]),
            timeout=15,
        )
        assert r.status_code == 404

    def test_d_admin_b_delete_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.delete(f"{API}/projects/{pid}", headers=_auth(two_new_tenants["b"]["token"]), timeout=15)
        assert r.status_code == 404

    def test_e_admin_b_transmit_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.post(
            f"{API}/projects/{pid}/transmit",
            headers=_auth(two_new_tenants["b"]["token"]),
            timeout=15,
        )
        assert r.status_code == 404

    def test_f_admin_b_unlock_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.post(
            f"{API}/projects/{pid}/unlock",
            headers=_auth(two_new_tenants["b"]["token"]),
            timeout=15,
        )
        assert r.status_code == 404

    def test_g_admin_b_integration_returns_404(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.get(
            f"{API}/integration/sites/{pid}",
            headers=_auth(two_new_tenants["b"]["token"]),
            timeout=15,
        )
        assert r.status_code == 404

    def test_h_admin_a_can_still_access_own_project(self, two_new_tenants):
        pid = two_new_tenants["project_a_id"]
        r = requests.get(f"{API}/projects/{pid}", headers=_auth(two_new_tenants["a"]["token"]), timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == pid


# ═════════════════════════════════════════════════════════════════
# E. SEC-002 — Existing demo tenants must also be isolated
#    (admin@demo.fr vs marc@mesureescalier.com)
# ═════════════════════════════════════════════════════════════════
class TestSec002DemoTenants:
    def test_a_marie_does_not_see_marc_projects(self, admin_demo_token, marc_token):
        # Marc creates a project in his own tenant
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "MarcClient_TEST", "address": "Marc 1"},
            headers=_auth(marc_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        marc_pid = r.json()["id"]

        # Marie's list must not include it
        r = requests.get(f"{API}/projects", headers=_auth(admin_demo_token), timeout=15)
        assert r.status_code == 200
        assert marc_pid not in [p["id"] for p in r.json()], "TENANT LEAK Marie→Marc"

        # And direct GET should 404
        r = requests.get(
            f"{API}/projects/{marc_pid}", headers=_auth(admin_demo_token), timeout=15
        )
        assert r.status_code == 404

        # Marc himself can still see it
        r = requests.get(f"{API}/projects/{marc_pid}", headers=_auth(marc_token), timeout=15)
        assert r.status_code == 200

        # cleanup
        requests.delete(f"{API}/projects/{marc_pid}", headers=_auth(marc_token), timeout=15)


# ═════════════════════════════════════════════════════════════════
# F. SEC-002 — Same-tenant visibility (Marie admin + Sophie tech)
# ═════════════════════════════════════════════════════════════════
class TestSec002SameTenantVisibility:
    def test_sophie_sees_marie_project(self, admin_demo_token, sophie_token):
        # Marie creates a project
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "MarieClient_TEST", "address": "Marie 1"},
            headers=_auth(admin_demo_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        pid = r.json()["id"]

        # Sophie must see it (technicien sees unassigned + assigned in own company)
        r = requests.get(f"{API}/projects", headers=_auth(sophie_token), timeout=15)
        assert r.status_code == 200
        assert pid in [p["id"] for p in r.json()], "Same-tenant tech CANNOT see admin project (regression)"

        # cleanup
        requests.delete(f"{API}/projects/{pid}", headers=_auth(admin_demo_token), timeout=15)


# ═════════════════════════════════════════════════════════════════
# G. REGRESSION — Project CRUD + transmit/unlock + photos + stats
#    + user invite/delete within same tenant
# ═════════════════════════════════════════════════════════════════
class TestRegression:
    def test_a_full_project_crud(self, admin_demo_token):
        h = _auth(admin_demo_token)
        # Create
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "CRUD_TEST", "address": "10 r CRUD", "city": "Lyon"},
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        pid = r.json()["id"]

        # Read
        r = requests.get(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.status_code == 200
        assert r.json()["client_nom"] == "CRUD_TEST"

        # Update
        r = requests.put(
            f"{API}/projects/{pid}", json={"city": "Marseille"}, headers=h, timeout=15
        )
        assert r.status_code == 200

        r = requests.get(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.json()["city"] == "Marseille"

        # Transmit → locked
        r = requests.post(f"{API}/projects/{pid}/transmit", headers=h, timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.json()["locked"] is True

        # Unlock
        r = requests.post(f"{API}/projects/{pid}/unlock", headers=h, timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.json()["locked"] is False

        # Delete
        r = requests.delete(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{API}/projects/{pid}", headers=h, timeout=15)
        assert r.status_code == 404

    def test_b_stairs_v2_crud(self, admin_demo_token):
        h = _auth(admin_demo_token)
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "STAIRS_TEST", "address": "stair st"},
            headers=h,
            timeout=15,
        )
        pid = r.json()["id"]

        # create stair
        r = requests.post(
            f"{API}/projects/{pid}/stairs",
            json={"name": "E1", "shape": "droit"},
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]

        # list stairs
        r = requests.get(f"{API}/projects/{pid}/stairs", headers=h, timeout=15)
        assert r.status_code == 200
        assert any(s["id"] == sid for s in r.json())

        # update
        r = requests.patch(
            f"{API}/projects/{pid}/stairs/{sid}",
            json={"name": "E1-renamed"},
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200

        # delete
        r = requests.delete(f"{API}/projects/{pid}/stairs/{sid}", headers=h, timeout=15)
        assert r.status_code == 200

        # cleanup project
        requests.delete(f"{API}/projects/{pid}", headers=h, timeout=15)

    def test_c_photos_crud(self, admin_demo_token):
        h = _auth(admin_demo_token)
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "PHOTO_TEST", "address": "x"},
            headers=h,
            timeout=15,
        )
        pid = r.json()["id"]

        # Add photo
        r = requests.post(
            f"{API}/projects/{pid}/photos",
            json={"base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgAAIAAAUAAeImBZsAAAAASUVORK5CYII=", "caption": "test"},
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        photo_id = r.json()["id"]

        # List
        r = requests.get(f"{API}/projects/{pid}/photos", headers=h, timeout=15)
        assert r.status_code == 200
        assert any(p["id"] == photo_id for p in r.json())

        # Update caption
        r = requests.patch(
            f"{API}/projects/{pid}/photos/{photo_id}",
            json={"caption": "updated"},
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200

        # Delete
        r = requests.delete(f"{API}/projects/{pid}/photos/{photo_id}", headers=h, timeout=15)
        assert r.status_code == 200

        requests.delete(f"{API}/projects/{pid}", headers=h, timeout=15)

    def test_d_stats_endpoint(self, admin_demo_token):
        r = requests.get(f"{API}/stats", headers=_auth(admin_demo_token), timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("total_projects", "by_status", "total_measurements"):
            assert key in body, f"missing key {key} in stats: {body}"

    def test_e_exports_pdf(self, admin_demo_token):
        h = _auth(admin_demo_token)
        r = requests.post(
            f"{API}/projects",
            json={"client_nom": "EXPORT_TEST", "address": "exp"},
            headers=h,
            timeout=15,
        )
        pid = r.json()["id"]
        # PDF and DXF endpoints (route presence/200 or 404 if requires measurement)
        for fmt in ("pdf", "dxf"):
            r = requests.get(f"{API}/exports/{fmt}/{pid}", headers=h, timeout=20)
            # Accept 200 or 404 (no measurement yet) — anything 5xx is a regression
            assert r.status_code < 500, f"exports/{fmt} returned {r.status_code}: {r.text[:200]}"
        requests.delete(f"{API}/projects/{pid}", headers=h, timeout=15)

    def test_f_user_invite_and_delete_same_tenant(self, admin_demo_token):
        h = _auth(admin_demo_token)
        sfx = uuid.uuid4().hex[:6]
        email = f"invited_{sfx}@example.com"
        r = requests.post(
            f"{API}/users",
            json={
                "full_name": "Invited Tech",
                "email": email,
                "password": "Strong1234",
                "role": "technicien",
            },
            headers=h,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        # invited user should inherit Marie's company_id
        assert r.json()["company_id"], "invited user missing company_id"

        # delete
        r = requests.delete(f"{API}/users/{uid}", headers=h, timeout=15)
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════
# Z. P3 — Rate limit on /api/auth/login (MUST RUN LAST: floods bucket)
# ═════════════════════════════════════════════════════════════════
class TestZRateLimit:
    def test_login_returns_429_after_threshold(self):
        # The middleware allows max 30 attempts per 5 min per IP.
        # Earlier tests already consumed some attempts (login fixtures + wrong-pwd test),
        # so simply hammer ~35 wrong passwords here — at least one must come back 429.
        got_429 = False
        last_status = None
        for i in range(40):
            r = _login(ADMIN_DEMO[0], f"wrong_{i}")
            last_status = r.status_code
            if r.status_code == 429:
                got_429 = True
                # Verify Retry-After header present
                assert "retry-after" in {k.lower() for k in r.headers.keys()}, (
                    "429 response missing Retry-After header"
                )
                break
            time.sleep(0.05)
        assert got_429, f"never received 429 after 40 attempts (last={last_status})"
