"""Iter6 backend tests:
- wall_type now accepts 'brique_parement' (4th enum value); arbitrary strings rejected (422).
- New optional Mesure fields: bay_diagonal_1, bay_diagonal_2, diag_1_verified, diag_2_verified.
- Legacy bay_diagonal still accepted for backward compat.
- export.xlsx + export.pdf still work with brique_parement.
"""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# --- session-scoped helpers ---
@pytest.fixture(scope="module")
def headers_admin():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@mesurechassis.fr", "password": "admin123"},
                      timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def headers_commercial():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "commercial@mesurechassis.fr",
                            "password": "commercial123"},
                      timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def chantier_id(headers_commercial, headers_admin):
    r = requests.post(f"{API}/chantiers",
                      json={"client_name": "TEST_Iter6_Brique",
                            "address": "1 rue de la Brique, Paris",
                            "status": "devis_a_faire"},
                      headers=headers_commercial, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    requests.delete(f"{API}/chantiers/{cid}", headers=headers_admin, timeout=30)


# ---------- wall_type enum: brique_parement (NEW) ----------
class TestWallTypeBriqueParement:
    def test_brique_parement_accepted(self, headers_commercial, chantier_id):
        """POST /api/mesures with wall_type='brique_parement' → 200 + persisted."""
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_wt_brique", "wall_type": "brique_parement"},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        mid = r.json()["id"]
        assert r.json()["wall_type"] == "brique_parement"
        # Verify persistence via GET list
        g = requests.get(f"{API}/chantiers/{chantier_id}/mesures",
                         headers=headers_commercial, timeout=30)
        assert g.status_code == 200
        target = next((m for m in g.json() if m["id"] == mid), None)
        assert target is not None
        assert target["wall_type"] == "brique_parement"

    @pytest.mark.parametrize("wt", ["ite", "iti", "crepi_simple", "brique_parement"])
    def test_all_four_wall_types_accepted(self, headers_commercial, chantier_id, wt):
        """All 4 valid wall_type enum values are accepted (200) and persisted."""
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": f"TEST_iter6_wt_{wt}", "wall_type": wt},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["wall_type"] == wt

    @pytest.mark.parametrize("bad", [
        "invalid_xxx", "BRIQUE_PAREMENT", "brique-parement",
        "brique parement", "brique", "parement", "foo", "", " ",
    ])
    def test_invalid_wall_type_rejected(self, headers_commercial, chantier_id, bad):
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_wt_invalid", "wall_type": bad},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 422, (
            f"Expected 422 for wall_type={bad!r}, got {r.status_code}: {r.text}")


