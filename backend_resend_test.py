"""Tests for Resend integration on the forgot-password / reset-password flow.

Endpoints under test:
  - POST /api/auth/forgot-password
  - POST /api/auth/reset-password
  - POST /api/auth/login   (regression)
  - POST /api/auth/register (regression)
  - GET  /api/auth/me      (regression)

Reads BACKEND URL from /app/frontend/.env (EXPO_PUBLIC_BACKEND_URL).
Hits MongoDB directly to read the (intentionally non-exposed) password_reset_code
when Resend delivers successfully.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

# ----- Resolve BACKEND URL -----
FRONT_ENV = dotenv_values("/app/frontend/.env")
BACKEND_URL = FRONT_ENV.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
assert BACKEND_URL, "EXPO_PUBLIC_BACKEND_URL not set"
API = f"{BACKEND_URL}/api"

# ----- Resolve Mongo creds -----
BACK_ENV = dotenv_values("/app/backend/.env")
MONGO_URL = BACK_ENV.get("MONGO_URL") or os.environ.get("MONGO_URL")
DB_NAME = BACK_ENV.get("DB_NAME") or os.environ.get("DB_NAME") or "test_database"

ADMIN_EMAIL = "admin@mesurechassis.fr"
ADMIN_PASSWORD = "admin123"
COMMERCIAL_EMAIL = "commercial@mesurechassis.fr"
COMMERCIAL_PASSWORD = "commercial123"
TECH_EMAIL = "tech@mesurechassis.fr"
TECH_PASSWORD = "tech123"

BACKEND_LOG = "/var/log/supervisor/backend.err.log"

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    flag = "✅" if ok else "❌"
    print(f"{flag} {name}{(' — ' + detail) if detail else ''}")


def read_log_tail(byte_offset: int) -> str:
    """Returns content of backend.err.log starting at byte_offset."""
    try:
        with open(BACKEND_LOG, "rb") as f:
            f.seek(byte_offset)
            return f.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"<read fail: {e}>"


def log_size() -> int:
    try:
        return os.path.getsize(BACKEND_LOG)
    except Exception:
        return 0


async def mongo_get_reset_code(email: str) -> tuple[str | None, str | None]:
    """Reads password_reset_code from MongoDB for an email."""
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        doc = await client[DB_NAME].users.find_one({"email": email.lower()})
        if not doc:
            return None, None
        return doc.get("password_reset_code"), doc.get("password_reset_expires_at")
    finally:
        client.close()


def login(email: str, password: str) -> tuple[int, dict]:
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


def main():
    print(f"BACKEND={BACKEND_URL}")
    print(f"DB_NAME={DB_NAME}")
    print("=" * 80)

    # ============================================================
    # 0) Sanity: backend up & admin can login (baseline)
    # ============================================================
    sc, body = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    record("0.admin login (baseline)", sc == 200 and "access_token" in body,
           f"sc={sc}, has_token={'access_token' in body}")
    if sc != 200:
        print("Critical: admin baseline login failed, aborting.")
        return
    admin_token = body["access_token"]

    # ============================================================
    # 1) POST /api/auth/forgot-password with existing email — Resend OK
    # ============================================================
    offset = log_size()
    r = httpx.post(f"{API}/auth/forgot-password", json={"email": ADMIN_EMAIL}, timeout=30)
    sc1 = r.status_code
    try:
        body1 = r.json()
    except Exception:
        body1 = {}
    ok1 = (
        sc1 == 200
        and body1.get("ok") is True
        and isinstance(body1.get("message"), str)
    )
    record("1.forgot-password existing email → 200 ok:true",
           ok1, f"sc={sc1}, body_keys={list(body1.keys())}")

    # IMPORTANT: when Resend delivered → NO beta_reset_code
    no_beta_code = "beta_reset_code" not in body1
    record("1.NO beta_reset_code in response (Resend delivered)",
           no_beta_code,
           f"body_keys={list(body1.keys())}")

    # Wait for log flush then verify Resend OK log line
    time.sleep(1.5)
    log_chunk = read_log_tail(offset)
    has_resend_ok = bool(
        re.search(rf"📧 Resend OK → {re.escape(ADMIN_EMAIL)}.*id=", log_chunk)
        or re.search(rf"Resend OK.* {re.escape(ADMIN_EMAIL)}.*id=", log_chunk)
    )
    # We also check for a fallback mock line meaning Resend FAILED
    has_resend_fail = bool(re.search(r"Resend FAIL|Resend exception|EMAIL \(MOCK", log_chunk))
    record(
        "1.backend log shows '📧 Resend OK → <email> (..., id=...)'",
        has_resend_ok and not has_resend_fail,
        f"resend_ok={has_resend_ok} resend_fail/mock={has_resend_fail}",
    )

    # ============================================================
    # 2) POST /api/auth/forgot-password with unknown email — anti-enum
    # ============================================================
    offset = log_size()
    unknown_email = f"nope_test_{uuid.uuid4().hex[:8]}@example.com"
    r = httpx.post(f"{API}/auth/forgot-password", json={"email": unknown_email}, timeout=30)
    sc2 = r.status_code
    body2 = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record("2.forgot-password unknown email → 200 (anti-enum)",
           sc2 == 200 and body2.get("ok") is True,
           f"sc={sc2}, body={body2}")
    record("2.NO beta_reset_code for unknown email",
           "beta_reset_code" not in body2,
           f"keys={list(body2.keys())}")

    time.sleep(1.0)
    log_chunk = read_log_tail(offset)
    # No Resend send should have happened for unknown email
    no_resend_call = not re.search(
        rf"Resend OK → {re.escape(unknown_email)}|Resend FAIL.*{re.escape(unknown_email)}",
        log_chunk,
    )
    record("2.no Resend send triggered for unknown email", no_resend_call, "")

    # ============================================================
    # 3) Invalid email format → 400
    # ============================================================
    r = httpx.post(f"{API}/auth/forgot-password", json={"email": "pas_un_email"}, timeout=30)
    sc3 = r.status_code
    body3 = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "3.forgot-password invalid email → 400 'Email invalide.'",
        sc3 == 400 and body3.get("detail") == "Email invalide.",
        f"sc={sc3} detail={body3.get('detail')}",
    )

    # ============================================================
    # 4) FULL reset-password flow on a test user
    # ============================================================
    test_email = f"qa_reset_{uuid.uuid4().hex[:8]}@mesurechassis.fr"
    test_password_initial = "InitialPass1234!"
    test_password_new = "NouveauPass1234!"

    # 4a. Register (legacy mode: role=technician → active, no email verification)
    r = httpx.post(
        f"{API}/auth/register",
        json={
            "name": "QA Reset Tester",
            "email": test_email,
            "password": test_password_initial,
            "role": "technician",
            "company_id": "default",
        },
        timeout=30,
    )
    sc4a = r.status_code
    body4a = r.json() if r.status_code == 200 else {}
    record(
        "4a.register test user (legacy role-mode)",
        sc4a == 200 and "access_token" in body4a,
        f"sc={sc4a} email={test_email}",
    )
    if sc4a != 200:
        print("Cannot continue reset flow without user.")
        finalize()
        return

    # Login baseline OK with initial password
    sc, _ = login(test_email, test_password_initial)
    record("4a.login with INITIAL password", sc == 200, f"sc={sc}")

    # 4b. Forgot-password for test user
    offset = log_size()
    r = httpx.post(f"{API}/auth/forgot-password", json={"email": test_email}, timeout=30)
    sc4b = r.status_code
    body4b = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "4b.forgot-password for test user → 200, no beta_reset_code",
        sc4b == 200 and body4b.get("ok") is True and "beta_reset_code" not in body4b,
        f"sc={sc4b} keys={list(body4b.keys())}",
    )
    time.sleep(1.0)
    log4b = read_log_tail(offset)
    delivered_resend = bool(re.search(rf"Resend OK → {re.escape(test_email)}.*id=", log4b))
    record(
        "4b.Resend delivered (log shows OK)",
        delivered_resend,
        f"snippet={log4b[-300:] if not delivered_resend else 'OK'}",
    )

    # 4c. Fetch code directly from DB
    code, expires_at = asyncio.run(mongo_get_reset_code(test_email))
    record(
        "4c.fetch reset code from MongoDB",
        bool(code) and len(code) == 6 and code.isdigit(),
        f"code_len={len(code) if code else 0} expires={expires_at}",
    )

    if not code:
        print("No code in DB, cannot continue reset flow.")
        cleanup_test_user(test_email, admin_token)
        finalize()
        return

    # 4d. Reset with valid code → 200
    r = httpx.post(
        f"{API}/auth/reset-password",
        json={"email": test_email, "code": code, "new_password": test_password_new},
        timeout=30,
    )
    sc4d = r.status_code
    body4d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "4d.reset-password with valid code → 200",
        sc4d == 200 and body4d.get("ok") is True,
        f"sc={sc4d} body={body4d}",
    )

    # 4e. Login with new password
    sc4e, body4e = login(test_email, test_password_new)
    record(
        "4e.login with NEW password → 200 + token",
        sc4e == 200 and "access_token" in body4e,
        f"sc={sc4e}",
    )

    # Confirm old password no longer works
    sc_old, _ = login(test_email, test_password_initial)
    record(
        "4e.login with OLD password → 401",
        sc_old == 401,
        f"sc={sc_old}",
    )

    # 4f. Reuse same code → 400
    r = httpx.post(
        f"{API}/auth/reset-password",
        json={"email": test_email, "code": code, "new_password": "AnotherPass5678!"},
        timeout=30,
    )
    sc4f = r.status_code
    body4f = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record(
        "4f.reuse same code → 400 'Code invalide ou expiré.'",
        sc4f == 400 and body4f.get("detail") == "Code invalide ou expiré.",
        f"sc={sc4f} detail={body4f.get('detail')}",
    )

    # ============================================================
    # 5) Failure cases
    # ============================================================
    # Empty email body
    r = httpx.post(f"{API}/auth/forgot-password", json={"email": ""}, timeout=30)
    record(
        "5.empty email → 400",
        r.status_code == 400 and r.json().get("detail") == "Email invalide.",
        f"sc={r.status_code}",
    )
    # Missing email key
    r = httpx.post(f"{API}/auth/forgot-password", json={}, timeout=30)
    record(
        "5.missing email key → 400",
        r.status_code == 400,
        f"sc={r.status_code}",
    )
    # reset-password missing field → 400
    r = httpx.post(
        f"{API}/auth/reset-password",
        json={"email": test_email, "code": ""},
        timeout=30,
    )
    record(
        "5.reset-password missing field → 400",
        r.status_code == 400,
        f"sc={r.status_code}",
    )
    # reset-password with weak password
    r = httpx.post(
        f"{API}/auth/reset-password",
        json={"email": test_email, "code": "000000", "new_password": "abc"},
        timeout=30,
    )
    record(
        "5.reset-password weak password (<6 chars) → 400",
        r.status_code == 400,
        f"sc={r.status_code}",
    )

    # ============================================================
    # 6) Regression: admin login + /auth/me + register + profile
    # ============================================================
    sc, body = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    record("6.regression admin login still works", sc == 200, f"sc={sc}")
    token_admin = body.get("access_token")

    sc, body = login(COMMERCIAL_EMAIL, COMMERCIAL_PASSWORD)
    record("6.regression commercial login works", sc == 200, f"sc={sc}")

    sc, body = login(TECH_EMAIL, TECH_PASSWORD)
    record("6.regression tech login works", sc == 200, f"sc={sc}")

    r = httpx.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {token_admin}"},
        timeout=20,
    )
    record(
        "6.regression GET /auth/me admin",
        r.status_code == 200 and r.json().get("email") == ADMIN_EMAIL,
        f"sc={r.status_code}",
    )

    r = httpx.get(
        f"{API}/company/profile",
        headers={"Authorization": f"Bearer {token_admin}"},
        timeout=20,
    )
    record(
        "6.regression GET /company/profile",
        r.status_code == 200 and "company_id" in r.json(),
        f"sc={r.status_code}",
    )

    # Cleanup test user
    cleanup_test_user(test_email, token_admin)
    finalize()


def cleanup_test_user(email: str, admin_token: str):
    """Delete test user from DB to keep environment clean."""
    async def _do():
        client = AsyncIOMotorClient(MONGO_URL)
        try:
            res = await client[DB_NAME].users.delete_many({"email": email.lower()})
            return res.deleted_count
        finally:
            client.close()

    try:
        n = asyncio.run(_do())
        record(f"CLEANUP delete test user {email}", n >= 1, f"deleted={n}")
    except Exception as e:
        record(f"CLEANUP delete test user", False, str(e))


def finalize():
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print()
    print("=" * 80)
    print(f"RESULT: {passed}/{total} passed")
    print("=" * 80)
    failed = [(n, d) for n, ok, d in results if not ok]
    if failed:
        print("FAILED:")
        for n, d in failed:
            print(f"  ❌ {n} — {d}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
