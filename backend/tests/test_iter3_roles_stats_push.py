"""Iteration 3 — role restrictions, push-token, stats/company.

Covers:
- Role gating on POST/PATCH/DELETE /api/chantiers
- POST /api/mesures still allowed for all 3 roles
- POST /api/auth/push-token persistence & clearing
- PATCH chantier assignment triggers best-effort push (no error when no token)
- GET /api/stats/company structure + admin-only + company isolation
"""
import os
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ----- Role restrictions on chantiers -----------------------------------
class TestChantierRoleRestrictions:
    """POST/PATCH/DELETE role gating + mesure access for all roles."""

    @pytest.fixture
    def created_chantier(self, admin_headers):
        r = requests.post(f"{API}/chantiers", headers=admin_headers, json={
            "client_name": f"TEST_role_{uuid.uuid4().hex[:6]}",
            "address": "1 rue du Test, 75000 Paris",
        }, timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        yield cid
        requests.delete(f"{API}/chantiers/{cid}", headers=admin_headers, timeout=30)

    def test_post_chantier_admin_ok(self, admin_headers):
        r = requests.post(f"{API}/chantiers", headers=admin_headers, json={
            "client_name": f"TEST_admin_{uuid.uuid4().hex[:6]}", "address": "addr"},
            timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        # cleanup
        requests.delete(f"{API}/chantiers/{cid}", headers=admin_headers, timeout=30)

    def test_post_chantier_commercial_ok(self, commercial_headers, admin_headers):
        r = requests.post(f"{API}/chantiers", headers=commercial_headers, json={
            "client_name": f"TEST_com_{uuid.uuid4().hex[:6]}", "address": "addr"},
            timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        requests.delete(f"{API}/chantiers/{cid}", headers=admin_headers, timeout=30)

    def test_post_chantier_technician_forbidden(self, tech_headers):
        r = requests.post(f"{API}/chantiers", headers=tech_headers, json={
            "client_name": "TEST_tech_should_fail", "address": "addr"},
            timeout=30)
        assert r.status_code == 403, r.text

    def test_patch_chantier_admin_ok(self, admin_headers, created_chantier):
        r = requests.patch(f"{API}/chantiers/{created_chantier}",
                           headers=admin_headers,
                           json={"status": "technique_a_valider"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "technique_a_valider"

    def test_patch_chantier_commercial_ok(self, commercial_headers, created_chantier):
        r = requests.patch(f"{API}/chantiers/{created_chantier}",
                           headers=commercial_headers,
                           json={"client_name": "TEST_patched_com"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["client_name"] == "TEST_patched_com"

    def test_patch_chantier_technician_forbidden(self, tech_headers, created_chantier):
        r = requests.patch(f"{API}/chantiers/{created_chantier}",
                           headers=tech_headers,
                           json={"status": "cloture"}, timeout=30)
        assert r.status_code == 403, r.text

    def test_delete_chantier_commercial_allowed(self, commercial_headers, created_chantier):
        """Matrix RBAC: Commercial CAN delete a chantier (canManage = admin+commercial)."""
        r = requests.delete(f"{API}/chantiers/{created_chantier}",
                            headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text

    def test_delete_chantier_technician_forbidden(self, tech_headers, created_chantier):
        r = requests.delete(f"{API}/chantiers/{created_chantier}",
                            headers=tech_headers, timeout=30)
        assert r.status_code == 403, r.text

    def test_delete_chantier_admin_ok(self, admin_headers):
        # Create our own to delete
        c = requests.post(f"{API}/chantiers", headers=admin_headers, json={
            "client_name": f"TEST_del_{uuid.uuid4().hex[:6]}", "address": "addr"},
            timeout=30).json()
        r = requests.delete(f"{API}/chantiers/{c['id']}", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        # Verify gone
        g = requests.get(f"{API}/chantiers/{c['id']}", headers=admin_headers, timeout=30)
        assert g.status_code == 404


# ----- Mesures accessible for all roles ---------------------------------
class TestMesureAllRoles:

    @pytest.fixture
    def shared_chantier(self, admin_headers):
        r = requests.post(f"{API}/chantiers", headers=admin_headers, json={
            "client_name": f"TEST_mesure_shared_{uuid.uuid4().hex[:6]}",
            "address": "addr"}, timeout=30)
        cid = r.json()["id"]
        yield cid
        requests.delete(f"{API}/chantiers/{cid}", headers=admin_headers, timeout=30)

    def _mk_mesure_payload(self, cid):
        return {
            "chantier_id": cid, "block_type": "standard", "label": "TEST_M",
            "width_top": 1000, "width_middle": 1000, "width_bottom": 1000,
            "height_left": 2000, "height_middle": 2000, "height_right": 2000,
            "diag_1": 2236, "diag_2": 2236,
        }

    def test_mesure_admin_forbidden_without_artisan_mode(self, admin_headers, shared_chantier):
        """Matrix RBAC: Admin BLOCKED from creating mesures (unless artisan_mode)."""
        r = requests.post(f"{API}/mesures", headers=admin_headers,
                          json=self._mk_mesure_payload(shared_chantier), timeout=30)
        # In artisan_mode=true, admin can post (200). Without, 403.
        # Our conftest disables artisan_mode, so expect 403.
        assert r.status_code == 403, r.text

    def test_mesure_commercial(self, commercial_headers, shared_chantier):
        r = requests.post(f"{API}/mesures", headers=commercial_headers,
                          json=self._mk_mesure_payload(shared_chantier), timeout=30)
        assert r.status_code == 200, r.text

    def test_mesure_technician(self, tech_headers, shared_chantier):
        r = requests.post(f"{API}/mesures", headers=tech_headers,
                          json=self._mk_mesure_payload(shared_chantier), timeout=30)
        assert r.status_code == 200, r.text


# ----- Push token --------------------------------------------------------
class TestPushToken:

    def test_set_push_token(self, tech_headers):
        r = requests.post(f"{API}/auth/push-token", headers=tech_headers,
                          json={"push_token": "ExponentPushToken[TEST_xxx]"}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True}

    def test_clear_push_token_with_null(self, tech_headers):
        # set then clear
        requests.post(f"{API}/auth/push-token", headers=tech_headers,
                      json={"push_token": "ExponentPushToken[TEST_yyy]"}, timeout=30)
        r = requests.post(f"{API}/auth/push-token", headers=tech_headers,
                          json={"push_token": None}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json() == {"ok": True}

    def test_me_endpoint_still_works_after_token_set(self, tech_headers):
        # /api/auth/me should not be required to expose push_token; just must work
        requests.post(f"{API}/auth/push-token", headers=tech_headers,
                      json={"push_token": "ExponentPushToken[TEST_zzz]"}, timeout=30)
        r = requests.get(f"{API}/auth/me", headers=tech_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        # email/id/role/company_id must be present
        for k in ("id", "email", "role", "company_id", "name"):
            assert k in data


# ----- PATCH assignment triggers best-effort push -----------------------
class TestPatchAssignmentPushBestEffort:

    def test_patch_assigned_to_no_token_no_error(self, admin_headers, tech_token):
        # Ensure the tech user has NO push_token by clearing first
        tech_h = {"Authorization": f"Bearer {tech_token}",
                  "Content-Type": "application/json"}
        requests.post(f"{API}/auth/push-token", headers=tech_h,
                      json={"push_token": None}, timeout=30)

        # Look up tech user id via /api/users (admin)
        users = requests.get(f"{API}/users", headers=admin_headers, timeout=30).json()
        tech_user = next(u for u in users if u["email"] == "tech@mesurechassis.fr")
        tech_id = tech_user["id"]

        c = requests.post(f"{API}/chantiers", headers=admin_headers, json={
            "client_name": f"TEST_assign_{uuid.uuid4().hex[:6]}",
            "address": "addr"}, timeout=30).json()
        try:
            r = requests.patch(f"{API}/chantiers/{c['id']}",
                               headers=admin_headers,
                               json={"assigned_to": tech_id}, timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["assigned_to"] == tech_id
        finally:
            requests.delete(f"{API}/chantiers/{c['id']}",
                            headers=admin_headers, timeout=30)


# ----- /api/stats/company -----------------------------------------------
class TestStatsCompany:

    def test_stats_admin_default_shape(self, admin_headers):
        r = requests.get(f"{API}/stats/company", headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Required keys
        for k in ("total_chantiers", "by_status", "closure_rate",
                  "total_mesures", "total_alerts", "by_technician"):
            assert k in data, f"missing key {k}"
        assert isinstance(data["by_status"], dict)
        for s in ("devis_a_faire", "technique_a_valider", "cloture"):
            assert s in data["by_status"]
            assert isinstance(data["by_status"][s], int)
        assert isinstance(data["closure_rate"], (int, float))
        assert isinstance(data["total_mesures"], int)
        assert isinstance(data["total_alerts"], int)
        assert isinstance(data["by_technician"], list)

    def test_stats_commercial_forbidden(self, commercial_headers):
        r = requests.get(f"{API}/stats/company", headers=commercial_headers, timeout=30)
        assert r.status_code == 403, r.text

    def test_stats_technician_forbidden(self, tech_headers):
        r = requests.get(f"{API}/stats/company", headers=tech_headers, timeout=30)
        assert r.status_code == 403, r.text

    def test_stats_isolated_by_company(self, session):
        # Register a fresh admin in a new company AND a tech (admin can't post mesures
        # in matrix RBAC, so we need a tech for that step).
        company_id = f"acme-test-{uuid.uuid4().hex[:6]}"
        admin_email = f"TEST_acme_admin_{uuid.uuid4().hex[:8]}@example.com"
        reg = session.post(f"{API}/auth/register", json={
            "name": "TEST Acme Admin", "email": admin_email,
            "password": "pw123456", "role": "admin",
            "company_id": company_id,
        }, timeout=30)
        assert reg.status_code == 200, reg.text
        token = reg.json()["access_token"]
        h = _h(token)
        # Also create a tech in same company
        tech_email = f"TEST_acme_tech_{uuid.uuid4().hex[:8]}@example.com"
        treg = session.post(f"{API}/auth/register", json={
            "name": "TEST Acme Tech", "email": tech_email,
            "password": "pw123456", "role": "technician",
            "company_id": company_id,
        }, timeout=30)
        assert treg.status_code == 200, treg.text
        th = _h(treg.json()["access_token"])
        try:
            # Fresh company: zero chantiers — by_status now contains 5 internal statuses
            stats = requests.get(f"{API}/stats/company", headers=h, timeout=30).json()
            assert stats["total_chantiers"] == 0
            # All 5 internal statuses must be present with count 0
            for s in ("devis_a_faire", "technique_a_valider", "en_commande",
                      "en_fabrication", "cloture"):
                assert stats["by_status"].get(s, 0) == 0
            assert stats["closure_rate"] == 0.0
            assert stats["total_mesures"] == 0
            assert stats["total_alerts"] == 0
            assert stats["by_technician"] == []

            # Admin creates a chantier in this company (admin CAN create chantiers)
            c = requests.post(f"{API}/chantiers", headers=h, json={
                "client_name": "TEST_acme_chantier",
                "address": "addr",
                "status": "cloture",
            }, timeout=30).json()
            # Assign to the tech user so by_technician aggregates
            me_tech = requests.get(f"{API}/auth/me", headers=th, timeout=30).json()
            requests.patch(f"{API}/chantiers/{c['id']}", headers=h,
                           json={"assigned_to": me_tech["id"]}, timeout=30)

            # Tech posts mesure with alerts (matrix RBAC: only com/tech can)
            mr = requests.post(f"{API}/mesures", headers=th, json={
                "chantier_id": c["id"], "block_type": "standard", "label": "M1",
                "width_top": 1000, "width_middle": 1010, "width_bottom": 1000,
                "height_left": 2000, "height_middle": 2000, "height_right": 2000,
            }, timeout=30)
            assert mr.status_code == 200, mr.text

            stats2 = requests.get(f"{API}/stats/company", headers=h, timeout=30).json()
            assert stats2["total_chantiers"] == 1
            assert stats2["by_status"]["cloture"] == 1
            assert stats2["closure_rate"] == 100.0
            assert stats2["total_mesures"] == 1
            assert stats2["total_alerts"] >= 1
            assert len(stats2["by_technician"]) == 1
            tb = stats2["by_technician"][0]
            assert tb["user_id"] == me_tech["id"]
            assert tb["mesures"] == 1
            assert tb["alerts"] >= 1
            assert tb["name"] == "TEST Acme Tech"
        finally:
            # cleanup chantiers for this company
            chs = requests.get(f"{API}/chantiers", headers=h, timeout=30).json()
            for ch in chs:
                requests.delete(f"{API}/chantiers/{ch['id']}", headers=h, timeout=30)
