"""
Backend test suite for MesureEscalier v2 — Multi-stairs (Niveaux > Tronçons).

Covers:
  A. SCÉNARIO COMPLET v2 — CRUD stairs / niveaux / troncons + compute
  B. MIGRATION v2 idempotente — projets legacy ont stairs[]
  C. EXPORT PDF/DXF v2 — fallback synthétique
  D. PAYWALL + RBAC — 402 expired, 404 cross-admin
  E. NON-RÉGRESSION — login, /preview legacy, photos, logo, paywall, element_title
"""
from __future__ import annotations

import os
import sys
import json
import base64
import requests

BASE = "https://stair-pro.preview.emergentagent.com"
API = f"{BASE}/api"

ADMIN = {"email": "admin@demo.fr", "password": "Demo1234!"}
SOLO = {"email": "marc@mesureescalier.com", "password": "Demo1234!"}
TECH = {"email": "sophie@mesureescaliee.com", "password": "Demo1234!"}
EXPIRED = {"email": "expired@demo.fr", "password": "Demo1234!"}

results = []  # list[(ok, name, detail)]


def log(ok: bool, name: str, detail: str = ""):
    tag = "PASS" if ok else "FAIL"
    line = f"[{tag}] {name}"
    if detail:
        line += f" :: {detail}"
    print(line)
    results.append((ok, name, detail))


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    return r


