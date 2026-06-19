"""Tests pour la feature Import cahier des charges via IA (Gemini 2.5 Flash).

Couvre :
    - POST   /api/chantiers/{cid}/import-spec  (Excel happy-path, vide, mauvais
                                                  format, 401, 404)
    - GET    /api/chantiers/{cid}/spec-drafts
    - GET    /api/spec-drafts/{draft_id}
    - POST   /api/spec-drafts/{draft_id}/confirm
    - POST   /api/spec-drafts/{draft_id}/reject

Le compte utilisé est `cousin.artisan@test.mesurechassis.com` (artisan solo,
beta, plan pro). Un chantier de test est créé pour la session.
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from openpyxl import Workbook

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ARTISAN_EMAIL = "cousin.artisan@test.mesurechassis.com"
ARTISAN_PWD = "Cousin2026!"

# Timeout large car appel Gemini réel (5-30s typique)
AI_TIMEOUT = 90


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def artisan_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ARTISAN_EMAIL, "password": ARTISAN_PWD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(artisan_token):
    return {"Authorization": f"Bearer {artisan_token}"}


@pytest.fixture(scope="module")
def chantier_id(auth_headers):
    """Crée un chantier dédié à ces tests."""
    payload = {
        "last_name": "PYTEST_SpecImport",
        "first_name": "Test",
        "address": "12 rue de la Mesure",
        "postal_code": "1000",
        "city": "Bruxelles",
        "status": "a_mesurer",
    }
    r = requests.post(
        f"{API}/chantiers",
        json=payload,
        headers={**auth_headers, "Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code == 200, f"Chantier create failed: {r.status_code} {r.text}"
    data = r.json()
    cid = data["id"]
    yield cid
    # Cleanup : delete created mesures + chantier
    try:
        requests.delete(f"{API}/chantiers/{cid}", headers=auth_headers, timeout=20)
    except Exception:
        pass


def _make_excel_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Chassis"
    ws.append(["Désignation", "Largeur (mm)", "Hauteur (mm)", "Quantité", "Type", "Notes"])
    ws.append(["Fenêtre salon", 1200, 1500, 2, "Standard", "PVC blanc oscillo-battant"])
    ws.append(["Porte d'entrée", 900, 2150, 1, "Porte", "Alu gris anthracite RAL 7016"])
    ws.append(["Baie coulissante", 2400, 2150, 1, "Coulissant", "Alu noir 2 vantaux"])
    ws.append(["Fenêtre cuisine", 800, 1000, 1, "Standard", "PVC blanc fixe"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestSpecImportExcel:
    """Happy path : import Excel → IA Gemini → SpecDraft pending."""

    def test_import_excel_returns_pending_draft(self, auth_headers, chantier_id):
        files = {
            "file": (
                "cahier_charges.xlsx",
                _make_excel_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        t0 = time.time()
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            headers=auth_headers,
            files=files,
            timeout=AI_TIMEOUT,
        )
        elapsed = time.time() - t0
        print(f"\n[IA] Excel parse: {elapsed:.1f}s, status={r.status_code}")
        assert r.status_code == 200, f"Import failed: {r.status_code} {r.text}"
        data = r.json()
        # Schéma
        for key in ("id", "chantier_id", "filename", "source", "items", "summary", "status"):
            assert key in data, f"Missing key {key} in response"
        assert data["chantier_id"] == chantier_id
        assert data["source"] == "excel"
        assert data["status"] == "pending"
        assert isinstance(data["items"], list)
        # Sauvegarde pour les tests suivants
        pytest.shared_draft_id = data["id"]
        pytest.shared_items = data["items"]

    def test_items_extracted_correctly(self):
        items = getattr(pytest, "shared_items", None)
        assert items is not None, "Le test précédent a échoué."
        # 4 lignes de châssis attendues (l'IA peut être tolérante : ≥3)
        assert len(items) >= 3, f"Attendu ≥3 items, reçu {len(items)}"
        # Tous les block_type doivent être valides
        for it in items:
            assert it["block_type"] in {"standard", "coulissant", "porte", "trapeze"}, (
                f"block_type invalide: {it['block_type']}"
            )
            assert isinstance(it["width_mm"], int)
            assert isinstance(it["height_mm"], int)
            assert isinstance(it["quantity"], int)
        # Vérifie qu'il y a au moins une quantité > 1 (la ligne "Fenêtre salon" x2)
        quantities = [it["quantity"] for it in items]
        has_porte = any(it["block_type"] == "porte" for it in items)
        has_coul = any(it["block_type"] == "coulissant" for it in items)
        assert max(quantities) >= 2, f"Aucun item avec quantity>=2 : {quantities}"
        assert has_porte, "Aucun item 'porte' détecté"
        assert has_coul, "Aucun item 'coulissant' détecté"


class TestSpecImportErrors:
    """Cas d'erreur : fichier vide, format invalide, 401, 404."""

    def test_empty_file_returns_400(self, auth_headers, chantier_id):
        files = {"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            headers=auth_headers, files=files, timeout=30,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_unsupported_format_returns_400(self, auth_headers, chantier_id):
        files = {"file": ("notes.txt", b"random text content", "text/plain")}
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            headers=auth_headers, files=files, timeout=30,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_no_auth_returns_401(self, chantier_id):
        files = {"file": ("x.xlsx", _make_excel_bytes(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            files=files, timeout=30,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    def test_unknown_chantier_returns_404(self, auth_headers):
        files = {"file": ("x.xlsx", _make_excel_bytes(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = requests.post(
            f"{API}/chantiers/does-not-exist-zzz/import-spec",
            headers=auth_headers, files=files, timeout=30,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


class TestSpecDraftsList:
    """GET /api/chantiers/{cid}/spec-drafts et GET /api/spec-drafts/{id}."""

    def test_list_drafts(self, auth_headers, chantier_id):
        r = requests.get(
            f"{API}/chantiers/{chantier_id}/spec-drafts",
            headers=auth_headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        drafts = r.json()
        assert isinstance(drafts, list)
        # Le draft créé doit y figurer en status=pending
        ids = [d["id"] for d in drafts]
        assert pytest.shared_draft_id in ids
        for d in drafts:
            assert d["status"] == "pending"

    def test_get_draft_detail(self, auth_headers):
        did = pytest.shared_draft_id
        r = requests.get(f"{API}/spec-drafts/{did}", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"] == did
        assert d["status"] == "pending"
        assert isinstance(d["items"], list)


class TestSpecConfirm:
    """POST /confirm : crée N mesures et passe le draft en imported."""

    def test_confirm_creates_mesures(self, auth_headers, chantier_id):
        did = pytest.shared_draft_id
        items = pytest.shared_items
        expected_count = sum(int(it["quantity"]) for it in items)

        # Comptage initial des mesures
        r0 = requests.get(
            f"{API}/chantiers/{chantier_id}",
            headers=auth_headers, timeout=30,
        )
        assert r0.status_code == 200

        # GET mesures avant
        r_before = requests.get(
            f"{API}/chantiers/{chantier_id}/mesures",
            headers=auth_headers, timeout=30,
        )
        before_count = len(r_before.json()) if r_before.status_code == 200 else 0

        # Confirm
        r = requests.post(
            f"{API}/spec-drafts/{did}/confirm",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"items": items},
            timeout=30,
        )
        assert r.status_code == 200, f"Confirm failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["ok"] is True
        assert body["mesures_created"] == expected_count
        assert body["draft_id"] == did

        # Vérifie que le draft est passé en imported (récup directe via GET)
        r2 = requests.get(f"{API}/spec-drafts/{did}", headers=auth_headers, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["status"] == "imported"

        # Vérifie que les mesures ont été créées avec flag imported_from_spec
        r_after = requests.get(
            f"{API}/chantiers/{chantier_id}/mesures",
            headers=auth_headers, timeout=30,
        )
        assert r_after.status_code == 200
        mesures = r_after.json()
        assert len(mesures) - before_count == expected_count, (
            f"Mesures créées: {len(mesures)-before_count}, attendu {expected_count}"
        )
        imported = [m for m in mesures if (m.get("options") or {}).get("imported_from_spec")]
        assert len(imported) >= expected_count, "Flag imported_from_spec manquant"
        # Vérifie pré-remplissage dims
        sample = imported[0]
        assert sample.get("width_top") is not None
        assert sample.get("width_middle") is not None
        assert sample.get("width_bottom") is not None
        assert sample.get("height_left") is not None
        assert sample.get("height_middle") is not None
        assert sample.get("height_right") is not None

    def test_confirm_already_imported_returns_400(self, auth_headers):
        """Reconfirmer un draft déjà importé doit échouer."""
        did = pytest.shared_draft_id
        r = requests.post(
            f"{API}/spec-drafts/{did}/confirm",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"items": pytest.shared_items},
            timeout=30,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"


class TestSpecReject:
    """POST /reject : un brouillon pending → rejected."""

    def test_reject_draft(self, auth_headers, chantier_id):
        # Création d'un second draft via mini-Excel
        wb = Workbook()
        ws = wb.active
        ws.append(["Désignation", "Largeur (mm)", "Hauteur (mm)", "Quantité"])
        ws.append(["Fenêtre wc", 600, 800, 1])
        buf = io.BytesIO()
        wb.save(buf)
        files = {
            "file": ("mini.xlsx", buf.getvalue(),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            headers=auth_headers, files=files, timeout=AI_TIMEOUT,
        )
        assert r.status_code == 200, r.text
        did = r.json()["id"]

        # Reject
        r2 = requests.post(
            f"{API}/spec-drafts/{did}/reject",
            headers=auth_headers, timeout=30,
        )
        assert r2.status_code == 200
        assert r2.json().get("ok") is True

        # Vérifie que le draft passe en rejected
        r3 = requests.get(f"{API}/spec-drafts/{did}", headers=auth_headers, timeout=30)
        assert r3.status_code == 200
        assert r3.json()["status"] == "rejected"

        # Il ne doit plus apparaître dans la liste (status=pending uniquement)
        r4 = requests.get(
            f"{API}/chantiers/{chantier_id}/spec-drafts",
            headers=auth_headers, timeout=30,
        )
        assert r4.status_code == 200
        assert did not in [d["id"] for d in r4.json()]
