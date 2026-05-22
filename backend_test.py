"""MesureEscalier — Backend tests for Iteration 4 features.

Covers:
  A. Paywall trial 90 days (admin@demo.fr active, expired@demo.fr locked)
  B. Company logo upload + injection in PDF
  C. Project photos CRUD with 10-per-project limit and ACL
  D. Non-regression: login, projects CRUD, measurement preview/validate,
     PDF/DXF exports, /api/stats.
"""
from __future__ import annotations

import sys
from typing import Dict, Optional, Tuple

import requests

BASE = "https://stair-pro.preview.emergentagent.com/api"

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)
TINY_PNG_DATA_URI = "data:image/png;base64," + TINY_PNG_B64

ACCOUNTS = {
    "admin":   {"email": "admin@demo.fr",             "password": "Demo1234!"},
    "solo":    {"email": "marc@mesureescalier.com",   "password": "Demo1234!"},
    "tech":    {"email": "sophie@mesureescaliee.com", "password": "Demo1234!"},
    "expired": {"email": "expired@demo.fr",           "password": "Demo1234!"},
}

results = []


def log(status: str, name: str, detail: str = ""):
    icon = {"PASS": "OK ", "FAIL": "XX ", "INFO": "-- "}.get(status, "?? ")
    print(f"{icon}[{status}] {name}{' :: ' + detail if detail else ''}")
    results.append((status, name, detail))


