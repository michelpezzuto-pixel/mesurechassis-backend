"""Regression test suite — MesureChâssis backend post-refactor.

Coverage:
  1) Auth (login/me) for admin, commercial, technician
  2) Chantiers CRUD
  3) Mesures CRUD
  4) Users / Company profile / Stats
  5) Exports (PDF, JSON, CSV, XLSX)
  6) Feedbacks
  7) Error handling: 422 / 404 / 400
  8) RBAC sanity checks (no 500s)
"""
from __future__ import annotations

import os
import sys
import uuid

import requests

BASE = os.environ.get(
    "REVIEW_BACKEND_URL",
    "https://window-field-app.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMM = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    icon = "PASS" if ok else "FAIL"
    print(f"[{icon}] {name}{' — ' + detail if detail else ''}")
    results.append((name, ok, detail))


def login(email: str, password: str) -> str | None:
    r = requests.post(
        f"{API}/auth/login", json={"email": email, "password": password},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    return r.json()["access_token"]


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# 1) AUTH
admin_token = login(*ADMIN)
record("1a. POST /auth/login (admin)", admin_token is not None)
comm_token = login(*COMM)
record("1b. POST /auth/login (commercial)", comm_token is not None)
tech_token = login(*TECH)
record("1c. POST /auth/login (technician)", tech_token is not None)

if not admin_token:
    print("FATAL: cannot login as admin, abort.")
    sys.exit(1)

for role, tok in [("admin", admin_token), ("commercial", comm_token),
                  ("technician", tech_token)]:
    r = requests.get(f"{API}/auth/me", headers=H(tok), timeout=10)
    record(f"2. GET /auth/me ({role})",
           r.status_code == 200 and r.json().get("role") in
           {"admin", "commercial", "technician"},
           f"status={r.status_code}")

# Capture initial artisan_mode for restore
r = requests.get(f"{API}/company/profile", headers=H(admin_token), timeout=10)
initial_artisan_mode = bool(r.json().get("artisan_mode")) if r.status_code == 200 else False
print(f"\n>>> Initial artisan_mode = {initial_artisan_mode}\n")

# 3) GET /chantiers
r = requests.get(f"{API}/chantiers", headers=H(admin_token), timeout=10)
ok = r.status_code == 200 and isinstance(r.json(), list)
record("3. GET /chantiers", ok,
       f"status={r.status_code}, count={len(r.json()) if ok else 'n/a'}")

# 4) POST /chantiers
suffix = uuid.uuid4().hex[:6]
payload = {
    "first_name": "Élodie",
    "last_name": f"Régression-{suffix}",
    "address": f"42 rue du Refactoring {suffix}, 75003 Paris",
    "postal_code": "75003",
    "city": "Paris",
    "appointment_at": "2026-07-15T14:30:00Z",
    "notes": "Test regression post-refactor",
}
r = requests.post(f"{API}/chantiers", headers=H(admin_token),
                  json=payload, timeout=15)
chantier_id = r.json()["id"] if r.status_code == 200 else None
record("4. POST /chantiers (admin)", r.status_code == 200 and chantier_id,
       f"status={r.status_code}")
if chantier_id:
    cn = r.json().get("client_name")
    record("4b. client_name auto-composé",
           cn == f"Régression-{suffix} Élodie", f"got={cn!r}")

if not chantier_id:
    print("FATAL: cannot create chantier, abort.")
    sys.exit(1)

# 5) PATCH /chantiers
r = requests.patch(f"{API}/chantiers/{chantier_id}", headers=H(admin_token),
                   json={"notes": "Updated by regression", "status": "technique_a_valider"},
                   timeout=10)
record("5. PATCH /chantiers/{id}",
       r.status_code == 200 and r.json().get("status") == "technique_a_valider",
       f"status={r.status_code}")

# 6) GET /chantiers/{id}
r = requests.get(f"{API}/chantiers/{chantier_id}", headers=H(admin_token), timeout=10)
record("6. GET /chantiers/{id}",
       r.status_code == 200 and r.json()["id"] == chantier_id,
       f"status={r.status_code}")

# 7) POST /mesures (standard)
m_payload = {
    "chantier_id": chantier_id,
    "block_type": "standard",
    "label": "Salon — fenêtre Ouest",
    "bay_width": 1500,
    "bay_height": 2400,
    "bay_diagonal_1": 2828,
    "bay_diagonal_2": 2828,
    "diag_1_verified": True,
    "diag_2_verified": True,
}
r = requests.post(f"{API}/mesures", headers=H(admin_token),
                  json=m_payload, timeout=15)
mesure_id = r.json().get("id") if r.status_code == 200 else None
record("7. POST /mesures (standard 1500x2400)",
       r.status_code == 200 and mesure_id,
       f"status={r.status_code}, alerts={r.json().get('alerts') if r.status_code == 200 else 'n/a'}")

# 7b) trapeze for export coverage
r = requests.post(f"{API}/mesures", headers=H(admin_token), json={
    "chantier_id": chantier_id, "block_type": "trapeze", "label": "Pignon",
    "bay_width": 1800, "height_left": 1200, "height_right": 1600,
}, timeout=15)
m_trap = r.json().get("id") if r.status_code == 200 else None
record("7b. POST /mesures (trapeze)", r.status_code == 200 and m_trap,
       f"status={r.status_code}")

# 8) GET /chantiers/{id}/mesures
r = requests.get(f"{API}/chantiers/{chantier_id}/mesures",
                 headers=H(admin_token), timeout=10)
record("8. GET /chantiers/{id}/mesures",
       r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 2,
       f"status={r.status_code}, n={len(r.json()) if r.status_code == 200 else 'n/a'}")

# 9) PATCH /mesures
if mesure_id:
    upd = dict(m_payload)
    upd["label"] = "Salon — fenêtre Ouest (révisée)"
    upd["bay_height"] = 2410
    r = requests.patch(f"{API}/mesures/{mesure_id}", headers=H(admin_token),
                       json=upd, timeout=10)
    record("9. PATCH /mesures/{id}",
           r.status_code == 200 and r.json().get("bay_height") == 2410,
           f"status={r.status_code}")

# 10) GET /users
r = requests.get(f"{API}/users", headers=H(admin_token), timeout=10)
record("10. GET /users (admin)",
       r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 3,
       f"status={r.status_code}, n={len(r.json()) if r.status_code == 200 else 'n/a'}")

# 11) GET /company/profile
r = requests.get(f"{API}/company/profile", headers=H(admin_token), timeout=10)
record("11. GET /company/profile",
       r.status_code == 200 and "artisan_mode" in r.json() and "company_id" in r.json(),
       f"status={r.status_code}")

# 12) PATCH /company/profile (toggle then restore)
new_val = not initial_artisan_mode
r = requests.patch(f"{API}/company/profile", headers=H(admin_token),
                   json={"artisan_mode": new_val}, timeout=10)
record("12a. PATCH /company/profile (toggle)",
       r.status_code == 200 and r.json().get("artisan_mode") == new_val,
       f"status={r.status_code}")
r = requests.patch(f"{API}/company/profile", headers=H(admin_token),
                   json={"artisan_mode": initial_artisan_mode}, timeout=10)
record("12b. PATCH /company/profile (restore)",
       r.status_code == 200 and r.json().get("artisan_mode") == initial_artisan_mode,
       f"status={r.status_code}")

# 13) GET /stats/company
r = requests.get(f"{API}/stats/company", headers=H(admin_token), timeout=10)
record("13. GET /stats/company",
       r.status_code == 200 and "by_status" in r.json() and "total_chantiers" in r.json(),
       f"status={r.status_code}")

# 14) GET /stats/commercials
r = requests.get(f"{API}/stats/commercials", headers=H(admin_token), timeout=10)
record("14. GET /stats/commercials",
       r.status_code == 200 and "commercials" in r.json(),
       f"status={r.status_code}")

# 15) export.pdf
r = requests.get(f"{API}/chantiers/{chantier_id}/export.pdf",
                 headers=H(admin_token), timeout=20)
record("15. GET export.pdf",
       (r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf")
        and r.content.startswith(b"%PDF-") and len(r.content) > 1000),
       f"status={r.status_code}, bytes={len(r.content)}")

# 16) export.json
r = requests.get(f"{API}/chantiers/{chantier_id}/export.json",
                 headers=H(admin_token), timeout=15)
try:
    j = r.json()
    record("16. GET export.json (schema mc.v1)",
           (r.status_code == 200 and j.get("schema_version") == "mc.v1"
            and "client" in j and "openings" in j
            and j.get("openings_count") == len(j.get("openings", []))),
           f"status={r.status_code}, openings={j.get('openings_count')}")
    shapes = {o.get("shape") for o in j.get("openings", [])}
    record("16b. export.json shapes",
           "rectangular" in shapes and "trapezoidal" in shapes,
           f"shapes={shapes}")
except Exception as exc:
    record("16. GET export.json", False, f"err={exc}")

# 17) export.csv
r = requests.get(f"{API}/chantiers/{chantier_id}/export.csv",
                 headers=H(admin_token), timeout=15)
ct = r.headers.get("content-type", "")
record("17. GET export.csv",
       r.status_code == 200 and "text/csv" in ct and len(r.content) > 50,
       f"status={r.status_code}, ct={ct}")

# 18) export.xlsx
r = requests.get(f"{API}/chantiers/{chantier_id}/export.xlsx",
                 headers=H(admin_token), timeout=15)
ct = r.headers.get("content-type", "")
record("18. GET export.xlsx",
       (r.status_code == 200 and "spreadsheetml.sheet" in ct
        and r.content.startswith(b"PK")),
       f"status={r.status_code}, ct={ct[:50]}")

# 19) POST /feedbacks
r = requests.post(f"{API}/feedbacks", headers=H(comm_token), json={
    "page_context": "regression-test",
    "user_comment": "Post-refactor smoke test",
    "encoded_data_snapshot": {"foo": "bar"},
}, timeout=10)
fb_id = r.json().get("id") if r.status_code == 200 else None
record("19. POST /feedbacks (commercial)",
       r.status_code == 200 and fb_id, f"status={r.status_code}")

# 20) GET /feedbacks (admin)
r = requests.get(f"{API}/feedbacks", headers=H(admin_token), timeout=10)
record("20. GET /feedbacks (admin)",
       r.status_code == 200 and isinstance(r.json(), list),
       f"status={r.status_code}")

# RBAC sanity (no 500)
r = requests.post(f"{API}/chantiers", headers=H(tech_token), json={
    "first_name": "RBAC", "last_name": "Test",
    "address": "1 rue Test, 75001 Paris",
}, timeout=10)
record("RBAC-1. Tech POST /chantiers — no 500",
       r.status_code != 500,
       f"status={r.status_code} (artisan_mode={initial_artisan_mode})")
if r.status_code == 200:
    extra = r.json().get("id")
    if extra:
        requests.delete(f"{API}/chantiers/{extra}", headers=H(admin_token), timeout=10)

r = requests.get(f"{API}/stats/company", headers=H(comm_token), timeout=10)
record("RBAC-2. Commercial GET /stats/company — no 500",
       r.status_code != 500, f"status={r.status_code}")

# ERROR HANDLING
r = requests.post(f"{API}/chantiers", headers=H(admin_token),
                  json={"first_name": "MissingAddr"}, timeout=10)
record("ERR-1. POST /chantiers w/o address → 422",
       r.status_code == 422, f"status={r.status_code}")

r = requests.get(f"{API}/chantiers/nonexistent-id-xyz",
                 headers=H(admin_token), timeout=10)
record("ERR-2. GET /chantiers/nonexistent-id → 404",
       r.status_code == 404, f"status={r.status_code}")

r = requests.patch(f"{API}/chantiers/{chantier_id}", headers=H(admin_token),
                   json={"status": "foobar"}, timeout=10)
record("ERR-3. PATCH status=foobar → 400",
       r.status_code == 400, f"status={r.status_code}")

# CLEANUP
if mesure_id:
    r = requests.delete(f"{API}/mesures/{mesure_id}", headers=H(admin_token), timeout=10)
    record("21. DELETE /mesures/{id}", r.status_code == 200, f"status={r.status_code}")
if m_trap:
    requests.delete(f"{API}/mesures/{m_trap}", headers=H(admin_token), timeout=10)
if fb_id:
    requests.delete(f"{API}/feedbacks/{fb_id}", headers=H(admin_token), timeout=10)

r = requests.delete(f"{API}/chantiers/{chantier_id}", headers=H(admin_token), timeout=10)
record("22. DELETE /chantiers/{id}", r.status_code == 200, f"status={r.status_code}")

# Final restore
r = requests.patch(f"{API}/company/profile", headers=H(admin_token),
                   json={"artisan_mode": initial_artisan_mode}, timeout=10)
print(f"\n>>> Final artisan_mode restored to {initial_artisan_mode}: status={r.status_code}\n")

total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
print(f"\n{'='*70}\nREGRESSION RESULT: {passed}/{total} passed\n{'='*70}")
if passed != total:
    print("\nFAILURES:")
    for name, ok, det in results:
        if not ok:
            print(f"  - {name}: {det}")
sys.exit(0 if passed == total else 1)
