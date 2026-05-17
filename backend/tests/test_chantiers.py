"""Tests CRUD chantiers + pipeline 4-étapes."""
from __future__ import annotations

import pytest

from tests.conftest import PYTEST_TAG, hdr

pytestmark = pytest.mark.asyncio


class TestChantierCRUD:
    async def test_create_as_admin(self, client, admin_jwt):
        r = await client.post(
            "/api/chantiers",
            headers=hdr(admin_jwt),
            json={
                "client_name": f"{PYTEST_TAG}admin",
                "address": "1 rue de Test",
                "status": "devis_a_faire",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["client_name"] == f"{PYTEST_TAG}admin"
        assert data["status"] == "devis_a_faire"

    async def test_create_as_commercial(self, client, commercial_jwt):
        r = await client.post(
            "/api/chantiers",
            headers=hdr(commercial_jwt),
            json={
                "client_name": f"{PYTEST_TAG}com",
                "address": "2 rue de Test",
            },
        )
        assert r.status_code == 200

    async def test_create_as_tech_forbidden(self, client, tech_jwt):
        r = await client.post(
            "/api/chantiers",
            headers=hdr(tech_jwt),
            json={
                "client_name": f"{PYTEST_TAG}tech",
                "address": "3 rue de Test",
            },
        )
        assert r.status_code == 403

    async def test_list_filter_q(self, client, admin_jwt):
        r = await client.get(
            "/api/chantiers",
            headers=hdr(admin_jwt),
            params={"q": PYTEST_TAG},
        )
        assert r.status_code == 200
        items = r.json()
        assert all(PYTEST_TAG in c["client_name"] for c in items)
        assert len(items) >= 1

    async def test_get_nonexistent_returns_404(self, client, admin_jwt):
        r = await client.get(
            "/api/chantiers/does-not-exist", headers=hdr(admin_jwt)
        )
        assert r.status_code == 404


class TestPipelineTransitions:
    """Vérifie les 4 transitions du pipeline."""

    async def test_pipeline_full_advance(self, client, admin_jwt):
        # 1) Création à "devis_a_faire" (À mesurer)
        r = await client.post(
            "/api/chantiers",
            headers=hdr(admin_jwt),
            json={
                "client_name": f"{PYTEST_TAG}pipeline",
                "address": "4 rue Pipeline",
            },
        )
        assert r.status_code == 200
        cid = r.json()["id"]
        assert r.json()["status"] == "devis_a_faire"

        # 2) Advance to technique_a_valider
        r = await client.patch(
            f"/api/chantiers/{cid}",
            headers=hdr(admin_jwt),
            json={"status": "technique_a_valider"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "technique_a_valider"

        # 3) Advance to en_fabrication
        r = await client.patch(
            f"/api/chantiers/{cid}",
            headers=hdr(admin_jwt),
            json={"status": "en_fabrication"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "en_fabrication"

        # 4) Advance to cloture
        r = await client.patch(
            f"/api/chantiers/{cid}",
            headers=hdr(admin_jwt),
            json={"status": "cloture"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cloture"

    async def test_invalid_status_returns_400(self, client, admin_jwt):
        # Créer un chantier puis essayer un statut invalide
        r = await client.post(
            "/api/chantiers",
            headers=hdr(admin_jwt),
            json={
                "client_name": f"{PYTEST_TAG}invalid_status",
                "address": "5 rue X",
            },
        )
        cid = r.json()["id"]
        r = await client.patch(
            f"/api/chantiers/{cid}",
            headers=hdr(admin_jwt),
            json={"status": "foobar"},
        )
        assert r.status_code == 400
