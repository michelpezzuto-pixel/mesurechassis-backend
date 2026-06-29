"""
Smoke / non-regression test for V2 stairs HTTP flow:
  POST /api/projects/{pid}/stairs        (create)
  GET  /api/projects/{pid}/stairs/{sid}  (read)
  GET  /api/projects/{pid}/stairs/{sid}/compute  (compute)

Triggered after the ArUco frontend feature was added — backend should
remain untouched. Uses the public EXPO_PUBLIC_BACKEND_URL.
"""
import os
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")

ADMIN = {"email": "admin@demo.fr", "password": "Demo1234!"}


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture
def project(admin_token):
    payload = {"client_nom": f"TEST_v2_{uuid.uuid4().hex[:6]}",
               "address": "1 rue ArUco", "postal_code": "75001", "city": "Paris"}
    r = requests.post(f"{BASE_URL}/api/projects", json=payload,
                      headers=_h(admin_token), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{BASE_URL}/api/projects/{pid}",
                    headers=_h(admin_token), timeout=30)


class TestStairsV2Flow:
    def test_create_stair_droit_seeded(self, admin_token, project):
        pid = project
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/stairs",
            headers=_h(admin_token),
            json={"name": "TEST escalier", "shape": "droit"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["shape"] == "droit"
        assert s["name"] == "TEST escalier"
        assert len(s["niveaux"]) == 1
        n = s["niveaux"][0]
        assert n["floor_index"] == 0
        assert len(n["troncons"]) == 1
        assert n["troncons"][0]["type"] == "droit"

    def test_get_stair_then_compute(self, admin_token, project):
        pid = project
        r = requests.post(
            f"{BASE_URL}/api/projects/{pid}/stairs",
            headers=_h(admin_token),
            json={"name": "TEST compute", "shape": "droit"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]

        g = requests.get(
            f"{BASE_URL}/api/projects/{pid}/stairs/{sid}",
            headers=_h(admin_token), timeout=30,
        )
        assert g.status_code == 200
        assert g.json()["id"] == sid

        c = requests.get(
            f"{BASE_URL}/api/projects/{pid}/stairs/{sid}/compute",
            headers=_h(admin_token), timeout=30,
        )
        assert c.status_code == 200, c.text
        body = c.json()
        # Body shape: should at least carry per-niveau or aggregate
        assert isinstance(body, (dict, list)), type(body)

    def test_get_projects_list_ok(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/projects",
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
