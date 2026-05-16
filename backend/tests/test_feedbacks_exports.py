"""Feedbacks and exports (PDF/JSON) tests."""
import requests
import pytest


@pytest.fixture(scope="module")
def chantier_with_mesure(api_url):
    s = requests.Session()
    r = s.post(f"{api_url}/auth/login",
               json={"email": "commercial@mesurechassis.fr", "password": "commercial123"},
               timeout=30)
    headers = {"Authorization": f"Bearer {r.json()['access_token']}",
               "Content-Type": "application/json"}
    r = s.post(f"{api_url}/chantiers",
               json={"client_name": "TEST_ExportClient",
                     "address": "20 rue Export, 75002 Paris",
                     "status": "technique_a_valider"},
               headers=headers, timeout=30)
    cid = r.json()["id"]
    # add a mesure
    s.post(f"{api_url}/mesures",
           json={"chantier_id": cid, "block_type": "standard", "label": "F1",
                 "width_top": 1000, "width_middle": 1010, "width_bottom": 1020,
                 "height_left": 1500, "height_middle": 1500, "height_right": 1500,
                 "diag_1": 1800, "diag_2": 1810},
           headers=headers, timeout=30)
    yield cid, headers
    s.delete(f"{api_url}/chantiers/{cid}", headers=headers, timeout=30)


class TestFeedbacks:
    def test_unauth_create_feedback(self, api_url):
        r = requests.post(f"{api_url}/feedbacks",
                          json={"page_context": "x", "user_comment": "y"}, timeout=30)
        assert r.status_code == 401

    def test_tech_create_feedback(self, api_url, tech_headers):
        r = requests.post(f"{api_url}/feedbacks",
                          json={"page_context": "/screen/test",
                                "user_comment": "TEST feedback from tech",
                                "encoded_data_snapshot": {"k": "v"}},
                          headers=tech_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user_comment"] == "TEST feedback from tech"
        assert data["user_email"] == "tech@mesurechassis.fr"
        assert data["id"]

    def test_tech_cannot_list_feedbacks(self, api_url, tech_headers):
        r = requests.get(f"{api_url}/feedbacks", headers=tech_headers, timeout=30)
        assert r.status_code == 403, f"Expected 403 for tech, got {r.status_code}"

    def test_commercial_cannot_list_feedbacks(self, api_url, commercial_headers):
        r = requests.get(f"{api_url}/feedbacks",
                         headers=commercial_headers, timeout=30)
        assert r.status_code == 403

    def test_admin_list_feedbacks(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/feedbacks", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestExports:
    def test_export_pdf_unauth(self, api_url, chantier_with_mesure):
        cid, _ = chantier_with_mesure
        r = requests.get(f"{api_url}/chantiers/{cid}/export.pdf", timeout=30)
        assert r.status_code == 401

    def test_export_pdf_success(self, api_url, chantier_with_mesure):
        cid, headers = chantier_with_mesure
        r = requests.get(f"{api_url}/chantiers/{cid}/export.pdf",
                         headers=headers, timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"content-type={ct}"
        # PDF magic
        assert r.content[:4] == b"%PDF", f"Not a PDF: {r.content[:8]}"
        assert len(r.content) > 500

    def test_export_pdf_404(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/chantiers/nope-id/export.pdf",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 404

    def test_export_json_success(self, api_url, chantier_with_mesure):
        cid, headers = chantier_with_mesure
        r = requests.get(f"{api_url}/chantiers/{cid}/export.json",
                         headers=headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "chantier" in data and "mesures" in data
        assert data["chantier"]["id"] == cid
        assert isinstance(data["mesures"], list)
        assert len(data["mesures"]) >= 1
        # ensure no mongo _id leakage
        assert "_id" not in data["chantier"]
        for m in data["mesures"]:
            assert "_id" not in m
