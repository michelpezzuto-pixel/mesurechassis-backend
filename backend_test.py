"""Backend tests for MesureChâssis Iteration 8 — Master Workflow."""
from __future__ import annotations

import os
import sys
from typing import Any

import requests

BACKEND = os.environ.get("BACKEND_URL", "https://window-field-app.preview.emergentagent.com").rstrip("/")
API = f"{BACKEND}/api"

CREDS = {
    "admin": {"email": "admin@mesurechassis.fr", "password": "admin123"},
    "commercial": {"email": "commercial@mesurechassis.fr", "password": "commercial123"},
    "technician": {"email": "tech@mesurechassis.fr", "password": "tech123"},
}

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {name} — {detail}")


def login(role: str) -> str:
    r = requests.post(f"{API}/auth/login", json=CREDS[role], timeout=30)
    if r.status_code >= 500:
        print(f"5xx on login {role}: {r.status_code} {r.text}")
        sys.exit(1)
    if r.status_code != 200:
        raise RuntimeError(f"Login {role} failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


def auth(role: str) -> dict:
    return {"Authorization": f"Bearer {login(role)}"}


def check_5xx(r: requests.Response, where: str) -> None:
    if r.status_code >= 500:
        print(f"5xx detected at {where}: {r.status_code} {r.text[:400]}")
        sys.exit(2)


def main() -> int:
    admin_h = auth("admin")
    com_h = auth("commercial")
    tech_h = auth("technician")

    # --- Test 1: GET /company/profile for all roles ---
    for role, h in (("admin", admin_h), ("commercial", com_h), ("technician", tech_h)):
        r = requests.get(f"{API}/company/profile", headers=h, timeout=30)
        check_5xx(r, f"GET /company/profile [{role}]")
        ok = r.status_code == 200
        body = r.json() if ok else {}
        shape_ok = (
            ok
            and body.get("company_id") == "default"
            and "name" in body
            and isinstance(body.get("artisan_mode"), bool)
        )
        record(
            f"GET /company/profile as {role}",
            shape_ok,
            f"status={r.status_code} body={body}",
        )

    # --- Test 2: PATCH /company/profile (admin sets artisan=true) ---
    r = requests.patch(
        f"{API}/company/profile",
        headers=admin_h,
        json={"name": "Menuiserie Test", "artisan_mode": True},
        timeout=30,
    )
    check_5xx(r, "PATCH /company/profile admin->true")
    body = r.json() if r.status_code == 200 else {}
    record(
        "PATCH /company/profile (admin, artisan_mode=true)",
        r.status_code == 200 and body.get("artisan_mode") is True and body.get("name") == "Menuiserie Test",
        f"status={r.status_code} body={body}",
    )

    # --- Test 3: Mode Artisan Unique — RBAC bypass ---
    # Re-login to refresh artisan_mode on user dict
    admin_h = auth("admin")
    com_h = auth("commercial")
    tech_h = auth("technician")

    r = requests.get(f"{API}/chantiers", headers=admin_h, timeout=30)
    check_5xx(r, "GET /chantiers admin")
    chantiers = r.json() if r.status_code == 200 else []
    if not chantiers:
        record("Bootstrap chantiers list", False, "no chantiers available")
        return _finalize()
    sample_id = chantiers[0]["id"]

    # 3.a Commercial PATCH (already allowed normally, but verify it works)
    r = requests.patch(
        f"{API}/chantiers/{sample_id}",
        headers=com_h,
        json={"notes": "test artisan"},
        timeout=30,
    )
    check_5xx(r, "PATCH /chantiers commercial")
    record(
        "Artisan bypass: Commercial PATCH /chantiers",
        r.status_code == 200,
        f"status={r.status_code}",
    )

    # 3.b Technician POST /mesures — POST /mesures uses auth_user, no role gate.
    # The artisan bypass concept applies to require_roles deps. Test it succeeds.
    r = requests.post(
        f"{API}/mesures",
        headers=tech_h,
        json={
            "chantier_id": sample_id,
            "block_type": "standard",
            "label": "Test Artisan Tech",
            "bay_width": 1200.0,
            "bay_height": 1400.0,
            "bay_diagonal_1": 1840.0,
            "bay_diagonal_2": 1842.0,
            "bloc_thickness": 200.0,
            "wall_type": "ite",
            "diag_1_verified": True,
            "diag_2_verified": True,
        },
        timeout=30,
    )
    check_5xx(r, "POST /mesures technician (artisan)")
    record(
        "Artisan bypass: Technician POST /mesures",
        r.status_code == 200,
        f"status={r.status_code} body={r.text[:200] if r.status_code != 200 else 'ok'}",
    )

    # 3.c Technician DELETE /chantiers/{id} — uses require_roles(["admin","commercial"]);
    # under artisan_mode, bypass kicks in.
    r = requests.post(
        f"{API}/chantiers",
        headers=admin_h,
        json={"first_name": "Throwaway", "last_name": "Tech", "address": "1 rue Test"},
        timeout=30,
    )
    check_5xx(r, "POST throwaway chantier admin")
    throwaway_id = r.json().get("id") if r.status_code == 200 else None
    if not throwaway_id:
        record("Bootstrap throwaway chantier", False, f"status={r.status_code}")
    else:
        r = requests.delete(f"{API}/chantiers/{throwaway_id}", headers=tech_h, timeout=30)
        check_5xx(r, "DELETE /chantiers technician (artisan)")
        record(
            "Artisan bypass: Technician DELETE /chantiers",
            r.status_code == 200,
            f"status={r.status_code}",
        )

    # --- Test 4: RESET artisan_mode=false ---
    r = requests.patch(
        f"{API}/company/profile",
        headers=admin_h,
        json={"artisan_mode": False},
        timeout=30,
    )
    check_5xx(r, "RESET artisan_mode false")
    body = r.json() if r.status_code == 200 else {}
    record(
        "RESET PATCH /company/profile (artisan_mode=false)",
        r.status_code == 200 and body.get("artisan_mode") is False,
        f"status={r.status_code} body={body}",
    )

    # Re-login to refresh artisan_mode flag
    tech_h = auth("technician")
    com_h = auth("commercial")
    admin_h = auth("admin")

    # 4.a Commercial PATCH /company/profile → 403 (now that artisan is off)
    r = requests.patch(f"{API}/company/profile", headers=com_h, json={"artisan_mode": False}, timeout=30)
    check_5xx(r, "PATCH /company/profile commercial post-reset")
    record(
        "PATCH /company/profile commercial → 403 (post-reset)",
        r.status_code == 403,
        f"status={r.status_code}",
    )

    # 4.b Technician PATCH /company/profile → 403
    r = requests.patch(f"{API}/company/profile", headers=tech_h, json={"artisan_mode": False}, timeout=30)
    check_5xx(r, "PATCH /company/profile technician post-reset")
    record(
        "PATCH /company/profile technician → 403 (post-reset)",
        r.status_code == 403,
        f"status={r.status_code}",
    )

    # 4.c Technician POST /mesures post-reset:
    # NOTE: implementation uses Depends(auth_user) on POST /mesures (NOT require_roles),
    # so technician can still POST. The review request expects 403; report mismatch.
    r = requests.post(
        f"{API}/mesures",
        headers=tech_h,
        json={
            "chantier_id": sample_id,
            "block_type": "standard",
            "label": "PostReset",
            "bay_width": 1000.0,
            "bay_height": 1200.0,
            "bay_diagonal_1": 1562.0,
            "bay_diagonal_2": 1563.0,
            "bloc_thickness": 200.0,
            "wall_type": "ite",
        },
        timeout=30,
    )
    check_5xx(r, "POST /mesures technician post-reset")
    expected_403 = (r.status_code == 403)
    record(
        "Technician POST /mesures post-reset → expected 403",
        expected_403,
        f"status={r.status_code} (impl uses auth_user — no role gate on POST /mesures)",
    )

    # --- Test 5: Structured client fields ---
    r = requests.post(
        f"{API}/chantiers",
        headers=admin_h,
        json={
            "first_name": "Marie",
            "last_name": "Dupont",
            "address": "15 Rue X",
            "postal_code": "75011",
            "city": "Paris",
            "appointment_at": "2026-06-20T10:00:00Z",
            "notes": "Test",
        },
        timeout=30,
    )
    check_5xx(r, "POST /chantiers structured client")
    body = r.json() if r.status_code == 200 else {}
    test_chantier_id = body.get("id")
    structured_ok = (
        r.status_code == 200
        and body.get("client_name") == "Dupont Marie"
        and body.get("first_name") == "Marie"
        and body.get("last_name") == "Dupont"
        and body.get("postal_code") == "75011"
        and body.get("city") == "Paris"
    )
    record(
        "POST /chantiers structured (no client_name) auto-composes 'Dupont Marie'",
        structured_ok,
        f"status={r.status_code} client_name={body.get('client_name')!r} pc={body.get('postal_code')} city={body.get('city')}",
    )

    r = requests.get(f"{API}/chantiers", headers=admin_h, timeout=30)
    check_5xx(r, "GET /chantiers")
    chantiers = r.json() if r.status_code == 200 else []
    found = next((c for c in chantiers if c.get("id") == test_chantier_id), None)
    record(
        "GET /chantiers includes structured fields for new chantier",
        bool(found and found.get("first_name") == "Marie"
             and found.get("postal_code") == "75011"
             and found.get("city") == "Paris"),
        f"found={bool(found)} fn={(found or {}).get('first_name')}",
    )

    # --- Test 6: Export JSON mc.v1 ---
    mesures_payloads = [
        {
            "chantier_id": test_chantier_id,
            "block_type": "standard",
            "label": "Fenêtre salon",
            "bay_width": 1200.0,
            "bay_height": 1400.0,
            "bay_diagonal_1": 1840.0,
            "bay_diagonal_2": 1842.0,
            "diag_1_verified": True,
            "diag_2_verified": True,
            "bloc_thickness": 200.0,
            "wall_type": "ite",
        },
        {
            "chantier_id": test_chantier_id,
            "block_type": "trapeze",
            "label": "Lucarne",
            "bay_width": 1000.0,
            "height_left": 900.0,
            "height_right": 1200.0,
            "bloc_thickness": 200.0,
            "wall_type": "iti",
        },
        {
            "chantier_id": test_chantier_id,
            "block_type": "porte",
            "label": "Porte entrée",
            "bay_width": 900.0,
            "bay_height": 2100.0,
            "bay_diagonal_1": 2284.0,
            "bay_diagonal_2": 2285.0,
            "diag_1_verified": True,
            "diag_2_verified": True,
            "floor_reserve": 20.0,
            "bloc_thickness": 200.0,
            "wall_type": "ite",
        },
    ]
    for p in mesures_payloads:
        r = requests.post(f"{API}/mesures", headers=admin_h, json=p, timeout=30)
        check_5xx(r, f"POST /mesures {p['block_type']}")
        record(
            f"POST /mesures {p['block_type']}",
            r.status_code == 200,
            f"status={r.status_code} {'' if r.status_code == 200 else r.text[:200]}",
        )

    r = requests.get(f"{API}/chantiers/{test_chantier_id}/export.json", headers=admin_h, timeout=30)
    check_5xx(r, "GET export.json")
    if r.status_code != 200:
        record("GET export.json", False, f"status={r.status_code} body={r.text[:300]}")
        return _finalize()
    exp = r.json()

    top_ok = (
        exp.get("schema_version") == "mc.v1"
        and "exported_at" in exp
        and exp.get("company_id") == "default"
        and "client" in exp
        and "project" in exp
        and isinstance(exp.get("openings_count"), int)
        and isinstance(exp.get("openings"), list)
    )
    record(
        "Export top-level (schema_version=mc.v1, exported_at, company_id, client, project, openings_count, openings)",
        top_ok,
        f"keys={list(exp.keys())} schema={exp.get('schema_version')}",
    )

    cli = exp.get("client", {})
    cli_ok = all(k in cli for k in ("display_name", "first_name", "last_name", "address", "postal_code", "city"))
    cli_values_ok = (
        cli.get("display_name") == "Dupont Marie"
        and cli.get("first_name") == "Marie"
        and cli.get("last_name") == "Dupont"
        and cli.get("address") == "15 Rue X"
        and cli.get("postal_code") == "75011"
        and cli.get("city") == "Paris"
    )
    record(
        "Export client object keys + values",
        cli_ok and cli_values_ok,
        f"cli={cli}",
    )

    prj = exp.get("project", {})
    prj_ok = all(k in prj for k in ("id", "status", "appointment_at", "notes", "created_at", "assigned_to"))
    record(
        "Export project has id/status/appointment_at/notes/created_at/assigned_to",
        prj_ok,
        f"prj keys={list(prj.keys())} appt={prj.get('appointment_at')}",
    )

    openings = exp.get("openings", [])
    record(
        "Export openings_count matches number of mesures",
        exp.get("openings_count") == len(openings) == 3,
        f"openings_count={exp.get('openings_count')} len(openings)={len(openings)}",
    )

    by_type: dict[str, Any] = {o.get("block_type"): o for o in openings}
    std = by_type.get("standard")
    trap = by_type.get("trapeze")
    porte = by_type.get("porte")

    record(
        "Standard opening shape == 'rectangular'",
        bool(std and std.get("shape") == "rectangular"),
        f"shape={(std or {}).get('shape')}",
    )
    record(
        "Trapeze opening shape == 'trapezoidal'",
        bool(trap and trap.get("shape") == "trapezoidal"),
        f"shape={(trap or {}).get('shape')}",
    )
    record(
        "Porte opening shape == 'rectangular'",
        bool(porte and porte.get("shape") == "rectangular"),
        f"shape={(porte or {}).get('shape')}",
    )

    if trap:
        td = trap.get("dimensions_mm", {})
        keys = set(td.keys())
        record(
            "Trapezoidal dimensions_mm has ONLY {width, height_left, height_right}",
            keys == {"width", "height_left", "height_right"},
            f"trap.dimensions_mm keys={keys}",
        )

    if std:
        sd = std.get("dimensions_mm", {})
        record(
            "Standard dimensions_mm has width/height/diagonal_1/diagonal_2",
            all(k in sd for k in ("width", "height", "diagonal_1", "diagonal_2")),
            f"std.dimensions_mm={sd}",
        )
        dv = std.get("diagonals_verified", {})
        record(
            "Standard has diagonals_verified {d1:bool, d2:bool}",
            isinstance(dv.get("d1"), bool) and isinstance(dv.get("d2"), bool),
            f"diagonals_verified={dv}",
        )

    if porte:
        pd = porte.get("dimensions_mm", {})
        record(
            "Porte dimensions_mm includes floor_reserve",
            "floor_reserve" in pd and pd.get("floor_reserve") == 20.0,
            f"porte.dimensions_mm={pd}",
        )
        dv = porte.get("diagonals_verified", {})
        record(
            "Porte has diagonals_verified",
            isinstance(dv.get("d1"), bool) and isinstance(dv.get("d2"), bool),
            f"diagonals_verified={dv}",
        )

    # --- Test 7: Cleanup ---
    r = requests.delete(f"{API}/chantiers/{test_chantier_id}", headers=admin_h, timeout=30)
    check_5xx(r, "DELETE test chantier")
    record(
        "DELETE test chantier as admin",
        r.status_code == 200,
        f"status={r.status_code}",
    )

    r = requests.get(f"{API}/company/profile", headers=admin_h, timeout=30)
    check_5xx(r, "GET /company/profile final")
    body = r.json() if r.status_code == 200 else {}
    record(
        "Final: artisan_mode is false",
        r.status_code == 200 and body.get("artisan_mode") is False,
        f"body={body}",
    )

    return _finalize()


def _finalize() -> int:
    print("\n=== SUMMARY ===")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(n, d) for n, ok, d in results if not ok]
    print(f"{passed}/{len(results)} passed")
    if failed:
        print("\nFailed:")
        for n, d in failed:
            print(f"  - {n}: {d}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
