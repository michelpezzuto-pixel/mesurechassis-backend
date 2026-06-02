"""Test suite for Stripe checkout fix + DB cleanup endpoint.

Targets:
- POST /api/stripe/create-checkout-session (regression fix for "Entreprise introuvable")
- GET  /api/stripe/subscription-status
- POST /api/platform/db/cleanup (new destructive admin endpoint)

Restore plan : after the destructive cleanup, recreate admin / commercial / tech
users via the legacy register path so the rest of the test suite still works.
"""
from __future__ import annotations

import os
import sys
import uuid
import time
import json
import requests

BASE = os.environ.get(
    "BACKEND_URL",
    "https://window-field-app.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE}/api"
PLATFORM_TOKEN = "mc-platform-2026"

ADMIN_EMAIL = "admin@mesurechassis.fr"
ADMIN_PASS = "admin123"
ADMIN_NAME = "Marc Dubois"

COM_EMAIL = "commercial@mesurechassis.fr"
COM_PASS = "commercial123"
COM_NAME = "Sophie Martin"

TECH_EMAIL = "tech@mesurechassis.fr"
TECH_PASS = "tech123"
TECH_NAME = "Lucas Petit"

REPORT: list[tuple[bool, str]] = []


def step(ok: bool, msg: str, details: str = "") -> None:
    REPORT.append((ok, msg))
    marker = "✅" if ok else "❌"
    print(f"{marker} {msg}")
    if details:
        print(f"     {details}")


def login(email: str, password: str) -> tuple[int, dict]:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return r.status_code, body


def auth_h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────
# TEST 1 — STRIPE CHECKOUT FIX
# ─────────────────────────────────────────────────────────────────────────
def test_stripe_fix() -> None:
    print("\n=== TEST 1 — STRIPE CHECKOUT FIX ===")

    sc, body = login(ADMIN_EMAIL, ADMIN_PASS)
    if sc != 200 or "access_token" not in body:
        step(False, f"Admin login → {sc}", json.dumps(body)[:200])
        return
    token = body["access_token"]
    step(True, f"Admin login → 200 token len={len(token)}")

    # Plan = solo
    for plan in ("solo", "entreprise", "pro"):
        r = requests.post(
            f"{API}/stripe/create-checkout-session",
            headers={**auth_h(token), "Content-Type": "application/json"},
            json={"plan": plan},
            timeout=30,
        )
        if r.status_code == 200:
            try:
                resp = r.json()
            except Exception:
                resp = {}
            url = resp.get("checkout_url", "")
            if "checkout.stripe.com" in url:
                step(True, f"POST /stripe/create-checkout-session plan={plan} → 200 (url={url[:60]}...)")
            else:
                step(False, f"plan={plan} 200 but checkout_url missing/wrong: {url[:120]}")
        else:
            # Show body for debug
            try:
                detail = r.json()
            except Exception:
                detail = {"raw": r.text[:300]}
            # Specifically catch the bug we fixed
            if r.status_code == 404 and "Entreprise introuvable" in str(detail):
                step(False, f"REGRESSION! plan={plan} → 404 'Entreprise introuvable' (the bug is BACK)")
            else:
                step(False, f"plan={plan} → {r.status_code}", json.dumps(detail)[:300])

    # Plan = unknown
    r = requests.post(
        f"{API}/stripe/create-checkout-session",
        headers={**auth_h(token), "Content-Type": "application/json"},
        json={"plan": "unknown"},
        timeout=20,
    )
    try:
        d = r.json()
    except Exception:
        d = {"raw": r.text[:200]}
    if r.status_code == 400 and "Plan inconnu" in str(d):
        step(True, "plan=unknown → 400 'Plan inconnu'")
    else:
        step(False, f"plan=unknown → {r.status_code}", json.dumps(d)[:200])

    # GET /stripe/subscription-status
    r = requests.get(
        f"{API}/stripe/subscription-status",
        headers=auth_h(token),
        timeout=15,
    )
    try:
        d = r.json()
    except Exception:
        d = {"raw": r.text[:200]}
    if r.status_code == 200 and "has_subscription" in d and "is_locked" in d:
        step(
            True,
            f"GET /stripe/subscription-status → 200 has_subscription={d.get('has_subscription')} is_locked={d.get('is_locked')}",
        )
    else:
        step(False, f"GET /stripe/subscription-status → {r.status_code}", json.dumps(d)[:200])


# ─────────────────────────────────────────────────────────────────────────
# TEST 2 — DB CLEANUP ENDPOINT
# ─────────────────────────────────────────────────────────────────────────
def register_legacy(name: str, email: str, password: str, role: str, company_id: str = "default") -> int:
    r = requests.post(
        f"{API}/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "role": role,
            "company_id": company_id,
        },
        timeout=20,
    )
    return r.status_code


