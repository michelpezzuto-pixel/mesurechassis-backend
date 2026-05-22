"""
Backend tests for MesureEscalier API (iteration 2).
Roles: admin (with/without solo_mode) + technicien. Commercial role removed.
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

ADMIN = {"email": "admin@demo.fr", "password": "Demo1234!"}            # solo_mode = False
ARTISAN = {"email": "marc@mesureescalier.com", "password": "Demo1234!"}  # admin + solo_mode True
TECHNICIEN = {"email": "sophie@mesureescaliee.com", "password": "Demo1234!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    body = r.json()
    return body["token"], body["user"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def tokens():
    a_tok, a_user = _login(ADMIN)
    ar_tok, ar_user = _login(ARTISAN)
    t_tok, t_user = _login(TECHNICIEN)
    return {
        "admin": (a_tok, a_user),
        "artisan": (ar_tok, ar_user),
        "technicien": (t_tok, t_user),
    }


# ---------- AUTH / SEED MIGRATION ----------
class TestAuthAndSeed:
    def test_admin_seed_role_and_solo(self):
        _, u = _login(ADMIN)
        assert u["role"] == "admin"
        assert u["solo_mode"] is False

    def test_artisan_seed_role_and_solo(self):
        _, u = _login(ARTISAN)
        assert u["role"] == "admin"           # migrated from commercial
        assert u["solo_mode"] is True

    def test_technicien_seed_role(self):
        _, u = _login(TECHNICIEN)
        assert u["role"] == "technicien"
        assert u["solo_mode"] is False

    def test_register_defaults_solo_mode_false(self):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"full_name": "T R", "email": email,
                                "password": "Test1234!", "company_name": "T Co"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["role"] == "admin"
        assert body["user"]["solo_mode"] is False

    def test_me_contains_new_fields(self, tokens):
        tok, _ = tokens["admin"]
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        b = r.json()
        for k in ("solo_mode", "full_name", "company_name", "role"):
            assert k in b


# ---------- PROFILE UPDATE ----------
class TestProfileUpdate:
    def test_admin_updates_full_name_and_company(self, tokens):
        tok, u = tokens["admin"]
        new_name = f"Admin {uuid.uuid4().hex[:4]}"
        r = requests.put(f"{BASE_URL}/api/auth/me", headers=_h(tok),
                         json={"full_name": new_name, "company_name": "Escaliers Demo SARL"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["full_name"] == new_name
        # restore
        requests.put(f"{BASE_URL}/api/auth/me", headers=_h(tok),
                     json={"full_name": u["full_name"]}, timeout=30)

    def test_technicien_solo_mode_update_forbidden(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.put(f"{BASE_URL}/api/auth/me", headers=_h(tok),
                         json={"solo_mode": True}, timeout=30)
        assert r.status_code == 403

    def test_admin_solo_mode_toggle(self, tokens):
        tok, _ = tokens["admin"]
        # toggle ON
        r = requests.put(f"{BASE_URL}/api/auth/me", headers=_h(tok),
                         json={"solo_mode": True}, timeout=30)
        assert r.status_code == 200 and r.json()["solo_mode"] is True
        # toggle OFF (restore baseline)
        r2 = requests.put(f"{BASE_URL}/api/auth/me", headers=_h(tok),
                          json={"solo_mode": False}, timeout=30)
        assert r2.status_code == 200 and r2.json()["solo_mode"] is False


# ---------- USERS RBAC (no more 'commercial') ----------
class TestUsersInvite:
    def test_invite_technicien_ok(self, tokens):
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

    def test_invite_commercial_rejected_422(self, tokens):
        tok, _ = tokens["admin"]
        email = f"TEST_inv_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{BASE_URL}/api/users", headers=_h(tok), json={
            "full_name": "Bad", "email": email,
            "password": "Test1234!", "role": "commercial",
        }, timeout=30)
        assert r.status_code == 422, r.text

    def test_technicien_cannot_list_users(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.get(f"{BASE_URL}/api/users", headers=_h(tok), timeout=30)
        assert r.status_code == 403


# ---------- PROJECTS / SOLO MODE ----------
@pytest.fixture
def admin_project(tokens):
    tok, _ = tokens["admin"]
    payload = {"client_nom": f"TEST_{uuid.uuid4().hex[:6]}", "address": "1 rue Test",
               "postal_code": "75001", "city": "Paris"}
    r = requests.post(f"{BASE_URL}/api/projects", json=payload, headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid, tok
    requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30)


@pytest.fixture
def artisan_project(tokens):
    tok, _ = tokens["artisan"]
    payload = {"client_nom": f"TEST_{uuid.uuid4().hex[:6]}", "address": "2 rue Solo"}
    r = requests.post(f"{BASE_URL}/api/projects", json=payload, headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid, tok
    a_tok, _ = tokens["admin"]
    requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)


class TestProjectsRBAC:
    def test_technicien_cannot_create_project(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(tok),
                          json={"client_nom": "X", "address": "a"}, timeout=30)
        assert r.status_code == 403

    def test_admin_create_brouillon_not_locked(self, admin_project):
        pid, tok = admin_project
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30).json()
        assert g["status"] == "brouillon"
        assert g["locked"] is False
        assert g["technicien_id"] is None

    def test_artisan_create_auto_locks_and_assigns_self(self, tokens, artisan_project):
        pid, tok = artisan_project
        _, u = tokens["artisan"]
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30).json()
        assert g["status"] == "a_mesurer"
        assert g["locked"] is True
        assert g["technicien_id"] == u["id"]

    def test_admin_can_edit_unlocked(self, admin_project):
        pid, tok = admin_project
        r = requests.put(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok),
                         json={"notes": "edited"}, timeout=30)
        assert r.status_code == 200
        assert r.json()["notes"] == "edited"

    def test_technicien_cannot_edit_project(self, tokens, admin_project):
        pid, _ = admin_project
        # transmit so technicien can see
        a_tok, _ = tokens["admin"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(a_tok), timeout=30)
        t_tok, _ = tokens["technicien"]
        r = requests.put(f"{BASE_URL}/api/projects/{pid}", headers=_h(t_tok),
                         json={"notes": "x"}, timeout=30)
        assert r.status_code == 403

    def test_technicien_cannot_delete(self, tokens, admin_project):
        pid, _ = admin_project
        t_tok, _ = tokens["technicien"]
        r = requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(t_tok), timeout=30)
        assert r.status_code == 403

    def test_admin_sees_all_technicien_sees_assigned_or_unassigned(self, tokens, admin_project):
        pid, _ = admin_project
        a_tok, _ = tokens["admin"]
        t_tok, _ = tokens["technicien"]
        a_list = requests.get(f"{BASE_URL}/api/projects", headers=_h(a_tok), timeout=30).json()
        t_list = requests.get(f"{BASE_URL}/api/projects", headers=_h(t_tok), timeout=30).json()
        assert any(p["id"] == pid for p in a_list)
        # Project is brouillon with technicien_id=None → visible to technicien (unassigned)
        assert any(p["id"] == pid for p in t_list)


# ---------- MEASUREMENT ----------
_MEAS = {
    "material": "bois", "hauteur_brute": 2700, "sols_finis_zero": True,
    "reserve_bas": 0, "reserve_haut": 0, "epaisseur_dalle": 200,
    "tremie_longueur": 2200, "tremie_largeur": 900, "reculement_max": 3500,
    "remarques": "ok",
}


class TestMeasurement:
    def test_admin_no_solo_cannot_measure(self, tokens, admin_project):
        pid, tok = admin_project
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                          headers=_h(tok), json=_MEAS, timeout=30)
        assert r.status_code == 403

    def test_admin_no_solo_cannot_validate(self, tokens, admin_project):
        pid, _ = admin_project
        # Create measurement via technicien path: transmit → technicien measures → admin tries validate
        a_tok, _ = tokens["admin"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(a_tok), timeout=30)
        t_tok, _ = tokens["technicien"]
        m = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                          headers=_h(t_tok), json=_MEAS, timeout=30)
        assert m.status_code == 200
        v = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/validate",
                          headers=_h(a_tok), timeout=30)
        assert v.status_code == 403

    def test_technicien_can_measure_transmitted(self, tokens, admin_project):
        pid, _ = admin_project
        a_tok, _ = tokens["admin"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/transmit", headers=_h(a_tok), timeout=30)
        t_tok, _ = tokens["technicien"]
        r = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                          headers=_h(t_tok), json=_MEAS, timeout=30)
        assert r.status_code == 200, r.text
        g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(t_tok), timeout=30).json()
        assert g["status"] == "a_verifier"
        v = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/validate",
                          headers=_h(t_tok), timeout=30)
        assert v.status_code == 200
        g2 = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(t_tok), timeout=30).json()
        assert g2["status"] == "valide"

    def test_artisan_solo_mode_full_flow(self, tokens):
        """Admin+solo creates project (auto-locked a_mesurer) → measures → validates."""
        tok, _ = tokens["artisan"]
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(tok),
                         json={"client_nom": "TEST_SOLO", "address": "rue Solo"}, timeout=30)
        pid = r.json()["id"]
        try:
            m = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                              headers=_h(tok), json=_MEAS, timeout=30)
            assert m.status_code == 200, m.text
            v = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement/validate",
                              headers=_h(tok), timeout=30)
            assert v.status_code == 200
            g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30).json()
            assert g["status"] == "valide"
        finally:
            requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(tok), timeout=30)

    def test_artisan_solo_can_measure_brouillon_via_toggle(self, tokens):
        """Toggle admin solo_mode ON → create with solo OFF first? Instead: verify admin w/ solo
        measuring an existing brouillon auto-locks it. Use a fresh admin solo flow."""
        a_tok, a_user = tokens["admin"]
        # ensure solo OFF for setup
        requests.put(f"{BASE_URL}/api/auth/me", headers=_h(a_tok), json={"solo_mode": False}, timeout=30)
        r = requests.post(f"{BASE_URL}/api/projects", headers=_h(a_tok),
                         json={"client_nom": "TEST_TOGGLE", "address": "rue T"}, timeout=30)
        pid = r.json()["id"]
        try:
            # Turn solo ON, then measure brouillon → should auto-lock
            requests.put(f"{BASE_URL}/api/auth/me", headers=_h(a_tok), json={"solo_mode": True}, timeout=30)
            m = requests.post(f"{BASE_URL}/api/projects/{pid}/measurement",
                              headers=_h(a_tok), json=_MEAS, timeout=30)
            assert m.status_code == 200, m.text
            g = requests.get(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30).json()
            assert g["locked"] is True
            assert g["technicien_id"] == a_user["id"]
            assert g["status"] == "a_verifier"
        finally:
            requests.put(f"{BASE_URL}/api/auth/me", headers=_h(a_tok), json={"solo_mode": False}, timeout=30)
            requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(a_tok), timeout=30)


# ---------- STATS ----------
class TestStats:
    def test_admin_stats_has_team_size(self, tokens):
        tok, _ = tokens["admin"]
        r = requests.get(f"{BASE_URL}/api/stats", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        b = r.json()
        for k in ("total_projects", "by_status", "total_measurements",
                  "validated_measurements", "average_steps", "team_size"):
            assert k in b
        assert isinstance(b["team_size"], int) and b["team_size"] >= 3

    def test_technicien_stats_team_size_null(self, tokens):
        tok, _ = tokens["technicien"]
        r = requests.get(f"{BASE_URL}/api/stats", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        assert r.json()["team_size"] is None