def hdrs(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# =============================================================================
# A. SCÉNARIO COMPLET v2
# =============================================================================
def section_A():
    print("\n===== A. SCÉNARIO COMPLET v2 (CRUD stairs/niveaux/troncons + compute) =====")
    r = login(SOLO)
    if r.status_code != 200:
        log(False, "A0 login marc (solo)", f"HTTP {r.status_code} body={r.text[:200]}")
        return None
    token = r.json()["token"]
    log(True, "A0 login marc@mesureescalier.com")

    # 1. POST /projects
    proj_payload = {
        "client_nom": "Bernard",
        "client_prenom": "Hélène",
        "address": "27 Allée des Tilleuls",
        "postal_code": "69003",
        "city": "Lyon",
        "phone": "0478123456",
        "notes": "Rénovation escalier Cave → R+1",
    }
    r = requests.post(f"{API}/projects", json=proj_payload, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A1 POST /projects", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    pid = r.json()["id"]
    log(True, "A1 POST /projects", f"pid={pid}")

    # 2. POST /projects/{pid}/stairs  (Cave-to-RDC)
    r = requests.post(f"{API}/projects/{pid}/stairs", json={"name": "Cave-to-RDC"},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A2 POST /stairs", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    stair = r.json()
    sid = stair["id"]
    ok2 = stair.get("name") == "Cave-to-RDC" and stair.get("niveaux") == []
    log(ok2, "A2 POST /stairs", f"sid={sid} name={stair.get('name')} niveaux={stair.get('niveaux')}")

    # 3. GET /projects/{pid}/stairs
    r = requests.get(f"{API}/projects/{pid}/stairs", headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A3 GET /stairs", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        stairs_list = r.json()
        log(any(s["id"] == sid for s in stairs_list), "A3 GET /stairs", f"count={len(stairs_list)}")

    # 4. PATCH stair name
    r = requests.patch(f"{API}/projects/{pid}/stairs/{sid}",
                       json={"name": "Cave-Rénovée"}, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A4 PATCH /stairs/{sid}", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        log(r.json().get("name") == "Cave-Rénovée", "A4 PATCH /stairs/{sid}", f"name={r.json().get('name')}")

    # 5. POST niveau RDC (h=2700)
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux",
                      json={"label": "RDC", "hauteur_mm": 2700, "sol_fini": True},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A5 POST /niveaux (RDC)", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    niv_rdc = r.json()
    nid_rdc = niv_rdc["id"]
    log(True, "A5 POST /niveaux (RDC)", f"nid={nid_rdc} h={niv_rdc.get('hauteur_mm')}")

    # 6. POST tronçon droit 3500x900 sur RDC
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_rdc}/troncons",
                      json={"type": "droit", "longueur_mm": 3500, "largeur_mm": 900},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A6 POST tronçon droit RDC", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        t_droit = r.json()
        tid_droit = t_droit["id"]
        log(True, "A6 POST tronçon droit RDC", f"tid={tid_droit} type={t_droit['type']}")

    # 7. POST tronçon palier 1000mm
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_rdc}/troncons",
                      json={"type": "palier", "longueur_mm": 1000},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A7 POST tronçon palier RDC", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        t_palier = r.json()
        log(True, "A7 POST tronçon palier RDC", f"tid={t_palier['id']}")

    # 8. POST niveau R+1 h=2500, sol_fini False, reserve 50
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux",
                      json={"label": "R+1", "hauteur_mm": 2500, "sol_fini": False, "reserve_mm": 50},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A8 POST /niveaux (R+1)", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    niv_r1 = r.json()
    nid_r1 = niv_r1["id"]
    log(True, "A8 POST /niveaux (R+1)", f"nid={nid_r1} h={niv_r1.get('hauteur_mm')} reserve={niv_r1.get('reserve_mm')}")

    # 9. POST tronçon quart_bas 2800mm sur R+1
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_r1}/troncons",
                      json={"type": "quart_bas", "longueur_mm": 2800, "largeur_mm": 900},
                      headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A9 POST tronçon quart_bas R+1", f"HTTP {r.status_code} {r.text[:200]}")
    else:
        log(True, "A9 POST tronçon quart_bas R+1", f"tid={r.json()['id']}")

    # 10. GET /compute — KEY TEST
    r = requests.get(f"{API}/projects/{pid}/stairs/{sid}/compute", headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "A10 GET /compute", f"HTTP {r.status_code} {r.text[:200]}")
        return token
    c = r.json()
    print(f"   [compute payload] {json.dumps(c, ensure_ascii=False, indent=2)[:1500]}")

    # Verify expected values
    th = c.get("total_height", 0)
    ts = c.get("total_steps", 0)
    tr = c.get("total_reculement", 0)
    ll = c.get("limon_length", 0)
    expected_th = 2700 + (2500 - 50)  # 5150
    ok_th = abs(th - expected_th) < 5
    log(ok_th, "A10.a total_height ≈ 5150", f"total_height={th} (expected ~{expected_th})")
    log(20 <= ts <= 35, "A10.b total_steps ~ 25-30", f"total_steps={ts}")
    expected_tr = 3500 + 1000 + 2800  # 7300
    log(abs(tr - expected_tr) < 10, "A10.c total_reculement = sum longueurs", f"total_reculement={tr} (expected {expected_tr})")
    log(ll > 0, "A10.d limon_length > 0", f"limon={ll}")

    niveaux_calc = c.get("niveaux_calc", [])
    log(len(niveaux_calc) == 2, "A10.e niveaux_calc length=2", f"len={len(niveaux_calc)}")

    if len(niveaux_calc) >= 1:
        n0 = niveaux_calc[0]
        h0 = n0.get("h", 0)
        g0 = n0.get("g", 0)
        n_steps0 = n0.get("n_steps_niveau", 0)
        log(13 <= n_steps0 <= 17, "A10.f RDC n_steps_niveau ~15", f"n={n_steps0}")
        log(150 <= h0 <= 210, "A10.g RDC h dans [150,210]", f"h={h0}")
        log(220 <= g0 <= 400, "A10.h RDC g raisonnable", f"g={g0}")
        log(isinstance(n0.get("valid_blondel"), bool), "A10.i RDC valid_blondel boolean", f"valid_blondel={n0.get('valid_blondel')}")
        tc0 = n0.get("troncons_calc", [])
        log(len(tc0) == 2, "A10.j RDC troncons_calc count=2", f"len={len(tc0)}")
        droit_calc = next((x for x in tc0 if x["type"] == "droit"), None)
        palier_calc = next((x for x in tc0 if x["type"] == "palier"), None)
        if droit_calc:
            log(droit_calc.get("n_marches", 0) >= 8, "A10.k RDC droit n_marches ~10", f"n_marches={droit_calc.get('n_marches')}")
        if palier_calc:
            log(palier_calc.get("n_marches", -1) == 0, "A10.l RDC palier n_marches=0", f"n_marches={palier_calc.get('n_marches')}")

    if len(niveaux_calc) >= 2:
        n1 = niveaux_calc[1]
        hef = n1.get("hauteur_effective", 0)
        log(abs(hef - 2450) < 5, "A10.m R+1 hauteur_effective=2450", f"hef={hef}")
        log(11 <= n1.get("n_steps_niveau", 0) <= 16, "A10.n R+1 n_steps ~14", f"n={n1.get('n_steps_niveau')}")

    log("warnings" in c and isinstance(c["warnings"], list), "A10.o warnings is list", f"warnings={c.get('warnings')}")

    # 11. PATCH troncon longueur_mm
    if 't_droit' in locals():
        r = requests.patch(
            f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_rdc}/troncons/{tid_droit}",
            json={"longueur_mm": 4000}, headers=hdrs(token), timeout=20)
        if r.status_code != 200:
            log(False, "A11 PATCH troncon", f"HTTP {r.status_code} {r.text[:200]}")
        else:
            log(r.json().get("longueur_mm") == 4000, "A11 PATCH troncon longueur_mm=4000",
                f"longueur={r.json().get('longueur_mm')}")

        # 12. DELETE troncon
        r = requests.delete(
            f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_rdc}/troncons/{tid_droit}",
            headers=hdrs(token), timeout=20)
        log(r.status_code == 200, "A12 DELETE troncon", f"HTTP {r.status_code}")

    # 13. DELETE niveau R+1
    r = requests.delete(f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid_r1}",
                        headers=hdrs(token), timeout=20)
    log(r.status_code == 200, "A13 DELETE niveau R+1", f"HTTP {r.status_code}")

    # 14. DELETE stair
    r = requests.delete(f"{API}/projects/{pid}/stairs/{sid}", headers=hdrs(token), timeout=20)
    log(r.status_code == 200, "A14 DELETE stair", f"HTTP {r.status_code}")

    return {"token": token, "pid": pid}


