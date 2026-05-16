"""Iter4 tests — new MesureCreate fields (bay_*, floor_reserve, bloc_thickness, wall_type, etc.)

Validates:
- POST /api/mesures accepts new raw-bay + wall fields and returns them
- Legacy fields still accepted (backward compat)
- Mixing new + legacy fields works (no conflict)
- wall_type accepts arbitrary strings at backend (no enum validation server-side)
- GET /api/chantiers/{id}/mesures returns the new fields populated
- GET /api/chantiers/{id}/export.pdf still returns 200 + application/pdf
- GET /api/chantiers/{id}/export.json returns mesures with new fields nested
- Roles: technician can POST /api/mesures with new fields
"""
import pytest
import requests


NEW_FIELDS = [
    "bay_height", "bay_width", "bay_diagonal", "floor_reserve",
    "bloc_thickness", "wall_type",
    "insulation_thickness", "finish_outer", "finish_inner",
]


@pytest.fixture(scope="module")
def chantier_ctx(api_url):
    """Create a fresh chantier as commercial; yield (cid, commercial_headers, tech_headers)."""
    s = requests.Session()
    r = s.post(f"{api_url}/auth/login",
               json={"email": "commercial@mesurechassis.fr", "password": "commercial123"},
               timeout=30)
    assert r.status_code == 200, r.text
    com_token = r.json()["access_token"]
    com_headers = {"Authorization": f"Bearer {com_token}", "Content-Type": "application/json"}

    r = s.post(f"{api_url}/auth/login",
               json={"email": "tech@mesurechassis.fr", "password": "tech123"},
               timeout=30)
    assert r.status_code == 200, r.text
    tech_token = r.json()["access_token"]
    tech_headers = {"Authorization": f"Bearer {tech_token}", "Content-Type": "application/json"}

    r = s.post(f"{api_url}/chantiers",
               json={"client_name": "TEST_Iter4Client",
                     "address": "12 rue de l'Iter4, 75004 Paris",
                     "status": "technique_a_valider"},
               headers=com_headers, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]

    yield cid, com_headers, tech_headers

    # Cleanup as admin
    r = s.post(f"{api_url}/auth/login",
               json={"email": "admin@mesurechassis.fr", "password": "admin123"},
               timeout=30)
    admin_headers = {"Authorization": f"Bearer {r.json()['access_token']}",
                     "Content-Type": "application/json"}
    s.delete(f"{api_url}/chantiers/{cid}", headers=admin_headers, timeout=30)


