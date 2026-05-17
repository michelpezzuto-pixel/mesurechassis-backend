"""Tests exports : RBAC (Commercial = PDF only) + contenu enrichi + bug latin-1."""
from __future__ import annotations

import pytest
import pytest_asyncio

from tests.conftest import PYTEST_TAG, hdr

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def chantier_with_mesure(client, commercial_jwt):
    """Chantier avec une mesure pour valider les exports."""
    r = await client.post(
        "/api/chantiers",
        headers=hdr(commercial_jwt),
        json={
            "client_name": f"{PYTEST_TAG}export",
            "address": "7 rue Export",
            "site_photos": [
                {
                    "uri": "data:image/png;base64,iVBORw0KGgo",
                    "caption": "Photo test caption",
                }
            ],
        },
    )
    cid = r.json()["id"]
    await client.post(
        "/api/mesures",
        headers=hdr(commercial_jwt),
        json={
            "chantier_id": cid,
            "block_type": "standard",
            "label": "Salon",
            "bay_width": 1500,
            "bay_height": 2400,
            "bay_diagonal_1": 2828,
            "bay_diagonal_2": 2828,
            "floor_reserve": 50,
            "bloc_thickness": 200,
            "wall_type": "ite",
            "insulation_thickness": 120,
            "renovation_mode": True,
            "width_top": 1500,
            "width_bottom": 1498,
            "height_left": 2400,
            "height_right": 2402,
        },
    )
    return cid


class TestExportRBAC:
    async def test_commercial_pdf_ok(
        self, client, commercial_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.pdf",
            headers=hdr(commercial_jwt),
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")

    async def test_commercial_json_forbidden(
        self, client, commercial_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.json",
            headers=hdr(commercial_jwt),
        )
        assert r.status_code == 403

    async def test_commercial_csv_forbidden(
        self, client, commercial_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.csv",
            headers=hdr(commercial_jwt),
        )
        assert r.status_code == 403

    async def test_commercial_xlsx_forbidden(
        self, client, commercial_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.xlsx",
            headers=hdr(commercial_jwt),
        )
        assert r.status_code == 403

    async def test_tech_all_formats_ok(
        self, client, tech_jwt, chantier_with_mesure
    ):
        for ext in ("pdf", "json", "csv", "xlsx"):
            r = await client.get(
                f"/api/chantiers/{chantier_with_mesure}/export.{ext}",
                headers=hdr(tech_jwt),
            )
            assert r.status_code == 200, f".{ext} should be 200 for tech"

    async def test_admin_all_formats_ok(
        self, client, admin_jwt, chantier_with_mesure
    ):
        for ext in ("pdf", "json", "csv", "xlsx"):
            r = await client.get(
                f"/api/chantiers/{chantier_with_mesure}/export.{ext}",
                headers=hdr(admin_jwt),
            )
            assert r.status_code == 200


class TestExportContent:
    async def test_json_schema_v2_full(
        self, client, tech_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.json",
            headers=hdr(tech_jwt),
        )
        data = r.json()
        assert data["schema_version"] == "mc.v2"
        assert data["openings_count"] == 1
        op = data["openings"][0]
        assert op["renovation_mode"] is True
        assert op["shape"] == "rectangular"
        assert op["dimensions_mm"]["width"] == 1500
        assert op["dimensions_mm"]["width_top"] == 1500
        assert op["dimensions_mm"]["height_right"] == 2402
        # Construction
        assert op["construction"]["wall_type"] == "ite"
        assert op["construction"]["wall_type_label"] == "ITE"
        assert op["construction"]["bloc_thickness_mm"] == 200
        # Photos
        assert data["site_photos_count"] == 1
        assert data["site_photos"][0]["caption"] == "Photo test caption"

    async def test_csv_has_new_columns(
        self, client, tech_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.csv",
            headers=hdr(tech_jwt),
        )
        body = r.content.decode("utf-8-sig")
        # En-tête enrichie
        for col in ("L. haut", "L. bas", "H. gauche", "H. droite", "Rénovation"):
            assert col in body, f"Missing column: {col}"
        # Bloc photos
        assert "[PHOTOS ANTI-LITIGE]" in body
        assert "Photo test caption" in body

    async def test_pdf_is_valid(
        self, client, tech_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.pdf",
            headers=hdr(tech_jwt),
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 1500

    async def test_xlsx_is_valid(
        self, client, tech_jwt, chantier_with_mesure
    ):
        r = await client.get(
            f"/api/chantiers/{chantier_with_mesure}/export.xlsx",
            headers=hdr(tech_jwt),
        )
        assert r.status_code == 200
        # ZIP magic (xlsx = zip)
        assert r.content[:2] == b"PK"
        assert len(r.content) > 1000


class TestExportFilenameUnicode:
    async def test_apostrophe_does_not_crash(
        self, client, commercial_jwt, admin_jwt, tech_jwt
    ):
        """Régression : nom avec apostrophes ne doit pas crasher (latin-1)."""
        r = await client.post(
            "/api/chantiers",
            headers=hdr(commercial_jwt),
            json={
                "client_name": f"{PYTEST_TAG}M. d'Aujourd'hui",
                "address": "8 rue de l'Église",
            },
        )
        cid = r.json()["id"]
        for ext in ("pdf", "csv", "xlsx", "json"):
            r = await client.get(
                f"/api/chantiers/{cid}/export.{ext}",
                headers=hdr(tech_jwt),
            )
            assert r.status_code == 200, f".{ext} crashed on apostrophe"
            # Vérifie que le header Content-Disposition est latin-1 safe
            cd = r.headers.get("content-disposition", "")
            cd.encode("latin-1")  # ne doit pas lever