# =============================================================================
# B. MIGRATION v2
# =============================================================================
def section_B():
    print("\n===== B. MIGRATION v2 (legacy projets ont stairs[]) =====")
    r = login(ADMIN)
    if r.status_code != 200:
        log(False, "B0 login admin", f"HTTP {r.status_code}")
        return
    token = r.json()["token"]
    log(True, "B0 login admin")

    r = requests.get(f"{API}/projects", headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "B1 GET /projects", f"HTTP {r.status_code}")
        return
    projs = r.json()
    log(True, "B1 GET /projects admin", f"count={len(projs)}")

    # Find a legacy project (created earlier, with stairs migrated)
    if not projs:
        log(False, "B2 projets disponibles", "Aucun projet legacy trouvé")
        return

    # Test GET stair list for each legacy project
    found_with_stairs = 0
    sample_pid = None
    sample_sid = None
    for p in projs:
        pid = p["id"]
        rr = requests.get(f"{API}/projects/{pid}/stairs", headers=hdrs(token), timeout=20)
        if rr.status_code == 200:
            stairs = rr.json()
            if stairs and len(stairs) >= 1:
                found_with_stairs += 1
                if sample_pid is None:
                    sample_pid = pid
                    sample_sid = stairs[0]["id"]
    log(found_with_stairs >= 1, "B2 GET /projects/{pid}/stairs (migrés)",
        f"{found_with_stairs}/{len(projs)} projets ont au moins 1 escalier")

    if sample_pid and sample_sid:
        # Vérifier la structure migrée : 1 niveau + 1 tronçon droit
        rr = requests.get(f"{API}/projects/{sample_pid}/stairs/{sample_sid}",
                          headers=hdrs(token), timeout=20)
        if rr.status_code == 200:
            stair = rr.json()
            niveaux = stair.get("niveaux", [])
            has_n = len(niveaux) >= 1
            has_t = bool(niveaux) and len(niveaux[0].get("troncons", [])) >= 1
            log(has_n, "B3 stair migré a >=1 niveau", f"niveaux={len(niveaux)}")
            log(has_t, "B3.b 1er niveau a >=1 tronçon", f"troncons={len(niveaux[0].get('troncons', []))}")
        else:
            log(False, "B3 GET stair migré", f"HTTP {rr.status_code}")

        # Compute on migrated stair
        rr = requests.get(f"{API}/projects/{sample_pid}/stairs/{sample_sid}/compute",
                          headers=hdrs(token), timeout=20)
        if rr.status_code != 200:
            log(False, "B4 GET compute on migrated stair", f"HTTP {rr.status_code} {rr.text[:200]}")
        else:
            c = rr.json()
            ts = c.get("total_steps", 0)
            th = c.get("total_height", 0)
            log(ts > 0, "B4 compute migré total_steps>0", f"total_steps={ts} total_height={th}")
    return {"token": token, "sample_pid": sample_pid}


