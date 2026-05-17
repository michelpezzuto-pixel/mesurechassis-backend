"""Comprehensive backend regression test for MesureChâssis (RBAC + Exports)."""
from __future__ import annotations

import sys
import requests

BASE_URL = "https://window-field-app.preview.emergentagent.com/api"

ADMIN = {"email": "admin@mesurechassis.fr", "password": "admin123"}
COMMERCIAL = {"email": "commercial@mesurechassis.fr", "password": "commercial123"}
TECH = {"email": "tech@mesurechassis.fr", "password": "tech123"}

PASS: list[str] = []
FAIL: list[str] = []


def _log_pass(name: str, detail: str = "") -> None:
    PASS.append(f"{name} — {detail}" if detail else name)
    print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))


def _log_fail(name: str, detail: str) -> None:
    FAIL.append(f"{name} — {detail}")
    print(f"  FAIL  {name} — {detail}")


def login(creds: dict) -> str:
    r = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Login failed for {creds['email']}: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def expect(name: str, cond: bool, fail_detail: str = "", pass_detail: str = "") -> bool:
    if cond:
        _log_pass(name, pass_detail)
        return True
    _log_fail(name, fail_detail)
    return False


def main() -> int:
    print("=" * 80)
    print("MesureChâssis backend regression — RBAC + Exports + Latin-1 fix")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)

    print("\n[STEP 0] Login admin/commercial/technician")
    admin = login(ADMIN)
    commercial = login(COMMERCIAL)
    tech = login(TECH)
    _log_pass("Admin login")
    _log_pass("Commercial login")
    _log_pass("Technician login")

    # ---- Step 1 : Disable artisan_mode ---------------------------------
    print("\n[STEP 1] Disable artisan_mode (admin only)")
    r = requests.patch(
        f"{BASE_URL}/company/profile",
        json={"artisan_mode": False},
        headers=H(admin),
        timeout=30,
    )
    if not expect(
        "PATCH /company/profile artisan_mode=false (admin)",
        r.status_code == 200 and r.json().get("artisan_mode") is False,
        f"status={r.status_code} body={r.text[:200]}",
    ):
        return 1

    r = requests.get(f"{BASE_URL}/company/profile", headers=H(admin), timeout=30)
    expect(
        "GET /company/profile shows artisan_mode=false",
        r.status_code == 200 and r.json().get("artisan_mode") is False,
        f"status={r.status_code} body={r.text[:200]}",
    )

    # ---- Setup chantier ------------------------------------------------
    print("\n[SETUP] Create test chantier (as commercial)")
    chantier_payload = {
        "first_name": "Hélène",
        "last_name": "Régnier-Marchand",
        "address": "14 rue Saint-Honoré, 75001 Paris",
        "postal_code": "75001",
        "city": "Paris",
        "appointment_at": "2026-07-15T09:30:00Z",
        "notes": "Test régression RBAC + exports",
    }
    r = requests.post(
        f"{BASE_URL}/chantiers", json=chantier_payload, headers=H(commercial), timeout=30
    )
    if r.status_code != 200:
        _log_fail("Commercial POST /chantiers (setup)", f"{r.status_code} {r.text[:200]}")
        return 1
    chantier_id = r.json()["id"]
    _log_pass("Commercial POST /chantiers (setup)", f"id={chantier_id[:8]}")

    # ---- Step 2 : RBAC MESURES (without artisan) -----------------------
    print("\n[STEP 2] RBAC MESURES — artisan_mode=false")

    standard_mesure = {
        "chantier_id": chantier_id,
        "block_type": "standard",
        "label": "Fenêtre salon",
        "bay_width": 1500.0,
        "bay_height": 2400.0,
        "bay_diagonal_1": 2828.0,
        "bay_diagonal_2": 2828.0,
        "diag_1_verified": True,
        "diag_2_verified": True,
        "floor_reserve": 30.0,
        "bloc_thickness": 200.0,
        "wall_type": "iti",
        "insulation_thickness": 100.0,
        "finish_inner": 12.0,
        "renovation_mode": True,
        "width_top": 1502.0,
        "width_bottom": 1498.0,
        "height_left": 2402.0,
        "height_right": 2398.0,
    }

    # 2a. Admin POST → 403
    r = requests.post(
        f"{BASE_URL}/mesures", json=standard_mesure, headers=H(admin), timeout=30
    )
    expect(
        "Admin POST /mesures → 403",
        r.status_code == 403,
        f"got {r.status_code} body={r.text[:200]}",
    )

    # 2b. Commercial POST → 200
    r = requests.post(
        f"{BASE_URL}/mesures", json=standard_mesure, headers=H(commercial), timeout=30
    )
    if not expect(
        "Commercial POST /mesures → 200",
        r.status_code == 200,
        f"got {r.status_code} body={r.text[:300]}",
    ):
        return 1
    mesure_id_comm = r.json()["id"]

    # 2c. Technician POST → 200
    trapeze_mesure = {
        "chantier_id": chantier_id,
        "block_type": "trapeze",
        "label": "Fenêtre comble trapèze",
        "bay_width": 1200.0,
        "height_left": 1200.0,
        "height_right": 1600.0,
        "bloc_thickness": 200.0,
    }
    r = requests.post(
        f"{BASE_URL}/mesures", json=trapeze_mesure, headers=H(tech), timeout=30
    )
    if not expect(
        "Technician POST /mesures → 200",
        r.status_code == 200,
        f"got {r.status_code} body={r.text[:300]}",
    ):
        return 1
    mesure_id_tech = r.json()["id"]

    # 2d. Admin PATCH → 403
    r = requests.patch(
        f"{BASE_URL}/mesures/{mesure_id_comm}",
        json={**standard_mesure, "bay_height": 2410.0},
        headers=H(admin),
        timeout=30,
    )
    expect(
        "Admin PATCH /mesures/{id} → 403",
        r.status_code == 403,
        f"got {r.status_code} body={r.text[:200]}",
    )

    # 2e. Admin DELETE → 403
    r = requests.delete(
        f"{BASE_URL}/mesures/{mesure_id_tech}", headers=H(admin), timeout=30
    )
    expect(
        "Admin DELETE /mesures/{id} → 403",
        r.status_code == 403,
        f"got {r.status_code} body={r.text[:200]}",
    )

    # Add a porte mesure to enrich exports
    porte_mesure = {
        "chantier_id": chantier_id,
        "block_type": "porte",
        "label": "Porte entrée",
        "bay_width": 900.0,
        "bay_height": 2150.0,
        "bay_diagonal_1": 2330.0,
        "bay_diagonal_2": 2330.0,
        "diag_1_verified": True,
        "diag_2_verified": True,
        "floor_reserve": 35.0,
        "bloc_thickness": 200.0,
        "wall_type": "ite",
        "insulation_thickness": 140.0,
        "finish_outer": 8.0,
    }
    r = requests.post(
        f"{BASE_URL}/mesures", json=porte_mesure, headers=H(tech), timeout=30
    )
    expect(
        "Technician POST /mesures (porte) → 200",
        r.status_code == 200,
        f"got {r.status_code} body={r.text[:300]}",
    )

    # ---- Step 3 : RBAC EXPORTS (without artisan) -----------------------
    print("\n[STEP 3] RBAC EXPORTS — artisan_mode=false")

    formats = [
        ("pdf", "application/pdf"),
        ("json", "application/json"),
        ("csv", "text/csv"),
        ("xlsx",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]

    # 3a. Commercial PDF → 200
    r = requests.get(
        f"{BASE_URL}/chantiers/{chantier_id}/export.pdf",
        headers=H(commercial), timeout=60,
    )
    expect(
        "Commercial GET export.pdf → 200",
        r.status_code == 200 and r.content[:4] == b"%PDF",
        f"got {r.status_code} len={len(r.content)}",
    )

    # 3b. Commercial json/csv/xlsx → 403
    for fmt in ("json", "csv", "xlsx"):
        r = requests.get(
            f"{BASE_URL}/chantiers/{chantier_id}/export.{fmt}",
            headers=H(commercial), timeout=60,
        )
        expect(
            f"Commercial GET export.{fmt} → 403",
            r.status_code == 403,
            f"got {r.status_code} body={r.text[:200]}",
        )

    # 3c. Technician all 4 → 200
    for fmt, _ in formats:
        r = requests.get(
            f"{BASE_URL}/chantiers/{chantier_id}/export.{fmt}",
            headers=H(tech), timeout=60,
        )
        ok = r.status_code == 200
        expect(
            f"Technician GET export.{fmt} → 200",
            ok,
            f"got {r.status_code} body={r.text[:200] if not ok else ''}",
        )

    # 3d. Admin all 4 → 200
    for fmt, _ in formats:
        r = requests.get(
            f"{BASE_URL}/chantiers/{chantier_id}/export.{fmt}",
            headers=H(admin), timeout=60,
        )
        ok = r.status_code == 200
        expect(
            f"Admin GET export.{fmt} → 200",
            ok,
            f"got {r.status_code} body={r.text[:200] if not ok else ''}",
        )

    # ---- Step 4 : Content validation -----------------------------------
    print("\n[STEP 4] Content validation (admin)")

    # 4a. JSON
    r = requests.get(
        f"{BASE_URL}/chantiers/{chantier_id}/export.json",
        headers=H(admin), timeout=30,
    )
    if r.status_code == 200:
        body = r.json()
        expect(
            "JSON: schema_version present",
            "schema_version" in body,
            f"keys={list(body.keys())[:10]}",
            f"schema_version={body.get('schema_version')!r}",
        )
        openings = body.get("openings", [])
        expect(
            "JSON: openings list with >=2 items",
            isinstance(openings, list) and len(openings) >= 2,
            f"openings_count={len(openings) if isinstance(openings, list) else 'n/a'}",
            f"openings_count={len(openings)}",
        )
        has_dims = all(isinstance(o.get("dimensions_mm"), dict) for o in openings)
        expect(
            "JSON: openings[].dimensions_mm present (all)",
            has_dims,
            "at least one opening missing dimensions_mm",
            f"all {len(openings)} have dimensions_mm",
        )
        has_renov_flag = all("renovation_mode" in o for o in openings)
        expect(
            "JSON: openings[].renovation_mode flag (all)",
            has_renov_flag,
            "no opening has renovation_mode key",
        )
        has_construction = all("construction" in o for o in openings)
        expect(
            "JSON: openings[].construction present (all)",
            has_construction,
            "at least one opening missing construction",
        )
        expect(
            "JSON: site_photos array present",
            isinstance(body.get("site_photos"), list),
            f"got {type(body.get('site_photos')).__name__}",
        )
        site_photos = body.get("site_photos") or []
        if site_photos:
            has_caption = all("caption" in p for p in site_photos)
            expect(
                "JSON: site_photos[].caption present",
                has_caption,
                "some site_photo items missing caption key",
            )
        else:
            _log_pass(
                "JSON: site_photos[].caption (n/a — empty)",
                "no site photos in test chantier",
            )
        # Verify trapeze opening shape
        trap = next((o for o in openings if o.get("block_type") == "trapeze"), None)
        if trap is not None:
            expect(
                "JSON: trapeze opening shape='trapezoidal'",
                trap.get("shape") == "trapezoidal",
                f"got shape={trap.get('shape')!r}",
            )
    else:
        _log_fail("JSON content fetch", f"{r.status_code} {r.text[:200]}")

    # 4b. CSV
    r = requests.get(
        f"{BASE_URL}/chantiers/{chantier_id}/export.csv",
        headers=H(admin), timeout=30,
    )
    if r.status_code == 200:
        text = r.content.decode("utf-8-sig")
        header = text.split("\n", 1)[0]
        expect(
            "CSV: enriched column 'L. haut' present",
            "L. haut" in header,
            f"header={header[:300]}",
        )
        expect(
            "CSV: enriched column 'H. gauche' present",
            "H. gauche" in header,
            f"header={header[:300]}",
        )
        expect(
            "CSV: content-type text/csv",
            r.headers.get("content-type", "").startswith("text/csv"),
            f"ct={r.headers.get('content-type')}",
        )
    else:
        _log_fail("CSV content fetch", f"{r.status_code}")

    # 4c. XLSX
    r = requests.get(
        f"{BASE_URL}/chantiers/{chantier_id}/export.xlsx",
        headers=H(admin), timeout=30,
    )
    if r.status_code == 200:
        expect(
            "XLSX: size > 1000 bytes",
            len(r.content) > 1000,
            f"len={len(r.content)}",
            f"len={len(r.content)}",
        )
        expect(
            "XLSX: magic PK",
            r.content[:2] == b"PK",
            f"first4={r.content[:4]!r}",
        )
        expect(
            "XLSX: content-type spreadsheetml.sheet",
            "spreadsheetml.sheet" in r.headers.get("content-type", ""),
            f"ct={r.headers.get('content-type')}",
        )
    else:
        _log_fail("XLSX content fetch", f"{r.status_code}")

    # 4d. PDF
    r = requests.get(
        f"{BASE_URL}/chantiers/{chantier_id}/export.pdf",
        headers=H(admin), timeout=60,
    )
    if r.status_code == 200:
        expect(
            "PDF: size > 1500 bytes",
            len(r.content) > 1500,
            f"len={len(r.content)}",
            f"len={len(r.content)}",
        )
        expect(
            "PDF: magic %PDF",
            r.content[:4] == b"%PDF",
            f"first4={r.content[:4]!r}",
        )
    else:
        _log_fail("PDF content fetch", f"{r.status_code}")

    # ---- Step 5 : Latin-1 filename bug ---------------------------------
    print("\n[STEP 5] Latin-1 filename bug — apostrophe in client_name")
    apostrophe_payload = {
        "client_name": "M. d'Aujourd'hui",
        "address": "1 place de l'Étoile, 75008 Paris",
        "postal_code": "75008",
        "city": "Paris",
    }
    r = requests.post(
        f"{BASE_URL}/chantiers",
        json=apostrophe_payload,
        headers=H(commercial),
        timeout=30,
    )
    apos_id = None
    if r.status_code == 200:
        apos_id = r.json()["id"]
        _log_pass(
            "POST /chantiers with apostrophe client_name",
            f"id={apos_id[:8]} client_name={r.json().get('client_name')!r}",
        )
        r = requests.get(
            f"{BASE_URL}/chantiers/{apos_id}/export.pdf",
            headers=H(admin), timeout=60,
        )
        expect(
            "Export PDF (apostrophe client) → 200 (no Latin-1 crash)",
            r.status_code == 200 and r.content[:4] == b"%PDF",
            f"status={r.status_code} body={r.text[:200] if r.status_code != 200 else ''}",
        )
        r2 = requests.get(
            f"{BASE_URL}/chantiers/{apos_id}/export.csv",
            headers=H(admin), timeout=30,
        )
        expect(
            "Export CSV (apostrophe client) → 200",
            r2.status_code == 200,
            f"status={r2.status_code} body={r2.text[:200] if r2.status_code != 200 else ''}",
        )
        r3 = requests.get(
            f"{BASE_URL}/chantiers/{apos_id}/export.xlsx",
            headers=H(admin), timeout=30,
        )
        expect(
            "Export XLSX (apostrophe client) → 200",
            r3.status_code == 200,
            f"status={r3.status_code} body={r3.text[:200] if r3.status_code != 200 else ''}",
        )
    else:
        _log_fail(
            "POST /chantiers with apostrophe client_name",
            f"{r.status_code} {r.text[:200]}",
        )

    # ---- Cleanup -------------------------------------------------------
    print("\n[CLEANUP] Delete test chantiers + re-enable artisan_mode")
    if apos_id:
        r = requests.delete(
            f"{BASE_URL}/chantiers/{apos_id}", headers=H(admin), timeout=30
        )
        expect(
            "DELETE apostrophe chantier (cleanup)",
            r.status_code == 200,
            f"{r.status_code} {r.text[:200]}",
        )
    r = requests.delete(
        f"{BASE_URL}/chantiers/{chantier_id}", headers=H(admin), timeout=30
    )
    expect(
        "DELETE main test chantier (cleanup)",
        r.status_code == 200,
        f"{r.status_code} {r.text[:200]}",
    )

    r = requests.patch(
        f"{BASE_URL}/company/profile",
        json={"artisan_mode": True},
        headers=H(admin), timeout=30,
    )
    expect(
        "PATCH /company/profile artisan_mode=true (restore)",
        r.status_code == 200 and r.json().get("artisan_mode") is True,
        f"{r.status_code} {r.text[:200]}",
    )

    # ---- Summary -------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"PASS: {len(PASS)}")
    print(f"FAIL: {len(FAIL)}")
    if FAIL:
        print("\nFailed tests:")
        for f in FAIL:
            print(f"  - {f}")
    print("=" * 80)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
