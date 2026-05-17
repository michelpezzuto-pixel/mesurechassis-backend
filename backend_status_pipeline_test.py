"""Test the 3-stage status pipeline transitions on /api/chantiers.

Goals:
1. Login admin
2. GET /chantiers -> diversified statuses, expect 8 chantiers
3. PATCH a non-cloture chantier through en_fabrication -> cloture
4. status_filter=cloture returns the now-closed chantier
5. invalid status -> 400
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import requests

BASE = "https://window-field-app.preview.emergentagent.com/api"
ADMIN = {"email": "admin@mesurechassis.fr", "password": "admin123"}

results = []


def log(ok: bool, name: str, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" :: {detail}" if detail else ""))
    results.append((ok, name, detail))


def main() -> int:
    s = requests.Session()
    # 1. Login
    r = s.post(f"{BASE}/auth/login", json=ADMIN, timeout=15)
    if r.status_code != 200:
        log(False, "admin login", f"status={r.status_code} body={r.text[:200]}")
        return 1
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    log(True, "admin login", f"role={r.json()['user']['role']}")

    # 2. GET chantiers
    r = s.get(f"{BASE}/chantiers", timeout=15)
    if r.status_code != 200:
        log(False, "GET /chantiers", f"status={r.status_code} body={r.text[:200]}")
        return 1
    chantiers = r.json()
    count = len(chantiers)
    breakdown = Counter(c["status"] for c in chantiers)
    print(f"[INFO] Total chantiers: {count}")
    print(f"[INFO] Status breakdown: {dict(breakdown)}")
    log(count == 8, f"GET /chantiers count==8 (got {count})")

    # Check diversified statuses
    expected_statuses = {"devis_a_faire", "technique_a_valider", "en_commande",
                         "en_fabrication", "cloture"}
    present = set(breakdown.keys())
    missing = expected_statuses - present
    log(not missing, "diversified statuses present",
        f"present={sorted(present)} missing={sorted(missing)}")

    # 3. Pick non-cloture chantier
    candidates = [c for c in chantiers if c["status"] != "cloture"]
    if not candidates:
        log(False, "find non-cloture chantier", "none found")
        return 1
    target = candidates[0]
    cid = target["id"]
    print(f"[INFO] target chantier id={cid} client={target.get('client_name')} "
          f"status={target['status']}")

    # PATCH -> en_fabrication
    r = s.patch(f"{BASE}/chantiers/{cid}", json={"status": "en_fabrication"}, timeout=15)
    ok = r.status_code == 200 and r.json().get("status") == "en_fabrication"
    log(ok, "PATCH -> en_fabrication",
        f"status_code={r.status_code} resp_status={r.json().get('status') if r.ok else r.text[:200]}")

    # PATCH -> cloture
    r = s.patch(f"{BASE}/chantiers/{cid}", json={"status": "cloture"}, timeout=15)
    ok = r.status_code == 200 and r.json().get("status") == "cloture"
    log(ok, "PATCH -> cloture",
        f"status_code={r.status_code} resp_status={r.json().get('status') if r.ok else r.text[:200]}")

    # 4. Filter by status_filter=cloture
    r = s.get(f"{BASE}/chantiers", params={"status_filter": "cloture"}, timeout=15)
    if r.status_code != 200:
        log(False, "GET /chantiers?status_filter=cloture", f"status={r.status_code}")
    else:
        items = r.json()
        ids = {c["id"] for c in items}
        all_cloture = all(c["status"] == "cloture" for c in items)
        log(cid in ids and all_cloture,
            "status_filter=cloture returns updated chantier",
            f"count={len(items)} target_present={cid in ids} all_cloture={all_cloture}")

    # 5. Invalid status -> 400
    r = s.patch(f"{BASE}/chantiers/{cid}", json={"status": "foobar"}, timeout=15)
    log(r.status_code == 400, "invalid status -> 400",
        f"status_code={r.status_code} body={r.text[:200]}")

    # Summary
    total = len(results)
    passed = sum(1 for ok, _, _ in results if ok)
    print(f"\n=== {passed}/{total} PASSED ===")
    return 0 if passed == total else 2


if __name__ == "__main__":
    sys.exit(main())
