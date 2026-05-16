"""Iteration 2: multi-tenant isolation, chantier assignment, hors-équerre tolerance, feedback DELETE."""
import uuid

import pytest
import requests


# ---------- Fixtures for two distinct companies ----------------------------
@pytest.fixture(scope="module")
def acme_user(api_url):
    """Register a new user in company 'acme-test'."""
    email = f"TEST_acme_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = requests.post(f"{api_url}/auth/register", json={
        "name": "TEST Acme Tech",
        "email": email,
        "password": "acme123pw",
        "role": "technician",
        "company_id": "acme-test",
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "token": data["access_token"],
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['access_token']}",
                    "Content-Type": "application/json"},
        "email": email,
    }


@pytest.fixture(scope="module")
def acme_admin(api_url):
    """Register an admin in company 'acme-test' (for feedback isolation tests)."""
    email = f"TEST_acme_admin_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    r = requests.post(f"{api_url}/auth/register", json={
        "name": "TEST Acme Admin",
        "email": email,
        "password": "acmeadm123",
        "role": "admin",
        "company_id": "acme-test",
    }, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "token": data["access_token"],
        "headers": {"Authorization": f"Bearer {data['access_token']}",
                    "Content-Type": "application/json"},
    }


# ---------- Registration with custom company_id ----------------------------
class TestRegisterCompany:
    def test_register_persists_company_id(self, api_url, acme_user):
        assert acme_user["user"]["company_id"] == "acme-test"

    def test_me_returns_company_id(self, api_url, acme_user):
        r = requests.get(f"{api_url}/auth/me", headers=acme_user["headers"], timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["company_id"] == "acme-test"
        assert body["email"] == acme_user["email"].lower()

    def test_default_admin_company_is_default(self, api_url, admin_headers):
        r = requests.get(f"{api_url}/auth/me", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["company_id"] == "default"


# ---------- Multi-tenant chantier isolation --------------------------------
class TestChantierIsolation:
    def test_seeded_chantiers_visible_to_default_admin(self, api_url, admin_headers):
        """Backfill check — at least the 5 seeded chantiers should be visible."""
        r = requests.get(f"{api_url}/chantiers", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        items = r.json()
        # all returned must belong to default company
        for c in items:
            assert c["company_id"] == "default", c
        # the 5 seeded clients should be present
        names = {c["client_name"] for c in items}
        seeded = {"Famille Lefèvre", "Boulangerie Moreau", "M. et Mme Bernard",
                  "SCI Le Clos", "Cabinet Dr. Rousseau"}
        assert seeded.issubset(names), f"Missing seeded: {seeded - names}"

    def test_acme_chantier_invisible_to_default_admin(self, api_url, acme_admin, admin_headers):
        # Acme admin creates a chantier (iter3: technician role can't create)
        r = requests.post(f"{api_url}/chantiers", json={
            "client_name": "TEST_AcmeOnly",
            "address": "1 Acme Street",
            "status": "devis_a_faire",
        }, headers=acme_admin["headers"], timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        assert r.json()["company_id"] == "acme-test"

        # Default admin lists -> must NOT see it
        r2 = requests.get(f"{api_url}/chantiers", headers=admin_headers, timeout=30)
        assert r2.status_code == 200
        ids = {c["id"] for c in r2.json()}
        assert cid not in ids, "Cross-company leakage in GET /chantiers"

        # Default admin GET by id -> 404
        r3 = requests.get(f"{api_url}/chantiers/{cid}", headers=admin_headers, timeout=30)
        assert r3.status_code == 404, f"Expected 404 cross-company, got {r3.status_code}"

        # Default admin PATCH -> 404
        r4 = requests.patch(f"{api_url}/chantiers/{cid}",
                            json={"status": "cloture"},
                            headers=admin_headers, timeout=30)
        assert r4.status_code == 404, f"Expected 404 cross-company PATCH, got {r4.status_code}"

        # Default admin POST mesure on acme chantier -> 404
        r5 = requests.post(f"{api_url}/mesures", json={
            "chantier_id": cid, "block_type": "standard", "label": "X",
        }, headers=admin_headers, timeout=30)
        assert r5.status_code == 404, f"Expected 404 cross-company POST mesure, got {r5.status_code}"

        # Cleanup (DELETE requires admin role per iter3)
        requests.delete(f"{api_url}/chantiers/{cid}",
                        headers=acme_admin["headers"], timeout=30)

    def test_acme_user_sees_only_acme_chantiers(self, api_url, acme_user):
        r = requests.get(f"{api_url}/chantiers", headers=acme_user["headers"], timeout=30)
        assert r.status_code == 200
        for c in r.json():
            assert c["company_id"] == "acme-test"


# ---------- PATCH assigned_to persistence ----------------------------------
class TestChantierAssignment:
    def test_patch_assigned_to_persists(self, api_url, commercial_headers, admin_headers):
        # commercial creates chantier
        r = requests.post(f"{api_url}/chantiers", json={
            "client_name": "TEST_AssignClient",
            "address": "9 Assign Lane",
        }, headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]

        # find tech user_id via /api/users
        ru = requests.get(f"{api_url}/users", headers=admin_headers, timeout=30)
        assert ru.status_code == 200
        techs = [u for u in ru.json() if u["role"] == "technician"
                 and u["email"] == "tech@mesurechassis.fr"]
        assert techs, "Tech user not found"
        tech_id = techs[0]["id"]

        # PATCH assigned_to
        rp = requests.patch(f"{api_url}/chantiers/{cid}",
                            json={"assigned_to": tech_id},
                            headers=commercial_headers, timeout=30)
        assert rp.status_code == 200, rp.text
        assert rp.json()["assigned_to"] == tech_id

        # GET to verify persistence
        rg = requests.get(f"{api_url}/chantiers/{cid}",
                          headers=commercial_headers, timeout=30)
        assert rg.status_code == 200
        assert rg.json()["assigned_to"] == tech_id

        # Cleanup
        requests.delete(f"{api_url}/chantiers/{cid}",
                        headers=commercial_headers, timeout=30)


# ---------- Hors-équerre tolerance (>5mm now) -----------------------------
class TestHorsEquerreTolerance:
    @pytest.fixture
    def chantier_id(self, api_url, commercial_headers):
        r = requests.post(f"{api_url}/chantiers", json={
            "client_name": "TEST_Tolerance",
            "address": "Tolerance street",
        }, headers=commercial_headers, timeout=30)
        cid = r.json()["id"]
        yield cid
        requests.delete(f"{api_url}/chantiers/{cid}",
                        headers=commercial_headers, timeout=30)

    def test_delta_3mm_no_alert(self, api_url, commercial_headers, chantier_id):
        r = requests.post(f"{api_url}/mesures", json={
            "chantier_id": chantier_id, "block_type": "standard", "label": "Tol3",
            "diag_1": 1800, "diag_2": 1803,
        }, headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text
        alerts = r.json()["alerts"]
        assert not any("Hors-équerre" in a for a in alerts), \
            f"Should NOT alert at 3mm delta, got {alerts}"

    def test_delta_5mm_no_alert_at_boundary(self, api_url, commercial_headers, chantier_id):
        r = requests.post(f"{api_url}/mesures", json={
            "chantier_id": chantier_id, "block_type": "standard", "label": "Tol5",
            "diag_1": 1800, "diag_2": 1805,
        }, headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text
        alerts = r.json()["alerts"]
        # tolerance is "> 5", so exactly 5 mm should NOT alert
        assert not any("Hors-équerre" in a for a in alerts), \
            f"Should NOT alert at exactly 5mm (>5 tolerance), got {alerts}"

    def test_delta_10mm_alerts(self, api_url, commercial_headers, chantier_id):
        r = requests.post(f"{api_url}/mesures", json={
            "chantier_id": chantier_id, "block_type": "standard", "label": "Tol10",
            "diag_1": 1800, "diag_2": 1810,
        }, headers=commercial_headers, timeout=30)
        assert r.status_code == 200, r.text
        alerts = r.json()["alerts"]
        assert any("Hors-équerre" in a for a in alerts), \
            f"Should alert at 10mm delta, got {alerts}"


# ---------- Feedback DELETE (admin only) and company isolation ------------
class TestFeedbackDeleteAndIsolation:
    def test_admin_delete_feedback(self, api_url, tech_headers, admin_headers):
        # tech creates a feedback in default company
        rc = requests.post(f"{api_url}/feedbacks", json={
            "page_context": "/test/delete",
            "user_comment": "TEST_delete_me_feedback",
            "encoded_data_snapshot": {},
        }, headers=tech_headers, timeout=30)
        assert rc.status_code == 200, rc.text
        fid = rc.json()["id"]

        # admin sees it
        rl = requests.get(f"{api_url}/feedbacks", headers=admin_headers, timeout=30)
        assert rl.status_code == 200
        assert any(f["id"] == fid for f in rl.json())

        # admin deletes
        rd = requests.delete(f"{api_url}/feedbacks/{fid}",
                             headers=admin_headers, timeout=30)
        assert rd.status_code == 200, rd.text

        # verify gone
        rl2 = requests.get(f"{api_url}/feedbacks", headers=admin_headers, timeout=30)
        assert rl2.status_code == 200
        assert not any(f["id"] == fid for f in rl2.json()), \
            "Feedback still present after DELETE"

    def test_tech_cannot_delete_feedback(self, api_url, tech_headers, admin_headers):
        # tech creates a feedback
        rc = requests.post(f"{api_url}/feedbacks", json={
            "page_context": "/test/forbid_delete",
            "user_comment": "TEST_tech_cannot_delete",
            "encoded_data_snapshot": {},
        }, headers=tech_headers, timeout=30)
        assert rc.status_code == 200
        fid = rc.json()["id"]

        # tech tries to delete -> 403
        rd = requests.delete(f"{api_url}/feedbacks/{fid}",
                             headers=tech_headers, timeout=30)
        assert rd.status_code == 403, f"Expected 403 for tech DELETE, got {rd.status_code}"

        # cleanup as admin
        requests.delete(f"{api_url}/feedbacks/{fid}",
                        headers=admin_headers, timeout=30)

    def test_feedback_isolation_between_companies(self, api_url, acme_user,
                                                   acme_admin, admin_headers):
        # Acme user creates a feedback
        rc = requests.post(f"{api_url}/feedbacks", json={
            "page_context": "/acme/page",
            "user_comment": "TEST_acme_feedback_isolation",
            "encoded_data_snapshot": {"co": "acme"},
        }, headers=acme_user["headers"], timeout=30)
        assert rc.status_code == 200, rc.text
        fid = rc.json()["id"]
        assert rc.json()["company_id"] == "acme-test"

        # Default admin must NOT see it
        rl_default = requests.get(f"{api_url}/feedbacks",
                                   headers=admin_headers, timeout=30)
        assert rl_default.status_code == 200
        assert not any(f["id"] == fid for f in rl_default.json()), \
            "Cross-company feedback leak to default admin"

        # Acme admin SHOULD see it
        rl_acme = requests.get(f"{api_url}/feedbacks",
                                headers=acme_admin["headers"], timeout=30)
        assert rl_acme.status_code == 200
        assert any(f["id"] == fid for f in rl_acme.json()), \
            "Acme admin cannot see own-company feedback"

        # Cleanup
        requests.delete(f"{api_url}/feedbacks/{fid}",
                        headers=acme_admin["headers"], timeout=30)


# ---------- Regex special chars in search ----------------------------------
class TestSearchRegexEscape:
    def test_search_with_parentheses_no_500(self, api_url, commercial_headers):
        # Create a chantier with parentheses in address
        rc = requests.post(f"{api_url}/chantiers", json={
            "client_name": "TEST_RegexClient",
            "address": "Rue (2) Special *test+",
        }, headers=commercial_headers, timeout=30)
        assert rc.status_code == 200
        cid = rc.json()["id"]

        try:
            # Search with regex special characters in the query
            for q in ["Rue (2)", "Special *", "test+", "(2)"]:
                rs = requests.get(f"{api_url}/chantiers",
                                  params={"q": q},
                                  headers=commercial_headers, timeout=30)
                assert rs.status_code == 200, \
                    f"q={q!r} returned {rs.status_code}: {rs.text}"

            # And the actual escaped match should find our chantier
            rs2 = requests.get(f"{api_url}/chantiers",
                               params={"q": "Rue (2)"},
                               headers=commercial_headers, timeout=30)
            assert rs2.status_code == 200
            assert any(c["id"] == cid for c in rs2.json()), \
                "Chantier should match escaped regex search"
        finally:
            requests.delete(f"{api_url}/chantiers/{cid}",
                            headers=commercial_headers, timeout=30)