# =============================================================================
# C. EXPORT PDF v2 (fallback synthétique)
# =============================================================================
def section_C():
    print("\n===== C. EXPORT PDF/DXF v2 (fallback synthétique) =====")
    r = login(SOLO)
    if r.status_code != 200:
        log(False, "C0 login marc", f"HTTP {r.status_code}")
        return
    token = r.json()["token"]
    log(True, "C0 login marc")

    # Create a fresh v2 project (no measurement legacy)
    proj = {
        "client_nom": "Caron", "client_prenom": "Léa",
        "address": "5 rue du Port", "postal_code": "44000", "city": "Nantes",
        "phone": "0240000000", "notes": "Test export v2",
    }
    r = requests.post(f"{API}/projects", json=proj, headers=hdrs(token), timeout=20)
    if r.status_code != 200:
        log(False, "C1 create v2 project", f"HTTP {r.status_code}")
        return
    pid = r.json()["id"]
    # stair + niveau + tronçon
    r = requests.post(f"{API}/projects/{pid}/stairs", json={"name": "Escalier Test"},
                      headers=hdrs(token), timeout=20)
    sid = r.json()["id"]
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux",
                      json={"label": "RDC", "hauteur_mm": 2700, "sol_fini": True},
                      headers=hdrs(token), timeout=20)
    nid = r.json()["id"]
    r = requests.post(f"{API}/projects/{pid}/stairs/{sid}/niveaux/{nid}/troncons",
                      json={"type": "droit", "longueur_mm": 3500, "largeur_mm": 900},
                      headers=hdrs(token), timeout=20)
    log(r.status_code == 200, "C1 v2 project + stair/niveau/troncon créés", f"pid={pid}")

    # C2 PDF
    r = requests.get(f"{API}/projects/{pid}/export/pdf", headers=hdrs(token), timeout=30)
    ok_pdf = r.status_code == 200 and r.content[:5] == b"%PDF-"
    log(ok_pdf, "C2 GET /export/pdf (v2 fallback)",
        f"HTTP {r.status_code} size={len(r.content)} head={r.content[:10]}")

    # C3 DXF
    r = requests.get(f"{API}/projects/{pid}/export/dxf", headers=hdrs(token), timeout=30)
    ok_dxf = r.status_code == 200 and len(r.content) > 100 and b"SECTION" in r.content
    log(ok_dxf, "C3 GET /export/dxf (v2 fallback)",
        f"HTTP {r.status_code} size={len(r.content)} contains_SECTION={b'SECTION' in r.content}")


