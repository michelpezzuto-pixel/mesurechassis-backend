"""Backend test suite for MesureChâssis — Iteration 7."""
from __future__ import annotations
import os
import sys
import uuid
import json
import time
import requests

BASE = os.environ.get("BACKEND_URL", "https://window-field-app.preview.emergentagent.com") + "/api"

ADMIN = {"email": "admin@mesurechassis.fr", "password": "admin123"}
COMM = {"email": "commercial@mesurechassis.fr", "password": "commercial123"}
TECH = {"email": "tech@mesurechassis.fr", "password": "tech123"}

results: list[tuple[str, bool, str]] = []

def record(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} - {detail}")
    results.append((name, ok, detail))


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def login(creds):
    r = requests.post(f"{BASE}/auth/login", json=creds, timeout=30)
    return r


# ===== 1. AUTH =====
print("\n=== 1. AUTH ===")
tokens = {}
users = {}
for label, creds in [("admin", ADMIN), ("commercial", COMM), ("tech", TECH)]:
    r = login(creds)
    if r.status_code == 200 and "access_token" in r.json():
        tokens[label] = r.json()["access_token"]
        users[label] = r.json()["user"]
        record(f"login {label}", True, f"role={r.json()['user']['role']}")
    else:
        record(f"login {label}", False, f"HTTP {r.status_code} {r.text[:200]}")

# /auth/me
for label, tok in tokens.items():
    r = requests.get(f"{BASE}/auth/me", headers=hdr(tok), timeout=20)
    if r.status_code == 200 and "role" in r.json() and "company_id" in r.json():
        record(f"/auth/me {label}", True, f"role={r.json()['role']} company_id={r.json()['company_id']}")
    else:
        record(f"/auth/me {label}", False, f"HTTP {r.status_code} {r.text[:200]}")

# Bad pwd
r = login({"email": "admin@mesurechassis.fr", "password": "WRONG"})
record("bad-password 401", r.status_code == 401, f"HTTP {r.status_code}")


# ===== 2. CHANTIERS DISPATCH FLOW =====
print("\n=== 2. CHANTIERS DISPATCH ===")
chantier_id = None
# Create as commercial
r = requests.post(f"{BASE}/chantiers",
                  headers=hdr(tokens["commercial"]),
                  json={"client_name": "Famille Durand - Test Iter7",
                        "address": "10 rue Lafayette, 75009 Paris"},
                  timeout=20)
if r.status_code == 200:
    j = r.json()
    chantier_id = j["id"]
    ok = j["status"] == "devis_a_faire"
    record("POST /chantiers as commercial (default status devis_a_faire)", ok,
           f"status={j['status']} id={chantier_id}")
else:
    record("POST /chantiers as commercial", False, f"HTTP {r.status_code} {r.text[:200]}")

# PATCH as admin
tech_user_id = users["tech"]["id"]
patch_body = {
    "assigned_to": tech_user_id,
    "appointment_at": "2026-06-15T10:00:00Z",
    "notes": "RDV client",
}
r = requests.patch(f"{BASE}/chantiers/{chantier_id}",
                   headers=hdr(tokens["admin"]),
                   json=patch_body, timeout=20)
if r.status_code == 200:
    j = r.json()
    persisted = (j.get("assigned_to") == tech_user_id
                 and j.get("appointment_at") == "2026-06-15T10:00:00Z"
                 and j.get("notes") == "RDV client")
    record("PATCH /chantiers/{id} as admin persists 3 fields", persisted,
           f"assigned_to={j.get('assigned_to')} appt={j.get('appointment_at')} notes={j.get('notes')}")
else:
    record("PATCH /chantiers/{id} as admin", False, f"HTTP {r.status_code} {r.text[:200]}")

# Non-admin/commercial cannot PATCH (technician)
r = requests.patch(f"{BASE}/chantiers/{chantier_id}",
                   headers=hdr(tokens["tech"]),
                   json={"notes": "hacking"}, timeout=20)
record("PATCH /chantiers as technician → 403", r.status_code == 403,
       f"HTTP {r.status_code}")

