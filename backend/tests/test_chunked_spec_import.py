"""Tests Build 12 — Chunked Upload pour Import CDC (anti-502 Cloudflare).

Couvre les endpoints `/api/chantiers/{cid}/import-spec/chunked/*` :
    - init      : création de session (upload_id)
    - chunk     : upload d'un chunk individuel (avec idempotence)
    - complete  : assemblage + lancement IA en background
    - abort     : cleanup

Vérifie aussi la modification de `_expand_items_for_mesures` :
    - bay_width / bay_height pré-remplis
    - options.validated_on_site = False

Compte utilisé : applereview@mesurechassis.com (admin, Pharmacie Centrale).
"""
from __future__ import annotations

import asyncio
import io
import math
import os
import time
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api" if BASE_URL else "http://localhost:8001/api"

APPLE_EMAIL = "applereview@mesurechassis.com"
APPLE_PWD = "AppleReview2026!"

CHUNK_SIZE = 1024 * 1024  # 1 Mo


# Sync pymongo client (évite conflits asyncio loop avec Motor)
def _sync_find_one(collection: str, query: dict):
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url:
        # fallback : importer depuis backend/.env
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
    client = MongoClient(mongo_url)
    try:
        return client[db_name][collection].find_one(query)
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_fake_pdf_bytes(target_size: int = 3 * 1024 * 1024) -> bytes:
    """Génère un PDF minimal valide puis pad avec du texte pour atteindre la taille cible.

    Note : le binaire est un PDF avec en-tête %PDF-1.4. Gemini va échouer (contenu
    aléatoire) mais le TRANSPORT chunké doit fonctionner — c'est ce qu'on teste ici.
    """
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    trailer = b"\n%%EOF\n"
    padding_size = target_size - len(header) - len(trailer)
    padding = (b"% pad line abcdefghijklmnopqrstuvwxyz 0123456789\n" * (padding_size // 50 + 1))[:padding_size]
    return header + padding + trailer


def _chunks_of(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i:i + size]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": APPLE_EMAIL, "password": APPLE_PWD},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def chantier_id(hdr):
    """Récupère le chantier 'Pharmacie Centrale' s'il existe, sinon en crée un."""
    r = requests.get(f"{API}/chantiers", headers=hdr, timeout=30)
    assert r.status_code == 200, r.text
    chantiers = r.json()
    for c in chantiers:
        # Pharmacie Centrale → cherche par nom (last_name ou client_name)
        name = " ".join(
            str(c.get(k, "") or "")
            for k in ("last_name", "first_name", "client_name", "company_name")
        ).lower()
        if "pharmacie" in name and "central" in name:
            return c["id"]
    # Fallback : créer un chantier dédié
    payload = {
        "last_name": "PYTEST_ChunkedUpload",
        "first_name": "Test",
        "address": "1 rue du Chunk",
        "postal_code": "1000",
        "city": "Bruxelles",
        "status": "a_mesurer",
    }
    r = requests.post(
        f"{API}/chantiers",
        json=payload,
        headers={**hdr, "Content-Type": "application/json"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# /init — validations
# ---------------------------------------------------------------------------
class TestChunkedInit:
    def test_init_happy_path(self, hdr, chantier_id):
        body = {
            "filename": "plan.pdf",
            "mime_type": "application/pdf",
            "total_size": 3 * 1024 * 1024,
            "total_chunks": 3,
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "upload_id" in data
        assert "chunk_size" in data
        assert data["chunk_size"] == 1024 * 1024
        # cleanup
        requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/{data['upload_id']}/abort",
            headers=hdr, timeout=10,
        )

    def test_init_invalid_size_zero(self, hdr, chantier_id):
        body = {"filename": "x.pdf", "mime_type": "application/pdf", "total_size": 0, "total_chunks": 1}
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_init_size_too_big_returns_413(self, hdr, chantier_id):
        body = {
            "filename": "huge.pdf",
            "mime_type": "application/pdf",
            "total_size": 20 * 1024 * 1024,  # >15 Mo
            "total_chunks": 20,
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        assert r.status_code == 413, r.text

    def test_init_too_many_chunks_returns_400(self, hdr, chantier_id):
        body = {
            "filename": "x.pdf",
            "mime_type": "application/pdf",
            "total_size": 1024,
            "total_chunks": 100,  # >64
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_init_zero_chunks_returns_400(self, hdr, chantier_id):
        body = {
            "filename": "x.pdf",
            "mime_type": "application/pdf",
            "total_size": 1024,
            "total_chunks": 0,
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_init_unsupported_extension_returns_400(self, hdr, chantier_id):
        body = {
            "filename": "notes.txt",
            "mime_type": "text/plain",
            "total_size": 1024,
            "total_chunks": 1,
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json=body, timeout=15,
        )
        assert r.status_code == 400, r.text


# ---------------------------------------------------------------------------
# /chunk — upload + erreurs
# ---------------------------------------------------------------------------
class TestChunkedChunk:
    def test_chunk_unknown_upload_id_returns_404(self, hdr, chantier_id):
        fake_id = str(uuid.uuid4())
        files = {"file": ("c", b"abc", "application/octet-stream")}
        data = {"chunk_index": "0"}
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/{fake_id}/chunk",
            headers=hdr, files=files, data=data, timeout=15,
        )
        assert r.status_code == 404, r.text

    def test_chunk_out_of_bounds_returns_400(self, hdr, chantier_id):
        # Init avec 2 chunks attendus
        init = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json={"filename": "x.pdf", "mime_type": "application/pdf",
                  "total_size": 1024, "total_chunks": 2},
            timeout=15,
        )
        assert init.status_code == 200
        upload_id = init.json()["upload_id"]
        try:
            files = {"file": ("c", b"abc", "application/octet-stream")}
            r = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files, data={"chunk_index": "5"},
                timeout=15,
            )
            assert r.status_code == 400, r.text
            # negative aussi
            r2 = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files, data={"chunk_index": "-1"},
                timeout=15,
            )
            assert r2.status_code == 400, r2.text
        finally:
            requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/abort",
                headers=hdr, timeout=10,
            )

    def test_chunk_idempotent_overwrite(self, hdr, chantier_id):
        """Upload du même chunk_index deux fois → ne double pas le compteur."""
        init = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json={"filename": "x.pdf", "mime_type": "application/pdf",
                  "total_size": 2048, "total_chunks": 2},
            timeout=15,
        )
        upload_id = init.json()["upload_id"]
        try:
            files = {"file": ("c", b"x" * 1024, "application/octet-stream")}
            r1 = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files, data={"chunk_index": "0"},
                timeout=15,
            )
            assert r1.status_code == 200
            assert r1.json()["received_chunks"] == 1
            # Re-upload du même chunk
            files2 = {"file": ("c", b"y" * 1024, "application/octet-stream")}
            r2 = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files2, data={"chunk_index": "0"},
                timeout=15,
            )
            assert r2.status_code == 200, r2.text
            assert r2.json()["received_chunks"] == 1, (
                f"Idempotence cassée : {r2.json()}"
            )
        finally:
            requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/abort",
                headers=hdr, timeout=10,
            )


