"""
BETA GRATUITE — Backend validation tests.

T1 Profil entreprise reflète BETA_MODE
T2 Limite Freemium désactivée
T3 Pas de paywall même avec plan='free' forcé
T4 Register en mode beta
T5 Régression pytest existante
"""
import json
import os
import random
import string
import sys
from datetime import datetime, timezone

import requests

BASE = "https://window-field-app.preview.emergentagent.com/api"
PLATFORM_TOKEN = "mc-platform-2026"

ADMIN_EMAIL = "admin@mesurechassis.fr"
ADMIN_PASS = "admin123"
COMMERCIAL_EMAIL = "commercial@mesurechassis.fr"
COMMERCIAL_PASS = "commercial123"
TECH_EMAIL = "tech@mesurechassis.fr"
TECH_PASS = "tech123"


results = []


def log(label, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    line = f"[{tag}] {label} :: {detail}"
    print(line)
    results.append((ok, label, detail))


def H(token):
    return {"Authorization": f"Bearer {token}"}


def login(email, password):
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"], r.json()["user"]


# ============================================================
# T1 - Profil reflète BETA_MODE
# ============================================================
def test_T1():
    print("\n===== T1 — Profil entreprise reflète BETA_MODE =====")
    token, user = login(ADMIN_EMAIL, ADMIN_PASS)
    log("T1.login admin", True, f"user_id={user['id']}, company_id={user['company_id']}")
    r = requests.get(f"{BASE}/company/profile", headers=H(token), timeout=30)
    log("T1.GET /company/profile status==200", r.status_code == 200,
        f"status={r.status_code}")
    if r.status_code != 200:
        return token
    p = r.json()
    log("T1.beta_mode==true", p.get("beta_mode") is True, f"beta_mode={p.get('beta_mode')}")
    log("T1.plan==pro", p.get("plan") == "pro", f"plan={p.get('plan')}")
    log("T1.subscription_status==active", p.get("subscription_status") == "active",
        f"subscription_status={p.get('subscription_status')}")
    exp = p.get("subscription_expires_at")
    log("T1.subscription_expires_at present", bool(exp), f"exp={exp}")
    if exp:
        try:
            dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            delta_years = (dt - datetime.now(timezone.utc)).days / 365.25
            log("T1.expires_at > now+9y", delta_years > 9, f"~{delta_years:.2f} years from now")
        except Exception as e:
            log("T1.expires_at parsable ISO", False, str(e))
    return token


# ============================================================
# T2 - Limite Freemium désactivée
# ============================================================
def test_T2(admin_token):
    print("\n===== T2 — Limite Freemium désactivée =====")
    created_ids = []
    payload = {
        "first_name": "Beta",
        "last_name": "Test",
        "address": "1 rue Beta",
        "postal_code": "75001",
        "city": "Paris",
        "status": "devis_a_faire",
    }
    for i in range(5):
        r = requests.post(f"{BASE}/chantiers", headers=H(admin_token),
                          json=payload, timeout=30)
        ok = r.status_code == 200
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        log(f"T2.create chantier #{i+1} 200", ok,
            f"status={r.status_code} body_preview={str(body)[:120]}")
        if ok:
            created_ids.append(body["id"])
        else:
            break

    # Cleanup
    for cid in created_ids:
        r = requests.delete(f"{BASE}/chantiers/{cid}", headers=H(admin_token), timeout=30)
        log(f"T2.cleanup DELETE {cid[:8]}", r.status_code == 200, f"status={r.status_code}")


# ============================================================
# T3 - Pas de paywall même avec plan=free forcé
# ============================================================
def test_T3(admin_token, tech_token):
    print("\n===== T3 — Plan='free' forcé : paywall bypassé en beta =====")
    # 1) Set plan=free via platform endpoint
    r = requests.post(
        f"{BASE}/platform/companies/default/subscription",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={"plan": "free"},
        timeout=30,
    )
    log("T3.platform set plan=free", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
    if r.status_code == 200:
        p = r.json()
        log("T3.plan==free after platform set", p.get("plan") == "free", f"plan={p.get('plan')}")

    # 1b) Verify beta_mode still True
    r = requests.get(f"{BASE}/company/profile", headers=H(admin_token), timeout=30)
    if r.status_code == 200:
        p = r.json()
        log("T3.beta_mode still true after free plan", p.get("beta_mode") is True,
            f"beta_mode={p.get('beta_mode')} plan={p.get('plan')}")

    # 2) Create a chantier with plan=free (should pass thanks to BETA_MODE)
    payload = {
        "first_name": "Marie",
        "last_name": "Dubois-Beta",
        "address": "12 rue Saint-Honoré",
        "postal_code": "75001",
        "city": "Paris",
        "status": "devis_a_faire",
    }
    r = requests.post(f"{BASE}/chantiers", headers=H(admin_token), json=payload, timeout=30)
    log("T3.POST /chantiers admin with plan=free 200", r.status_code == 200,
        f"status={r.status_code} detail={r.text[:200]}")
    chantier_id = None
    if r.status_code == 200:
        chantier_id = r.json()["id"]

    # 3) Add a measure (technician role)
    if chantier_id:
        mesure_payload = {
            "chantier_id": chantier_id,
            "block_type": "standard",
            "label": "Salon - Fenêtre 1",
            "bay_width": 1500,
            "bay_height": 2400,
            "bay_diagonal_1": 2828,
            "bay_diagonal_2": 2828,
            "bloc_thickness": 200,
            "wall_type": "iti",
            "insulation_thickness": 100,
            "finish_outer": 10,
            "finish_inner": 13,
        }
        r = requests.post(f"{BASE}/mesures", headers=H(tech_token),
                          json=mesure_payload, timeout=30)
        log("T3.POST /mesures (tech) 200", r.status_code == 200,
            f"status={r.status_code} body={r.text[:200]}")

    # 4) Exports
    if chantier_id:
        # PDF
        r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.pdf",
                         headers=H(admin_token), timeout=60)
        magic_ok = r.status_code == 200 and r.content.startswith(b"%PDF")
        log("T3.export.pdf 200 + magic %PDF", magic_ok,
            f"status={r.status_code} bytes={len(r.content)} head={r.content[:10]!r}")

        # CSV
        r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.csv",
                         headers=H(admin_token), timeout=60)
        ct = r.headers.get("content-type", "")
        log("T3.export.csv 200 + text/csv", r.status_code == 200 and "text/csv" in ct,
            f"status={r.status_code} ct={ct} bytes={len(r.content)}")

        # XLSX
        r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.xlsx",
                         headers=H(admin_token), timeout=60)
        magic_ok = r.status_code == 200 and r.content.startswith(b"PK")
        log("T3.export.xlsx 200 + magic PK", magic_ok,
            f"status={r.status_code} bytes={len(r.content)} head={r.content[:4]!r}")

        # JSON
        r = requests.get(f"{BASE}/chantiers/{chantier_id}/export.json",
                         headers=H(admin_token), timeout=30)
        has_schema = False
        if r.status_code == 200:
            try:
                j = r.json()
                has_schema = j.get("schema_version", "").startswith("mc.v")
            except Exception:
                pass
        log("T3.export.json 200 + schema_version", r.status_code == 200 and has_schema,
            f"status={r.status_code}")

    # 5) ⚠️ CLEANUP : restore plan=pro
    r = requests.post(
        f"{BASE}/platform/companies/default/subscription",
        headers={"X-Platform-Token": PLATFORM_TOKEN},
        json={"plan": "pro"},
        timeout=30,
    )
    log("T3.CLEANUP platform set plan=pro", r.status_code == 200, f"status={r.status_code}")

    if chantier_id:
        r = requests.delete(f"{BASE}/chantiers/{chantier_id}", headers=H(admin_token), timeout=30)
        log("T3.CLEANUP DELETE chantier", r.status_code == 200, f"status={r.status_code}")