# GET shows updated fields
r = requests.get(f"{BASE}/chantiers", headers=hdr(tokens["admin"]), timeout=20)
if r.status_code == 200:
    found = next((c for c in r.json() if c["id"] == chantier_id), None)
    ok = bool(found and found.get("notes") == "RDV client"
              and found.get("appointment_at") == "2026-06-15T10:00:00Z"
              and found.get("assigned_to") == tech_user_id)
    record("GET /chantiers shows updated fields", ok,
           f"found={bool(found)} notes={found.get('notes') if found else None}")
else:
    record("GET /chantiers list", False, f"HTTP {r.status_code}")


# ===== 3. MESURES — 4 BLOCK TYPES =====
print("\n=== 3. MESURES ===")
mesures_created = []

# Standard
payload_std = {
    "chantier_id": chantier_id, "block_type": "standard", "label": "Salon",
    "bay_width": 1200, "bay_height": 2100,
    "bay_diagonal_1": 2419, "bay_diagonal_2": 2419,
    "diag_1_verified": True, "diag_2_verified": True,
    "bloc_thickness": 200, "wall_type": "ite",
}
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json=payload_std, timeout=20)
if r.status_code == 200:
    mesures_created.append(r.json()["id"])
    record("POST /mesures standard", True, f"id={r.json()['id']}")
else:
    record("POST /mesures standard", False, f"HTTP {r.status_code} {r.text[:300]}")

# Coulissant with floor_reserve
payload_coul = {
    "chantier_id": chantier_id, "block_type": "coulissant", "label": "Baie Salon",
    "bay_width": 2400, "bay_height": 2200,
    "bay_diagonal_1": 3253, "bay_diagonal_2": 3253,
    "diag_1_verified": True, "diag_2_verified": True,
    "floor_reserve": 50, "bloc_thickness": 200, "wall_type": "iti",
}
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json=payload_coul, timeout=20)
if r.status_code == 200:
    j = r.json()
    mesures_created.append(j["id"])
    record("POST /mesures coulissant", j.get("floor_reserve") == 50,
           f"floor_reserve={j.get('floor_reserve')}")
else:
    record("POST /mesures coulissant", False, f"HTTP {r.status_code} {r.text[:300]}")

# Porte with floor_reserve
payload_porte = {
    "chantier_id": chantier_id, "block_type": "porte", "label": "Porte d'entrée",
    "bay_width": 900, "bay_height": 2150,
    "bay_diagonal_1": 2331, "bay_diagonal_2": 2331,
    "diag_1_verified": True, "diag_2_verified": True,
    "floor_reserve": 30, "bloc_thickness": 200, "wall_type": "crepi_simple",
}
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json=payload_porte, timeout=20)
if r.status_code == 200:
    j = r.json()
    mesures_created.append(j["id"])
    record("POST /mesures porte", j.get("floor_reserve") == 30,
           f"floor_reserve={j.get('floor_reserve')}")
else:
    record("POST /mesures porte", False, f"HTTP {r.status_code} {r.text[:300]}")

# Trapeze WITHOUT diagonals - only bay_width + height_left + height_right
payload_trap = {
    "chantier_id": chantier_id, "block_type": "trapeze", "label": "Lucarne",
    "bay_width": 1500, "height_left": 1800, "height_right": 1600,
}
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json=payload_trap, timeout=20)
if r.status_code == 200:
    j = r.json()
    mesures_created.append(j["id"])
    ok = (j.get("bay_width") == 1500
          and j.get("height_left") == 1800
          and j.get("height_right") == 1600
          and j.get("bay_diagonal_1") is None
          and j.get("bay_diagonal_2") is None
          and j.get("bay_height") is None)
    record("POST /mesures trapeze (no diagonals, no bay_height)", ok,
           f"bay_width={j.get('bay_width')} hL={j.get('height_left')} hR={j.get('height_right')} d1={j.get('bay_diagonal_1')}")
else:
    record("POST /mesures trapeze", False, f"HTTP {r.status_code} {r.text[:300]}")

