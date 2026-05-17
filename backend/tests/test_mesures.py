"""Tests CRUD mesures + RBAC strict (Admin ne peut PAS éditer)."""
from __future__ import annotations

import pytest
import pytest_asyncio

from tests.conftest import PYTEST_TAG, hdr

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def chantier_id(client, commercial_jwt):
    """Crée un chantier de travail pour les tests de mesures."""
    r = await client.post(
        "/api/chantiers",
        headers=hdr(commercial_jwt),
        json={
            "client_name": f"{PYTEST_TAG}mesures",
            "address": "6 rue Mesure",
        },
    )
    assert r.status_code == 200
    return r.json()["id"]


class TestMesureRBAC:
    async def test_admin_create_mesure_forbidden(
        self, client, admin_jwt, chantier_id
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(admin_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Salon",
                "bay_width": 1500,
                "bay_height": 2400,
            },
        )
        assert r.status_code == 403

    async def test_commercial_create_mesure_ok(
        self, client, commercial_jwt, chantier_id
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(commercial_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Salon",
                "bay_width": 1500,
                "bay_height": 2400,
            },
        )
        assert r.status_code == 200

    async def test_tech_create_mesure_ok(
        self, client, tech_jwt, chantier_id
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Cuisine",
                "bay_width": 1200,
                "bay_height": 2100,
            },
        )
        assert r.status_code == 200

    async def test_admin_patch_mesure_forbidden(
        self, client, admin_jwt, commercial_jwt, chantier_id
    ):
        # Create one via commercial
        r = await client.post(
            "/api/mesures",
            headers=hdr(commercial_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "X",
                "bay_width": 1000,
                "bay_height": 2000,
            },
        )
        mid = r.json()["id"]
        # Admin tries to patch
        r = await client.patch(
            f"/api/mesures/{mid}",
            headers=hdr(admin_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "X-Admin",
                "bay_width": 1100,
                "bay_height": 2000,
            },
        )
        assert r.status_code == 403


class TestMesureAlerts:
    async def test_faux_aplomb_alert(
        self, client, commercial_jwt, chantier_id
    ):
        """Écarts > 5mm sur les largeurs déclenchent l'alerte 'Faux-aplomb'."""
        r = await client.post(
            "/api/mesures",
            headers=hdr(commercial_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Test alerte",
                "width_top": 1500,
                "width_middle": 1502,
                "width_bottom": 1510,  # 10mm écart → alerte
            },
        )
        assert r.status_code == 200
        alerts = r.json()["alerts"]
        assert any("Faux-aplomb" in a for a in alerts)

    async def test_hors_equerre_alert(
        self, client, commercial_jwt, chantier_id
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(commercial_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Diag",
                "diag_1": 2900,
                "diag_2": 2910,  # 10mm écart
            },
        )
        assert r.status_code == 200
        alerts = r.json()["alerts"]
        assert any("équerre" in a.lower() for a in alerts)

    async def test_no_alert_clean_data(
        self, client, commercial_jwt, chantier_id
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(commercial_jwt),
            json={
                "chantier_id": chantier_id,
                "block_type": "standard",
                "label": "Clean",
                "width_top": 1500,
                "width_middle": 1500,
                "width_bottom": 1500,
            },
        )
        assert r.status_code == 200
        assert r.json()["alerts"] == []