def test_cleanup_endpoint() -> None:
    print("\n=== TEST 2 — DB CLEANUP ENDPOINT ===")

    # 2.1 No header → 403
    r = requests.post(
        f"{API}/platform/db/cleanup",
        json={"keep_email": ADMIN_EMAIL, "confirm": "DELETE_ALL"},
        timeout=15,
    )
    if r.status_code == 403:
        step(True, "Cleanup without X-Platform-Token → 403")
    else:
        step(False, f"Cleanup without token → {r.status_code} (expected 403)")

    # 2.2 Wrong token → 403
    r = requests.post(
        f"{API}/platform/db/cleanup",
        headers={"X-Platform-Token": "wrong-token"},
        json={"keep_email": ADMIN_EMAIL, "confirm": "DELETE_ALL"},
        timeout=15,
    )
    if r.status_code == 403:
        step(True, "Cleanup with wrong X-Platform-Token → 403")
    else:
        step(False, f"Cleanup with wrong token → {r.status_code} (expected 403)")

    # 2.3 Correct token, missing confirm
    r = requests.post(
        f"{API}/platform/db/cleanup",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={"keep_email": ADMIN_EMAIL},
        timeout=15,
    )
    if r.status_code == 400 and "DELETE_ALL" in r.text:
        step(True, "Cleanup missing confirm → 400 'Pour confirmer, envoyez ...'")
    else:
        step(False, f"Cleanup missing confirm → {r.status_code} ({r.text[:200]})")

    # 2.4 Correct token + confirm but missing keep_email
    r = requests.post(
        f"{API}/platform/db/cleanup",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={"confirm": "DELETE_ALL"},
        timeout=15,
    )
    if r.status_code == 400 and "keep_email" in r.text:
        step(True, "Cleanup missing keep_email → 400 'keep_email est requis'")
    else:
        step(False, f"Cleanup missing keep_email → {r.status_code} ({r.text[:200]})")

    # 2.5 nonexistent user
    r = requests.post(
        f"{API}/platform/db/cleanup",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={
            "keep_email": "nonexistent_ghost_user@whatever.fr",
            "confirm": "DELETE_ALL",
        },
        timeout=15,
    )
    if r.status_code == 404 and "introuvable" in r.text:
        step(True, "Cleanup nonexistent keep_email → 404 'introuvable'")
    else:
        step(False, f"Cleanup nonexistent keep_email → {r.status_code} ({r.text[:200]})")

    # 2.6 Functional test --------------------------------------------------
    print("\n--- 2.6 FUNCTIONAL test (destructive) ---")
    uid = uuid.uuid4().hex[:8]
    email_a = f"cleanup_test_a_{uid}@mesurechassis.fr"
    email_b = f"cleanup_test_b_{uid}@mesurechassis.fr"
    email_c = f"cleanup_test_c_{uid}@mesurechassis.fr"

    for email, label in ((email_a, "A"), (email_b, "B"), (email_c, "C")):
        sc = register_legacy(f"Cleanup{label} Throwaway", email, "throwaway123", "technician", "default")
        if sc == 200:
            step(True, f"Register throwaway user {label} ({email}) → 200")
        else:
            step(False, f"Register throwaway user {label} → {sc}")

    # Login admin and count users
    sc, body = login(ADMIN_EMAIL, ADMIN_PASS)
    if sc != 200:
        step(False, f"Admin re-login pre-cleanup → {sc}")
        return
    admin_token = body["access_token"]
    r = requests.get(f"{API}/users", headers=auth_h(admin_token), timeout=15)
    if r.status_code == 200:
        users_before = len(r.json())
        step(True, f"GET /users (admin) → 200, count={users_before}")
    else:
        users_before = -1
        step(False, f"GET /users (admin) → {r.status_code}")

    # Perform cleanup
    r = requests.post(
        f"{API}/platform/db/cleanup",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={"keep_email": email_a, "confirm": "DELETE_ALL"},
        timeout=60,
    )
    if r.status_code == 200:
        try:
            payload = r.json()
        except Exception:
            payload = {}
        ok = (
            payload.get("ok") is True
            and payload.get("kept_user", {}).get("email") == email_a
            and "deleted" in payload
            and "before" in payload
        )
        if ok:
            step(
                True,
                "Cleanup destructive → 200",
                f"deleted={payload.get('deleted')} before={payload.get('before')} kept={payload.get('kept_user')}",
            )
        else:
            step(False, f"Cleanup 200 but unexpected body: {json.dumps(payload)[:300]}")
    else:
        step(False, f"Cleanup destructive → {r.status_code} ({r.text[:300]})")
        # Don't continue with destructive verifications if it failed
        return

    # 2.6.e admin login → 401 (admin was wiped)
    sc, body = login(ADMIN_EMAIL, ADMIN_PASS)
    if sc == 401:
        step(True, "Login admin@mesurechassis.fr post-cleanup → 401 (expected: admin wiped)")
    else:
        step(False, f"Login admin post-cleanup → {sc} (expected 401)")

    # 2.6.f login kept user (email_a) → 200
    sc, body = login(email_a, "throwaway123")
    if sc == 200 and "access_token" in body:
        kept_token = body["access_token"]
        step(True, f"Login kept user {email_a} → 200")
    else:
        kept_token = None
        step(False, f"Login kept user → {sc} {json.dumps(body)[:200]}")

    # 2.6.g login deleted user (email_b) → 401
    sc, body = login(email_b, "throwaway123")
    if sc == 401:
        step(True, f"Login deleted user {email_b} → 401 (expected)")
    else:
        step(False, f"Login deleted user → {sc} (expected 401)")

    # 2.6.h GET /chantiers as kept user
    if kept_token:
        r = requests.get(f"{API}/chantiers", headers=auth_h(kept_token), timeout=15)
        if r.status_code == 200:
            try:
                items = r.json()
            except Exception:
                items = []
            step(True, f"GET /chantiers (kept user) → 200, n={len(items) if isinstance(items, list) else 'n/a'}")
        else:
            step(False, f"GET /chantiers (kept user) → {r.status_code}")