class TestNewFieldsAcceptance:
    def test_post_mesure_with_only_new_fields(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        payload = {
            "chantier_id": cid, "block_type": "standard", "label": "TEST_new_only",
            "bay_height": 2150.5, "bay_width": 1200.0, "bay_diagonal": 2470.25,
            "floor_reserve": 35.0,
            "bloc_thickness": 200.0, "wall_type": "ite",
            "insulation_thickness": 140.0, "finish_outer": 15.0, "finish_inner": 13.0,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for f in NEW_FIELDS:
            assert f in data, f"Missing field {f} in response: {data}"
            assert data[f] == payload[f], f"Field {f}: got {data[f]} expected {payload[f]}"
        # legacy fields should be None
        assert data.get("width_top") is None
        # alerts should be empty (compute_alerts uses legacy fields only)
        assert data["alerts"] == [], f"Expected empty alerts (no legacy fields), got {data['alerts']}"

    def test_post_mesure_legacy_only_still_works(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        payload = {
            "chantier_id": cid, "block_type": "standard", "label": "TEST_legacy_only",
            "width_top": 1000, "width_middle": 1002, "width_bottom": 1001,
            "height_left": 1500, "height_middle": 1500, "height_right": 1500,
            "diag_1": 1800, "diag_2": 1802,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["width_top"] == 1000
        # new fields default to None
        for f in NEW_FIELDS:
            assert data.get(f) is None, f"Expected {f}=None when only legacy provided, got {data.get(f)}"

    def test_post_mesure_mix_new_and_legacy(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        payload = {
            "chantier_id": cid, "block_type": "standard", "label": "TEST_mix",
            # legacy w/ faux-aplomb to trigger alerts
            "width_top": 1000, "width_middle": 1015, "width_bottom": 1020,
            "height_left": 1500, "height_middle": 1500, "height_right": 1500,
            "diag_1": 1800, "diag_2": 1810,
            # new
            "bay_height": 2150.0, "bay_width": 1200.0,
            "bloc_thickness": 200.0, "wall_type": "iti",
            "insulation_thickness": 100.0, "finish_inner": 13.0,
            "floor_reserve": 25.0,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["bay_height"] == 2150.0
        assert data["wall_type"] == "iti"
        assert data["width_top"] == 1000
        # Faux-aplomb alert still computed from legacy
        joined = " | ".join(data["alerts"])
        assert "Faux-aplomb" in joined and "Hors-équerre" in joined, f"alerts={data['alerts']}"

    @pytest.mark.parametrize("wall_type", ["ite", "iti", "crepi_simple"])
    def test_wall_type_valid_values(self, api_url, chantier_ctx, wall_type):
        cid, com_headers, _ = chantier_ctx
        payload = {"chantier_id": cid, "block_type": "standard",
                   "label": f"TEST_wt_{wall_type}",
                   "bay_height": 2000, "bay_width": 1000,
                   "bloc_thickness": 200, "wall_type": wall_type}
        r = requests.post(f"{api_url}/mesures", json=payload, headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["wall_type"] == wall_type

    def test_wall_type_arbitrary_string_rejected_iter5(self, api_url, chantier_ctx):
        """Updated for iter5: backend now enforces enum on wall_type — 422 on invalid."""
        cid, com_headers, _ = chantier_ctx
        payload = {"chantier_id": cid, "block_type": "standard", "label": "TEST_wt_arbitrary",
                   "bay_height": 2000, "bay_width": 1000, "wall_type": "foobar"}
        r = requests.post(f"{api_url}/mesures", json=payload, headers=com_headers, timeout=30)
        assert r.status_code == 422, r.text

    def test_technician_can_post_with_new_fields(self, api_url, chantier_ctx):
        cid, _, tech_headers = chantier_ctx
        payload = {
            "chantier_id": cid, "block_type": "coulissant", "label": "TEST_tech_new",
            "bay_height": 2100, "bay_width": 2400, "bay_diagonal": 3187,
            "floor_reserve": 30, "bloc_thickness": 200, "wall_type": "crepi_simple",
            "finish_outer": 20, "finish_inner": 13,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=tech_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["wall_type"] == "crepi_simple"
        assert d["bay_diagonal"] == 3187


class TestRetrievalAndExports:
    def test_list_mesures_returns_new_fields(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        r = requests.get(f"{api_url}/chantiers/{cid}/mesures",
                         headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        mesures = r.json()
        # Find the "TEST_new_only" mesure created earlier
        target = next((m for m in mesures if m["label"] == "TEST_new_only"), None)
        assert target is not None, f"TEST_new_only mesure not found in {[m['label'] for m in mesures]}"
        assert target["bay_height"] == 2150.5
        assert target["bay_width"] == 1200.0
        assert target["bay_diagonal"] == 2470.25
        assert target["floor_reserve"] == 35.0
        assert target["bloc_thickness"] == 200.0
        assert target["wall_type"] == "ite"
        assert target["insulation_thickness"] == 140.0
        assert target["finish_outer"] == 15.0
        assert target["finish_inner"] == 13.0

    def test_export_pdf_200_with_new_fields(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        r = requests.get(f"{api_url}/chantiers/{cid}/export.pdf",
                         headers=com_headers, timeout=60)
        assert r.status_code == 200, r.text[:300] if r.status_code != 200 else ""
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        # Sanity: PDF starts with %PDF-
        assert r.content[:5] == b"%PDF-", f"Not a PDF: first bytes={r.content[:20]!r}"
        assert len(r.content) > 1000, f"PDF too small: {len(r.content)} bytes"

    def test_export_json_includes_new_fields(self, api_url, chantier_ctx):
        cid, com_headers, _ = chantier_ctx
        r = requests.get(f"{api_url}/chantiers/{cid}/export.json",
                         headers=com_headers, timeout=30)
        assert r.status_code == 200, r.text
        payload = r.json()
        assert "chantier" in payload and "mesures" in payload
        mesures = payload["mesures"]
        target = next((m for m in mesures if m["label"] == "TEST_new_only"), None)
        assert target is not None
        for f in NEW_FIELDS:
            assert f in target, f"Field {f} missing in export.json mesure"
        assert target["wall_type"] == "ite"
        assert target["bay_height"] == 2150.5