# =============================================================================
# D. PAYWALL + RBAC
# =============================================================================
def section_D():
    print("\n===== D. PAYWALL + RBAC =====")
    # D1 paywall — expired POST stair → 402
    r = login(EXPIRED)
    if r.status_code != 200:
        log(False, "D0 login expired", f"HTTP {r.status_code}")
        return
    exp_token = r.json()["token"]
    locked = r.json()["user"].get("is_locked")
    log(locked is True, "D0 expired is_locked", f"is_locked={locked}")

    # Need some pid to test against. Use the admin's first project pid.
    r = login(ADMIN)
    admin_token = r.json()["token"]
    r = requests.get(f"{API}/projects", headers=hdrs(admin_token), timeout=20)
    pids = [p["id"] for p in r.json()] if r.status_code == 200 else []
    other_pid = pids[0] if pids else "non-existent"

    # POST /stairs with expired token → 402
    r = requests.post(f"{API}/projects/{other_pid}/stairs",
                      json={"name": "X"}, headers=hdrs(exp_token), timeout=20)
    log(r.status_code == 402, "D1 expired POST /stairs → 402",
        f"HTTP {r.status_code} body={r.text[:120]}")

    # D2 — sophie technicien tente GET /stairs sur projet d'admin non assigné
    r = login(TECH)
    if r.status_code != 200:
        log(False, "D2.0 login sophie", f"HTTP {r.status_code}")
        return
    tech_token = r.json()["token"]

    # Trouver un projet admin non assigné à sophie (admin solo marc créera un projet privé)
    r = login(SOLO)
    solo_token = r.json()["token"]
    proj = {"client_nom": "Privé", "address": "1 rue X", "notes": ""}
    r = requests.post(f"{API}/projects", json=proj, headers=hdrs(solo_token), timeout=20)
    if r.status_code != 200:
        log(False, "D2 create solo project", f"HTTP {r.status_code}")
        return
    private_pid = r.json()["id"]

    # Sophie n'est PAS rattachée à la société de marc → project_visible_to filter → 404
    r = requests.get(f"{API}/projects/{private_pid}/stairs", headers=hdrs(tech_token), timeout=20)
    log(r.status_code == 404, "D2 sophie GET /stairs sur projet d'un autre admin → 404",
        f"HTTP {r.status_code} body={r.text[:150]}")