# ─────────────────────────────────────────────────────────────────────────
# RESTORE STATE
# ─────────────────────────────────────────────────────────────────────────
def restore_state() -> None:
    print("\n=== RESTORE — recreate admin / commercial / tech ===")
    # Recreate admin, commercial, tech via legacy register
    sc_a = register_legacy(ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASS, "admin", "default")
    step(sc_a == 200, f"Re-register admin → {sc_a}")
    sc_c = register_legacy(COM_NAME, COM_EMAIL, COM_PASS, "commercial", "default")
    step(sc_c == 200, f"Re-register commercial → {sc_c}")
    sc_t = register_legacy(TECH_NAME, TECH_EMAIL, TECH_PASS, "technician", "default")
    step(sc_t == 200, f"Re-register tech → {sc_t}")

    # Verify each can login
    for email, pw, label in (
        (ADMIN_EMAIL, ADMIN_PASS, "admin"),
        (COM_EMAIL, COM_PASS, "commercial"),
        (TECH_EMAIL, TECH_PASS, "tech"),
    ):
        sc, body = login(email, pw)
        if sc == 200 and "access_token" in body:
            step(True, f"Verify login {label} ({email}) → 200")
        else:
            step(False, f"Verify login {label} → {sc} {json.dumps(body)[:200]}")


# ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    test_stripe_fix()
    test_cleanup_endpoint()
    restore_state()

    total = len(REPORT)
    passed = sum(1 for ok, _ in REPORT if ok)
    failed = total - passed
    print(f"\n=== SUMMARY: {passed}/{total} PASS ({failed} fail) ===")
    if failed:
        print("\nFailed steps:")
        for ok, msg in REPORT:
            if not ok:
                print(f"  ❌ {msg}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