def headers(token: Optional[str] = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def login(label: str) -> Tuple[Optional[str], Optional[dict]]:
    r = requests.post(f"{BASE}/auth/login", json=ACCOUNTS[label], timeout=30)
    if r.status_code != 200:
        log("FAIL", f"Login {label}", f"HTTP {r.status_code}: {r.text[:200]}")
        return None, None
    data = r.json()
    return data["token"], data["user"]


def test_paywall():
    print("\n=== A. PAYWALL ===")

    token_exp, user_exp = login("expired")
    if not token_exp:
        return None, None
    if (user_exp.get("is_locked") is True and user_exp.get("trial_days_remaining") == 0
            and user_exp.get("is_trial_active") is False):
        log("PASS", "Login expired -> is_locked=true, days=0, is_trial_active=false")
    else:
        log("FAIL", "Login expired",
            f"is_locked={user_exp.get('is_locked')} "
            f"days={user_exp.get('trial_days_remaining')} "
            f"is_trial_active={user_exp.get('is_trial_active')}")

    token_adm, user_adm = login("admin")
    if not token_adm:
        return None, None
    if user_adm.get("is_locked") is False and (user_adm.get("trial_days_remaining") or 0) > 0:
        log("PASS", "Login admin@demo.fr -> active",
            f"days_remaining={user_adm.get('trial_days_remaining')}")
    else:
        log("FAIL", "Login admin@demo.fr",
            f"is_locked={user_adm.get('is_locked')} "
            f"days={user_adm.get('trial_days_remaining')}")
    if user_adm.get("trial_days_remaining") != 90:
        log("INFO", "admin days_remaining != 90",
            f"got {user_adm.get('trial_days_remaining')}")

    # With expired token
    r = requests.get(f"{BASE}/auth/me", headers=headers(token_exp), timeout=30)
    if r.status_code == 200:
        log("PASS", "GET /auth/me (expired) -> 200")
    else:
        log("FAIL", "GET /auth/me (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.put(f"{BASE}/auth/me", headers=headers(token_exp),
                     json={"full_name": "Patrick Bloqué (test)"}, timeout=30)
    if r.status_code == 200:
        log("PASS", "PUT /auth/me (expired) -> 200")
    else:
        log("FAIL", "PUT /auth/me (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/projects", headers=headers(token_exp), timeout=30)
    if r.status_code == 402:
        log("PASS", "GET /projects (expired) -> 402")
    else:
        log("FAIL", "GET /projects (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.post(f"{BASE}/projects", headers=headers(token_exp),
                      json={"client_nom": "X", "address": "Y"}, timeout=30)
    if r.status_code == 402:
        log("PASS", "POST /projects (expired) -> 402")
    else:
        log("FAIL", "POST /projects (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/stats", headers=headers(token_exp), timeout=30)
    if r.status_code == 402:
        log("PASS", "GET /stats (expired) -> 402")
    else:
        log("FAIL", "GET /stats (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    payload = {
        "material": "bois", "hauteur_brute": 2700, "epaisseur_dalle": 200,
        "tremie_longueur": 2400, "tremie_largeur": 900, "reculement_max": 3500,
        "remarques": "",
    }
    r = requests.post(f"{BASE}/projects/does-not-exist/measurement/preview",
                      headers=headers(token_exp), json=payload, timeout=30)
    if r.status_code == 402:
        log("PASS", "POST /projects/<any>/measurement/preview (expired) -> 402")
    else:
        log("FAIL", "preview (expired)", f"HTTP {r.status_code}: {r.text[:200]}")

    # Active admin: same routes must NEVER be 402
    r = requests.get(f"{BASE}/projects", headers=headers(token_adm), timeout=30)
    if r.status_code == 200:
        log("PASS", "GET /projects (admin active) -> 200")
    else:
        log("FAIL", "GET /projects (admin active)", f"HTTP {r.status_code}: {r.text[:200]}")
    r = requests.get(f"{BASE}/stats", headers=headers(token_adm), timeout=30)
    if r.status_code == 200:
        log("PASS", "GET /stats (admin active) -> 200")
    else:
        log("FAIL", "GET /stats (admin active)", f"HTTP {r.status_code}: {r.text[:200]}")
    r = requests.post(f"{BASE}/projects/does-not-exist/measurement/preview",
                      headers=headers(token_adm), json=payload, timeout=30)
    if r.status_code in (200, 404):
        log("PASS", f"preview (admin active) -> {r.status_code} (never 402)")
    else:
        log("FAIL", "preview (admin active)", f"HTTP {r.status_code}: {r.text[:200]}")

    return token_adm, token_exp


def test_logo(token_adm: str):
    print("\n=== B. LOGO ENTREPRISE ===")

    r = requests.put(f"{BASE}/auth/me", headers=headers(token_adm),
                     json={"company_logo_base64": TINY_PNG_DATA_URI}, timeout=30)
    if r.status_code == 200 and r.json().get("company_logo_base64"):
        log("PASS", "PUT /auth/me set company_logo_base64 -> 200 with logo")
    else:
        log("FAIL", "PUT /auth/me set logo", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/auth/me", headers=headers(token_adm), timeout=30)
    if r.status_code == 200 and r.json().get("company_logo_base64"):
        log("PASS", "GET /auth/me returns company_logo_base64")
    else:
        log("FAIL", "GET /auth/me (logo)", f"HTTP {r.status_code}: {r.text[:200]}")

    pcreate = {
        "client_nom": "Durand", "client_prenom": "Marie",
        "address": "12 rue des Lilas", "postal_code": "75011", "city": "Paris",
        "phone": "0123456789", "notes": "Test logo PDF",
    }
    r = requests.post(f"{BASE}/projects", headers=headers(token_adm), json=pcreate, timeout=30)
    if r.status_code != 200:
        log("FAIL", "Create project (admin) for PDF test",
            f"HTTP {r.status_code}: {r.text[:200]}")
        return
    pid = r.json()["id"]
    log("PASS", "Create project (admin) for PDF test", f"pid={pid}")

    mpayload = {
        "material": "bois", "hauteur_brute": 2700, "epaisseur_dalle": 200,
        "tremie_longueur": 2400, "tremie_largeur": 900, "reculement_max": 3500,
        "remarques": "Test logo",
    }
    r = requests.post(f"{BASE}/projects/{pid}/measurement",
                      headers=headers(token_adm), json=mpayload, timeout=30)
    if r.status_code == 200:
        log("PASS", "Save measurement (admin) -> 200")
    elif r.status_code == 403:
        # admin without solo_mode cannot save measurement -> use technician
        log("INFO", "Admin (non-solo) cannot save measurement (403). "
                   "Assigning technician for PDF flow.")
        tok_tech, _ = login("tech")
        if tok_tech:
            r2 = requests.get(f"{BASE}/users", headers=headers(token_adm), timeout=30)
            sophie_id = None
            if r2.status_code == 200:
                for u in r2.json():
                    if u["email"] == "sophie@mesureescaliee.com":
                        sophie_id = u["id"]
                        break
            if sophie_id:
                requests.post(f"{BASE}/projects/{pid}/assign", headers=headers(token_adm),
                              json={"technicien_id": sophie_id}, timeout=30)
            r3 = requests.post(f"{BASE}/projects/{pid}/measurement",
                               headers=headers(tok_tech), json=mpayload, timeout=30)
            if r3.status_code == 200:
                log("PASS", "Save measurement (via technician) -> 200")
            else:
                log("FAIL", "Save measurement (via technician)",
                    f"HTTP {r3.status_code}: {r3.text[:200]}")
    else:
        log("FAIL", "Save measurement", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/projects/{pid}/export/pdf",
                     headers=headers(token_adm), timeout=60)
    if r.status_code == 200 and r.content[:5] == b"%PDF-":
        log("PASS", "GET /projects/{pid}/export/pdf -> %PDF- binary",
            f"size={len(r.content)} bytes")
    else:
        log("FAIL", "Export PDF",
            f"HTTP {r.status_code}, head={r.content[:32]!r}")

    r = requests.put(f"{BASE}/auth/me", headers=headers(token_adm),
                     json={"company_logo_base64": ""}, timeout=30)
    if r.status_code == 200:
        val = r.json().get("company_logo_base64")
        if val in (None, ""):
            log("PASS", 'PUT /auth/me {"company_logo_base64": ""} -> cleared')
        else:
            log("FAIL", "Clear logo (PUT)",
                f"still set: {str(val)[:60]!r}")
    else:
        log("FAIL", "Clear logo (PUT)", f"HTTP {r.status_code}: {r.text[:200]}")
    r = requests.get(f"{BASE}/auth/me", headers=headers(token_adm), timeout=30)
    if r.status_code == 200 and not r.json().get("company_logo_base64"):
        log("PASS", "GET /auth/me after clear -> logo empty/null")
    else:
        log("FAIL", "GET /auth/me after clear",
            f"logo={(r.json() or {}).get('company_logo_base64')!r}")

    requests.delete(f"{BASE}/projects/{pid}", headers=headers(token_adm), timeout=30)


def test_photos():
    print("\n=== C. PHOTOS DE CHANTIER ===")
    tok_solo, _ = login("solo")
    if not tok_solo:
        return
    pcreate = {
        "client_nom": "Lefebvre", "client_prenom": "Antoine",
        "address": "8 chemin du Moulin", "postal_code": "44000", "city": "Nantes",
        "phone": "0298765432", "notes": "Test photos",
    }
    r = requests.post(f"{BASE}/projects", headers=headers(tok_solo), json=pcreate, timeout=30)
    if r.status_code != 200:
        log("FAIL", "Create project (solo) for photos test",
            f"HTTP {r.status_code}: {r.text[:200]}")
        return
    pid = r.json()["id"]
    log("PASS", "Create project (solo) for photos test", f"pid={pid}")

    r = requests.get(f"{BASE}/projects/{pid}/photos", headers=headers(tok_solo), timeout=30)
    if r.status_code == 200 and r.json() == []:
        log("PASS", "GET /photos -> []")
    else:
        log("FAIL", "GET /photos initial", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.post(f"{BASE}/projects/{pid}/photos", headers=headers(tok_solo),
                      json={"base64": TINY_PNG_B64, "caption": "Test trémie"}, timeout=30)
    if (r.status_code == 200 and r.json().get("id") and r.json().get("base64")
            and r.json().get("caption") == "Test trémie" and r.json().get("created_at")):
        log("PASS", "POST first photo -> 200 with id, base64, caption, created_at")
        first_id = r.json()["id"]
    else:
        log("FAIL", "POST first photo", f"HTTP {r.status_code}: {r.text[:300]}")
        return

    for i in range(9):
        rr = requests.post(f"{BASE}/projects/{pid}/photos", headers=headers(tok_solo),
                           json={"base64": TINY_PNG_B64, "caption": f"Photo {i+2}"},
                           timeout=30)
        if rr.status_code != 200:
            log("FAIL", f"POST photo #{i+2}", f"HTTP {rr.status_code}: {rr.text[:200]}")
            return

    r11 = requests.post(f"{BASE}/projects/{pid}/photos", headers=headers(tok_solo),
                       json={"base64": TINY_PNG_B64, "caption": "Trop"}, timeout=30)
    detail = ""
    try:
        detail = r11.json().get("detail") or ""
    except Exception:
        pass
    if r11.status_code == 400 and "Limite atteinte" in detail:
        log("PASS", "11th photo -> 400 'Limite atteinte'")
    else:
        log("FAIL", "11th photo", f"HTTP {r11.status_code}: {r11.text[:200]}")

    r = requests.patch(f"{BASE}/projects/{pid}/photos/{first_id}",
                       headers=headers(tok_solo),
                       json={"caption": "Mise à jour"}, timeout=30)
    if r.status_code == 200:
        log("PASS", "PATCH photo caption -> 200")
    else:
        log("FAIL", "PATCH photo", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/projects", headers=headers(tok_solo), timeout=30)
    if r.status_code == 200:
        proj = next((p for p in r.json() if p["id"] == pid), None)
        if proj is not None and "photos" not in proj:
            log("PASS", "GET /projects list excludes photos field")
        else:
            log("FAIL", "GET /projects list excludes photos",
                f"proj keys: {list(proj.keys()) if proj else None}")
    else:
        log("FAIL", "GET /projects list", f"HTTP {r.status_code}")

    r = requests.get(f"{BASE}/projects/{pid}", headers=headers(tok_solo), timeout=30)
    body = r.json() if r.status_code == 200 else {}
    photos_arr = body.get("photos")
    if r.status_code == 200 and isinstance(photos_arr, list) and len(photos_arr) == 10:
        log("PASS", "GET /projects/{pid} detail includes photos array (10 items)")
    else:
        log("FAIL", "GET /projects/{pid} detail with photos",
            f"HTTP {r.status_code}, photos_type={type(photos_arr)}, "
            f"len={len(photos_arr) if isinstance(photos_arr, list) else 'n/a'}")

    r = requests.delete(f"{BASE}/projects/{pid}/photos/{first_id}",
                        headers=headers(tok_solo), timeout=30)
    if r.status_code == 200:
        log("PASS", "DELETE photo -> 200")
    else:
        log("FAIL", "DELETE photo", f"HTTP {r.status_code}: {r.text[:200]}")

    tok_tech, _ = login("tech")
    if tok_tech:
        r = requests.post(f"{BASE}/projects/{pid}/photos", headers=headers(tok_tech),
                          json={"base64": TINY_PNG_B64, "caption": "hack"}, timeout=30)
        if r.status_code == 404:
            log("PASS", "Sophie POST /photos on marc's project -> 404 (not visible)")
        else:
            log("FAIL", "Sophie POST /photos (not assigned)",
                f"HTTP {r.status_code}: {r.text[:200]}")

    requests.delete(f"{BASE}/projects/{pid}", headers=headers(tok_solo), timeout=30)


def test_regression():
    print("\n=== D. NON-REGRESSION ===")
    for label in ("admin", "solo", "tech"):
        tok, u = login(label)
        if tok and u and not u.get("is_locked"):
            log("PASS", f"Login {label} active -> ok",
                f"days={u.get('trial_days_remaining')}")
        else:
            log("FAIL", f"Login {label}", f"user={u}")

    tok_solo, _ = login("solo")
    pcreate = {
        "client_nom": "Bernard", "client_prenom": "Julie",
        "address": "3 place de la République", "postal_code": "69001",
        "city": "Lyon", "phone": "0478451212", "notes": "Régression",
    }
    r = requests.post(f"{BASE}/projects", headers=headers(tok_solo), json=pcreate, timeout=30)
    if r.status_code != 200:
        log("FAIL", "Create project (solo regression)",
            f"HTTP {r.status_code}: {r.text[:200]}")
        return
    pid = r.json()["id"]
    log("PASS", "Create project (solo regression)")

    mpayload = {
        "material": "bois", "hauteur_brute": 2700, "epaisseur_dalle": 200,
        "tremie_longueur": 2400, "tremie_largeur": 900, "reculement_max": 3500,
        "remarques": "",
    }
    r = requests.post(f"{BASE}/projects/{pid}/measurement/preview",
                      headers=headers(tok_solo), json=mpayload, timeout=30)
    if r.status_code == 200 and "n_steps" in r.json():
        log("PASS", "Measurement preview (solo)",
            f"n_steps={r.json().get('n_steps')}")
    else:
        log("FAIL", "Measurement preview", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.post(f"{BASE}/projects/{pid}/measurement",
                      headers=headers(tok_solo), json=mpayload, timeout=30)
    if r.status_code == 200:
        log("PASS", "Save measurement (solo)")
    else:
        log("FAIL", "Save measurement", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.post(f"{BASE}/projects/{pid}/measurement/validate",
                      headers=headers(tok_solo), timeout=30)
    if r.status_code == 200:
        log("PASS", "Validate measurement (solo)")
    else:
        log("FAIL", "Validate measurement", f"HTTP {r.status_code}: {r.text[:200]}")

    r = requests.get(f"{BASE}/projects/{pid}/export/pdf",
                     headers=headers(tok_solo), timeout=60)
    if r.status_code == 200 and r.content[:5] == b"%PDF-":
        log("PASS", "Export PDF (solo)", f"size={len(r.content)}")
    else:
        log("FAIL", "Export PDF (solo)",
            f"HTTP {r.status_code}, head={r.content[:32]!r}")

    r = requests.get(f"{BASE}/projects/{pid}/export/dxf",
                     headers=headers(tok_solo), timeout=30)
    if r.status_code == 200 and (b"SECTION" in r.content or r.content.startswith(b"0\n")):
        log("PASS", "Export DXF (solo)", f"size={len(r.content)}")
    else:
        log("FAIL", "Export DXF (solo)",
            f"HTTP {r.status_code}, head={r.content[:40]!r}")

    tok_adm, _ = login("admin")
    r = requests.get(f"{BASE}/stats", headers=headers(tok_adm), timeout=30)
    if r.status_code == 200 and "total_projects" in r.json():
        log("PASS", "GET /stats (admin)", f"total={r.json().get('total_projects')}")
    else:
        log("FAIL", "GET /stats (admin)", f"HTTP {r.status_code}: {r.text[:200]}")

    requests.delete(f"{BASE}/projects/{pid}", headers=headers(tok_solo), timeout=30)


def main():
    print(f"BASE={BASE}")
    token_adm, _ = test_paywall()
    if token_adm:
        test_logo(token_adm)
    test_photos()
    test_regression()

    print("\n=== SUMMARY ===")
    passes = sum(1 for s, *_ in results if s == "PASS")
    fails = sum(1 for s, *_ in results if s == "FAIL")
    infos = sum(1 for s, *_ in results if s == "INFO")
    print(f"PASS: {passes}  FAIL: {fails}  INFO: {infos}")
    if fails:
        print("\nFailed:")
        for s, n, d in results:
            if s == "FAIL":
                print(f"  - {n} :: {d}")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
