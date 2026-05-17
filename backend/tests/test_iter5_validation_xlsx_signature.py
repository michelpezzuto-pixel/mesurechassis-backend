"""Iter5 tests: wall_type strict enum, xlsx export, signature endpoints."""
import os
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
API = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"


# ---------- module-level fixtures ----------
@pytest.fixture(scope="module")
def headers_admin():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@mesurechassis.fr", "password": "admin123"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def headers_commercial():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "commercial@mesurechassis.fr", "password": "commercial123"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def headers_tech():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "tech@mesurechassis.fr", "password": "tech123"}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def other_company_headers():
    """Register a fresh user with a different company_id."""
    email = f"TEST_other_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "TEST Other Co",
        "email": email,
        "password": "pass1234",
        "role": "admin",
        "company_id": f"TEST_co_{uuid.uuid4().hex[:6]}",
    }
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def chantier_id(headers_commercial, headers_admin):
    r = requests.post(f"{API}/chantiers",
                      json={"client_name": "TEST_Iter5Client",
                            "address": "1 rue de Test, 75000 Paris"},
                      headers=headers_commercial, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    requests.delete(f"{API}/chantiers/{cid}", headers=headers_admin, timeout=30)


# ---------- wall_type enum validation ----------
class TestWallTypeValidation:
    @pytest.mark.parametrize("wt", ["ite", "iti", "crepi_simple"])
    def test_valid_wall_types_accepted(self, headers_commercial, chantier_id, wt):
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": f"TEST_wt_{wt}", "wall_type": wt},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["wall_type"] == wt

    def test_invalid_wall_type_rejected_422(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_wt_invalid", "wall_type": "invalid_value"},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    def test_null_wall_type_allowed(self, headers_commercial, chantier_id):
        # omitted → None
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_wt_none"},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("wall_type") is None

    def test_explicit_null_wall_type_allowed(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_wt_explicit_null", "wall_type": None},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("wall_type") is None


# ---------- export.xlsx ----------
class TestExportXlsx:
    def test_export_xlsx_as_admin(self, headers_admin, chantier_id):
        r = requests.get(f"{API}/chantiers/{chantier_id}/export.xlsx",
                         headers=headers_admin, timeout=30)
        assert r.status_code == 200, r.text
        ct = r.headers.get("Content-Type", "")
        assert "spreadsheetml.sheet" in ct, f"Bad content-type: {ct}"
        assert r.content[:2] == b"PK", f"Not a zip: first bytes={r.content[:4]!r}"

    def test_export_xlsx_as_commercial_forbidden(self, headers_commercial, chantier_id):
        """Matrix RBAC: Commercial gets 403 on XLSX (PDF only)."""
        r = requests.get(f"{API}/chantiers/{chantier_id}/export.xlsx",
                         headers=headers_commercial, timeout=30)
        assert r.status_code == 403, r.text

    def test_export_xlsx_as_technician(self, headers_tech, chantier_id):
        r = requests.get(f"{API}/chantiers/{chantier_id}/export.xlsx",
                         headers=headers_tech, timeout=30)
        assert r.status_code == 200
        assert r.content[:2] == b"PK"

    def test_export_xlsx_other_company_404(self, other_company_headers, chantier_id):
        r = requests.get(f"{API}/chantiers/{chantier_id}/export.xlsx",
                         headers=other_company_headers, timeout=30)
        assert r.status_code == 404, r.text

    def test_export_xlsx_nonexistent_404(self, headers_admin):
        r = requests.get(f"{API}/chantiers/{uuid.uuid4()}/export.xlsx",
                         headers=headers_admin, timeout=30)
        assert r.status_code == 404


# ---------- signature endpoints ----------
class TestSignature:
    DATA_URL = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII="

    def test_post_signature_persists(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/chantiers/{chantier_id}/signature",
                          json={"signature": self.DATA_URL},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["client_signature"] == self.DATA_URL
        assert body["signed_at"] is not None

        # GET verifies persistence
        g = requests.get(f"{API}/chantiers/{chantier_id}",
                         headers=headers_commercial, timeout=30)
        assert g.status_code == 200
        gb = g.json()
        assert gb["client_signature"] == self.DATA_URL
        assert gb["signed_at"] is not None

    def test_post_empty_signature_400(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/chantiers/{chantier_id}/signature",
                          json={"signature": ""},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 400, r.text

    def test_post_whitespace_signature_400(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/chantiers/{chantier_id}/signature",
                          json={"signature": "   "},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 400, r.text

    def test_post_signature_other_company_404(self, other_company_headers, chantier_id):
        r = requests.post(f"{API}/chantiers/{chantier_id}/signature",
                          json={"signature": self.DATA_URL},
                          headers=other_company_headers, timeout=30)
        assert r.status_code == 404, r.text

    def test_post_signature_nonexistent_404(self, headers_admin):
        r = requests.post(f"{API}/chantiers/{uuid.uuid4()}/signature",
                          json={"signature": self.DATA_URL},
                          headers=headers_admin, timeout=30)
        assert r.status_code == 404

    def test_delete_signature_clears(self, headers_commercial, chantier_id):
        # ensure set first
        requests.post(f"{API}/chantiers/{chantier_id}/signature",
                      json={"signature": self.DATA_URL},
                      headers=headers_commercial, timeout=30)

        r = requests.delete(f"{API}/chantiers/{chantier_id}/signature",
                            headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["client_signature"] is None
        assert body["signed_at"] is None

        g = requests.get(f"{API}/chantiers/{chantier_id}",
                         headers=headers_commercial, timeout=30)
        assert g.json()["client_signature"] is None
        assert g.json()["signed_at"] is None
