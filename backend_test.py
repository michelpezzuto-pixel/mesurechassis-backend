"""Backend tests — Export V2 PDF/DXF enrichment (May 2025).

Validates per-stair PDF sections, multi-stair DXF layers (STAIR_<NAME>_DROIT/PALIER/QUART_*),
multi-stair export, legacy non-regression, paywall.
"""
from __future__ import annotations

import os
import sys
import requests

BASE = os.environ.get("BACKEND_URL", "https://stair-pro.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

MARC = ("marc@mesureescalier.com", "Demo1234!")
ADMIN = ("admin@demo.fr", "Demo1234!")
EXPIRED = ("expired@demo.fr", "Demo1234!")

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, msg: str = ""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {msg}")
    RESULTS.append((name, ok, msg))


def login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {email} failed {r.status_code} {r.text}"
    data = r.json()
    return data.get("access_token") or data["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------- Tests ----------------

def test_smoke_pdf_v2(token: str, pid: str, sid_main: str):
    """Step 1: Export PDF for v2 project. Verify size > 5000, %PDF-1.4 header."""
    r = requests.get(f"{API}/projects/{pid}/export/pdf", headers=auth(token), timeout=60)
    if r.status_code != 200:
        record("PDF V2 export — HTTP 200", False, f"status={r.status_code} body={r.text[:200]}")
        return None
    record("PDF V2 export — HTTP 200", True, "status=200")

    ct = r.headers.get("Content-Type", "")
    record("PDF V2 — Content-Type", ct.startswith("application/pdf"), f"got {ct}")

    body = r.content
    record("PDF V2 — header %PDF-1.4", body.startswith(b"%PDF-1.4"), f"first 10 bytes: {body[:10]!r}")
    size_ok = len(body) > 5000
    record("PDF V2 — taille > 5000 bytes", size_ok, f"size={len(body)} bytes")
    return len(body)


def test_smoke_dxf_v2(token: str, pid: str):
    """Step 2: Export DXF for v2 project. Verify layers STAIR_CAVE-TO-RDC_*, LIMON."""
    r = requests.get(f"{API}/projects/{pid}/export/dxf", headers=auth(token), timeout=60)
    if r.status_code != 200:
        record("DXF V2 export — HTTP 200", False, f"status={r.status_code} body={r.text[:200]}")
        return None
    record("DXF V2 export — HTTP 200", True, "status=200")

    ct = r.headers.get("Content-Type", "")
    record("DXF V2 — Content-Type", ct.startswith("application/dxf"), f"got {ct}")

    text = r.text
    record("DXF V2 — contient SECTION", "SECTION" in text)
    record("DXF V2 — contient ENDSEC", "ENDSEC" in text)

    has_droit = "STAIR_CAVE-TO-RDC_DROIT" in text
    has_palier = "STAIR_CAVE-TO-RDC_PALIER" in text
    has_quart = "STAIR_CAVE-TO-RDC_QUART_HAUT" in text
    has_any = has_droit or has_palier or has_quart
    record("DXF V2 — layer STAIR_CAVE-TO-RDC_(DROIT|PALIER|QUART_HAUT)", has_any,
           f"droit={has_droit} palier={has_palier} quart_haut={has_quart}")

    record("DXF V2 — calque LIMON présent", "LIMON" in text, "limon trace required")
    return len(text)


def test_multi_stair_export(token: str, pid: str, base_pdf_size: int):
    """Step 3: Add Mezzanine stair, ensure PDF grew & DXF has both stair prefixes."""
    r = requests.post(f"{API}/projects/{pid}/stairs",
                      headers=auth(token), json={"name": "Mezzanine"}, timeout=30)
    if r.status_code != 200:
        record("Multi-stair — create Mezzanine", False, f"{r.status_code} {r.text[:200]}")
        return
    sid_mezz = r.json()["id"]
    record("Multi-stair — create Mezzanine", True, f"sid={sid_mezz}")

    r = requests.post(f"{API}/projects/{pid}/stairs/{sid_mezz}/niveaux",
                      headers=auth(token),
                      json={"label": "Mezz", "hauteur_mm": 1800, "sol_fini": True, "reserve_mm": 0},
                      timeout=30)
    if r.status_code != 200:
        record("Multi-stair — niveau Mezzanine", False, f"{r.status_code} {r.text[:200]}")
        return
    nid_mezz = r.json()["id"]
    record("Multi-stair — niveau Mezzanine", True, "")

    r = requests.post(f"{API}/projects/{pid}/stairs/{sid_mezz}/niveaux/{nid_mezz}/troncons",
                      headers=auth(token),
                      json={"type": "droit", "longueur_mm": 2500, "largeur_mm": 800},
                      timeout=30)
    record("Multi-stair — tronçon droit Mezzanine", r.status_code == 200, f"{r.status_code}")

    r = requests.get(f"{API}/projects/{pid}/export/pdf", headers=auth(token), timeout=60)
    if r.status_code != 200:
        record("Multi-stair PDF — HTTP 200", False, f"{r.status_code}")
    else:
        new_size = len(r.content)
        bigger = new_size > base_pdf_size
        record("Multi-stair PDF — taille augmentée", bigger,
               f"before={base_pdf_size}, after={new_size}")

    r = requests.get(f"{API}/projects/{pid}/export/dxf", headers=auth(token), timeout=60)
    if r.status_code != 200:
        record("Multi-stair DXF — HTTP 200", False, f"{r.status_code}")
        return
    text = r.text
    has_cave = "STAIR_CAVE-TO-RDC_" in text
    has_mezz = "STAIR_MEZZANINE_" in text
    record("Multi-stair DXF — deux préfixes de calques distincts",
           has_cave and has_mezz, f"cave-to-rdc={has_cave} mezzanine={has_mezz}")


def test_legacy_non_regression(admin_token: str):
    """Step 4: legacy project (migrated) → PDF works, contains both legacy + v2 sections."""
    r = requests.get(f"{API}/projects", headers=auth(admin_token), timeout=30)
    if r.status_code != 200:
        record("Legacy — list projects (admin)", False, f"{r.status_code}")
        return
    projects = r.json()
    if not projects:
        record("Legacy — list projects (admin)", False, "no projects")
        return
    record("Legacy — list projects (admin)", True, f"{len(projects)} projects")

    target = None
    for p in projects:
        full = requests.get(f"{API}/projects/{p['id']}", headers=auth(admin_token), timeout=30)
        if full.status_code != 200:
            continue
        pdoc = full.json()
        if pdoc.get("measurement") and pdoc.get("stairs"):
            target = pdoc
            break
    if not target:
        record("Legacy — projet migré avec measurement + stairs[]", False,
               "no project with both legacy measurement & v2 stairs[] found")
        return
    record("Legacy — projet migré avec measurement + stairs[]", True,
           f"pid={target['id']} client={target.get('client_nom')}")

    r = requests.get(f"{API}/projects/{target['id']}/export/pdf",
                     headers=auth(admin_token), timeout=60)
    if r.status_code != 200:
        record("Legacy — GET /export/pdf 200", False, f"{r.status_code} {r.text[:200]}")
        return
    record("Legacy — GET /export/pdf 200", True, "")
    body = r.content
    record("Legacy — header %PDF-", body.startswith(b"%PDF-"), f"first 10: {body[:10]!r}")
    record("Legacy — PDF taille raisonnable (legacy+v2)", len(body) > 4000, f"size={len(body)}")


def test_paywall(pid: str):
    """Step 5a: expired user → /export/pdf returns 402."""
    try:
        token = login(*EXPIRED)
    except AssertionError as e:
        record("Paywall — login expired", False, str(e))
        return
    record("Paywall — login expired", True, "")

    r = requests.get(f"{API}/projects/{pid}/export/pdf", headers=auth(token), timeout=30)
    record("Paywall — expired GET /export/pdf renvoie 402", r.status_code == 402,
           f"status={r.status_code}")


def test_compute_blondel(token: str, pid: str, sid: str):
    """Step 5b: /compute returns coherent values."""
    r = requests.get(f"{API}/projects/{pid}/stairs/{sid}/compute",
                     headers=auth(token), timeout=30)
    if r.status_code != 200:
        record("Compute — GET /compute 200", False, f"{r.status_code} {r.text[:200]}")
        return
    record("Compute — GET /compute 200", True, "")
    data = r.json()
    total_steps = data.get("total_steps", 0)
    record("Compute — total_steps cohérent (>0)", total_steps > 0,
           f"total_steps={total_steps}")
    niv0 = (data.get("niveaux_calc") or [{}])[0]
    h = niv0.get("h", 0)
    bl = niv0.get("blondel_value", 0)
    valid = niv0.get("valid_blondel", False)
    record("Compute — h ~180 RDC", 160 <= h <= 200, f"h={h}")
    record("Compute — blondel 560-670 valid", valid and 560 <= bl <= 670,
           f"blondel={bl} valid={valid}")


# ---------------- Orchestration ----------------

def main():
    print(f"\n=== Backend Export V2 Tests against {API} ===\n")

    try:
        marc_token = login(*MARC)
        record("Auth — marc@mesureescalier.com", True, "")
    except Exception as e:
        record("Auth — marc@mesureescalier.com", False, str(e))
        return summarize()

    proj_payload = {
        "client_nom": "Lemoine",
        "client_prenom": "Théo",
        "address": "12 rue des Limons",
        "postal_code": "69000",
        "city": "Lyon",
        "phone": "0612345678",
        "notes": "Projet test export V2",
    }
    r = requests.post(f"{API}/projects", headers=auth(marc_token), json=proj_payload, timeout=30)
    if r.status_code != 200:
        record("Setup — POST /projects", False, f"{r.status_code} {r.text[:200]}")
        return summarize()
    pid = r.json()["id"]
    record("Setup — POST /projects", True, f"pid={pid}")

    r = requests.post(f"{API}/projects/{pid}/stairs",
                      headers=auth(marc_token), json={"name": "Cave-to-RDC"}, timeout=30)
    if r.status_code != 200:
        record("Setup — POST /stairs Cave-to-RDC", False, f"{r.status_code} {r.text[:200]}")
        return summarize()
    sid = r.json()["id"]
    record("Setup — POST /stairs Cave-to-RDC", True, f"sid={sid}")

    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux",
                      headers=auth(marc_token),
                      json={"label": "RDC", "hauteur_mm": 2700, "sol_fini": True, "reserve_mm": 0},
                      timeout=30)
    if r.status_code != 200:
        record("Setup — niveau RDC", False, f"{r.status_code} {r.text[:200]}")
        return summarize()
    nid_rdc = r.json()["id"]
    record("Setup — niveau RDC", True, "")

    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux",
                      headers=auth(marc_token),
                      json={"label": "R+1", "hauteur_mm": 2500, "sol_fini": False, "reserve_mm": 50},
                      timeout=30)
    if r.status_code != 200:
        record("Setup — niveau R+1", False, f"{r.status_code} {r.text[:200]}")
        return summarize()
    nid_r1 = r.json()["id"]
    record("Setup — niveau R+1", True, "")

    for ttype, longueur in [("droit", 2000), ("palier", 1000), ("quart_haut", 1500)]:
        r = requests.post(
            f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_rdc}/troncons",
            headers=auth(marc_token),
            json={"type": ttype, "longueur_mm": longueur, "largeur_mm": 900},
            timeout=30,
        )
        record(f"Setup — RDC tronçon {ttype} L={longueur}", r.status_code == 200,
               f"{r.status_code} {r.text[:100] if r.status_code!=200 else ''}")

    r = requests.post(
        f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_r1}/troncons",
        headers=auth(marc_token),
        json={"type": "droit", "longueur_mm": 3500, "largeur_mm": 900},
        timeout=30,
    )
    record("Setup — R+1 tronçon droit L=3500", r.status_code == 200,
           f"{r.status_code} {r.text[:100] if r.status_code!=200 else ''}")

    pdf_size = test_smoke_pdf_v2(marc_token, pid, sid) or 0
    test_smoke_dxf_v2(marc_token, pid)
    test_multi_stair_export(marc_token, pid, pdf_size)

    try:
        admin_token = login(*ADMIN)
        record("Auth — admin@demo.fr", True, "")
        test_legacy_non_regression(admin_token)
    except Exception as e:
        record("Auth — admin@demo.fr", False, str(e))

    test_paywall(pid)
    test_compute_blondel(marc_token, pid, sid)

    return summarize()


def summarize():
    print("\n=== SUMMARY ===")
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"Total: {len(RESULTS)} | Passed: {passed} | Failed: {failed}")
    if failed:
        print("\nFailed tests:")
        for name, ok, msg in RESULTS:
            if not ok:
                print(f"  - {name}: {msg}")
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