# Invalid block_type
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json={"chantier_id": chantier_id, "block_type": "WAT", "label": "x"},
                  timeout=20)
record("Invalid block_type → 400", r.status_code == 400, f"HTTP {r.status_code}")

# Invalid wall_type
r = requests.post(f"{BASE}/mesures", headers=hdr(tokens["tech"]),
                  json={"chantier_id": chantier_id, "block_type": "standard",
                        "label": "x", "wall_type": "FOOBAR"},
                  timeout=20)
record("Invalid wall_type → 422", r.status_code == 422, f"HTTP {r.status_code}")

# GET list
r = requests.get(f"{BASE}/chantiers/{chantier_id}/mesures",
                 headers=hdr(tokens["tech"]), timeout=20)
if r.status_code == 200:
    record("GET /chantiers/{id}/mesures", len(r.json()) >= 4,
           f"count={len(r.json())}")
else:
    record("GET /chantiers/{id}/mesures", False, f"HTTP {r.status_code}")


# ===== 4. MULTI-TENANT ISOLATION =====
print("\n=== 4. MULTI-TENANT ISOLATION ===")
other_company = f"acme-{uuid.uuid4().hex[:8]}"
other_email = f"admin-{uuid.uuid4().hex[:8]}@acmecorp.fr"
r = requests.post(f"{BASE}/auth/register",
                  json={"name": "Jean Acme", "email": other_email,
                        "password": "Acme1234!", "role": "admin",
                        "company_id": other_company}, timeout=20)
if r.status_code == 200:
    other_token = r.json()["access_token"]
    other_user = r.json()["user"]
    record("register user in other company", True, f"company_id={other_user['company_id']}")

    # Create chantier as other-company admin
    r2 = requests.post(f"{BASE}/chantiers", headers=hdr(other_token),
                       json={"client_name": "Acme Client", "address": "Acme HQ"},
                       timeout=20)
    if r2.status_code == 200:
        other_chantier = r2.json()
        record("Acme chantier carries its company_id",
               other_chantier["company_id"] == other_company,
               f"company_id={other_chantier['company_id']}")
        # Admin (default company) must NOT see it
        rl = requests.get(f"{BASE}/chantiers", headers=hdr(tokens["admin"]), timeout=20)
        seen = any(c["id"] == other_chantier["id"] for c in rl.json())
        record("default admin does NOT list other-company chantiers", not seen,
               f"saw_it={seen}")
        # GET by id from default admin → 404
        rg = requests.get(f"{BASE}/chantiers/{other_chantier['id']}",
                          headers=hdr(tokens["admin"]), timeout=20)
        record("default admin GET other-company chantier → 404",
               rg.status_code == 404, f"HTTP {rg.status_code}")
    else:
        record("Acme create chantier", False, f"HTTP {r2.status_code} {r2.text[:200]}")
else:
    record("register other-company user", False, f"HTTP {r.status_code} {r.text[:200]}")

# Verify default-company chantier carries default company_id
record("commercial chantier company_id == default",
       any(c["id"] == chantier_id and c["company_id"] == "default"
           for c in requests.get(f"{BASE}/chantiers",
                                 headers=hdr(tokens["admin"])).json()),
       "")


# ===== 5. STATS COMMERCIAUX =====
print("\n=== 5. STATS COMMERCIAUX ===")
r = requests.get(f"{BASE}/stats/commercials", headers=hdr(tokens["admin"]), timeout=30)
if r.status_code == 200:
    j = r.json()
    keys_ok = all(k in j for k in ("commercials", "total_created", "total_converted", "global_conversion_rate"))
    row_keys_ok = True
    if j["commercials"]:
        row = j["commercials"][0]
        row_keys_ok = all(k in row for k in
                          ("user_id", "name", "email", "created", "converted", "conversion_rate"))
    record("GET /stats/commercials as admin", keys_ok and row_keys_ok,
           f"commercials={len(j.get('commercials', []))} total_created={j.get('total_created')}")
else:
    record("GET /stats/commercials as admin", False, f"HTTP {r.status_code}")