# ---------- new diagonal fields ----------
class TestNewDiagonalFields:
    def test_all_four_diagonal_fields_persisted(self, headers_commercial, chantier_id):
        """POST with bay_diagonal_1 + _2 + diag_1_verified=true + diag_2_verified=false."""
        payload = {
            "chantier_id": chantier_id,
            "block_type": "standard",
            "label": "TEST_iter6_diag",
            "bay_height": 2150.0,
            "bay_width": 1200.0,
            "bay_diagonal_1": 2470.25,
            "bay_diagonal_2": 2471.10,
            "diag_1_verified": True,
            "diag_2_verified": False,
            "wall_type": "brique_parement",
        }
        r = requests.post(f"{API}/mesures", json=payload,
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["bay_diagonal_1"] == 2470.25
        assert d["bay_diagonal_2"] == 2471.10
        assert d["diag_1_verified"] is True
        assert d["diag_2_verified"] is False
        mid = d["id"]

        # GET → verify persistence
        g = requests.get(f"{API}/chantiers/{chantier_id}/mesures",
                         headers=headers_commercial, timeout=30)
        target = next(m for m in g.json() if m["id"] == mid)
        assert target["bay_diagonal_1"] == 2470.25
        assert target["bay_diagonal_2"] == 2471.10
        assert target["diag_1_verified"] is True
        assert target["diag_2_verified"] is False

    def test_legacy_bay_diagonal_still_accepted(self, headers_commercial, chantier_id):
        """Backward compat: single bay_diagonal still works."""
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_iter6_legacy_diag",
                                "bay_height": 2000, "bay_width": 1000,
                                "bay_diagonal": 2236.0},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["bay_diagonal"] == 2236.0
        # New fields default to None when not supplied
        assert d.get("bay_diagonal_1") is None
        assert d.get("bay_diagonal_2") is None
        assert d.get("diag_1_verified") is None
        assert d.get("diag_2_verified") is None

    def test_partial_new_diagonal_fields(self, headers_commercial, chantier_id):
        """Only one of the two new diagonals provided — still 200."""
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_iter6_partial_diag",
                                "bay_diagonal_1": 2500.0,
                                "diag_1_verified": True},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["bay_diagonal_1"] == 2500.0
        assert d["bay_diagonal_2"] is None
        assert d["diag_1_verified"] is True
        assert d["diag_2_verified"] is None

    def test_verified_flags_default_none_when_omitted(self, headers_commercial, chantier_id):
        r = requests.post(f"{API}/mesures",
                          json={"chantier_id": chantier_id, "block_type": "standard",
                                "label": "TEST_iter6_no_verified",
                                "bay_diagonal_1": 2470, "bay_diagonal_2": 2471},
                          headers=headers_commercial, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["diag_1_verified"] is None
        assert d["diag_2_verified"] is None


# ---------- exports with brique_parement ----------
class TestExportsBriqueParement:
    @pytest.fixture(scope="class")
    def chantier_with_brique(self, headers_commercial, headers_admin):
        cr = requests.post(f"{API}/chantiers",
                           json={"client_name": "TEST_Iter6_Export",
                                 "address": "Export brique, Lyon",
                                 "status": "devis_a_faire"},
                           headers=headers_commercial, timeout=30)
        assert cr.status_code == 200, cr.text
        cid = cr.json()["id"]
        # Add a brique_parement mesure with new diagonals
        mr = requests.post(f"{API}/mesures",
                           json={"chantier_id": cid, "block_type": "standard",
                                 "label": "TEST_export_brique",
                                 "bay_height": 2100, "bay_width": 1200,
                                 "bay_diagonal_1": 2418, "bay_diagonal_2": 2420,
                                 "diag_1_verified": True, "diag_2_verified": True,
                                 "bloc_thickness": 200, "wall_type": "brique_parement",
                                 "insulation_thickness": 0,
                                 "finish_outer": 30},
                           headers=headers_commercial, timeout=30)
        assert mr.status_code == 200, mr.text
        yield cid
        requests.delete(f"{API}/chantiers/{cid}", headers=headers_admin, timeout=30)

    def test_export_xlsx_with_brique_parement(self, chantier_with_brique):
        """Matrix RBAC: Commercial 403 on XLSX → login as tech to validate file."""
        tech_login = requests.post(f"{API}/auth/login",
                                   json={"email": "tech@mesurechassis.fr",
                                         "password": "tech123"}, timeout=30)
        tech_headers = {
            "Authorization": f"Bearer {tech_login.json()['access_token']}",
            "Content-Type": "application/json",
        }
        r = requests.get(f"{API}/chantiers/{chantier_with_brique}/export.xlsx",
                         headers=tech_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml.sheet" in ct, f"Bad content-type: {ct}"
        assert r.content[:2] == b"PK", "Invalid XLSX magic bytes"
        assert len(r.content) > 1000, "XLSX suspiciously small"

    def test_export_pdf_with_brique_parement(self, headers_commercial, chantier_with_brique):
        r = requests.get(f"{API}/chantiers/{chantier_with_brique}/export.pdf",
                         headers=headers_commercial, timeout=60)
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"Bad content-type: {ct}"
        # Valid PDF starts with %PDF
        assert r.content[:4] == b"%PDF", "Invalid PDF magic bytes"
        assert len(r.content) > 500, "PDF suspiciously small"
