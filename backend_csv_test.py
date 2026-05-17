"""
Targeted backend test — CSV export endpoint + regression on other exports.
Base URL: REACT_APP_BACKEND_URL/api (external) — fallback to localhost:8001/api.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone

BASE = "https://window-field-app.preview.emergentagent.com/api"

CREDS = {
    "admin": ("admin@mesurechassis.fr", "admin123"),
    "commercial": ("commercial@mesurechassis.fr", "commercial123"),
    "tech": ("tech@mesurechassis.fr", "tech123"),
}

results = []


def log(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    line = f"[{tag}] {name} — {detail}"
    print(line)
    results.append((name, ok, detail))


def login(role):
    email, pwd = CREDS[role]
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"login {role} failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    print(f"BASE = {BASE}")
    admin_t = login("admin")
    com_t = login("commercial")
    tech_t = login("tech")
    log("login admin/commercial/tech", True, "tokens acquired")

    # Create a fresh chantier with 3 mesures: standard, trapeze, porte
    payload = {
        "first_name": "Élise",
        "last_name": "Lefebvre",
        "address": "12 rue des Tilleuls",
        "postal_code": "69003",
        "city": "Lyon",
        "appointment_at": "2026-07-15T09:30:00Z",
        "notes": "Test CSV export — 3 mesures",
    }
    r = requests.post(f"{BASE}/chantiers", json=payload, headers=auth(admin_t), timeout=15)
    if r.status_code != 200:
        log("POST /chantiers", False, f"{r.status_code} {r.text}")
        sys.exit(1)
    chantier = r.json()
    cid = chantier["id"]
    log("POST /chantiers (admin)", True, f"id={cid} client={chantier.get('client_name')}")

    # Mesure 1 — standard rectangular
    m1 = {
        "chantier_id": cid,
        "label": "Salon",
        "block_type": "standard",
        "wall_type": "ite",
        "bloc_thickness": 200,
        "bay_width": 1200,
        "bay_height": 1500,
        "bay_diagonal_1": 1921,
        "bay_diagonal_2": 1921,
        "diag_1_verified": True,
        "diag_2_verified": True,
    }
    # Mesure 2 — trapeze
    m2 = {
        "chantier_id": cid,
        "label": "Comble",
        "block_type": "trapeze",
        "wall_type": "iti",
        "bloc_thickness": 200,
        "bay_width": 1000,
        "height_left": 1200,
        "height_right": 1600,
    }
    # Mesure 3 — porte
    m3 = {
        "chantier_id": cid,
        "label": "Porte entrée",
        "block_type": "porte",
        "wall_type": "brique_parement",
        "bloc_thickness": 200,
        "bay_width": 900,
        "bay_height": 2100,
        "bay_diagonal_1": 2285,
        "bay_diagonal_2": 2285,
        "diag_1_verified": True,
        "diag_2_verified": False,
        "floor_reserve": 35,
    }
    for i, m in enumerate([m1, m2, m3], 1):
        r = requests.post(f"{BASE}/mesures", json=m, headers=auth(admin_t), timeout=15)
        if r.status_code != 200:
            log(f"POST /mesures #{i}", False, f"{r.status_code} {r.text}")
            sys.exit(1)
    log("POST /mesures x3 (standard, trapeze, porte)", True, "created")

    # --- SCENARIO 1: GET CSV as admin ---
    r = requests.get(f"{BASE}/chantiers/{cid}/export.csv", headers=auth(admin_t), timeout=15)
    if r.status_code != 200:
        log("CSV admin 200", False, f"{r.status_code} {r.text[:200]}")
        sys.exit(1)
    ct = r.headers.get("content-type", "")
    log("CSV admin 200 + content-type", ct.startswith("text/csv"), f"status=200 ct='{ct}'")

    raw = r.content
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    log("CSV starts with UTF-8 BOM", has_bom, f"first4={raw[:4]!r}")

    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    header = lines[0] if lines else ""
    expected_substr = "Chantier;Adresse;Code Postal;Ville;Statut;Label;Type;Forme"
    log("CSV header contains expected columns", expected_substr in header,
        f"header[:80]='{header[:80]}'")

    data_rows = [ln for ln in lines[1:] if ln.strip()]
    log("CSV has at least one data row", len(data_rows) >= 1, f"rows={len(data_rows)}")
    log("CSV has 3 data rows (1 per mesure)", len(data_rows) == 3, f"rows={len(data_rows)}")

    # Parse rows
    import csv as csvmod
    import io
    reader = csvmod.reader(io.StringIO(text), delimiter=";")
    rows = list(reader)
    hdr = rows[0]

    def col(name):
        return hdr.index(name)

    rect_row = None
    trap_row = None
    porte_row = None
    for row in rows[1:]:
        label = row[col("Label")]
        bt = row[col("Type")]
        if bt == "trapeze":
            trap_row = row
        elif bt == "porte":
            porte_row = row
        elif bt == "standard":
            rect_row = row

    # --- Trapeze checks ---
    if trap_row is None:
        log("CSV trapeze row present", False, "not found")
    else:
        forme = trap_row[col("Forme")]
        hg = trap_row[col("Hauteur G (mm)")]
        hd = trap_row[col("Hauteur D (mm)")]
        h = trap_row[col("Hauteur (mm)")]
        d1 = trap_row[col("Diag 1 (mm)")]
        d2 = trap_row[col("Diag 2 (mm)")]
        log("CSV trapeze Forme=trapezoidal", forme == "trapezoidal", f"forme='{forme}'")
        log("CSV trapeze Hauteur G/D filled", bool(hg) and bool(hd), f"hg='{hg}' hd='{hd}'")
        log("CSV trapeze Hauteur/Diag1/Diag2 empty", h == "" and d1 == "" and d2 == "",
            f"h='{h}' d1='{d1}' d2='{d2}'")

    # --- Standard checks ---
    if rect_row is None:
        log("CSV standard row present", False, "not found")
    else:
        forme = rect_row[col("Forme")]
        h = rect_row[col("Hauteur (mm)")]
        d1 = rect_row[col("Diag 1 (mm)")]
        d2 = rect_row[col("Diag 2 (mm)")]
        d1ok = rect_row[col("Diag1 OK")]
        log("CSV standard Forme=rectangular", forme == "rectangular", f"forme='{forme}'")
        log("CSV standard Hauteur populated", h != "", f"h='{h}'")
        log("CSV standard Diag1/Diag2 populated", d1 != "" and d2 != "", f"d1='{d1}' d2='{d2}'")
        log("CSV standard Diag1 OK in {oui,non}", d1ok in ("oui", "non"), f"d1ok='{d1ok}'")

    # --- Porte checks ---
    if porte_row is None:
        log("CSV porte row present", False, "not found")
    else:
        forme = porte_row[col("Forme")]
        reserve = porte_row[col("Réserve sol (mm)")]
        log("CSV porte Forme=rectangular", forme == "rectangular", f"forme='{forme}'")
        log("CSV porte Réserve sol populated", reserve != "", f"reserve='{reserve}'")

    # --- SCENARIO 2: CSV as commercial ---
    r = requests.get(f"{BASE}/chantiers/{cid}/export.csv", headers=auth(com_t), timeout=15)
    log("CSV commercial 200", r.status_code == 200, f"status={r.status_code}")

    # --- SCENARIO 3: CSV as technician ---
    r = requests.get(f"{BASE}/chantiers/{cid}/export.csv", headers=auth(tech_t), timeout=15)
    log("CSV technician 200", r.status_code == 200, f"status={r.status_code}")

    # --- SCENARIO 4: CSV without token → 401 ---
    r = requests.get(f"{BASE}/chantiers/{cid}/export.csv", timeout=15)
    log("CSV no-auth → 401/403", r.status_code in (401, 403), f"status={r.status_code}")

    # --- SCENARIO 5: bad uuid → 404 ---
    r = requests.get(f"{BASE}/chantiers/nonexistent-uuid-abc123/export.csv",
                     headers=auth(admin_t), timeout=15)
    log("CSV bad uuid → 404", r.status_code == 404, f"status={r.status_code}")

    # --- SCENARIO 6: Regression on PDF / XLSX / JSON ---
    r = requests.get(f"{BASE}/chantiers/{cid}/export.pdf", headers=auth(admin_t), timeout=20)
    pdf_ok = r.status_code == 200 and r.content[:5] == b"%PDF-"
    log("PDF export 200 + %PDF- magic", pdf_ok, f"status={r.status_code} head={r.content[:5]!r}")

    r = requests.get(f"{BASE}/chantiers/{cid}/export.xlsx", headers=auth(admin_t), timeout=20)
    xlsx_ok = r.status_code == 200 and r.content[:2] == b"PK"
    log("XLSX export 200 + PK magic", xlsx_ok, f"status={r.status_code} head={r.content[:2]!r}")

    r = requests.get(f"{BASE}/chantiers/{cid}/export.json", headers=auth(admin_t), timeout=15)
    json_ok = r.status_code == 200
    sv = ""
    if json_ok:
        try:
            sv = r.json().get("schema_version", "")
        except Exception as e:
            json_ok = False
            sv = f"parse error: {e}"
    log("JSON export 200 + schema_version=mc.v1", json_ok and sv == "mc.v1",
        f"status={r.status_code} schema_version='{sv}'")

    # Cleanup: delete the test chantier
    r = requests.delete(f"{BASE}/chantiers/{cid}", headers=auth(admin_t), timeout=15)
    log("Cleanup DELETE chantier", r.status_code in (200, 204), f"status={r.status_code}")

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 60)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 60)
    failed = [(n, d) for n, ok, d in results if not ok]
    if failed:
        print("FAILED:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
