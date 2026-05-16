"""Mesures business-logic tests: standard alerts, trapeze slope_angle, listing."""
import math
import requests
import pytest


@pytest.fixture(scope="module")
def chantier_id(api_url, request):
    # Create chantier via commercial token
    s = requests.Session()
    r = s.post(f"{api_url}/auth/login",
               json={"email": "commercial@mesurechassis.fr", "password": "commercial123"},
               timeout=30)
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = s.post(f"{api_url}/chantiers",
               json={"client_name": "TEST_MesuresClient",
                     "address": "10 rue du Test, 75001 Paris",
                     "status": "technique_a_valider"},
               headers=headers, timeout=30)
    cid = r.json()["id"]

    yield cid, headers

    # Cleanup
    s.delete(f"{api_url}/chantiers/{cid}", headers=headers, timeout=30)


class TestMesures:
    def test_unauth_create_mesure(self, api_url):
        r = requests.post(f"{api_url}/mesures",
                          json={"chantier_id": "x", "block_type": "standard",
                                "label": "T1"}, timeout=30)
        assert r.status_code == 401

    def test_standard_alerts(self, api_url, chantier_id):
        cid, headers = chantier_id
        payload = {
            "chantier_id": cid, "block_type": "standard", "label": "Fenetre1",
            "width_top": 1000, "width_middle": 1010, "width_bottom": 1020,
            "height_left": 1500, "height_middle": 1500, "height_right": 1500,
            "diag_1": 1800, "diag_2": 1810,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        alerts = data["alerts"]
        joined = " | ".join(alerts)
        assert "Faux-aplomb" in joined, f"alerts={alerts}"
        assert "Hors-équerre" in joined, f"alerts={alerts}"
        # heights equal => no faux-aplomb on heights
        assert not any("hauteurs" in a for a in alerts)

    def test_trapeze_slope_angle(self, api_url, chantier_id):
        cid, headers = chantier_id
        payload = {
            "chantier_id": cid, "block_type": "trapeze", "label": "Trap1",
            "width_small": 800, "width_intermediate": 1200,
            "height_small": 1500, "height_large": 1700,
        }
        r = requests.post(f"{api_url}/mesures", json=payload, headers=headers, timeout=30)
        assert r.status_code == 200, r.text
        slope = r.json()["slope_angle_deg"]
        expected = round(math.degrees(math.atan(200 / 400)), 2)  # 26.57
        assert slope == pytest.approx(expected, abs=0.05), f"slope={slope}, expected≈{expected}"
        assert slope == pytest.approx(26.57, abs=0.05)

    def test_list_mesures_includes_alerts(self, api_url, chantier_id):
        cid, headers = chantier_id
        r = requests.get(f"{api_url}/chantiers/{cid}/mesures",
                         headers=headers, timeout=30)
        assert r.status_code == 200
        mesures = r.json()
        assert len(mesures) >= 2
        # Find standard mesure and verify alerts persisted
        std = next((m for m in mesures if m["block_type"] == "standard"), None)
        assert std is not None
        assert any("Faux-aplomb" in a for a in std["alerts"])
        trap = next((m for m in mesures if m["block_type"] == "trapeze"), None)
        assert trap is not None
        assert trap["slope_angle_deg"] is not None

    def test_invalid_block_type(self, api_url, chantier_id):
        cid, headers = chantier_id
        r = requests.post(f"{api_url}/mesures",
                          json={"chantier_id": cid, "block_type": "unknown",
                                "label": "x"}, headers=headers, timeout=30)
        assert r.status_code == 400

    def test_mesure_chantier_404(self, api_url, chantier_id):
        _, headers = chantier_id
        r = requests.post(f"{api_url}/mesures",
                          json={"chantier_id": "nope", "block_type": "standard",
                                "label": "x"}, headers=headers, timeout=30)
        assert r.status_code == 404
