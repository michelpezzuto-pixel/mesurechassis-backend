"""Lot B — Logo entreprise: tests ciblés.

Couvre :
1. CRUD logo via PATCH /api/company/profile
2. Génération PDF avec logo
3. Génération PDF sans logo
4. RBAC (commercial/technician interdits)
5. Logo invalide (PATCH accepté, PDF ne crash pas)
6. Cleanup
"""
from __future__ import annotations

import base64
import io
import os
import sys
import time
from typing import Optional

import requests

# --- Config -----------------------------------------------------------
BACKEND_URL = "https://window-field-app.preview.emergentagent.com"
API = f"{BACKEND_URL}/api"

ADMIN = ("admin@mesurechassis.fr", "admin123")
COMM = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

# 100x50 PNG (gris semi-transparent) — généré sans Pillow, brut.
# On utilise un PNG minimal valide encodé en base64.
PNG_200x100_B64 = "iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAIAAABM5OhcAAABGklEQVR4nO3SQQ3AIADAQEAm/n2AiTUky52CPjrPHvC59TqAfzIWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORMBYJY5EwFgljkTAWCWORuBe8AiG7VCroAAAAAElFTkSuQmCC"
LOGO_DATA_URL = f"data:image/png;base64,{PNG_200x100_B64}"

results: list[tuple[str, bool, str]] = []


def log(name: str, ok: bool, info: str = "") -> None:
    results.append((name, ok, info))
    icon = "✅" if ok else "❌"
    print(f"{icon} {name} — {info}")