# =============================================================================
# E. NON-RÉGRESSION
# =============================================================================
def section_E():
    print("\n===== E. NON-RÉGRESSION =====")
    # E1 login 3 comptes actifs
    for label, creds in [("admin", ADMIN), ("solo", SOLO), ("tech", TECH)]:
        r = login(creds)
        if r.status_code == 200:
            u = r.json()["user"]
            log(not u.get("is_locked"), f"E1 login {label} actif",
                f"is_locked={u.get('is_locked')} trial_days={u.get('trial_days_remaining')}")
        else:
            log(False, f"E1 login {label}", f"HTTP {r.status_code}")

    # E2 measurement legacy preview h=2700/recul=3500 → 15 marches, h=180
    r = login(SOLO)
    token = r.json()["token"]
    # Need a pid (any visible project)
    rr = requests.get(f"{API}/projects", headers=hdrs(token), timeout=20)
    pid = rr.json()[0]["id"] if rr.json() else None
    if not pid:
        log(False, "E2 measurement /preview legacy", "no pid")
    else:
        payload = {
            "element_title": "Escalier Principal",
            "material": "bois",
            "hauteur_brute": 2700, "sols_finis_zero": True,
            "reserve_bas": 0, "reserve_haut": 0,
            "epaisseur_dalle": 200,
            "tremie_longueur": 2500, "tremie_largeur": 1000,
            "reculement_max": 3500,
            "remarques": "Standard test",
        }
        r = requests.post(f"{API}/projects/{pid}/measurement/preview",
                          json=payload, headers=hdrs(token), timeout=20)
        if r.status_code != 200:
            log(False, "E2 /measurement/preview", f"HTTP {r.status_code} {r.text[:200]}")
        else:
            res = r.json()
            n = res.get("n_steps")
            h = res.get("h")
            log(n == 15 and abs(h - 180) < 1, "E2 legacy preview h=2700/recul=3500 → 15 marches h=180",
                f"n_steps={n} h={h}")

    # E3 Photos CRUD : add → list → patch → delete
    # mini PNG 1x1 base64
    PNG_1x1 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    r = login(SOLO)
    token = r.json()["token"]
    rr = requests.get(f"{API}/projects", headers=hdrs(token), timeout=20)
    pid = rr.json()[0]["id"] if rr.json() else None
    if pid:
        r = requests.post(f"{API}/projects/{pid}/photos",
                          json={"base64": PNG_1x1, "caption": "test photo"},
                          headers=hdrs(token), timeout=20)
        if r.status_code != 200:
            log(False, "E3 POST photo", f"HTTP {r.status_code} {r.text[:200]}")
        else:
            photo_id = r.json()["id"]
            log(True, "E3 POST photo", f"id={photo_id}")
            rr2 = requests.get(f"{API}/projects/{pid}/photos", headers=hdrs(token), timeout=20)
            log(rr2.status_code == 200 and any(ph["id"] == photo_id for ph in rr2.json()),
                "E3.b GET photos", f"count={len(rr2.json())}")
            rp = requests.patch(f"{API}/projects/{pid}/photos/{photo_id}",
                                json={"caption": "updated"}, headers=hdrs(token), timeout=20)
            log(rp.status_code == 200, "E3.c PATCH photo", f"HTTP {rp.status_code}")
            rd = requests.delete(f"{API}/projects/{pid}/photos/{photo_id}",
                                 headers=hdrs(token), timeout=20)
            log(rd.status_code == 200, "E3.d DELETE photo", f"HTTP {rd.status_code}")

    # E4 Logo upload (admin solo only)
    r = login(SOLO)
    token = r.json()["token"]
    logo_b64 = "data:image/png;base64," + PNG_1x1
    r = requests.put(f"{API}/auth/me", json={"company_logo_base64": logo_b64},
                     headers=hdrs(token), timeout=20)
    log(r.status_code == 200 and r.json().get("company_logo_base64"),
        "E4 PUT /auth/me logo upload",
        f"HTTP {r.status_code} logo_set={bool(r.json().get('company_logo_base64'))}")

    # E5 Paywall actif : expired → /projects → 402
    r = login(EXPIRED)
    if r.status_code == 200:
        et = r.json()["token"]
        rr = requests.get(f"{API}/projects", headers=hdrs(et), timeout=20)
        log(rr.status_code == 402, "E5 paywall /projects expired → 402", f"HTTP {rr.status_code}")
    else:
        log(False, "E5 login expired", f"HTTP {r.status_code}")

    # E6 element_title legacy persisté
    r = login(SOLO)
    token = r.json()["token"]
    proj = {"client_nom": "Vidal", "address": "8 rue test", "notes": ""}
    rr = requests.post(f"{API}/projects", json=proj, headers=hdrs(token), timeout=20)
    if rr.status_code == 200:
        pid = rr.json()["id"]
        payload = {
            "element_title": "Escalier Cave Premium",
            "material": "bois", "hauteur_brute": 2700, "sols_finis_zero": True,
            "reserve_bas": 0, "reserve_haut": 0,
            "epaisseur_dalle": 200,
            "tremie_longueur": 2500, "tremie_largeur": 1000,
            "reculement_max": 3500, "remarques": "",
        }
        rs = requests.post(f"{API}/projects/{pid}/measurement", json=payload,
                           headers=hdrs(token), timeout=20)
        if rs.status_code != 200:
            log(False, "E6 POST measurement", f"HTTP {rs.status_code} {rs.text[:200]}")
        else:
            saved_title = rs.json().get("element_title")
            log(saved_title == "Escalier Cave Premium", "E6 element_title legacy persisté",
                f"element_title={saved_title}")
            # And GET project should re-expose it via measurement
            rg = requests.get(f"{API}/projects/{pid}", headers=hdrs(token), timeout=20)
            mm = rg.json().get("measurement", {}) or {}
            log(mm.get("element_title") == "Escalier Cave Premium",
                "E6.b GET /projects/{pid} measurement.element_title",
                f"element_title={mm.get('element_title')}")


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    print(f"BASE URL: {BASE}")
    # Quick liveness
    try:
        r = requests.get(f"{API}/", timeout=10)
        print(f"API root: HTTP {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"API root unreachable: {e}")
        sys.exit(1)

    try:
        section_A()
    except Exception as e:
        log(False, "Section A exception", str(e))
    try:
        section_B()
    except Exception as e:
        log(False, "Section B exception", str(e))
    try:
        section_C()
    except Exception as e:
        log(False, "Section C exception", str(e))
    try:
        section_D()
    except Exception as e:
        log(False, "Section D exception", str(e))
    try:
        section_E()
    except Exception as e:
        log(False, "Section E exception", str(e))

    # Summary
    total = len(results)
    passed = sum(1 for ok, _, _ in results if ok)
    failed = total - passed
    print("\n=================== SUMMARY ===================")
    print(f"Total: {total}  Passed: {passed}  Failed: {failed}")
    if failed:
        print("\nFailures:")
        for ok, name, detail in results:
            if not ok:
                print(f"  - {name} :: {detail}")
    sys.exit(0 if failed == 0 else 1)