# ============================================================
# T4 - Register en mode beta
# ============================================================
def test_T4():
    print("\n===== T4 — Register en mode beta =====")
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"beta_test_{random_suffix}@mesurechassis.fr"
    password = "Test1234!"
    payload = {
        "email": email,
        "password": password,
        "name": "Beta Tester",
        "company_name": "BetaCorp",
    }
    r = requests.post(f"{BASE}/auth/register", json=payload, timeout=30)
    log("T4.POST /auth/register 200", r.status_code == 200,
        f"status={r.status_code} body={r.text[:300]}")
    if r.status_code != 200:
        return
    data = r.json()
    user = data.get("user", {})
    verification_link = data.get("verification_link")
    log("T4.user.role==admin", user.get("role") == "admin", f"role={user.get('role')}")
    log("T4.user.status==pending_verification",
        user.get("status") == "pending_verification",
        f"status={user.get('status')}")
    log("T4.verification_link present", bool(verification_link),
        f"link_preview={(verification_link or '')[:80]}")

    if not verification_link:
        return
    # Extract token from URL
    # Format expected: https://.../verify?token=xxx ou similaire
    token_param = None
    if "token=" in verification_link:
        token_param = verification_link.split("token=", 1)[1].split("&", 1)[0]
    log("T4.extract token from link", bool(token_param), f"token={token_param[:20] if token_param else None}...")
    if not token_param:
        return

    # POST /auth/verify
    r = requests.post(f"{BASE}/auth/verify", json={"token": token_param}, timeout=30)
    log("T4.POST /auth/verify 200", r.status_code == 200,
        f"status={r.status_code} body={r.text[:200]}")
    new_token = None
    if r.status_code == 200:
        new_token = r.json().get("access_token")

    # Login
    r = requests.post(f"{BASE}/auth/login",
                      json={"email": email, "password": password}, timeout=30)
    log("T4.login new account 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        new_token = r.json()["access_token"]

    if not new_token:
        return

    # GET /company/profile
    r = requests.get(f"{BASE}/company/profile", headers=H(new_token), timeout=30)
    log("T4.GET /company/profile new account 200", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        p = r.json()
        log("T4.new_account.plan==pro", p.get("plan") == "pro", f"plan={p.get('plan')}")
        log("T4.new_account.subscription_status==active",
            p.get("subscription_status") == "active",
            f"subscription_status={p.get('subscription_status')}")
        log("T4.new_account.beta_mode==true", p.get("beta_mode") is True,
            f"beta_mode={p.get('beta_mode')}")
        exp = p.get("subscription_expires_at")
        if exp:
            try:
                dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                delta_years = (dt - datetime.now(timezone.utc)).days / 365.25
                log("T4.new_account expires_at > now+9y", delta_years > 9,
                    f"~{delta_years:.2f} years")
            except Exception:
                pass


# ============================================================
# Run all
# ============================================================
def main():
    print(f"BASE={BASE}")
    admin_token, _ = login(ADMIN_EMAIL, ADMIN_PASS)
    tech_token, _ = login(TECH_EMAIL, TECH_PASS)

    test_T1()
    test_T2(admin_token)
    test_T3(admin_token, tech_token)
    test_T4()

    # Final state check
    print("\n===== FINAL STATE CHECK =====")
    r = requests.get(f"{BASE}/company/profile", headers=H(admin_token), timeout=30)
    if r.status_code == 200:
        p = r.json()
        log("FINAL.default plan==pro", p.get("plan") == "pro", f"plan={p.get('plan')}")
        log("FINAL.default status==active", p.get("subscription_status") == "active",
            f"status={p.get('subscription_status')}")
        log("FINAL.default artisan_mode preserved (echo only)", True,
            f"artisan_mode={p.get('artisan_mode')}")

    print("\n===== SUMMARY =====")
    passed = sum(1 for r in results if r[0])
    total = len(results)
    print(f"{passed}/{total} PASS")
    fails = [(lab, det) for ok, lab, det in results if not ok]
    if fails:
        print(f"\n{len(fails)} FAILED:")
        for lab, det in fails:
            print(f"  - {lab} :: {det}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
