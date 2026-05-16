"""Chantiers CRUD, filter, search, get-by-id, patch, 401 handling."""
import requests


class TestChantiers:
    def test_list_unauth(self, api_url):
        r = requests.get(f"{api_url}/chantiers", timeout=30)
        assert r.status_code == 401

    def test_list_all_returns_seed(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/chantiers", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 5, f"Expected >=5 seeded chantiers, got {len(data)}"
        # validate shape
        for c in data:
            assert "id" in c and "client_name" in c and "address" in c and "status" in c

    def test_filter_by_status(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/chantiers?status_filter=devis_a_faire",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        for c in data:
            assert c["status"] == "devis_a_faire"

    def test_search_by_address_paris(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/chantiers?q=Paris", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        for c in data:
            assert "paris" in c["address"].lower() or "paris" in c["client_name"].lower()

    def test_create_get_patch_chantier(self, api_url, commercial_headers):
        payload = {"client_name": "TEST_Client", "address": "1 rue de Test, 75000 Paris",
                   "status": "devis_a_faire"}
        r = requests.post(f"{api_url}/chantiers", json=payload,
                          headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["id"]
        assert created["client_name"] == "TEST_Client"
        cid = created["id"]

        # GET by id
        r2 = requests.get(f"{api_url}/chantiers/{cid}", headers=commercial_headers, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["id"] == cid

        # PATCH status
        r3 = requests.patch(f"{api_url}/chantiers/{cid}", json={"status": "cloture"},
                            headers=commercial_headers, timeout=30)
        assert r3.status_code == 200
        assert r3.json()["status"] == "cloture"

        # verify persistence
        r4 = requests.get(f"{api_url}/chantiers/{cid}", headers=commercial_headers, timeout=30)
        assert r4.json()["status"] == "cloture"

        # cleanup
        requests.delete(f"{api_url}/chantiers/{cid}", headers=commercial_headers, timeout=30)

    def test_get_chantier_404(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/chantiers/nonexistent-id",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 404
