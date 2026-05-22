"""
Backend tests for MesureEscalier API.
Run: pytest /app/backend/tests/test_mesure_escalier.py -v --tb=short \
        --junitxml=/app/test_reports/pytest/pytest_results.xml
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
COMMERCIAL = {"email": "marc@mesureescalier.com", "password": "Demo1234!"}
TECHNICIEN = {"email": "sophie@mesureescaliee.com", "password": "Demo1234!"}


# ---------- helpers ----------
def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def tokens():
    a_tok, a_user = _login(ADMIN)
    c_tok, c_user = _login(COMMERCIAL)
    t_tok, t_user = _login(TECHNICIEN)
    return {
        "admin": (a_tok, a_user),
        "commercial": (c_tok, c_user),
        "technicien": (t_tok, t_user),
    }


@pytest.fixture
def commercial_project(tokens):
    tok, _ = tokens["commercial"]
    payload = {
        "client_nom": f"TEST_{uuid.uuid4().hex[:6]}",
        "client_prenom": "Jean",
        "address": "10 rue Test",
        "postal_code": "75001",
        "city": "Paris",
        "phone": "0102030405",
        "notes": "auto",
    }
    r = requests.post(f"{BASE_URL}/api/projects", json=payload, headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid, tok
    # cleanup via admin
    a_tok, _ = tokens["admin"]
    requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)


# ---------- AUTH ----------
class TestAuth:
    def test_demo_logins_ok(self):
        for c in (ADMIN, COMMERCIAL, TECHNICIEN):
            tok, user = _login(c)
            assert user["email"] == c["email"]
            assert user["role"] in ("admin", "commercial", "technicien")

    def test_login_bad_credentials(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "admin@demo.fr", "password": "wrong"}, timeout=30)
        assert r.status_code == 401

    def test_me_returns_user(self, tokens):
        tok, user = tokens["admin"]
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN["email"]

    def test_me_no_token_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 401

    def test_register_creates_admin(self):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"full_name": "T R", "email": email,
                                "password": "Test1234!", "company_name": "T Co"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["role"] == "admin"
        assert body["user"]["email"] == email.lower()


# ---------- USERS RBAC ----------
class TestUsersRBAC:
    def test_admin_list_users(self, tokens):
        tok, _ = tokens["admin"]
        r = requests.get(f"{BASE_URL}/api/users", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()]
        assert ADMIN["email"] in emails

    def test_commercial_cannot_list_users(self, tokens):
        tok, _ = tokens["commercial"]
        r = requests.get(f"{BASE_URL}/api/users", headers=_h(tok), timeout=30)
        assert r.status_code == 403

    def test_admin_invite_and_delete(self, tokens):
        tok, _ = tokens["admin"]
        email = f"TEST_inv_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{BASE_URL}/api/users", headers=_h(tok), json={
            "full_name": "Invited", "email": email,
            "password": "Test1234!", "role": "technicien",
        }, timeout=30)
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        assert r.json()["role"] == "technicien"
        d = requests.delete(f"{BASE_URL}/api/users/{uid}", headers=_h(tok), timeout=30)
        assert d.status_code == 200

    def test_technicien_cannot_invite(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.post(f"{BASE_URL}/api/users", headers=_h(tok), json={
            "full_name": "X", "email": "x@x.fr",
            "password": "Test1234!", "role": "commercial",
        }, timeout=30)
        assert r.status_code == 403


# ---------- PROJECTS ----------
class TestProjects:
    def test_technicien_cannot_create_project(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(tok),
                          json={"client_nom": "X", "address": "a"}, timeout=30)
        assert r.status_code == 403

    def test_commercial_creates_and_lists_own(self, tokens, commercial_project):
        pid, tok = commercial_project
        r = requests.get(f"{BASE_URL}/api/projects", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json())

    def test_admin_sees_all_projects(self, tokens, commercial_project):
        pid, _ = commercial_project
        a_tok, _ = tokens["admin"]
        r = requests.get(f"{BASE_URL}/api/projects", headers=_h(a_tok), timeout=30)
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json())

    def test_technicien_does_not_see_unassigned(self, tokens, commercial_project):
        pid, _ = commercial_project
        t_tok, _ = tokens["technicien"]
        r = requests.get(f"{BASE_URL}/api/projects", headers=_h(t_tok), timeout=30)
        assert r.status_code == 200
        assert not any(p["id"] == pid for p in r.json())

    def test_transmit_locks_and_status_a_mesurer(self, tokens, commercial_project):
        pid, tok = commercial_project
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/transmit",
                          headers=_h(tok), timeout=30)
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30)
        body = g.json()
        assert body["locked"] is True
        assert body["status"] == "a_mesurer"

    def test_commercial_cannot_edit_after_transmit(self, tokens, commercial_project):
        pid, tok = commercial_project
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(tok), timeout=30)
        r = requests.put(f"{BASE_URL}/api/projects/{pid}",
                         headers=_h(tok), json={"notes": "new"}, timeout=30)
        assert r.status_code == 403

    def test_technicien_cannot_edit_client_info(self, tokens, commercial_project):
        pid, _ = commercial_project
        t_tok, _ = tokens["technicien"]
        r = requests.put(f"{BASE_URL}/api/projects/{pid}",
                         headers=_h(t_tok), json={"notes": "x"}, timeout=30)
        assert r.status_code == 403

    def test_commercial_cannot_delete_locked(self, tokens, commercial_project):
        pid, tok = commercial_project
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(tok), timeout=30)
        r = requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30)
        assert r.status_code == 403

    def test_admin_can_delete_locked(self, tokens):
        c_tok, _ = tokens["commercial"]
        a_tok, _ = tokens["admin"]
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(c_tok),
                         json={"client_nom": "TEST_DEL", "address": "a"}, timeout=30)
        pid = r.json()["id"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(c_tok), timeout=30)
        d = requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)
        assert d.status_code == 200
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)
        assert g.status_code == 404


# ---------- MEASUREMENT ----------
_MEAS = {
    "material": "bois",
    "hauteur_brute": 2700,
    "sols_finis_zero": True,
    "reserve_bas": 0,
    "reserve_haut": 0,
    "epaisseur_dalle": 200,
    "tremie_longueur": 2200,
    "tremie_largeur": 900,
    "reculement_max": 3500,
    "remarques": "ok",
}


class TestMeasurement:
    def test_commercial_cannot_save_measurement(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                          headers=_h(c_tok), json=_MEAS, timeout=30)
        assert r.status_code == 403

    def test_preview_returns_blondel(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/preview",
                          headers=_h(c_tok), json=_MEAS, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("n_steps", "h", "g", "slope_angle", "hypotenuse",
                  "blondel_value", "shape", "true_height"):
            assert k in body
        assert body["n_steps"] >= 8
        assert 600 <= body["blondel_value"] <= 640

    def test_save_and_validate_measurement(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        # transmit first so technicien can measure
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(c_tok), timeout=30)
        t_tok, _ = tokens["technicien"]
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                          headers=_h(t_tok), json=_MEAS, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "result" in body and body["result"]["n_steps"] > 0
        # status should be a_verifier
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(t_tok), timeout=30)
        assert g.json()["status"] == "a_verifier"
        # validate (admin)
        a_tok, _ = tokens["admin"]
        v = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/validate",
                          headers=_h(a_tok), timeout=30)
        assert v.status_code == 200
        g2 = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)
        assert g2.json()["status"] == "valide"

    def test_blondel_invalid_hauteur(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        payload = dict(_MEAS, hauteur_brute=0)
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/preview",
                          headers=_h(c_tok), json=payload, timeout=30)
        assert r.status_code == 400

    def test_blondel_large_reculement_is_droit(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        payload = dict(_MEAS, reculement_max=10000)
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/preview",
                          headers=_h(c_tok), json=payload, timeout=30)
        assert r.status_code == 200
        assert "Droit" in r.json()["shape"]

    def test_blondel_small_reculement_quart_tournant(self, tokens, commercial_project):
        pid, c_tok = commercial_project
        payload = dict(_MEAS, reculement_max=2500)
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/preview",
                          headers=_h(c_tok), json=payload, timeout=30)
        assert r.status_code == 200
        shape = r.json()["shape"].lower()
        assert "quart" in shape or "hélicoïdal" in shape or "colima" in shape


# ---------- EXPORTS + INTEGRATION ----------
class TestExportsAndIntegration:
    @pytest.fixture
    def measured_project(self, tokens):
        c_tok, _ = tokens["commercial"]
        a_tok, _ = tokens["admin"]
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(c_tok),
                         json={"client_nom": "TEST_EXP", "address": "1 rue"}, timeout=30)
        pid = r.json()["id"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(c_tok), timeout=30)
        t_tok, _ = tokens["technicien"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                      headers=_h(t_tok), json=_MEAS, timeout=30)
        yield pid, a_tok
        requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)

    def test_export_pdf(self, measured_project):
        pid, a_tok = measured_project
        r = requests.get(f"{BASE_URL}/api/projects/{pid}/export/pdf",
                         headers={"Authorization": f"Bearer {a_tok}"}, timeout=60)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert len(r.content) > 1000
        assert r.content[:4] == b"%PDF"

    def test_export_dxf(self, measured_project):
        pid, a_tok = measured_project
        r = requests.get(f"{BASE_URL}/api/projects/{pid}/export/dxf",
                         headers={"Authorization": f"Bearer {a_tok}"}, timeout=60)
        assert r.status_code == 200
        body = r.text
        assert "LINE" in body
        assert "TEXT" in body
        assert body.strip().endswith("EOF")

    def test_integration_endpoint(self, measured_project):
        pid, a_tok = measured_project
        r = requests.get(f"{BASE_URL}/api/integration/sites/{pid}",
                         headers={"Authorization": f"Bearer {a_tok}"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["site_id"] == pid
        s = body["structure"]
        for k in ("true_height_mm", "reculement_mm", "slope_angle_deg", "hypotenuse_mm"):
            assert k in s
