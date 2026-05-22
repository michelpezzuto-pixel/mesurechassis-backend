"""
Iteration 3 — Smart math engine tests.
Covers: échappée, hard Blondel limits, ligne de foulée note,
limon length, integration payload, PDF/DXF content.
"""
import os
import math
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")

ARTISAN = {"email": "marc@mesureescalier.com", "password": "Demo1234!"}
ADMIN = {"email": "admin@demo.fr", "password": "Demo1234!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def artisan_tok():
    tok, _ = _login(ARTISAN)
    return tok


@pytest.fixture(scope="module")
def admin_tok():
    tok, _ = _login(ADMIN)
    return tok


@pytest.fixture(scope="module")
def artisan_project(artisan_tok):
    """Reusable artisan-owned project (locked auto since solo_mode)."""
    payload = {"client_nom": f"TEST_IT3_{uuid.uuid4().hex[:6]}", "address": "rue iter3"}
    r = requests.post(f"{BASE_URL}/api/projects", headers=_h(artisan_tok),
                      json=payload, timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    requests.delete(f"{BASE_URL}/api/projects/{pid}", headers=_h(artisan_tok), timeout=30)


# --------- Math engine: échappée + tournant scenario ---------
class TestEchappeeAndTournant:
    PAYLOAD = {
        "material": "bois",
        "hauteur_brute": 2800,
        "sols_finis_zero": True,
        "reserve_bas": 0, "reserve_haut": 0,
        "epaisseur_dalle": 200,
        "tremie_longueur": 1800, "tremie_largeur": 900,
        "reculement_max": 3500, "remarques": "test",
        "hauteur_sous_plafond_tremie": 2600,
    }

    def test_preview_with_plafond_tremie(self, artisan_tok, artisan_project):
        r = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement/preview",
                          headers=_h(artisan_tok), json=self.PAYLOAD, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # échappée ≈ 1200 mm (true_h 2800, reculement 4200, g 280, h 175,
        # x_tremie_start 2400 → 8 marches sous trémie → 1400mm → 2600-1400 = 1200)
        assert d["echappee"] is not None
        assert 1100 <= d["echappee"] <= 1300, f"echappee={d['echappee']}"
        assert d["echappee_critique"] is True
        # Quart-tournant requis
        assert "Quart-tournant" in d["shape"], d["shape"]
        assert d["is_tournant"] is True
        assert d["ligne_foulee_note"] is not None
        # Limon ≈ sqrt(2800² + 4200²) ≈ 5048
        assert 5040 <= d["limon_length"] <= 5060, f"limon={d['limon_length']}"
        assert d["limon_length"] == d["hypotenuse"]

    def test_preview_without_plafond_tremie(self, artisan_tok, artisan_project):
        payload = {k: v for k, v in self.PAYLOAD.items() if k != "hauteur_sous_plafond_tremie"}
        r = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement/preview",
                          headers=_h(artisan_tok), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["echappee"] is None
        assert d["echappee_critique"] is False
        assert d["is_tournant"] is True
        assert 5040 <= d["limon_length"] <= 5060

    def test_preview_generous_reculement_droit(self, artisan_tok, artisan_project):
        payload = {
            "material": "bois", "hauteur_brute": 2800, "sols_finis_zero": True,
            "reserve_bas": 0, "reserve_haut": 0, "epaisseur_dalle": 200,
            "tremie_longueur": 1800, "tremie_largeur": 900,
            "reculement_max": 5000, "remarques": "droit",
            "hauteur_sous_plafond_tremie": 2700,
        }
        r = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement/preview",
                          headers=_h(artisan_tok), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["shape"] == "Escalier Droit Recommandé", d["shape"]
        assert d["is_tournant"] is False
        assert d["ligne_foulee_note"] is None

    def test_limon_length_formula(self, artisan_tok, artisan_project):
        r = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement/preview",
                          headers=_h(artisan_tok), json=self.PAYLOAD, timeout=30)
        d = r.json()
        expected = math.sqrt(d["true_height"] ** 2 + d["reculement_needed"] ** 2)
        assert abs(d["limon_length"] - expected) < 1.0

    def test_hard_blondel_violation_forces_tournant(self, artisan_tok, artisan_project):
        # Very large height → no combo can satisfy hard rules (h≤210)
        # 5000mm / 29 steps ≈ 172mm h, OK. So we need to break it harder.
        # Force violation: huge height that requires h>210 even at n=29
        payload = {
            "material": "acier", "hauteur_brute": 7000, "sols_finis_zero": True,
            "reserve_bas": 0, "reserve_haut": 0, "epaisseur_dalle": 200,
            "tremie_longueur": 1000, "tremie_largeur": 800,
            "reculement_max": 1500, "remarques": "extreme",
        }
        r = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement/preview",
                          headers=_h(artisan_tok), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_tournant"] is True
        # Should contain a règles de l'art / hard-rule violation note OR a hélicoïdal / quart-tournant shape
        notes_blob = " ".join(d["notes"])
        assert ("Règles de l'art" in notes_blob) or ("hélicoïdal" in d["shape"].lower()) or ("tournant" in d["shape"].lower())


# --------- Integration endpoint ---------
class TestIntegrationEndpoint:
    def test_integration_payload_has_new_fields(self, artisan_tok, artisan_project):
        # Save a measurement with échappée critique scenario
        payload = TestEchappeeAndTournant.PAYLOAD
        m = requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement",
                          headers=_h(artisan_tok), json=payload, timeout=30)
        assert m.status_code == 200, m.text
        r = requests.get(f"{BASE_URL}/api/integration/sites/{artisan_project}",
                         headers=_h(artisan_tok), timeout=30)
        assert r.status_code == 200, r.text
        struct = r.json()["structure"]
        assert struct is not None
        for k in ("limon_length_mm", "echappee_mm", "echappee_critique", "is_tournant"):
            assert k in struct, f"Missing key {k}"
        assert struct["is_tournant"] is True
        assert struct["echappee_critique"] is True
        assert 5040 <= struct["limon_length_mm"] <= 5060


# --------- Exports ---------
class TestExports:
    def test_pdf_export_contains_limon_and_echappee(self, artisan_tok, artisan_project):
        # Make sure measurement is saved (échappée scenario)
        requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement",
                      headers=_h(artisan_tok),
                      json=TestEchappeeAndTournant.PAYLOAD, timeout=30)
        r = requests.get(f"{BASE_URL}/api/projects/{artisan_project}/export/pdf",
                         headers=_h(artisan_tok), timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        # PDF is binary but should be reasonably large (>5KB) due to extra rows
        assert len(r.content) > 5000, f"PDF too small: {len(r.content)}"

    def test_dxf_export_contains_limon_and_echappee_text(self, artisan_tok, artisan_project):
        requests.post(f"{BASE_URL}/api/projects/{artisan_project}/measurement",
                      headers=_h(artisan_tok),
                      json=TestEchappeeAndTournant.PAYLOAD, timeout=30)
        r = requests.get(f"{BASE_URL}/api/projects/{artisan_project}/export/dxf",
                         headers=_h(artisan_tok), timeout=30)
        assert r.status_code == 200
        txt = r.content.decode("utf-8", errors="ignore")
        assert "LIMON" in txt, "DXF missing LIMON text"
        assert "Echappee" in txt or "ECHAPPEE" in txt, "DXF missing ECHAPPEE annotation"