# Forbidden
for label in ("commercial", "tech"):
    r = requests.get(f"{BASE}/stats/commercials", headers=hdr(tokens[label]), timeout=20)
    record(f"/stats/commercials as {label} → 403", r.status_code == 403, f"HTTP {r.status_code}")

# PDF export
r = requests.get(f"{BASE}/stats/commercials/export.pdf",
                 headers=hdr(tokens["admin"]), timeout=60)
if r.status_code == 200:
    ct_ok = r.headers.get("content-type", "").startswith("application/pdf")
    magic_ok = r.content[:5] == b"%PDF-"
    record("/stats/commercials/export.pdf as admin",
           ct_ok and magic_ok and len(r.content) > 500,
           f"ct={r.headers.get('content-type')} bytes={len(r.content)} magic={r.content[:5]}")
else:
    record("/stats/commercials/export.pdf as admin", False, f"HTTP {r.status_code}")

for label in ("commercial", "tech"):
    r = requests.get(f"{BASE}/stats/commercials/export.pdf",
                     headers=hdr(tokens[label]), timeout=20)
    record(f"/stats/commercials/export.pdf as {label} → 403",
           r.status_code == 403, f"HTTP {r.status_code}")


# ===== 6. STATS COMPANY + FEEDBACKS =====
print("\n=== 6. STATS COMPANY + FEEDBACKS ===")
r = requests.get(f"{BASE}/stats/company", headers=hdr(tokens["admin"]), timeout=30)
if r.status_code == 200:
    j = r.json()
    record("/stats/company as admin", all(k in j for k in
                                          ("total_chantiers", "by_status", "closure_rate",
                                           "total_mesures", "by_technician")),
           f"total_chantiers={j.get('total_chantiers')}")
else:
    record("/stats/company as admin", False, f"HTTP {r.status_code}")

r = requests.post(f"{BASE}/feedbacks", headers=hdr(tokens["tech"]),
                  json={"page_context": "wizard", "user_comment": "Très clair !"},
                  timeout=20)
record("POST /feedbacks", r.status_code == 200, f"HTTP {r.status_code}")

r = requests.get(f"{BASE}/feedbacks", headers=hdr(tokens["admin"]), timeout=20)
record("GET /feedbacks as admin", r.status_code == 200 and isinstance(r.json(), list),
       f"HTTP {r.status_code} count={len(r.json()) if r.status_code == 200 else '-'}")


# ===== 7. EXPORTS PER CHANTIER =====
print("\n=== 7. EXPORTS PER CHANTIER ===")
r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.pdf",
                 headers=hdr(tokens["admin"]), timeout=60)
ok = r.status_code == 200 and r.content[:5] == b"%PDF-"
record("chantier export.pdf", ok,
       f"HTTP {r.status_code} bytes={len(r.content)} magic={r.content[:5]}")

r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.xlsx",
                 headers=hdr(tokens["admin"]), timeout=60)
ok = r.status_code == 200 and r.content[:2] == b"PK"
record("chantier export.xlsx", ok,
       f"HTTP {r.status_code} bytes={len(r.content)} magic={r.content[:2]}")


# ===== 8. DELETE chantier (cascade) =====
print("\n=== 8. DELETE chantier + cascade mesures ===")
r = requests.delete(f"{BASE}/chantiers/{chantier_id}",
                    headers=hdr(tokens["admin"]), timeout=20)
record("DELETE /chantiers/{id} as admin", r.status_code == 200,
       f"HTTP {r.status_code}")
# Verify mesures cascaded
r = requests.get(f"{BASE}/chantiers/{chantier_id}/mesures",
                 headers=hdr(tokens["admin"]), timeout=20)
# Should now be 404
record("Mesures cascade-deleted (chantier 404 on GET mesures)",
       r.status_code == 404, f"HTTP {r.status_code}")


# ===== SUMMARY =====
print("\n=== SUMMARY ===")
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"{passed}/{total} passed")
for n, ok, d in results:
    if not ok:
        print(f"  FAIL: {n} — {d}")
sys.exit(0 if passed == total else 1)
