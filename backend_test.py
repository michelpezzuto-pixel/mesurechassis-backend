"""Targeted regression test — DELETE /api/chantiers/{id} authorization."""
import sys
import uuid
import requests

BASE = "https://window-field-app.preview.emergentagent.com/api"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMM = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")


def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed {r.status_code}: {r.text}"
    j = r.json()
    return j["access_token"], j["user"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def stop_on_5xx(r, ctx):
    if r.status_code >= 500:
        print(f"FATAL 5xx at {ctx}: {r.status_code} {r.text}")
        sys.exit(2)


results = []


def rec(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name} -- {detail}")


# ---- 1) Commercial CAN delete now ----
def scenario_commercial_can_delete():
    tok_c, _ = login(*COMM)

    r = requests.post(f"{BASE}/chantiers", headers=hdr(tok_c),
                      json={"client_name": "DELETE_TEST_COMM",
                            "address": "1 rue du Test, 75001 Paris",
                            "status": "devis_a_faire"}, timeout=20)
    stop_on_5xx(r, "POST /chantiers commercial")
    if r.status_code != 200:
        rec("S1.create chantier", False, f"status={r.status_code} {r.text}")
        return
    chantier_id = r.json()["id"]
    rec("S1.create chantier (commercial)", True, f"id={chantier_id}")

    def mesure_payload(label):
        return {
            "chantier_id": chantier_id,
            "block_type": "standard",
            "label": label,
            "bay_width": 1200.0,
            "bay_height": 2100.0,
            "bay_diagonal_1": 2419.0,
            "bay_diagonal_2": 2419.0,
            "diag_1_verified": True,
            "diag_2_verified": True,
            "bloc_thickness": 200.0,
            "wall_type": "ite",
        }

    mids = []
    for lbl in ("Fenetre Salon", "Fenetre Cuisine"):
        rm = requests.post(f"{BASE}/mesures", headers=hdr(tok_c), json=mesure_payload(lbl), timeout=20)
        stop_on_5xx(rm, "POST /mesures commercial")
        if rm.status_code != 200:
            rec(f"S1.create mesure {lbl}", False, f"{rm.status_code} {rm.text}")
            return
        mids.append(rm.json()["id"])
    rec("S1.create 2 mesures", True, f"ids={mids}")

    rd = requests.delete(f"{BASE}/chantiers/{chantier_id}", headers=hdr(tok_c), timeout=20)
    stop_on_5xx(rd, "DELETE /chantiers commercial")
    ok = rd.status_code == 200
    rec("S1.DELETE chantier (commercial) -> 200", ok, f"status={rd.status_code} body={rd.text[:120]}")
    if not ok:
        return

    rg = requests.get(f"{BASE}/chantiers/{chantier_id}/mesures", headers=hdr(tok_c), timeout=20)
    stop_on_5xx(rg, "GET mesures after delete")
    rec("S1.GET mesures after delete -> 404", rg.status_code == 404, f"status={rg.status_code}")

    rc = requests.get(f"{BASE}/chantiers/{chantier_id}", headers=hdr(tok_c), timeout=20)
    stop_on_5xx(rc, "GET chantier after delete")
    rec("S1.GET chantier after delete -> 404", rc.status_code == 404, f"status={rc.status_code}")


# ---- 2) Technician CANNOT delete ----
def scenario_technician_forbidden():
    tok_t, _ = login(*TECH)
    r = requests.get(f"{BASE}/chantiers", headers=hdr(tok_t), timeout=20)
    stop_on_5xx(r, "GET /chantiers tech")
    if r.status_code != 200 or not r.json():
        tok_a, _ = login(*ADMIN)
        ra = requests.post(f"{BASE}/chantiers", headers=hdr(tok_a),
                           json={"client_name": "TECH_FORBID_PROBE",
                                 "address": "2 rue Test, 75002 Paris",
                                 "status": "devis_a_faire"}, timeout=20)
        if ra.status_code != 200:
            rec("S2.precond chantier", False, f"{ra.status_code}")
            return
        target = ra.json()["id"]
    else:
        target = r.json()[0]["id"]

    rd = requests.delete(f"{BASE}/chantiers/{target}", headers=hdr(tok_t), timeout=20)
    stop_on_5xx(rd, "DELETE /chantiers tech")
    rec("S2.DELETE as technician -> 403", rd.status_code == 403, f"status={rd.status_code} body={rd.text[:120]}")

    tok_a, _ = login(*ADMIN)
    rg = requests.get(f"{BASE}/chantiers/{target}", headers=hdr(tok_a), timeout=20)
    rec("S2.chantier still exists", rg.status_code == 200, f"status={rg.status_code}")


# ---- 3) Admin still works ----
def scenario_admin_regression():
    tok_a, _ = login(*ADMIN)
    r = requests.post(f"{BASE}/chantiers", headers=hdr(tok_a),
                      json={"client_name": "DELETE_TEST_ADMIN",
                            "address": "3 rue Test, 75003 Paris",
                            "status": "devis_a_faire"}, timeout=20)
    stop_on_5xx(r, "POST chantier admin")
    if r.status_code != 200:
        rec("S3.create chantier admin", False, f"{r.status_code} {r.text}")
        return
    cid = r.json()["id"]

    rm = requests.post(f"{BASE}/mesures", headers=hdr(tok_a),
                       json={"chantier_id": cid, "block_type": "standard",
                             "label": "Baie Admin",
                             "bay_width": 1500.0, "bay_height": 2200.0,
                             "bay_diagonal_1": 2663.0, "bay_diagonal_2": 2663.0,
                             "diag_1_verified": True, "diag_2_verified": True,
                             "bloc_thickness": 200.0, "wall_type": "ite"},
                       timeout=20)
    stop_on_5xx(rm, "POST mesure admin")
    rec("S3.create mesure (admin)", rm.status_code == 200, f"{rm.status_code}")

    rd = requests.delete(f"{BASE}/chantiers/{cid}", headers=hdr(tok_a), timeout=20)
    stop_on_5xx(rd, "DELETE chantier admin")
    rec("S3.DELETE chantier (admin) -> 200", rd.status_code == 200, f"{rd.status_code}")

    rg = requests.get(f"{BASE}/chantiers/{cid}/mesures", headers=hdr(tok_a), timeout=20)
    rec("S3.cascade — GET mesures after delete -> 404", rg.status_code == 404, f"{rg.status_code}")


# ---- 4) Cross-company isolation ----
def scenario_cross_company_isolation():
    iso_company = f"zzz-isolation-test-{uuid.uuid4().hex[:8]}"
    iso_email = f"iso.commercial+{uuid.uuid4().hex[:6]}@example.com"
    iso_password = "IsoPass!123"

    rr = requests.post(f"{BASE}/auth/register", json={
        "name": "Iso Commercial",
        "email": iso_email,
        "password": iso_password,
        "role": "commercial",
        "company_id": iso_company,
    }, timeout=20)
    stop_on_5xx(rr, "register iso user")
    if rr.status_code != 200:
        rec("S4.register iso user", False, f"{rr.status_code} {rr.text}")
        return
    tok_iso = rr.json()["access_token"]
    rec("S4.register iso user", True, f"company={iso_company}")

    rc = requests.post(f"{BASE}/chantiers", headers=hdr(tok_iso),
                       json={"client_name": "ISO_CHANTIER",
                             "address": "9 rue Isolee, 75009 Paris",
                             "status": "devis_a_faire"}, timeout=20)
    stop_on_5xx(rc, "POST chantier iso")
    if rc.status_code != 200:
        rec("S4.create iso chantier", False, f"{rc.status_code} {rc.text}")
        return
    iso_cid = rc.json()["id"]
    rec("S4.create iso chantier", True, f"id={iso_cid}")

    tok_c, _ = login(*COMM)
    rd = requests.delete(f"{BASE}/chantiers/{iso_cid}", headers=hdr(tok_c), timeout=20)
    stop_on_5xx(rd, "DELETE iso chantier from other company")
    rec("S4.DELETE iso chantier from other company (returns 200 no-op)",
        rd.status_code == 200, f"status={rd.status_code} body={rd.text[:80]}")

    rg = requests.get(f"{BASE}/chantiers/{iso_cid}", headers=hdr(tok_iso), timeout=20)
    stop_on_5xx(rg, "GET iso chantier as owner")
    rec("S4.iso chantier still exists (GET as owner -> 200)",
        rg.status_code == 200, f"status={rg.status_code}")

    # cleanup
    requests.delete(f"{BASE}/chantiers/{iso_cid}", headers=hdr(tok_iso), timeout=20)


if __name__ == "__main__":
    print(f"Base URL: {BASE}\n")
    scenario_commercial_can_delete()
    print()
    scenario_technician_forbidden()
    print()
    scenario_admin_regression()
    print()
    scenario_cross_company_isolation()

    print("\n=== Summary ===")
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name} :: {detail}")
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)
