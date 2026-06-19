"""Tests for the Affiliate Partners system (Build 9 — June 2026).

Covers:
- Admin-only CRUD endpoints (/api/partners)
- Validation rules (platform, reserved code prefix, duplicate code)
- Auto status switch when contract is signed
- Public tracking endpoints (/api/affiliate/...)
- PDF download endpoints (/api/_downloads/{partner-contract, roadmap-michel})
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")
assert BASE_URL, "EXPO_PUBLIC_BACKEND_URL must be set"
BASE_URL = BASE_URL.rstrip("/")

ADMIN_EMAIL = "cousin.admin@test.mesurechassis.com"
COMMERCIAL_EMAIL = "cousin.commercial@test.mesurechassis.com"
TECHNICIEN_EMAIL = "cousin.technicien@test.mesurechassis.com"
PWD = "Cousin2026!"


def _login(email: str, password: str = PWD) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers() -> dict:
    return {"Authorization": f"Bearer {_login(ADMIN_EMAIL)}"}


@pytest.fixture(scope="module")
def commercial_headers() -> dict:
    return {"Authorization": f"Bearer {_login(COMMERCIAL_EMAIL)}"}


@pytest.fixture(scope="module")
def technicien_headers() -> dict:
    return {"Authorization": f"Bearer {_login(TECHNICIEN_EMAIL)}"}


@pytest.fixture(scope="module")
def created_ids() -> list:
    """Track partner ids created during tests for teardown."""
    return []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin_headers, created_ids):
    yield
    # Soft-delete every partner created during tests
    for pid in created_ids:
        try:
            requests.delete(
                f"{BASE_URL}/api/partners/{pid}",
                headers=admin_headers,
                timeout=10,
            )
        except Exception:
            pass


# ────────────────────────────────────────────────────────────────────────
# 1. POST /api/partners
# ────────────────────────────────────────────────────────────────────────
class TestCreatePartner:
    def test_create_partner_valid(self, admin_headers, created_ids):
        payload = {
            "name": "TEST Influenceur Alpha",
            "email": "test_alpha@example.com",
            "platform": "tiktok",
            "handle": "@alpha",
            "audience_size": 10000,
        }
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json=payload,
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["platform"] == "tiktok"
        assert data["code"], "auto-generated code missing"
        assert data["status"] == "pending"
        assert data["commission_rate"] == 20.0
        assert data["commission_duration_months"] == 12
        assert data["contract_signed"] is False
        created_ids.append(data["id"])

    def test_create_partner_non_admin_commercial_403(self, commercial_headers):
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=commercial_headers,
            json={
                "name": "TEST Should Fail",
                "email": "x@example.com",
                "platform": "tiktok",
            },
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_create_partner_non_admin_technicien_403(self, technicien_headers):
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=technicien_headers,
            json={
                "name": "TEST Should Fail Tech",
                "email": "y@example.com",
                "platform": "tiktok",
            },
            timeout=15,
        )
        assert r.status_code == 403

    def test_create_partner_invalid_platform(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json={
                "name": "TEST Bad Platform",
                "email": "bp@example.com",
                "platform": "snapchat",
            },
            timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_create_partner_reserved_prefix(self, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json={
                "name": "TEST Reserved",
                "email": "res@example.com",
                "platform": "tiktok",
                "custom_code": "MC-XYZ",
            },
            timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "réservé" in r.text.lower() or "reserve" in r.text.lower()

    def test_create_partner_duplicate_custom_code(self, admin_headers, created_ids):
        code = "DUPCODE-001-XYZ"
        # 1st create
        r1 = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json={
                "name": "TEST Dup First",
                "email": "dup1@example.com",
                "platform": "youtube",
                "custom_code": code,
            },
            timeout=15,
        )
        assert r1.status_code in (200, 201), r1.text
        created_ids.append(r1.json()["id"])
        # 2nd with same code → 409
        r2 = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json={
                "name": "TEST Dup Second",
                "email": "dup2@example.com",
                "platform": "youtube",
                "custom_code": code,
            },
            timeout=15,
        )
        assert r2.status_code == 409, r2.text


# ────────────────────────────────────────────────────────────────────────
# 2-3. List & detail
# ────────────────────────────────────────────────────────────────────────
class TestListAndDetail:
    def test_list_partners_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/partners", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "partners" in data and "total" in data
        assert isinstance(data["partners"], list)
        assert data["total"] == len(data["partners"])

    def test_list_partners_non_admin_403(self, commercial_headers):
        r = requests.get(
            f"{BASE_URL}/api/partners", headers=commercial_headers, timeout=15
        )
        assert r.status_code == 403

    def test_get_partner_detail(self, admin_headers, created_ids):
        assert created_ids, "need at least one created partner"
        pid = created_ids[0]
        r = requests.get(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        )
        assert r.status_code == 200, r.text
        assert r.json()["id"] == pid

    def test_get_partner_not_found(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/partners/does-not-exist-xyz",
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# 4. PATCH
# ────────────────────────────────────────────────────────────────────────
class TestUpdatePartner:
    def test_patch_invalid_status(self, admin_headers, created_ids):
        pid = created_ids[0]
        r = requests.patch(
            f"{BASE_URL}/api/partners/{pid}",
            headers=admin_headers,
            json={"status": "banana"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_patch_contract_signed_auto_activates(self, admin_headers, created_ids):
        pid = created_ids[0]
        r = requests.patch(
            f"{BASE_URL}/api/partners/{pid}",
            headers=admin_headers,
            json={"contract_signed": True},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["contract_signed"] is True
        assert data.get("contract_signed_at"), "should set contract_signed_at"
        assert data["status"] == "active", "should auto-activate from pending"

    def test_patch_not_found(self, admin_headers):
        r = requests.patch(
            f"{BASE_URL}/api/partners/nope-xyz",
            headers=admin_headers,
            json={"notes": "x"},
            timeout=15,
        )
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# 6-7. Stats
# ────────────────────────────────────────────────────────────────────────
class TestStats:
    def test_partner_stats_zero(self, admin_headers, created_ids):
        # Use the 2nd partner (duplicate-code one) — fresh, no clicks/signups
        pid = created_ids[1] if len(created_ids) > 1 else created_ids[0]
        r = requests.get(
            f"{BASE_URL}/api/partners/{pid}/stats",
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ("clicks", "signups", "conversions"):
            assert d[key] == 0, f"{key} should be 0 for fresh partner"
        assert d["total_commission_due_eur"] == 0.0
        assert d["currency"] == "EUR"

    def test_partner_stats_not_found(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/partners/nope/stats",
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 404

    def test_global_summary(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/partners/stats/summary",
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        for key in (
            "total_partners",
            "active",
            "pending",
            "total_clicks",
            "total_signups",
            "total_conversions",
            "total_commission_due_eur",
            "total_commission_paid_eur",
        ):
            assert key in d, f"missing key {key}"
        assert d["total_partners"] >= 1
        assert d["active"] >= 1  # we activated one in TestUpdatePartner


# ────────────────────────────────────────────────────────────────────────
# 8-9. Public tracking
# ────────────────────────────────────────────────────────────────────────
class TestPublicTracking:
    def test_track_click_active_partner(self, admin_headers, created_ids):
        # created_ids[0] was set to active by TestUpdatePartner
        pid = created_ids[0]
        r = requests.get(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        )
        assert r.status_code == 200
        code = r.json()["code"]
        # No auth
        rc = requests.post(
            f"{BASE_URL}/api/affiliate/track-click",
            json={"code": code, "platform_source": "tiktok"},
            timeout=15,
        )
        assert rc.status_code == 200, rc.text
        assert rc.json().get("ok") is True

    def test_track_click_pending_partner(self, admin_headers, created_ids):
        # created_ids[1] should still be pending
        pid = created_ids[1] if len(created_ids) > 1 else created_ids[0]
        r = requests.get(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        )
        code = r.json()["code"]
        status = r.json()["status"]
        if status != "pending":
            pytest.skip(f"partner not pending: {status}")
        rc = requests.post(
            f"{BASE_URL}/api/affiliate/track-click",
            json={"code": code},
            timeout=15,
        )
        assert rc.status_code == 200
        body = rc.json()
        assert body.get("ok") is False
        assert body.get("reason") == "code_not_active"

    def test_track_click_unknown_code(self):
        r = requests.post(
            f"{BASE_URL}/api/affiliate/track-click",
            json={"code": "TOTALLY-FAKE-CODE-9999"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json().get("ok") is False

    def test_lookup_active(self, admin_headers, created_ids):
        pid = created_ids[0]
        code = requests.get(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        ).json()["code"]
        r = requests.get(
            f"{BASE_URL}/api/affiliate/lookup/{code}", timeout=15
        )
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is True
        assert "partner_name" in d
        assert "platform" in d
        assert "handle" in d

    def test_lookup_unknown(self):
        r = requests.get(
            f"{BASE_URL}/api/affiliate/lookup/NOPE-NOPE-NOPE", timeout=15
        )
        assert r.status_code == 200
        assert r.json()["found"] is False


# ────────────────────────────────────────────────────────────────────────
# 5. DELETE
# ────────────────────────────────────────────────────────────────────────
class TestDeletePartner:
    def test_delete_marks_terminated(self, admin_headers, created_ids):
        # Create one specifically for this test
        r = requests.post(
            f"{BASE_URL}/api/partners",
            headers=admin_headers,
            json={
                "name": "TEST To Delete",
                "email": "del@example.com",
                "platform": "instagram",
            },
            timeout=15,
        )
        assert r.status_code in (200, 201)
        pid = r.json()["id"]

        dr = requests.delete(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        )
        assert dr.status_code == 200
        assert dr.json().get("ok") is True

        # Verify status is terminated (not actually deleted)
        gr = requests.get(
            f"{BASE_URL}/api/partners/{pid}", headers=admin_headers, timeout=15
        )
        assert gr.status_code == 200
        assert gr.json()["status"] == "terminated"

    def test_delete_not_found(self, admin_headers):
        r = requests.delete(
            f"{BASE_URL}/api/partners/nope-nope-nope",
            headers=admin_headers,
            timeout=15,
        )
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────
# 10-11. PDF download endpoints (no auth)
# ────────────────────────────────────────────────────────────────────────
class TestPDFDownloads:
    def test_partner_contract_pdf(self):
        r = requests.get(
            f"{BASE_URL}/api/_downloads/partner-contract", timeout=30
        )
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_roadmap_michel_pdf(self):
        r = requests.get(
            f"{BASE_URL}/api/_downloads/roadmap-michel", timeout=30
        )
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
