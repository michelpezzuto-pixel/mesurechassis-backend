"""RBAC validation WITHOUT artisan_mode bypass.

Tests that role restrictions are correctly enforced when company.artisan_mode=false.
Re-enables artisan_mode at the end to avoid locking the user out of the Preview.
"""
import os
import sys
import json
import uuid
import requests
from pathlib import Path
from datetime import datetime, timezone

# Resolve backend base URL via frontend .env (REACT_APP_BACKEND_URL)
FRONT_ENV = Path("/app/frontend/.env")
BASE = None
for line in FRONT_ENV.read_text().splitlines():
    if line.startswith("EXPO_PUBLIC_BACKEND_URL=") or line.startswith("REACT_APP_BACKEND_URL="):
        BASE = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
assert BASE, "Cannot resolve backend URL from frontend/.env"
API = f"{BASE.rstrip('/')}/api"
print(f"[BASE] {API}")

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMM = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

results = []


def record(name, expected, got, passed, extra=""):
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {name}: expected {expected}, got {got}"
    if extra:
        msg += f" | {extra}"
    print(msg)
    results.append((name, expected, got, passed, extra))


def login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    return r


def h(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    # ---- 1) Admin login + disable artisan_mode ------------------------
    r = login(*ADMIN)
    record("Admin login", 200, r.status_code, r.status_code == 200)
    if r.status_code != 200:
        return finish()
    admin_token = r.json()["access_token"]

    # snapshot current profile
    r0 = requests.get(f"{API}/company/profile", headers=h(admin_token), timeout=20)
    print(f"[INFO] Initial company profile: {r0.status_code} {r0.text[:200]}")

    r = requests.patch(f"{API}/company/profile", headers=h(admin_token),
                       json={"artisan_mode": False}, timeout=20)
    ok = r.status_code == 200 and r.json().get("artisan_mode") is False
    record("PATCH /company/profile artisan_mode=false (admin)", "200 + artisan_mode=false",
           f"{r.status_code} artisan_mode={r.json().get('artisan_mode') if r.status_code==200 else 'n/a'}",
           ok)
    if not ok:
        return finish(admin_token)

    # Seed: admin creates a chantier (to be deleted/edited by commercial later)
    payload = {
        "first_name": "Camille",
        "last_name": "Lemoine",
        "address": "14 rue des Lilas",
        "postal_code": "75011",
        "city": "Paris",
        "appointment_at": "2026-07-12T09:30:00Z",
        "notes": "RBAC seed chantier",
    }
    r = requests.post(f"{API}/chantiers", headers=h(admin_token), json=payload, timeout=20)
    assert r.status_code == 200, f"Seed chantier failed: {r.status_code} {r.text}"
    seed_chantier_id = r.json()["id"]
    print(f"[SEED] chantier_id={seed_chantier_id}")

    # ---- 2) Commercial role tests ------------------------------------
    r = login(*COMM)
    record("Commercial login", 200, r.status_code, r.status_code == 200)
    comm_token = r.json()["access_token"]

    r = requests.get(f"{API}/chantiers", headers=h(comm_token), timeout=20)
    record("Commercial GET /chantiers", 200, r.status_code, r.status_code == 200)

    # POST create
    new_payload = {
        "first_name": "Julien",
        "last_name": "Bertrand",
        "address": "27 avenue des Champs",
        "postal_code": "33000",
        "city": "Bordeaux",
        "appointment_at": "2026-08-05T14:00:00Z",
        "notes": "Created by commercial - RBAC test",
    }
    r = requests.post(f"{API}/chantiers", headers=h(comm_token), json=new_payload, timeout=20)
    record("Commercial POST /chantiers", 200, r.status_code, r.status_code == 200)
    comm_chantier_id = r.json()["id"] if r.status_code == 200 else None

    # PATCH update existing
    if comm_chantier_id:
        r = requests.patch(f"{API}/chantiers/{comm_chantier_id}", headers=h(comm_token),
                           json={"notes": "Updated by commercial"}, timeout=20)
        record("Commercial PATCH /chantiers/{id}", 200, r.status_code, r.status_code == 200)

    # DELETE - review expects 403 (only admin), but server code allows admin+commercial.
    if comm_chantier_id:
        r = requests.delete(f"{API}/chantiers/{comm_chantier_id}", headers=h(comm_token), timeout=20)
        # Document the actual behavior:
        passed = r.status_code == 403
        record("Commercial DELETE /chantiers/{id} (review expects 403)", 403, r.status_code,
               passed, extra=("Server code allows admin+commercial → 200 is actual behavior"
                              if r.status_code == 200 else ""))

    # PATCH /company/profile - expect 403
    r = requests.patch(f"{API}/company/profile", headers=h(comm_token),
                       json={"name": "Hacky"}, timeout=20)
    record("Commercial PATCH /company/profile", 403, r.status_code, r.status_code == 403)

    # GET /admin/stats/commercials (review path) AND /stats/commercials (actual)
    r = requests.get(f"{API}/admin/stats/commercials", headers=h(comm_token), timeout=20)
    record("Commercial GET /admin/stats/commercials (review path, 404 likely)", "403 or 404",
           r.status_code, r.status_code in (403, 404))
    r = requests.get(f"{API}/stats/commercials", headers=h(comm_token), timeout=20)
    record("Commercial GET /stats/commercials (actual endpoint)", 403,
           r.status_code, r.status_code == 403)

    # ---- 3) Technician role tests ------------------------------------
    r = login(*TECH)
    record("Technician login", 200, r.status_code, r.status_code == 200)
    tech_token = r.json()["access_token"]

    r = requests.get(f"{API}/chantiers", headers=h(tech_token), timeout=20)
    record("Technician GET /chantiers", 200, r.status_code, r.status_code == 200)

    # POST create - expect 403
    r = requests.post(f"{API}/chantiers", headers=h(tech_token), json=new_payload, timeout=20)
    record("Technician POST /chantiers", 403, r.status_code, r.status_code == 403)

    # POST measurement on seed chantier - review says POST /api/chantiers/{id}/mesures
    # Actual endpoint is POST /api/mesures with chantier_id in body
    mesure_payload = {
        "chantier_id": seed_chantier_id,
        "block_type": "standard",
        "label": "Fenêtre salon RBAC test",
        "bay_width": 1200,
        "bay_height": 1500,
        "bay_diagonal_1": 1921,
        "bay_diagonal_2": 1921,
        "diag_1_verified": True,
        "diag_2_verified": True,
    }
    # Try review's literal path first (probably 404 / 405)
    r_lit = requests.post(f"{API}/chantiers/{seed_chantier_id}/mesures",
                          headers=h(tech_token), json=mesure_payload, timeout=20)
    print(f"[INFO] Tech POST /chantiers/{{id}}/mesures (literal review path): {r_lit.status_code}")
    # Actual endpoint
    r = requests.post(f"{API}/mesures", headers=h(tech_token), json=mesure_payload, timeout=20)
    record("Technician POST /mesures (actual measurement endpoint)", 200,
           r.status_code, r.status_code == 200,
           extra=f"literal /chantiers/{{id}}/mesures returned {r_lit.status_code}")

    # PATCH /chantiers/{id} - expect 403
    r = requests.patch(f"{API}/chantiers/{seed_chantier_id}", headers=h(tech_token),
                       json={"notes": "tech sneaks in"}, timeout=20)
    record("Technician PATCH /chantiers/{id}", 403, r.status_code, r.status_code == 403)

    # DELETE - expect 403
    r = requests.delete(f"{API}/chantiers/{seed_chantier_id}", headers=h(tech_token), timeout=20)
    record("Technician DELETE /chantiers/{id}", 403, r.status_code, r.status_code == 403)

    # PATCH /company/profile - expect 403
    r = requests.patch(f"{API}/company/profile", headers=h(tech_token),
                       json={"name": "tech-hack"}, timeout=20)
    record("Technician PATCH /company/profile", 403, r.status_code, r.status_code == 403)

    return finish(admin_token, cleanup_chantier_id=seed_chantier_id)


def finish(admin_token=None, cleanup_chantier_id=None):
    # ---- CLEANUP: re-enable artisan_mode + delete seed chantier -------
    if admin_token:
        if cleanup_chantier_id:
            r = requests.delete(f"{API}/chantiers/{cleanup_chantier_id}",
                                headers=h(admin_token), timeout=20)
            print(f"[CLEANUP] DELETE seed chantier {cleanup_chantier_id}: {r.status_code}")
        r = requests.patch(f"{API}/company/profile", headers=h(admin_token),
                           json={"artisan_mode": True}, timeout=20)
        if r.status_code == 200 and r.json().get("artisan_mode") is True:
            print("[CLEANUP] artisan_mode re-enabled (artisan_mode=true) ✓")
        else:
            print(f"[CLEANUP] FAILED to re-enable artisan_mode: {r.status_code} {r.text}")
            results.append(("CLEANUP re-enable artisan_mode", "200/true",
                            f"{r.status_code}/{r.json().get('artisan_mode') if r.status_code==200 else 'n/a'}",
                            False, "USER MAY BE LOCKED OUT — INVESTIGATE"))

    # ---- Summary -----------------------------------------------------
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, _, _, p, _ in results if p)
    total = len(results)
    for name, exp, got, p, extra in results:
        tag = "PASS" if p else "FAIL"
        line = f"  [{tag}] {name}: expected={exp}, got={got}"
        if extra:
            line += f" | {extra}"
        print(line)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}")
        # Best-effort: try to re-enable artisan_mode anyway
        try:
            r = login(*ADMIN)
            if r.status_code == 200:
                t = r.json()["access_token"]
                rr = requests.patch(f"{API}/company/profile", headers=h(t),
                                    json={"artisan_mode": True}, timeout=20)
                print(f"[FATAL-CLEANUP] re-enable artisan_mode: {rr.status_code}")
        except Exception as e2:
            print(f"[FATAL-CLEANUP] failed: {e2}")
        raise