# ---------------------------------------------------------------------------
# /complete — happy path E2E
# ---------------------------------------------------------------------------
class TestChunkedComplete:
    def test_full_flow_init_chunk_complete(self, hdr, chantier_id):
        # 1) Init
        pdf_bytes = _make_fake_pdf_bytes(3 * 1024 * 1024)  # 3 Mo
        total_chunks = math.ceil(len(pdf_bytes) / CHUNK_SIZE)
        init = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json={
                "filename": "fake_plan.pdf",
                "mime_type": "application/pdf",
                "total_size": len(pdf_bytes),
                "total_chunks": total_chunks,
            },
            timeout=15,
        )
        assert init.status_code == 200, init.text
        upload_id = init.json()["upload_id"]

        # 2) Upload de tous les chunks
        for idx, chunk in enumerate(_chunks_of(pdf_bytes, CHUNK_SIZE)):
            files = {"file": (f"c{idx}", chunk, "application/octet-stream")}
            r = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files, data={"chunk_index": str(idx)},
                timeout=30,
            )
            assert r.status_code == 200, f"Chunk {idx} failed: {r.text}"
            assert r.json()["received_chunks"] == idx + 1
        # 3) Complete
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/complete",
            headers=hdr, timeout=30,
        )
        assert r.status_code == 200, r.text
        draft = r.json()
        assert draft["status"] == "processing"
        assert draft["filename"] == "fake_plan.pdf"
        assert draft["source"] == "pdf"
        assert draft["chantier_id"] == chantier_id
        draft_id = draft["id"]

        # 4) Vérifie qu'un GET /spec-drafts/{id} retourne bien le draft
        r2 = requests.get(f"{API}/spec-drafts/{draft_id}", headers=hdr, timeout=15)
        assert r2.status_code == 200, r2.text
        # Le draft peut être déjà passé en "failed" (binaire random) mais
        # doit exister et matcher l'id.
        assert r2.json()["id"] == draft_id
        assert r2.json()["status"] in {"processing", "failed", "imported"}

        # 5) Vérifie en DB que la session chunked est marquée completed
        # (sync pymongo client pour éviter conflits asyncio loop)
        sess = _sync_find_one("spec_chunked_uploads", {"id": upload_id})
        assert sess is not None, "spec_chunked_uploads not found"
        assert sess["status"] == "completed", f"session status: {sess.get('status')}"
        assert sess.get("draft_id") == draft_id

    def test_complete_missing_chunks_returns_400(self, hdr, chantier_id):
        init = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json={"filename": "x.pdf", "mime_type": "application/pdf",
                  "total_size": 2 * 1024, "total_chunks": 2},
            timeout=15,
        )
        upload_id = init.json()["upload_id"]
        try:
            # On n'upload que le chunk 0 sur 2
            files = {"file": ("c", b"x" * 1024, "application/octet-stream")}
            requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/chunk",
                headers=hdr, files=files, data={"chunk_index": "0"}, timeout=15,
            )
            r = requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/complete",
                headers=hdr, timeout=15,
            )
            assert r.status_code == 400, r.text
        finally:
            requests.post(
                f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/abort",
                headers=hdr, timeout=10,
            )


