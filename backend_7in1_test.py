"""Backend 7-in-1 production-ready batch re-validation.

Covers:
  A) Feedback recipient email
  B) Auto team assignment email (+ anti-double self-assignment)
  C) Validation flow + manufacturing lock (backend acceptance only)
  D) Regression (pytest tests/)
  E) Mandatory cleanup (restore artisan_mode=true)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import requests

BASE_URL = os.environ.get(
    "BACKEND_URL",
    "https://window-field-app.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"
BACKEND_LOG = "/var/log/supervisor/backend.err.log"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMMERCIAL = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")


def login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def read_log_tail(byte_offset: int) -> str:
    """Read log content starting at byte_offset to current end."""
    try:
        with open(BACKEND_LOG, "rb") as f:
            f.seek(byte_offset)
            return f.read().decode("utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover
        return f"<read_log_tail error: {exc}>"


def log_size() -> int:
    try:
        return os.path.getsize(BACKEND_LOG)
    except Exception:
        return 0


def log_section(title: str) -> None:
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def assert_eq(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected!r} actual={actual!r}")
    print(f"  ✓ {label} = {actual!r}")


def main() -> int:
    results: dict[str, bool] = {}
    artisan_was: bool = True  # default expectation

    # Setup tokens
    admin_tok = login(*ADMIN)
    commercial_tok = login(*COMMERCIAL)
    tech_tok = login(*TECH)
    print(f"BASE={BASE_URL}")

    # ------------------------------------------------------------------
    # PRE-CHECK: snapshot artisan_mode, disable it for proper tests
    # ------------------------------------------------------------------
    log_section("PRE-CHECK : disable artisan_mode")
    r = requests.get(f"{API}/company/profile", headers=auth(admin_tok), timeout=15)
    r.raise_for_status()
    prof = r.json()
    artisan_was = bool(prof.get("artisan_mode", True))
    print(f"  initial artisan_mode = {artisan_was}")
    print(f"  initial plan = {prof.get('plan')}")
    print(f"  initial subscription_status = {prof.get('subscription_status')}")
    if artisan_was:
        r2 = requests.patch(
            f"{API}/company/profile",
            headers=auth(admin_tok),
            json={"artisan_mode": False},
            timeout=15,
        )
        r2.raise_for_status()
        assert r2.json()["artisan_mode"] is False
        print("  ✓ artisan_mode disabled for tests")

    # Get a non-admin user for assignment tests (commercial or technician)
    r = requests.get(f"{API}/users", headers=auth(admin_tok), timeout=15)
    r.raise_for_status()
    users = r.json()
    admin_user = next(u for u in users if u["email"] == ADMIN[0])
    commercial_user = next(u for u in users if u["email"] == COMMERCIAL[0])
    tech_user = next(u for u in users if u["email"] == TECH[0])
    print(f"  admin_id      = {admin_user['id']}")
    print(f"  commercial_id = {commercial_user['id']}")
    print(f"  tech_id       = {tech_user['id']}")

    created_chantiers: list[str] = []
    created_feedbacks: list[str] = []

    # ==================================================================
    # A) Feedback Recipient Email
    # ==================================================================
    log_section("A) Feedback Recipient Email (Point 6)")
    try:
        offset_a = log_size()
        payload_a = {
            "user_comment": "TEST_feedback_visualization Bug détecté sur l'écran X",
            "page_context": "/dashboard",
        }
        r = requests.post(
            f"{API}/feedbacks",
            headers=auth(admin_tok),
            json=payload_a,
            timeout=15,
        )
        assert r.status_code == 200, f"POST /feedbacks → {r.status_code} body={r.text}"
        body = r.json()
        for key in ("id", "user_email", "user_comment", "page_context", "company_id", "created_at"):
            assert key in body, f"missing key {key} in response"
        assert_eq(body["user_comment"], payload_a["user_comment"], "user_comment")
        assert_eq(body["page_context"], "/dashboard", "page_context")
        assert_eq(body["user_email"], ADMIN[0], "user_email")
        created_feedbacks.append(body["id"])

        # Give the logger a moment to flush
        time.sleep(0.4)
        tail_a = read_log_tail(offset_a)
        # Build excerpt around the feedback email
        excerpt_a = []
        capture = False
        for line in tail_a.splitlines():
            if "EMAIL (MOCK)" in line and not capture:
                capture = True
                excerpt_a.append(line)
                continue
            if capture:
                excerpt_a.append(line)
                if "─────────────────────────────────────────────────────" in line and len(excerpt_a) > 3:
                    # end of block
                    if any("[Feedback]" in ln for ln in excerpt_a):
                        break
                    else:
                        excerpt_a = []
                        capture = False
        excerpt_str = "\n".join(excerpt_a)

        # Subject contains "[Feedback]"
        assert "[Feedback]" in tail_a, "Subject [Feedback] not found in log"
        print("  ✓ Subject contains '[Feedback]'")
        # Body contains user_comment marker
        assert "TEST_feedback_visualization" in tail_a, "user_comment not in log"
        print("  ✓ Body contains 'TEST_feedback_visualization'")
        # Body contains admin email
        assert ADMIN[0] in tail_a, "admin email not in log"
        print(f"  ✓ Body contains admin email {ADMIN[0]}")
        # Body contains /dashboard
        assert "/dashboard" in tail_a, "page_context /dashboard not in log"
        print("  ✓ Body contains '/dashboard'")

        # Non-blocking validation: response 200 already validated above.
        results["A"] = True
        print()
        print("--- EMAIL EXCERPT (feedback) ---")
        print(excerpt_str if excerpt_str else tail_a[-1500:])
        print("--- /END ---")
    except Exception as exc:
        print(f"  ❌ A FAILED: {exc}")
        results["A"] = False

    # ==================================================================
    # B) Auto Team Assignment Email
    # ==================================================================
    log_section("B) Auto Team Assignment Email (Point 5)")
    try:
        # B-1 : assignation à commercial (différent du créateur admin)
        offset_b1 = log_size()
        body_b1 = {
            "first_name": "TEST",
            "last_name": "Assignment",
            "address": "10 rue Test",
            "postal_code": "75011",
            "city": "Paris",
            "status": "devis_a_faire",
            "assigned_to": commercial_user["id"],
        }
        r = requests.post(
            f"{API}/chantiers",
            headers=auth(admin_tok),
            json=body_b1,
            timeout=15,
        )
        assert r.status_code == 200, f"POST /chantiers → {r.status_code} {r.text}"
        ch1 = r.json()
        created_chantiers.append(ch1["id"])
        print(f"  ✓ chantier created id={ch1['id']} client_name={ch1['client_name']}")

        time.sleep(0.4)
        tail_b1 = read_log_tail(offset_b1)
        assert "Nouveau chantier attribué" in tail_b1, "subject 'Nouveau chantier attribué' missing"
        print("  ✓ Subject contains 'Nouveau chantier attribué'")
        assert "Assignment TEST" in tail_b1, "client_name 'Assignment TEST' missing"
        print("  ✓ Subject contains 'Assignment TEST' (client_name)")
        assert "10 rue Test, 75011, Paris" in tail_b1, "address line missing"
        print("  ✓ Body contains '10 rue Test, 75011, Paris'")
        assert commercial_user["email"] in tail_b1, "assignee email missing"
        print(f"  ✓ Email sent to {commercial_user['email']}")

        # Build excerpt
        excerpt_b1 = []
        capture = False
        for line in tail_b1.splitlines():
            if "EMAIL (MOCK)" in line and not capture:
                capture = True
                excerpt_b1.append(line)
                continue
            if capture:
                excerpt_b1.append(line)
                if "─────────────────────────────────────────────────────" in line and len(excerpt_b1) > 3:
                    if "Nouveau chantier attribué" in "\n".join(excerpt_b1):
                        break
                    else:
                        excerpt_b1 = []
                        capture = False
        print()
        print("--- EMAIL EXCERPT (assignment to commercial) ---")
        print("\n".join(excerpt_b1) if excerpt_b1 else tail_b1[-1500:])
        print("--- /END ---")

        # B-2 : self-assignment → no email
        offset_b2 = log_size()
        body_b2 = {
            "first_name": "SELF",
            "last_name": "Assignment",
            "address": "20 rue Solo",
            "postal_code": "75002",
            "city": "Paris",
            "status": "devis_a_faire",
            "assigned_to": admin_user["id"],
        }
        r = requests.post(
            f"{API}/chantiers",
            headers=auth(admin_tok),
            json=body_b2,
            timeout=15,
        )
        assert r.status_code == 200, f"POST /chantiers self → {r.status_code} {r.text}"
        ch2 = r.json()
        created_chantiers.append(ch2["id"])
        print(f"  ✓ self-assigned chantier created id={ch2['id']}")
        time.sleep(0.4)
        tail_b2 = read_log_tail(offset_b2)
        if "Nouveau chantier attribué" in tail_b2:
            print("  ❌ self-assignment SENT email — anti-double check FAILED")
            print("--- LOG TAIL (self-assignment) ---")
            print(tail_b2[-1500:])
            print("--- /END ---")
            raise AssertionError("self-assignment must not trigger email")
        print("  ✓ self-assignment did NOT trigger 'Nouveau chantier attribué' email")
        print()
        print("--- LOG TAIL EXCERPT (self-assignment block - should NOT contain 'Nouveau chantier attribué') ---")
        # Only show first 800 chars to confirm
        print(tail_b2[:1500] if tail_b2 else "(no new log lines)")
        print("--- /END ---")

        results["B"] = True
    except Exception as exc:
        print(f"  ❌ B FAILED: {exc}")
        results["B"] = False

    # ==================================================================
    # C) Validation flow + manufacturing lock
    # ==================================================================
    log_section("C) Validation Flow + Manufacturing Lock (Points 2/3/4)")
    try:
        # C-1: artisan_mode already false (pre-check)
        r = requests.get(f"{API}/company/profile", headers=auth(admin_tok), timeout=15)
        r.raise_for_status()
        assert r.json()["artisan_mode"] is False, "artisan_mode must be false for C"
        print("  ✓ artisan_mode=false")

        # Create a chantier with status="technique_a_valider"
        body_c = {
            "first_name": "Valide",
            "last_name": "Fabrication",
            "address": "5 chemin du Test",
            "postal_code": "69001",
            "city": "Lyon",
            "status": "technique_a_valider",
        }
        r = requests.post(
            f"{API}/chantiers", headers=auth(admin_tok), json=body_c, timeout=15
        )
        assert r.status_code == 200, f"POST /chantiers → {r.status_code} {r.text}"
        ch_c = r.json()
        created_chantiers.append(ch_c["id"])
        print(f"  ✓ created chantier status=technique_a_valider id={ch_c['id']}")

        # Admin PATCH status → en_fabrication
        r = requests.patch(
            f"{API}/chantiers/{ch_c['id']}",
            headers=auth(admin_tok),
            json={"status": "en_fabrication"},
            timeout=15,
        )
        assert r.status_code == 200, f"PATCH status en_fabrication → {r.status_code} {r.text}"
        assert r.json()["status"] == "en_fabrication"
        print("  ✓ Admin PATCH {status:'en_fabrication'} → 200 (backend doesn't gate, frontend does)")

        # Tech XLSX export on en_fabrication chantier
        r = requests.get(
            f"{API}/chantiers/{ch_c['id']}/export.xlsx",
            headers=auth(tech_tok),
            timeout=20,
        )
        assert r.status_code == 200, f"export.xlsx (tech, en_fabrication) → {r.status_code} {r.text[:200]}"
        assert r.content[:2] == b"PK", "xlsx must start with PK magic"
        print(f"  ✓ Tech GET export.xlsx on en_fabrication → 200 ({len(r.content)} bytes, magic PK)")

        results["C"] = True
    except Exception as exc:
        print(f"  ❌ C FAILED: {exc}")
        results["C"] = False

    # ==================================================================
    # D) Regression: pytest tests/
    # ==================================================================
    log_section("D) Regression — pytest tests/")
    try:
        proc = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--no-cov", "-q"],
            cwd="/app/backend",
            capture_output=True,
            text=True,
            timeout=240,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        # Print last 40 lines
        print("\n".join(out.splitlines()[-40:]))
        if proc.returncode == 0:
            results["D"] = True
            print("  ✓ pytest exit 0")
        else:
            print(f"  ❌ pytest exit {proc.returncode}")
            results["D"] = False
    except Exception as exc:
        print(f"  ❌ D FAILED: {exc}")
        results["D"] = False

    # ==================================================================
    # E) Mandatory cleanup
    # ==================================================================
    log_section("E) Mandatory Cleanup")
    cleanup_ok = True
    try:
        # Delete created chantiers
        for cid in created_chantiers:
            r = requests.delete(
                f"{API}/chantiers/{cid}", headers=auth(admin_tok), timeout=15
            )
            print(f"  DELETE /chantiers/{cid} → {r.status_code}")
        # Delete created feedbacks
        for fid in created_feedbacks:
            r = requests.delete(
                f"{API}/feedbacks/{fid}", headers=auth(admin_tok), timeout=15
            )
            print(f"  DELETE /feedbacks/{fid} → {r.status_code}")

        # Restore artisan_mode=true
        r = requests.patch(
            f"{API}/company/profile",
            headers=auth(admin_tok),
            json={"artisan_mode": True},
            timeout=15,
        )
        assert r.status_code == 200, f"PATCH artisan_mode=true → {r.status_code} {r.text}"
        assert r.json()["artisan_mode"] is True, "artisan_mode not restored"
        print("  ✓ PATCH artisan_mode=true → 200")

        # Verify final state
        r = requests.get(f"{API}/company/profile", headers=auth(admin_tok), timeout=15)
        r.raise_for_status()
        final = r.json()
        print(f"  ↳ FINAL profile: artisan_mode={final.get('artisan_mode')}, plan={final.get('plan')}, subscription_status={final.get('subscription_status')}, cancel_at_period_end={final.get('cancel_at_period_end')}")
        assert final.get("artisan_mode") is True
        results["E"] = cleanup_ok
    except Exception as exc:
        print(f"  ❌ E FAILED: {exc}")
        results["E"] = False

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    log_section("SUMMARY")
    for section in ("A", "B", "C", "D", "E"):
        flag = "✅ PASS" if results.get(section) else "❌ FAIL"
        print(f"  Section {section}: {flag}")

    overall = all(results.values())
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
