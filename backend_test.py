"""
Backend test suite for MesureEscalier Phase 1 polish.
Focus: validate that adding optional `element_title` field to MeasurementInput
did not break anything AND that it is correctly persisted/returned/exported.

Tested against the public EXPO_PUBLIC_BACKEND_URL.
"""
from __future__ import annotations

import sys
import requests

BASE = "https://stair-pro.preview.emergentagent.com"
API = f"{BASE}/api"

ADMIN = {"email": "admin@demo.fr", "password": "Demo1234!"}
SOLO = {"email": "marc@mesureescalier.com", "password": "Demo1234!"}
TECH = {"email": "sophie@mesureescaliee.com", "password": "Demo1234!"}
EXPIRED = {"email": "expired@demo.fr", "password": "Demo1234!"}

results = []


def log(ok, name, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name} {('-> ' + detail) if detail else ''}")
    results.append((ok, name, detail))


def login(creds):
    return requests.post(f"{API}/auth/login", json=creds, timeout=20)


def hdrs(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- A. element_title flow ----------
def test_element_title_flow():
    print("\n===== A. element_title flow =====")
    r = login(ADMIN)
    if r.status_code != 200:
        log(False, "A0 login admin", f"HTTP {r.status_code} body={r.text[:200]}")
        return None
    admin = r.json()
    token = admin["token"]
    log(True, "A0 login admin", f"is_locked={admin['user'].get('is_locked')}")

    payload_proj = {
        "client_nom": "Lefevre",
        "client_prenom": "Camille",
        "address": "12 rue des Acacias",
        "postal_code": "44000",
        "city": "Nantes",
        "phone": "0612345678",
        "notes": "Maison de campagne, cave + comble",
    }
    r = requests.post(f"{API}/projects", json=payload_proj, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A1 POST /projects", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    pid = r.json()["id"]
    log(True, "A1 POST /projects", f"id={pid}")

    meas_body = {
        "element_title": "Escalier de cave",
        "material": "bois",
        "hauteur_brute": 2700,
        "sols_finis_zero": True,
        "reserve_bas": 0,
        "reserve_haut": 0,
        "epaisseur_dalle": 200,
        "tremie_longueur": 2400,
        "tremie_largeur": 900,
        "reculement_max": 3500,
        "remarques": "",
    }
    r = requests.post(f"{API}/projects/{pid}/measurement", json=meas_body, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A2 POST /measurement (element_title)", f"HTTP {r.status_code} {r.text[:300]}")
        return token
    saved = r.json()
    log(saved.get("element_title") == "Escalier de cave",
        "A2 POST /measurement element_title persisté",
        f"element_title={saved.get('element_title')!r}")

    r = requests.get(f"{API}/projects/{pid}", headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A3 GET /projects/{id}", f"HTTP {r.status_code}")
    else:
        m = (r.json().get("measurement") or {})
        log(m.get("element_title") == "Escalier de cave",
            "A3 GET /projects/{id} measurement.element_title",
            f"val={m.get('element_title')!r}")

    meas_no_title = {k: v for k, v in meas_body.items() if k != "element_title"}
    r = requests.post(f"{API}/projects/{pid}/measurement/preview", json=meas_no_title, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A4 preview sans element_title", f"HTTP {r.status_code} {r.text[:300]}")
    else:
        res = r.json()
        missing = {"n_steps", "h", "g", "blondel_value"} - set(res.keys())
        log(not missing, "A4 preview sans element_title contient n_steps/h/g/blondel",
            f"n_steps={res.get('n_steps')} h={res.get('h')} g={res.get('g')} blondel={res.get('blondel_value')}")

    r = requests.post(f"{API}/projects/{pid}/measurement/validate", headers=hdrs(token), timeout=20)
    log(r.status_code == 200, "A5 POST /measurement/validate", f"HTTP {r.status_code}")

    r = requests.get(f"{API}/projects/{pid}/export/pdf", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code != 200:
        log(False, "A6 GET /export/pdf", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        content = r.content
        log(content[:5] == b"%PDF-", "A6 GET /export/pdf header %PDF-", f"size={len(content)} bytes")
        # ReportLab encodes plain text inside content streams; "Escalier de cave"
        # should appear as raw substring in the uncompressed PDF.
        found = b"Escalier de cave" in content
        log(found, "A6 GET /export/pdf mentionne 'Escalier de cave'",
            f"raw_search found={found}")

    return token, pid


# ---------- B. Non-regression ----------
def test_non_regression():
    print("\n===== B. Non-régression =====")
    tokens = {}
    for label, creds in [("admin", ADMIN), ("solo", SOLO), ("technicien", TECH)]:
        r = login(creds)
        if r.status_code != 200:
            log(False, f"B-login {label}", f"HTTP {r.status_code} {r.text[:200]}")
            continue
        u = r.json()["user"]
        tokens[label] = r.json()["token"]
        log(u.get("is_locked") is False, f"B-login {label} is_locked=false",
            f"is_locked={u.get('is_locked')} trial_days_remaining={u.get('trial_days_remaining')}")

    r = login(EXPIRED)
    if r.status_code != 200:
        log(False, "B-login expired", f"HTTP {r.status_code}")
    else:
        u = r.json()["user"]
        tok_exp = r.json()["token"]
        log(u.get("is_locked") is True, "B-login expired is_locked=true", f"is_locked={u.get('is_locked')}")
        r2 = requests.get(f"{API}/projects", headers=hdrs(tok_exp), timeout=20)
        log(r2.status_code == 402, "B expired GET /projects → 402", f"HTTP {r2.status_code}")

    admin_tok = tokens.get("admin")
    if not admin_tok:
        return

    payload_proj = {
        "client_nom": "Moreau",
        "client_prenom": "Julien",
        "address": "5 impasse du Verger",
        "postal_code": "75011",
        "city": "Paris",
        "phone": "0698765432",
        "notes": "",
    }
    r = requests.post(f"{API}/projects", json=payload_proj, headers=hdrs(admin_tok), timeout=20)
    log(r.status_code == 200, "B CRUD - POST /projects", f"HTTP {r.status_code}")
    pid3 = r.json()["id"] if r.status_code == 200 else None

    if pid3:
        r = requests.get(f"{API}/projects/{pid3}", headers=hdrs(admin_tok), timeout=20)
        log(r.status_code == 200, "B CRUD - GET /projects/{id}", f"HTTP {r.status_code}")
        r = requests.put(f"{API}/projects/{pid3}", json={"notes": "Mise à jour test"}, headers=hdrs(admin_tok), timeout=20)
        log(r.status_code == 200, "B CRUD - PUT /projects/{id}", f"HTTP {r.status_code}")
        r = requests.get(f"{API}/projects", headers=hdrs(admin_tok), timeout=20)
        log(r.status_code == 200 and isinstance(r.json(), list),
            "B CRUD - GET /projects list",
            f"HTTP {r.status_code} count={len(r.json()) if r.status_code == 200 else 'n/a'}")

    meas_body = {
        "material": "acier",
        "hauteur_brute": 2700,
        "sols_finis_zero": True,
        "reserve_bas": 0,
        "reserve_haut": 0,
        "epaisseur_dalle": 200,
        "tremie_longueur": 2400,
        "tremie_largeur": 900,
        "reculement_max": 3500,
        "remarques": "",
    }
    if pid3:
        r = requests.post(f"{API}/projects/{pid3}/measurement/preview", json=meas_body, headers=hdrs(admin_tok), timeout=20)
        if r.status_code != 200:
            log(False, "B Preview standard h=2700/recul=3500", f"HTTP {r.status_code} {r.text[:200]}")
        else:
            res = r.json()
            ok = (res.get("n_steps") == 15 and 178 <= res.get("h", 0) <= 182 and res.get("valid_blondel") is True)
            log(ok, "B Preview standard h=2700/recul=3500",
                f"n_steps={res.get('n_steps')} h={res.get('h')} valid_blondel={res.get('valid_blondel')}")

        r = requests.post(f"{API}/projects/{pid3}/measurement", json=meas_body, headers=hdrs(admin_tok), timeout=20)
        default_title = r.json().get("element_title") if r.status_code == 200 else None
        log(r.status_code == 200, "B Save measurement (sans element_title → default)",
            f"HTTP {r.status_code} default element_title={default_title!r}")

        r = requests.get(f"{API}/projects/{pid3}/export/dxf", headers=hdrs(admin_tok), timeout=30)
        if r.status_code != 200:
            log(False, "B Export DXF", f"HTTP {r.status_code}")
        else:
            txt = r.content[:80].decode(errors="ignore")
            log("SECTION" in txt and txt.lstrip().startswith("0"),
                "B Export DXF commence par 0\\nSECTION", f"prefix={txt[:40]!r}")

    r = requests.get(f"{API}/stats", headers=hdrs(admin_tok), timeout=20)
    log(r.status_code == 200, "B GET /api/stats admin", f"HTTP {r.status_code}")

    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    r = requests.put(f"{API}/auth/me", json={"company_logo_base64": tiny_png_b64}, headers=hdrs(admin_tok), timeout=20)
    log(r.status_code == 200, "B PUT /api/auth/me company_logo_base64", f"HTTP {r.status_code}")

    if pid3:
        r = requests.post(f"{API}/projects/{pid3}/photos",
                          json={"base64": tiny_png_b64, "caption": "Vue d'ensemble"},
                          headers=hdrs(admin_tok), timeout=20)
        log(r.status_code == 200, "B Photos POST 1", f"HTTP {r.status_code}")
        if r.status_code == 200:
            photo_id = r.json()["id"]
            r = requests.get(f"{API}/projects/{pid3}/photos", headers=hdrs(admin_tok), timeout=20)
            log(r.status_code == 200 and len(r.json()) >= 1, "B Photos GET",
                f"count={len(r.json()) if r.status_code==200 else 'n/a'}")
            for i in range(9):
                requests.post(f"{API}/projects/{pid3}/photos",
                              json={"base64": tiny_png_b64, "caption": f"photo {i+2}"},
                              headers=hdrs(admin_tok), timeout=20)
            r = requests.post(f"{API}/projects/{pid3}/photos",
                              json={"base64": tiny_png_b64, "caption": "photo 11 overlimit"},
                              headers=hdrs(admin_tok), timeout=20)
            log(r.status_code == 400, "B Photos limite 10 (11e rejetée)", f"HTTP {r.status_code}")
            r = requests.delete(f"{API}/projects/{pid3}/photos/{photo_id}", headers=hdrs(admin_tok), timeout=20)
            log(r.status_code == 200, "B Photos DELETE", f"HTTP {r.status_code}")

        requests.delete(f"{API}/projects/{pid3}", headers=hdrs(admin_tok), timeout=20)


def main():
    print(f"Testing against: {API}\n")
    test_element_title_flow()
    test_non_regression()

    print("\n===== SUMMARY =====")
    passed = sum(1 for ok, *_ in results if ok)
    total = len(results)
    print(f"{passed}/{total} checks passed")
    failed = [(n, d) for ok, n, d in results if not ok]
    if failed:
        print("\nFailures:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