# ---------------------------------------------------------------------------
# /abort — cleanup
# ---------------------------------------------------------------------------
class TestChunkedAbort:
    def test_abort_marks_session_aborted(self, hdr, chantier_id):
        init = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/init",
            headers={**hdr, "Content-Type": "application/json"},
            json={"filename": "x.pdf", "mime_type": "application/pdf",
                  "total_size": 1024, "total_chunks": 1},
            timeout=15,
        )
        upload_id = init.json()["upload_id"]
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec/chunked/{upload_id}/abort",
            headers=hdr, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # Vérifie en DB (sync pymongo client)
        sess = _sync_find_one("spec_chunked_uploads", {"id": upload_id})
        assert sess is not None
        assert sess["status"] == "aborted"


# ---------------------------------------------------------------------------
# _expand_items_for_mesures — unit test (bay_width/height + validated_on_site)
# ---------------------------------------------------------------------------
class TestExpandItemsForMesures:
    def test_expand_sets_bay_width_height_and_validated_false(self):
        # Import direct (in-process)
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.spec_import import _expand_items_for_mesures

        items = [
            {"label": "Fenêtre cuisine", "block_type": "standard",
             "width_mm": 1200, "height_mm": 1500, "quantity": 2, "notes": "PVC"},
            {"label": "Porte entrée", "block_type": "porte",
             "width_mm": 900, "height_mm": 2150, "quantity": 1, "notes": ""},
        ]
        payloads = _expand_items_for_mesures(items)
        # 2 + 1 = 3 mesures
        assert len(payloads) == 3
        # Tous doivent avoir bay_width, bay_height pré-remplis
        for p in payloads:
            assert "bay_width" in p
            assert "bay_height" in p
            assert p["bay_width"] is not None and p["bay_width"] > 0
            assert p["bay_height"] is not None and p["bay_height"] > 0
            # validated_on_site initial = False
            opts = p.get("options", {})
            assert opts.get("validated_on_site") is False, (
                f"validated_on_site != False : {opts}"
            )
            assert opts.get("imported_from_spec") is True

        # Les 2 fenêtres ont bay_width=1200 / bay_height=1500
        fen = [p for p in payloads if p["block_type"] == "standard"]
        assert len(fen) == 2
        for p in fen:
            assert p["bay_width"] == 1200.0
            assert p["bay_height"] == 1500.0
        # La porte
        portes = [p for p in payloads if p["block_type"] == "porte"]
        assert len(portes) == 1
        assert portes[0]["bay_width"] == 900.0
        assert portes[0]["bay_height"] == 2150.0
        # Suffix label (1/2), (2/2) pour qty=2
        labels = sorted([p["label"] for p in fen])
        assert any("(1/2)" in lab for lab in labels)
        assert any("(2/2)" in lab for lab in labels)


# ---------------------------------------------------------------------------
# Régression : import-spec classique doit toujours marcher (petit fichier)
# ---------------------------------------------------------------------------
class TestRegressionClassicImport:
    def test_classic_import_still_works_with_small_excel(self, hdr, chantier_id):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["Désignation", "Largeur (mm)", "Hauteur (mm)", "Quantité", "Type"])
        ws.append(["Fenêtre test", 1000, 1200, 1, "Standard"])
        buf = io.BytesIO()
        wb.save(buf)
        files = {
            "file": ("mini.xlsx", buf.getvalue(),
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        r = requests.post(
            f"{API}/chantiers/{chantier_id}/import-spec",
            headers=hdr, files=files, timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "processing"
        assert data["source"] == "excel"
        assert "id" in data
