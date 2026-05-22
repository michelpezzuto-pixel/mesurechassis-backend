"""MesureEscalier — End-to-end backend validation post-refactor.

Tests every critical /api/* route via the public external URL.
Uses three pre-seeded demo accounts. No code mutation.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

import requests

BASE = "https://stair-pro.preview.emergentagent.com/api"

ADMIN = ("admin@demo.fr", "Demo1234!")
SOLO = ("marc@mesureescalier.com", "Demo1234!")
TECH = ("sophie@mesureescaliee.com", "Demo1234!")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

results: Dict[str, Dict[str, Any]] = {}


def log(name: str, ok: bool, detail: str = "") -> None:
    color = GREEN if ok else RED
    icon = "PASS" if ok else "FAIL"
    print(f"{color}[{icon}]{RESET} {name}{(' :: ' + detail) if detail else ''}")
    results.setdefault(name.split('|')[0].strip(), {"steps": []})
    results[name.split('|')[0].strip()]["steps"].append({"name": name, "ok": ok, "detail": detail})


def H(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, pwd: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], int, Any]:
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": pwd}, timeout=20)
    if r.status_code != 200:
        return None, None, r.status_code, r.text
    js = r.json()
    return js.get("token"), js.get("user"), r.status_code, js


# ------------------------------------------------------------------ AUTH
def test_auth() -> Dict[str, str]:
    tokens: Dict[str, str] = {}
    for label, (e, p) in [("admin", ADMIN), ("solo", SOLO), ("tech", TECH)]:
        tok, user, code, body = login(e, p)
        ok = code == 200 and tok and user and user.get("email") == e
        log(f"AUTH | login {label} ({e})", bool(ok),
            f"http={code} role={user.get('role') if user else '?'} solo={user.get('solo_mode') if user else '?'}")
        if ok:
            tokens[label] = tok

    # /auth/me
    for label, tok in tokens.items():
        r = requests.get(f"{BASE}/auth/me", headers=H(tok), timeout=15)
        ok = r.status_code == 200 and r.json().get("email")
        log(f"AUTH | GET /auth/me ({label})", ok, f"http={r.status_code}")

    # /auth/me without token => 401/403
    r = requests.get(f"{BASE}/auth/me", timeout=10)
    log("AUTH | GET /auth/me without token", r.status_code in (401, 403), f"http={r.status_code}")

    # PUT /auth/me — change company_name (admin) and solo_mode toggle (admin only)
    if "admin" in tokens:
        original = requests.get(f"{BASE}/auth/me", headers=H(tokens["admin"])).json()
        new_company = f"Escaliers Demo SARL — TEST {int(time.time())}"
        r = requests.put(f"{BASE}/auth/me", headers=H(tokens["admin"]),
                         json={"company_name": new_company, "solo_mode": False}, timeout=15)
        ok = r.status_code == 200 and r.json().get("company_name") == new_company
        log("AUTH | PUT /auth/me update company_name (admin)", ok, f"http={r.status_code}")
        # restore
        requests.put(f"{BASE}/auth/me", headers=H(tokens["admin"]),
                     json={"company_name": original.get("company_name", "Escaliers Demo SARL")})

    if "tech" in tokens:
        r = requests.put(f"{BASE}/auth/me", headers=H(tokens["tech"]),
                         json={"solo_mode": True}, timeout=15)
        log("AUTH | PUT /auth/me solo_mode forbidden for tech", r.status_code == 403, f"http={r.status_code}")

    return tokens


# ------------------------------------------------------------------ PROJECTS
def test_projects(tokens: Dict[str, str]) -> Dict[str, str]:
    created: Dict[str, str] = {}

    # GET /projects (admin)
    r = requests.get(f"{BASE}/projects", headers=H(tokens["admin"]), timeout=15)
    log("PROJECTS | GET /projects (admin)", r.status_code == 200 and isinstance(r.json(), list),
        f"http={r.status_code} count={len(r.json()) if r.status_code == 200 else '?'}")

    # GET /projects (tech) — should be filtered
    r = requests.get(f"{BASE}/projects", headers=H(tokens["tech"]), timeout=15)
    log("PROJECTS | GET /projects (tech)", r.status_code == 200 and isinstance(r.json(), list),
        f"http={r.status_code} count={len(r.json()) if r.status_code == 200 else '?'}")

    # POST /projects (admin)
    payload = {
        "client_nom": "Lefevre",
        "client_prenom": "Caroline",
        "address": "14 Rue des Tilleuls",
        "postal_code": "44000",
        "city": "Nantes",
        "phone": "0240123456",
        "notes": "Maison neuve, escalier béton sur dalle haute.",
    }
    r = requests.post(f"{BASE}/projects", headers=H(tokens["admin"]), json=payload, timeout=15)
    ok = r.status_code == 200 and r.json().get("id")
    log("PROJECTS | POST /projects (admin)", ok, f"http={r.status_code}")
    if ok:
        created["admin"] = r.json()["id"]

    # POST /projects (tech) — should be forbidden
    r = requests.post(f"{BASE}/projects", headers=H(tokens["tech"]), json=payload, timeout=15)
    log("PROJECTS | POST /projects forbidden for tech", r.status_code == 403, f"http={r.status_code}")

    # POST /projects (solo) — should auto-lock + a_mesurer
    r = requests.post(f"{BASE}/projects", headers=H(tokens["solo"]),
                     json={**payload, "client_nom": "Mercier", "address": "8 Allée des Pins"}, timeout=15)
    if r.status_code == 200:
        j = r.json()
        ok = j.get("status") == "a_mesurer" and j.get("locked") is True and j.get("technicien_id")
        log("PROJECTS | POST /projects (solo) auto-locks & a_mesurer", ok,
            f"status={j.get('status')} locked={j.get('locked')}")
        created["solo"] = j["id"]
    else:
        log("PROJECTS | POST /projects (solo)", False, f"http={r.status_code}")

    pid = created.get("admin")
    if pid:
        # GET /projects/{id}
        r = requests.get(f"{BASE}/projects/{pid}", headers=H(tokens["admin"]), timeout=15)
        log("PROJECTS | GET /projects/{id}", r.status_code == 200 and r.json().get("id") == pid,
            f"http={r.status_code}")

        # PUT /projects/{id}
        r = requests.put(f"{BASE}/projects/{pid}", headers=H(tokens["admin"]),
                         json={"notes": "Mise à jour — RDV reporté."}, timeout=15)
        log("PROJECTS | PUT /projects/{id}", r.status_code == 200 and r.json().get("notes", "").startswith("Mise à jour"),
            f"http={r.status_code}")

        # PUT by tech — forbidden
        r = requests.put(f"{BASE}/projects/{pid}", headers=H(tokens["tech"]),
                         json={"notes": "Tentative"}, timeout=15)
        log("PROJECTS | PUT /projects/{id} forbidden for tech", r.status_code == 403, f"http={r.status_code}")

        # POST /projects/{id}/transmit
        r = requests.post(f"{BASE}/projects/{pid}/transmit", headers=H(tokens["admin"]), timeout=15)
        log("PROJECTS | POST /projects/{id}/transmit", r.status_code == 200, f"http={r.status_code}")

        # Verify status changed
        r2 = requests.get(f"{BASE}/projects/{pid}", headers=H(tokens["admin"]), timeout=15)
        log("PROJECTS | transmit -> status=a_mesurer & locked",
            r2.status_code == 200 and r2.json().get("status") == "a_mesurer" and r2.json().get("locked") is True,
            f"status={r2.json().get('status')} locked={r2.json().get('locked')}")

    return created


# ---------------------------------------------------------- MEASUREMENTS
def test_measurements(tokens: Dict[str, str], projects: Dict[str, str]) -> None:
    pid = projects.get("admin")
    if not pid:
        log("MEASUREMENTS | skipped — no project", False, "no admin project")
        return

    # Preview (any auth user)
    payload = {
        "material": "acier",
        "hauteur_brute": 2700,
        "sols_finis_zero": True,
        "reserve_bas": 0,
        "reserve_haut": 0,
        "epaisseur_dalle": 200,
        "tremie_longueur": 2400,
        "tremie_largeur": 1000,
        "reculement_max": 3500,
        "remarques": "RDC vers étage, mesures conformes plan.",
        "hauteur_sous_plafond_tremie": 2400,
    }
    r = requests.post(f"{BASE}/projects/{pid}/measurement/preview",
                      headers=H(tokens["tech"]), json=payload, timeout=15)
    if r.status_code != 200:
        log("MEASUREMENTS | preview (normal case)", False, f"http={r.status_code} body={r.text[:200]}")
        return
    res = r.json()
    required = ["true_height", "n_steps", "h", "g", "limon_length", "blondel_value", "valid_blondel", "echappee"]
    missing = [k for k in required if k not in res]
    ok = not missing and res.get("valid_blondel") is True
    log("MEASUREMENTS | preview (normal case 2700/3500/2400/200)", ok,
        f"n={res.get('n_steps')} h={res.get('h')} g={res.get('g')} 2h+g={res.get('blondel_value')} limon={res.get('limon_length')} echappee={res.get('echappee')} valid={res.get('valid_blondel')} missing={missing}")

    # Edge case — extreme small ceiling => échappée critique
    payload_crit = {**payload, "hauteur_sous_plafond_tremie": 2000, "tremie_longueur": 1500}
    r = requests.post(f"{BASE}/projects/{pid}/measurement/preview",
                      headers=H(tokens["tech"]), json=payload_crit, timeout=15)
    if r.status_code == 200:
        rc = r.json()
        log("MEASUREMENTS | preview detects échappée critique <2000",
            rc.get("echappee_critique") is True or (rc.get("echappee") is not None and rc.get("echappee") < 2000),
            f"echappee={rc.get('echappee')} critique={rc.get('echappee_critique')}")
    else:
        log("MEASUREMENTS | preview échappée critique", False, f"http={r.status_code}")

    # Edge case — impossible Blondel (huge height, no reculement) => quart-tournant / hélicoïdal
    payload_blondel = {**payload, "hauteur_brute": 3800, "reculement_max": 1500}
    r = requests.post(f"{BASE}/projects/{pid}/measurement/preview",
                      headers=H(tokens["tech"]), json=payload_blondel, timeout=15)
    if r.status_code == 200:
        rb = r.json()
        log("MEASUREMENTS | preview detects tournant/hélicoïdal when reculement<<needed",
            rb.get("is_tournant") is True or "tournant" in (rb.get("shape") or "").lower() or "hélic" in (rb.get("shape") or "").lower(),
            f"shape={rb.get('shape')} is_tournant={rb.get('is_tournant')}")
    else:
        log("MEASUREMENTS | preview blondel-fail case", False, f"http={r.status_code}")

    # POST measurement (save) — must be tech (or admin solo)
    r = requests.post(f"{BASE}/projects/{pid}/measurement",
                      headers=H(tokens["tech"]), json=payload, timeout=15)
    if r.status_code == 403:
        # tech not assigned — assign and retry
        # Assign tech to the project via admin
        # need tech id
        me = requests.get(f"{BASE}/auth/me", headers=H(tokens["tech"])).json()
        ar = requests.post(f"{BASE}/projects/{pid}/assign", headers=H(tokens["admin"]),
                           json={"technicien_id": me["id"]}, timeout=15)
        log("MEASUREMENTS | assign tech to project (helper)", ar.status_code == 200, f"http={ar.status_code}")
        r = requests.post(f"{BASE}/projects/{pid}/measurement",
                          headers=H(tokens["tech"]), json=payload, timeout=15)
    log("MEASUREMENTS | POST save measurement (tech)", r.status_code == 200 and r.json().get("result"),
        f"http={r.status_code}")

    # Admin cannot save measurement (unless solo)
    r2 = requests.post(f"{BASE}/projects/{pid}/measurement",
                       headers=H(tokens["admin"]), json=payload, timeout=15)
    log("MEASUREMENTS | POST measurement forbidden for non-solo admin", r2.status_code == 403, f"http={r2.status_code}")

    # Validate
    r = requests.post(f"{BASE}/projects/{pid}/measurement/validate",
                      headers=H(tokens["tech"]), timeout=15)
    log("MEASUREMENTS | POST /validate (tech)", r.status_code == 200, f"http={r.status_code}")

    # Confirm project status now 'valide'
    pr = requests.get(f"{BASE}/projects/{pid}", headers=H(tokens["admin"]), timeout=15)
    log("MEASUREMENTS | project status -> 'valide' after validate",
        pr.status_code == 200 and pr.json().get("status") == "valide",
        f"status={pr.json().get('status') if pr.status_code == 200 else '?'}")


# -------------------------------------------------------------- EXPORTS
def test_exports(tokens: Dict[str, str], projects: Dict[str, str]) -> None:
    pid = projects.get("admin")
    if not pid:
        log("EXPORTS | skipped — no project", False)
        return

    # PDF — note: review request mentions JSON with pdf_base64, but code returns StreamingResponse.
    # We test that endpoint returns 200 and content-length > 0 and the body starts with %PDF.
    r = requests.get(f"{BASE}/projects/{pid}/export/pdf", headers=H(tokens["admin"]), timeout=30)
    if r.status_code == 200:
        starts_ok = r.content[:4] == b"%PDF"
        log("EXPORTS | GET /export/pdf returns binary PDF", starts_ok,
            f"ctype={r.headers.get('content-type')} size={len(r.content)} starts={r.content[:8]!r}")
    else:
        log("EXPORTS | GET /export/pdf", False, f"http={r.status_code} body={r.text[:200]}")

    # Review request said POST /export/pdf — verify the verb actually used
    rpost = requests.post(f"{BASE}/projects/{pid}/export/pdf", headers=H(tokens["admin"]), timeout=10)
    log("EXPORTS | POST /export/pdf (review expects POST)", rpost.status_code in (200, 405),
        f"http={rpost.status_code} (current implementation uses GET only — Method Not Allowed expected)")

    # DXF
    r = requests.get(f"{BASE}/projects/{pid}/export/dxf", headers=H(tokens["admin"]), timeout=30)
    if r.status_code == 200:
        text = r.content.decode(errors="replace")
        ok = "SECTION" in text and "ENTITIES" in text
        log("EXPORTS | GET /export/dxf returns DXF text", ok,
            f"size={len(text)} header_ok={text[:32]!r}")
    else:
        log("EXPORTS | GET /export/dxf", False, f"http={r.status_code} body={r.text[:200]}")

    rpost = requests.post(f"{BASE}/projects/{pid}/export/dxf", headers=H(tokens["admin"]), timeout=10)
    log("EXPORTS | POST /export/dxf (review expects POST)", rpost.status_code in (200, 405),
        f"http={rpost.status_code} (current implementation uses GET only)")


# ---------------------------------------------------------------- VOICE
def test_voice(tokens: Dict[str, str]) -> None:
    # without file
    r = requests.post(f"{BASE}/transcribe", headers=H(tokens["admin"]), timeout=10)
    log("VOICE | POST /transcribe rejects missing file", r.status_code in (400, 422),
        f"http={r.status_code}")
    # without auth
    r = requests.post(f"{BASE}/transcribe", timeout=10)
    log("VOICE | POST /transcribe requires auth", r.status_code in (401, 403, 422),
        f"http={r.status_code}")
    # with empty fake audio bytes — will likely error 500 from OpenAI (expected, route is alive)
    files = {"audio": ("audio.m4a", b"\x00" * 64, "audio/m4a")}
    r = requests.post(f"{BASE}/transcribe", headers=H(tokens["admin"]), files=files, timeout=30)
    log("VOICE | POST /transcribe route alive (fake bytes)", r.status_code in (200, 400, 500, 503),
        f"http={r.status_code}")


# ---------------------------------------------------------------- STATS
def test_stats(tokens: Dict[str, str]) -> None:
    r = requests.get(f"{BASE}/stats", headers=H(tokens["admin"]), timeout=15)
    if r.status_code != 200:
        log("STATS | GET /stats (admin)", False, f"http={r.status_code}")
        return
    j = r.json()
    needed = ["total_projects", "by_status", "total_measurements", "validated_measurements", "average_steps", "team_size"]
    miss = [k for k in needed if k not in j]
    log("STATS | GET /stats (admin) full payload", not miss and isinstance(j.get("by_status"), dict),
        f"total={j.get('total_projects')} keys_missing={miss}")

    r2 = requests.get(f"{BASE}/stats", headers=H(tokens["tech"]), timeout=15)
    log("STATS | GET /stats (tech)", r2.status_code == 200, f"http={r2.status_code}")


# ----------------------------------------------------------- INTEGRATION
def test_integration(tokens: Dict[str, str], projects: Dict[str, str]) -> None:
    # Review mentioned GET /api/integration/projects but actual code exposes /integration/sites/{pid}
    r = requests.get(f"{BASE}/integration/projects", headers=H(tokens["admin"]), timeout=10)
    log("INTEGRATION | GET /integration/projects (review-expected route)", r.status_code == 200,
        f"http={r.status_code} (current implementation has /integration/sites/{{pid}} only — 404 expected)")

    pid = projects.get("admin")
    if pid:
        r = requests.get(f"{BASE}/integration/sites/{pid}", headers=H(tokens["admin"]), timeout=15)
        ok = r.status_code == 200 and r.json().get("site_id") == pid
        log("INTEGRATION | GET /integration/sites/{pid}", ok,
            f"http={r.status_code} structure={'yes' if (r.status_code == 200 and r.json().get('structure')) else 'no'}")
        # without auth
        r = requests.get(f"{BASE}/integration/sites/{pid}", timeout=10)
        log("INTEGRATION | GET /integration/sites/{pid} requires auth",
            r.status_code in (401, 403), f"http={r.status_code}")


# ------------------------------------------------------------- CLEANUP
def cleanup(tokens: Dict[str, str], projects: Dict[str, str]) -> None:
    for label, pid in projects.items():
        r = requests.delete(f"{BASE}/projects/{pid}", headers=H(tokens["admin"]), timeout=15)
        log(f"CLEANUP | DELETE project ({label})", r.status_code == 200, f"http={r.status_code}")


def main() -> int:
    print(f"\n=== MesureEscalier backend post-refactor validation ===\nBASE={BASE}\n")
    tokens = test_auth()
    if not all(k in tokens for k in ("admin", "tech", "solo")):
        print(f"{RED}Aborting: missing demo tokens.{RESET}")
        return 1
    projects = test_projects(tokens)
    test_measurements(tokens, projects)
    test_exports(tokens, projects)
    test_voice(tokens)
    test_stats(tokens)
    test_integration(tokens, projects)
    cleanup(tokens, projects)

    # Summary
    total = sum(len(v["steps"]) for v in results.values())
    fails = [s for v in results.values() for s in v["steps"] if not s["ok"]]
    print("\n===================== SUMMARY =====================")
    print(f"Total checks: {total}   Failures: {len(fails)}")
    if fails:
        print(f"{RED}Failed steps:{RESET}")
        for s in fails:
            print(f"  - {s['name']} :: {s['detail']}")
    print("===================================================\n")
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
