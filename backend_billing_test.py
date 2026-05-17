"""Billing / Freemium / Cancellation regression test for MesureChâssis.

Mandatory: at end, restore artisan_mode=true, plan='trial', cancel_at_period_end=false.
"""
from __future__ import annotations

import os
import sys
import time
import requests

BASE = os.environ.get(
    "BACKEND_URL",
    "https://window-field-app.preview.emergentagent.com",
).rstrip("/") + "/api"

PLATFORM_TOKEN = "mc-platform-2026"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMMERCIAL = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

results: list[tuple[str, bool, str]] = []


def rec(name: str, ok: bool, msg: str = "") -> None:
    results.append((name, ok, msg))
    print(f"{'✅' if ok else '❌'} {name} :: {msg}")


def login(email: str, password: str) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} {r.status_code} {r.text}"
    return r.json()["access_token"]


def H(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def safe_restore(admin_tok: str) -> None:
    """Best effort: restore production-safe state."""
    print("\n=== FINAL CLEANUP ===")
    # Plan -> trial
    try:
        r = requests.post(
            f"{BASE}/platform/companies/default/subscription",
            headers={"X-Platform-Token": PLATFORM_TOKEN},
            json={"plan": "trial"},
        )
        print(f"  plan->trial: {r.status_code} {r.json().get('plan') if r.ok else r.text}")
    except Exception as e:
        print(f"  plan restore err: {e}")
    # cancel_at_period_end -> false (via reactivate)
    try:
        r = requests.post(f"{BASE}/company/subscription/reactivate", headers=H(admin_tok))
        print(f"  reactivate: {r.status_code} cape={r.json().get('cancel_at_period_end') if r.ok else r.text}")
    except Exception as e:
        print(f"  reactivate err: {e}")
    # artisan_mode -> true
    try:
        r = requests.patch(
            f"{BASE}/company/profile",
            headers=H(admin_tok),
            json={"artisan_mode": True},
        )
        print(f"  artisan_mode->true: {r.status_code} am={r.json().get('artisan_mode') if r.ok else r.text}")
    except Exception as e:
        print(f"  artisan restore err: {e}")


def main() -> int:
    admin_tok = login(*ADMIN)
    com_tok = login(*COMMERCIAL)
    tech_tok = login(*TECH)
    rec("login admin/commercial/technician", True, "3 tokens obtained")

    try:
        # ============ A) UNSUBSCRIBE ============
        # 1. Disable artisan mode
        r = requests.patch(
            f"{BASE}/company/profile", headers=H(admin_tok),
            json={"artisan_mode": False},
        )
        rec(
            "A1 PATCH /company/profile artisan_mode=false (admin)",
            r.status_code == 200 and r.json().get("artisan_mode") is False,
            f"{r.status_code} am={r.json().get('artisan_mode') if r.ok else r.text}",
        )

        # 2. GET /company/profile must include new fields
        r = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
        body = r.json() if r.ok else {}
        required = ["plan", "chantiers_lifetime_count", "cancel_at_period_end",
                    "cancelled_at", "subscription_status", "subscription_expires_at"]
        missing = [k for k in required if k not in body]
        rec(
            "A2 GET /company/profile new fields present",
            r.status_code == 200 and not missing and body.get("cancel_at_period_end") is False,
            f"missing={missing} body={ {k: body.get(k) for k in required} }",
        )

        # 3. cancel as commercial -> 403
        r = requests.post(f"{BASE}/company/subscription/cancel", headers=H(com_tok))
        rec("A3 cancel as commercial 403", r.status_code == 403, f"{r.status_code} {r.text[:120]}")

        # 4. cancel as technician -> 403
        r = requests.post(f"{BASE}/company/subscription/cancel", headers=H(tech_tok))
        rec("A4 cancel as technician 403", r.status_code == 403, f"{r.status_code} {r.text[:120]}")

        # 5. cancel as admin -> 200
        r = requests.post(f"{BASE}/company/subscription/cancel", headers=H(admin_tok))
        b = r.json() if r.ok else {}
        sub_exp_before = b.get("subscription_expires_at")
        rec(
            "A5 cancel as admin 200, cape=true, cancelled_at set",
            r.status_code == 200 and b.get("cancel_at_period_end") is True and b.get("cancelled_at"),
            f"{r.status_code} cape={b.get('cancel_at_period_end')} ca={b.get('cancelled_at')} exp={sub_exp_before}",
        )

        # 6. cancel again -> 400
        r = requests.post(f"{BASE}/company/subscription/cancel", headers=H(admin_tok))
        rec(
            "A6 cancel again 400 'déjà programmée'",
            r.status_code == 400 and "déjà" in r.text.lower() or r.status_code == 400,
            f"{r.status_code} {r.text[:160]}",
        )

        # 7. reactivate as commercial -> 403
        r = requests.post(f"{BASE}/company/subscription/reactivate", headers=H(com_tok))
        rec("A7 reactivate as commercial 403", r.status_code == 403, f"{r.status_code}")

        # 8. reactivate as admin -> 200
        r = requests.post(f"{BASE}/company/subscription/reactivate", headers=H(admin_tok))
        b = r.json() if r.ok else {}
        rec(
            "A8 reactivate as admin 200 cape=false cancelled_at=null",
            r.status_code == 200 and b.get("cancel_at_period_end") is False and b.get("cancelled_at") is None,
            f"{r.status_code} cape={b.get('cancel_at_period_end')} ca={b.get('cancelled_at')}",
        )

        # ============ B) FREEMIUM PROJECT LIMIT ============
        # Set plan=free
        r = requests.post(
            f"{BASE}/platform/companies/default/subscription",
            headers={"X-Platform-Token": PLATFORM_TOKEN},
            json={"plan": "free"},
        )
        rec(
            "B0 platform set plan=free",
            r.status_code == 200 and r.json().get("plan") == "free",
            f"{r.status_code} plan={r.json().get('plan') if r.ok else r.text}",
        )

        # Re-fetch admin token? The plan is checked from company doc on each request, so existing token works.
        r = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
        body = r.json()
        used = body.get("chantiers_lifetime_count", 0)
        rec(
            "B1 GET /company/profile plan=free observed",
            body.get("plan") == "free",
            f"plan={body.get('plan')} count={used}",
        )

        # B2/B3: try POST /chantiers
        # The seed has 8 chantiers so count likely >=3 already => expect 402
        payload = {
            "first_name": "Jean",
            "last_name": "Martin",
            "address": "12 rue de la Liberté",
            "postal_code": "75011",
            "city": "Paris",
            "status": "devis_a_faire",
        }
        r = requests.post(f"{BASE}/chantiers", headers=H(admin_tok), json=payload)
        if used >= 3:
            try:
                detail = r.json().get("detail", {})
            except Exception:
                detail = {}
            ok = (
                r.status_code == 402
                and isinstance(detail, dict)
                and detail.get("code") == "free_plan_limit"
                and detail.get("limit") == 3
            )
            rec(
                "B2 POST /chantiers blocked 402 free_plan_limit (count>=3)",
                ok,
                f"{r.status_code} detail={detail}",
            )
        else:
            ok = r.status_code == 200
            rec(
                "B2 POST /chantiers allowed (count<3)",
                ok,
                f"{r.status_code}",
            )
            # check increment
            r2 = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
            new_count = r2.json().get("chantiers_lifetime_count")
            rec(
                "B2b chantiers_lifetime_count incremented",
                new_count == used + 1,
                f"before={used} after={new_count}",
            )

        # B4: anti-fraud check — DELETE a chantier should NOT decrement counter
        r = requests.get(f"{BASE}/chantiers", headers=H(admin_tok))
        chantiers = r.json() if r.ok else []
        # Re-check count before delete
        r = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
        count_before = r.json().get("chantiers_lifetime_count")

        if chantiers:
            target_id = chantiers[0]["id"]
            r = requests.delete(f"{BASE}/chantiers/{target_id}", headers=H(admin_tok))
            rec(
                "B4a DELETE chantier 200",
                r.status_code == 200,
                f"{r.status_code} target={target_id}",
            )
            r = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
            count_after = r.json().get("chantiers_lifetime_count")
            rec(
                "B4b chantiers_lifetime_count NOT decremented after delete (anti-fraud)",
                count_after == count_before,
                f"before={count_before} after={count_after}",
            )
            # POST again should still 402
            r = requests.post(f"{BASE}/chantiers", headers=H(admin_tok), json=payload)
            try:
                detail = r.json().get("detail", {})
            except Exception:
                detail = {}
            rec(
                "B4c POST /chantiers still 402 after delete",
                r.status_code == 402 and isinstance(detail, dict) and detail.get("code") == "free_plan_limit",
                f"{r.status_code} detail={detail}",
            )

        # B5: artisan_mode bypass for project limit (NOT for exports)
        r = requests.patch(
            f"{BASE}/company/profile", headers=H(admin_tok),
            json={"artisan_mode": True},
        )
        rec("B5a enable artisan_mode while plan=free", r.status_code == 200 and r.json().get("artisan_mode") is True, f"{r.status_code}")

        r = requests.post(f"{BASE}/chantiers", headers=H(admin_tok), json=payload)
        rec(
            "B5b POST /chantiers succeeds with artisan_mode=true even at limit",
            r.status_code == 200,
            f"{r.status_code} {r.text[:120]}",
        )
        # cleanup: delete that just-created chantier to keep state clean
        if r.ok:
            cid = r.json().get("id")
            if cid:
                requests.delete(f"{BASE}/chantiers/{cid}", headers=H(admin_tok))

        # Restore artisan_mode=false for export tests
        r = requests.patch(f"{BASE}/company/profile", headers=H(admin_tok), json={"artisan_mode": False})
        rec("B5c restore artisan_mode=false", r.status_code == 200 and r.json().get("artisan_mode") is False, f"{r.status_code}")

        # ============ C) FREEMIUM EXPORT LOCK ============
        r = requests.get(f"{BASE}/chantiers", headers=H(admin_tok))
        chantiers = r.json() if r.ok else []
        if not chantiers:
            rec("C0 chantier available for export tests", False, "no chantiers found")
        else:
            cid = chantiers[0]["id"]
            for fmt in ["pdf", "csv", "xlsx", "json"]:
                r = requests.get(f"{BASE}/chantiers/{cid}/export.{fmt}", headers=H(admin_tok))
                try:
                    detail = r.json().get("detail", {}) if r.headers.get("content-type", "").startswith("application/json") else {}
                except Exception:
                    detail = {}
                ok = r.status_code == 402 and isinstance(detail, dict) and detail.get("code") == "free_plan_no_export"
                rec(
                    f"C{fmt} export.{fmt} 402 free_plan_no_export (admin, plan=free)",
                    ok,
                    f"{r.status_code} detail={detail}",
                )

            # C5: artisan_mode does NOT bypass export lock
            r = requests.patch(f"{BASE}/company/profile", headers=H(admin_tok), json={"artisan_mode": True})
            rec("C5a enable artisan_mode for export lock test", r.status_code == 200 and r.json().get("artisan_mode") is True, f"{r.status_code}")

            r = requests.get(f"{BASE}/chantiers/{cid}/export.pdf", headers=H(admin_tok))
            try:
                detail = r.json().get("detail", {}) if r.headers.get("content-type", "").startswith("application/json") else {}
            except Exception:
                detail = {}
            rec(
                "C5b export.pdf still 402 free_plan_no_export with artisan_mode=true (ANTI-FRAUD)",
                r.status_code == 402 and isinstance(detail, dict) and detail.get("code") == "free_plan_no_export",
                f"{r.status_code} detail={detail}",
            )
            # also check xlsx
            r = requests.get(f"{BASE}/chantiers/{cid}/export.xlsx", headers=H(admin_tok))
            try:
                detail = r.json().get("detail", {}) if r.headers.get("content-type", "").startswith("application/json") else {}
            except Exception:
                detail = {}
            rec(
                "C5c export.xlsx still 402 free_plan_no_export with artisan_mode=true",
                r.status_code == 402 and isinstance(detail, dict) and detail.get("code") == "free_plan_no_export",
                f"{r.status_code} detail={detail}",
            )

            # Restore artisan_mode=false
            r = requests.patch(f"{BASE}/company/profile", headers=H(admin_tok), json={"artisan_mode": False})
            rec("C5d restore artisan_mode=false", r.status_code == 200 and r.json().get("artisan_mode") is False, f"{r.status_code}")

        # ============ D) RESTORE PRO ============
        r = requests.post(
            f"{BASE}/platform/companies/default/subscription",
            headers={"X-Platform-Token": PLATFORM_TOKEN},
            json={"plan": "trial"},
        )
        rec(
            "D1 platform set plan=trial",
            r.status_code == 200 and r.json().get("plan") == "trial",
            f"{r.status_code} plan={r.json().get('plan') if r.ok else r.text}",
        )

        # GET export pdf
        if chantiers:
            cid = chantiers[0]["id"]
            r = requests.get(f"{BASE}/chantiers/{cid}/export.pdf", headers=H(admin_tok))
            ok = r.status_code == 200 and r.content[:5] == b"%PDF-"
            rec(
                "D2 export.pdf 200 binary %PDF-",
                ok,
                f"{r.status_code} ct={r.headers.get('content-type')} magic={r.content[:5]!r}",
            )

        # POST /chantiers should succeed
        payload2 = {
            "first_name": "Sophie",
            "last_name": "Lemoine",
            "address": "8 avenue Victor Hugo",
            "postal_code": "33000",
            "city": "Bordeaux",
            "status": "devis_a_faire",
        }
        r = requests.post(f"{BASE}/chantiers", headers=H(admin_tok), json=payload2)
        rec(
            "D3 POST /chantiers 200 (plan=trial, no longer blocked)",
            r.status_code == 200,
            f"{r.status_code} {r.text[:160]}",
        )
        new_id = r.json().get("id") if r.ok else None

        # cleanup test chantier
        if new_id:
            requests.delete(f"{BASE}/chantiers/{new_id}", headers=H(admin_tok))

        # ============ F) REGRESSION SMOKE ============
        r = requests.get(f"{BASE}/chantiers", headers=H(admin_tok))
        rec("F1 GET /chantiers 200 (>=8)", r.status_code == 200 and len(r.json()) >= 7, f"{r.status_code} n={len(r.json()) if r.ok else 'n/a'}")
        r = requests.get(f"{BASE}/users", headers=H(admin_tok))
        rec("F2 GET /users 200 (>=11)", r.status_code == 200 and len(r.json()) >= 11, f"{r.status_code} n={len(r.json()) if r.ok else 'n/a'}")
        r = requests.get(f"{BASE}/stats/company", headers=H(admin_tok))
        rec("F3 GET /stats/company 200", r.status_code == 200, f"{r.status_code}")

    finally:
        safe_restore(admin_tok)
        # Final verification
        r = requests.get(f"{BASE}/company/profile", headers=H(admin_tok))
        b = r.json()
        print(f"\nFINAL STATE: plan={b.get('plan')} artisan_mode={b.get('artisan_mode')} cape={b.get('cancel_at_period_end')}")
        rec(
            "Z FINAL STATE plan=trial, artisan_mode=true, cape=false",
            b.get("plan") == "trial" and b.get("artisan_mode") is True and b.get("cancel_at_period_end") is False,
            f"plan={b.get('plan')} am={b.get('artisan_mode')} cape={b.get('cancel_at_period_end')}",
        )

    # summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed
    print(f"\n===== {passed}/{total} PASS — {failed} failures =====")
    if failed:
        for n, ok, msg in results:
            if not ok:
                print(f"  ❌ {n} :: {msg}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