def login(email: str, password: str) -> str:
    r = requests.post(
        f"{API}/auth/login", json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def H(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def main() -> int:
    # ------------------ Login admin --------------------------------------
    try:
        admin_tok = login(*ADMIN)
        log("Login admin", True, f"token len={len(admin_tok)}")
    except Exception as e:
        log("Login admin", False, str(e))
        return 1

    # Désactiver artisan_mode pour pouvoir tester le RBAC strict
    initial_profile = requests.get(
        f"{API}/company/profile", headers=H(admin_tok), timeout=15,
    ).json()
    initial_artisan = bool(initial_profile.get("artisan_mode"))
    print(f"   artisan_mode initial = {initial_artisan}")
    if initial_artisan:
        rr = requests.patch(
            f"{API}/company/profile",
            headers=H(admin_tok),
            json={"artisan_mode": False},
            timeout=15,
        )
        print(f"   PATCH artisan_mode=false → {rr.status_code}")

    # ------------------ T1. GET initial profile --------------------------
    r = requests.get(f"{API}/company/profile", headers=H(admin_tok), timeout=15)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    initial_logo = body.get("logo_base64")
    log(
        "T1. GET /company/profile (initial)",
        ok,
        f"status={r.status_code}, logo_base64={'present' if initial_logo else 'null/absent'} (len={len(initial_logo) if initial_logo else 0})",
    )

    # ------------------ T2. PATCH avec logo data URL ---------------------
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": LOGO_DATA_URL},
        timeout=15,
    )
    ok = r.status_code == 200 and r.json().get("logo_base64") == LOGO_DATA_URL
    log(
        "T2. PATCH /company/profile {logo_base64: <PNG>}",
        ok,
        f"status={r.status_code}, returned logo identique={r.json().get('logo_base64')==LOGO_DATA_URL if r.status_code==200 else 'N/A'}",
    )

    # ------------------ T3. GET vérifie persistance ----------------------
    r = requests.get(f"{API}/company/profile", headers=H(admin_tok), timeout=15)
    ok = r.status_code == 200 and r.json().get("logo_base64") == LOGO_DATA_URL
    log(
        "T3. GET /company/profile vérifie persist",
        ok,
        f"status={r.status_code}, persisté identique={r.json().get('logo_base64')==LOGO_DATA_URL if r.status_code==200 else 'N/A'}",
    )

    # ------------------ T4. PATCH chaîne vide retire le logo -------------
    # NOTE : update_company_profile filtre les valeurs None mais PAS les
    # chaînes vides — donc {logo_base64:''} devrait écraser à ''.
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": ""},
        timeout=15,
    )
    body = r.json() if r.status_code == 200 else {}
    cleared = body.get("logo_base64") in (None, "")
    log(
        "T4. PATCH {logo_base64:''} (clear)",
        r.status_code == 200 and cleared,
        f"status={r.status_code}, returned logo_base64={body.get('logo_base64')!r}",
    )

    # ------------------ T5. Re-PATCH logo pour tests PDF -----------------
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": LOGO_DATA_URL},
        timeout=15,
    )
    log(
        "T5. Re-PATCH logo pour tests PDF",
        r.status_code == 200,
        f"status={r.status_code}",
    )

    # ------------------ T6. GET /chantiers (récupérer un id) -------------
    r = requests.get(f"{API}/chantiers", headers=H(admin_tok), timeout=15)
    chantiers = r.json() if r.status_code == 200 else []
    chantier_id: Optional[str] = None
    created_test_chantier_id: Optional[str] = None
    if chantiers:
        chantier_id = chantiers[0]["id"]
        log(
            "T6. GET /chantiers (existant)",
            True,
            f"status={r.status_code}, n={len(chantiers)}, picked id={chantier_id}",
        )
    else:
        # Créer un chantier de test
        cr = requests.post(
            f"{API}/chantiers",
            headers=H(admin_tok),
            json={
                "first_name": "LotB",
                "last_name": "Logo",
                "address": "12 rue du Logo",
                "postal_code": "75001",
                "city": "Paris",
                "status": "devis_a_faire",
            },
            timeout=15,
        )
        if cr.status_code == 200:
            chantier_id = cr.json()["id"]
            created_test_chantier_id = chantier_id
            log(
                "T6. POST /chantiers (création test)",
                True,
                f"status=200, id={chantier_id}",
            )
        else:
            log(
                "T6. POST /chantiers (création test)",
                False,
                f"status={cr.status_code} body={cr.text[:200]}",
            )
            return 1

    assert chantier_id is not None

    # ------------------ T7. PDF avec logo --------------------------------
    r = requests.get(
        f"{API}/chantiers/{chantier_id}/export.pdf",
        headers=H(admin_tok),
        timeout=30,
    )
    pdf_bytes = r.content if r.status_code == 200 else b""
    starts_pdf = pdf_bytes.startswith(b"%PDF")
    size_ok = len(pdf_bytes) > 1500
    ct = r.headers.get("Content-Type", "")
    log(
        "T7. PDF avec logo",
        r.status_code == 200 and starts_pdf and size_ok
        and "application/pdf" in ct,
        f"status={r.status_code}, size={len(pdf_bytes)}, ct={ct}, magic=%PDF? {starts_pdf}",
    )

    # Cherche "DOCUMENT INTERNE" — comme c'est dans un PDF avec compression
    # FlateDecode, on essaie de décoder les streams pour extraire le texte.
    # Méthode simple : décompresser tous les flate streams.
    def find_document_interne(b: bytes) -> bool:
        if b"DOCUMENT INTERNE" in b:
            return True
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(b))
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
            return "DOCUMENT INTERNE" in text
        except Exception as e:
            print(f"   [find_document_interne] pypdf error: {e}")
            return False

    has_doc_interne = find_document_interne(pdf_bytes)
    log(
        "T7b. PDF contient 'DOCUMENT INTERNE'",
        has_doc_interne,
        "trouvé dans stream décompressé" if has_doc_interne else "non trouvé",
    )

    # ------------------ T8. PDF SANS logo --------------------------------
    rr = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": ""},
        timeout=15,
    )
    print(f"   Clear logo: status={rr.status_code}, logo={rr.json().get('logo_base64')!r}")

    r = requests.get(
        f"{API}/chantiers/{chantier_id}/export.pdf",
        headers=H(admin_tok),
        timeout=30,
    )
    pdf_bytes_no_logo = r.content if r.status_code == 200 else b""
    starts_pdf2 = pdf_bytes_no_logo.startswith(b"%PDF")
    size_ok2 = len(pdf_bytes_no_logo) > 1500
    ct2 = r.headers.get("Content-Type", "")
    log(
        "T8. PDF SANS logo",
        r.status_code == 200 and starts_pdf2 and size_ok2,
        f"status={r.status_code}, size={len(pdf_bytes_no_logo)}, ct={ct2}, magic={starts_pdf2}",
    )
    has_doc_interne2 = find_document_interne(pdf_bytes_no_logo)
    log(
        "T8b. PDF sans logo contient toujours 'DOCUMENT INTERNE'",
        has_doc_interne2,
        "trouvé" if has_doc_interne2 else "non trouvé",
    )

    # ------------------ T9. RBAC — Commercial ----------------------------
    comm_tok = login(*COMM)
    # GET autorisé
    r = requests.get(
        f"{API}/company/profile", headers=H(comm_tok), timeout=15,
    )
    log(
        "T9a. Commercial GET /company/profile autorisé",
        r.status_code == 200,
        f"status={r.status_code}",
    )
    # PATCH interdit
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(comm_tok),
        json={"logo_base64": LOGO_DATA_URL},
        timeout=15,
    )
    log(
        "T9b. Commercial PATCH logo → 403",
        r.status_code == 403,
        f"status={r.status_code} detail={r.text[:120]}",
    )

    # ------------------ T10. RBAC — Technician ---------------------------
    tech_tok = login(*TECH)
    r = requests.get(
        f"{API}/company/profile", headers=H(tech_tok), timeout=15,
    )
    log(
        "T10a. Technician GET /company/profile autorisé",
        r.status_code == 200,
        f"status={r.status_code}",
    )
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(tech_tok),
        json={"logo_base64": LOGO_DATA_URL},
        timeout=15,
    )
    log(
        "T10b. Technician PATCH logo → 403",
        r.status_code == 403,
        f"status={r.status_code} detail={r.text[:120]}",
    )

    # ------------------ T11. Logo invalide --------------------------------
    r = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": "pas-une-data-url"},
        timeout=15,
    )
    log(
        "T11a. PATCH logo invalide accepté (200)",
        r.status_code == 200,
        f"status={r.status_code}",
    )
    r = requests.get(
        f"{API}/chantiers/{chantier_id}/export.pdf",
        headers=H(admin_tok),
        timeout=30,
    )
    pdf_invalid = r.content if r.status_code == 200 else b""
    log(
        "T11b. PDF avec logo invalide ne crash pas",
        r.status_code == 200
        and pdf_invalid.startswith(b"%PDF")
        and len(pdf_invalid) > 1500,
        f"status={r.status_code}, size={len(pdf_invalid)}, magic={pdf_invalid[:5]!r}",
    )

    # ------------------ T12. Régression pytest ---------------------------
    print("\n--- T12. Régression pytest ---")
    import subprocess
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q", "--no-cov"],
        cwd="/app/backend",
        capture_output=True,
        text=True,
        timeout=240,
    )
    output = proc.stdout + proc.stderr
    # Cherche la ligne "167 passed"
    passed_167 = "167 passed" in output
    log(
        "T12. pytest tests/ -q --no-cov → 167 passed",
        passed_167,
        f"exit={proc.returncode}, tail={output.strip().splitlines()[-1] if output.strip() else '<empty>'}",
    )
    if not passed_167:
        print("   ----- pytest tail -----")
        print("\n".join(output.strip().splitlines()[-20:]))

    # ------------------ CLEANUP ------------------------------------------
    print("\n--- CLEANUP ---")
    # Retirer le logo
    rr = requests.patch(
        f"{API}/company/profile",
        headers=H(admin_tok),
        json={"logo_base64": ""},
        timeout=15,
    )
    final_logo = rr.json().get("logo_base64") if rr.status_code == 200 else "?"
    print(f"  Cleanup logo: status={rr.status_code}, final logo={final_logo!r}")

    # Restaurer artisan_mode initial
    if initial_artisan:
        rr = requests.patch(
            f"{API}/company/profile",
            headers=H(admin_tok),
            json={"artisan_mode": True},
            timeout=15,
        )
        print(f"  Restore artisan_mode=true: status={rr.status_code}, am={rr.json().get('artisan_mode')}")

    # Supprimer le chantier de test si on en a créé un
    if created_test_chantier_id:
        rr = requests.delete(
            f"{API}/chantiers/{created_test_chantier_id}",
            headers=H(admin_tok),
            timeout=15,
        )
        print(f"  DELETE test chantier {created_test_chantier_id}: status={rr.status_code}")

    # ------------------ SUMMARY ------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY Lot B — Logo entreprise")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"PASSED: {passed}/{total}")
    for name, ok, info in results:
        if not ok:
            print(f"  ❌ {name}: {info}")
    return 0 if passed == total else 2


if __name__ == "__main__":
    sys.exit(main())
