"""Couverture complémentaire : routes/stats.py, routes/company.py,
routes/feedbacks.py, routes/auth.py. Ciblés sur les chemins non couverts
par les tests existants pour booster significativement la couverture.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from tests.conftest import PYTEST_TAG, hdr

pytestmark = pytest.mark.asyncio


# ============================================================================
# routes/stats.py  (18% → ~85%)
# ============================================================================
class TestStatsCompany:
    async def test_stats_company_admin_ok(self, client, admin_jwt):
        r = await client.get("/api/stats/company", headers=hdr(admin_jwt))
        assert r.status_code == 200
        data = r.json()
        # Toutes les clés attendues sont présentes
        assert "total_chantiers" in data
        assert "by_status" in data
        assert "closure_rate" in data
        assert "total_mesures" in data
        assert "total_alerts" in data
        assert "by_technician" in data
        # Les 5 statuts métier sont initialisés à 0 ou positifs
        for st in ("devis_a_faire", "technique_a_valider", "en_commande",
                   "en_fabrication", "cloture"):
            assert st in data["by_status"]
            assert data["by_status"][st] >= 0

    async def test_stats_company_commercial_forbidden(
        self, client, commercial_jwt
    ):
        r = await client.get("/api/stats/company", headers=hdr(commercial_jwt))
        assert r.status_code == 403

    async def test_stats_company_tech_forbidden(self, client, tech_jwt):
        r = await client.get("/api/stats/company", headers=hdr(tech_jwt))
        assert r.status_code == 403


class TestStatsCommercials:
    async def test_stats_commercials_admin_ok(self, client, admin_jwt):
        r = await client.get("/api/stats/commercials", headers=hdr(admin_jwt))
        assert r.status_code == 200
        data = r.json()
        assert "commercials" in data
        assert "total_created" in data
        assert "total_converted" in data
        assert "global_conversion_rate" in data
        # Chaque ligne expose les bons champs
        for row in data["commercials"]:
            for f in ("user_id", "name", "email", "created", "converted",
                      "conversion_rate"):
                assert f in row

    async def test_stats_commercials_forbidden_for_non_admin(
        self, client, commercial_jwt, tech_jwt
    ):
        for tok in (commercial_jwt, tech_jwt):
            r = await client.get(
                "/api/stats/commercials", headers=hdr(tok)
            )
            assert r.status_code == 403

    async def test_stats_commercials_pdf_export(self, client, admin_jwt):
        r = await client.get(
            "/api/stats/commercials/export.pdf", headers=hdr(admin_jwt)
        )
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")
        assert len(r.content) > 1000

    async def test_stats_commercials_pdf_forbidden_for_commercial(
        self, client, commercial_jwt
    ):
        r = await client.get(
            "/api/stats/commercials/export.pdf", headers=hdr(commercial_jwt)
        )
        assert r.status_code == 403


# ============================================================================
# routes/company.py  (42% → ~85%)
# ============================================================================
class TestCompanyProfile:
    async def test_get_profile_any_authenticated_user(
        self, client, commercial_jwt, tech_jwt
    ):
        for tok in (commercial_jwt, tech_jwt):
            r = await client.get("/api/company/profile", headers=hdr(tok))
            assert r.status_code == 200
            data = r.json()
            assert data["company_id"] == "default"
            assert "artisan_mode" in data
            assert "subscription_status" in data

    async def test_patch_profile_admin_only(
        self, client, admin_jwt, commercial_jwt, tech_jwt
    ):
        # Admin can patch
        r = await client.patch(
            "/api/company/profile",
            headers=hdr(admin_jwt),
            json={"name": "PYTEST_company_name"},
        )
        assert r.status_code == 200
        # Commercial / Tech forbidden
        for tok in (commercial_jwt, tech_jwt):
            r = await client.patch(
                "/api/company/profile",
                headers=hdr(tok),
                json={"name": "should-fail"},
            )
            assert r.status_code == 403
        # Restore
        await client.patch(
            "/api/company/profile",
            headers=hdr(admin_jwt),
            json={"name": "default"},
        )


class TestPlatformSubscription:
    """L'endpoint /platform/.../subscription est protégé par un token sparé."""

    async def test_platform_endpoint_requires_token(self, client):
        r = await client.post(
            "/api/platform/companies/default/subscription",
            json={"extend_days": 30},
        )
        assert r.status_code == 403

    async def test_platform_endpoint_wrong_token(self, client):
        r = await client.post(
            "/api/platform/companies/default/subscription",
            headers={"X-Platform-Token": "wrong"},
            json={"extend_days": 30},
        )
        assert r.status_code == 403

    async def test_platform_extend_days_with_correct_token(self, client):
        import os
        token = os.getenv("PLATFORM_ADMIN_TOKEN", "mc-platform-2026")
        # Note : on étend de 90j seulement (= durée du trial) pour ne pas
        # polluer l'état production après les tests (artefact 365j observé).
        r = await client.post(
            "/api/platform/companies/default/subscription",
            headers={"X-Platform-Token": token},
            json={"extend_days": 90},
        )
        assert r.status_code == 200
        # subscription_expires_at should be roughly +90 days
        data = r.json()
        assert "subscription_expires_at" in data

    async def test_platform_set_status_active(self, client):
        import os
        token = os.getenv("PLATFORM_ADMIN_TOKEN", "mc-platform-2026")
        r = await client.post(
            "/api/platform/companies/default/subscription",
            headers={"X-Platform-Token": token},
            json={"subscription_status": "active"},
        )
        assert r.status_code == 200
        assert r.json()["subscription_status"] == "active"

    async def test_platform_invalid_status(self, client):
        import os
        token = os.getenv("PLATFORM_ADMIN_TOKEN", "mc-platform-2026")
        r = await client.post(
            "/api/platform/companies/default/subscription",
            headers={"X-Platform-Token": token},
            json={"subscription_status": "foobar"},
        )
        assert r.status_code == 400

    async def test_platform_empty_payload(self, client):
        import os
        token = os.getenv("PLATFORM_ADMIN_TOKEN", "mc-platform-2026")
        r = await client.post(
            "/api/platform/companies/default/subscription",
            headers={"X-Platform-Token": token},
            json={},
        )
        assert r.status_code == 400


# ============================================================================
# routes/feedbacks.py  (65% → ~95%)
# ============================================================================
class TestFeedbacks:
    async def test_create_and_list_feedback(
        self, client, commercial_jwt, admin_jwt
    ):
        r = await client.post(
            "/api/feedbacks",
            headers=hdr(commercial_jwt),
            json={
                "page_context": f"{PYTEST_TAG}page_dashboard",
                "user_comment": "Bouton mal aligné",
                "encoded_data_snapshot": {"key": "value"},
            },
        )
        assert r.status_code == 200
        fb_id = r.json()["id"]
        # List (admin only)
        r2 = await client.get("/api/feedbacks", headers=hdr(admin_jwt))
        assert r2.status_code == 200
        assert any(f["id"] == fb_id for f in r2.json())
        # Delete by admin
        r3 = await client.delete(
            f"/api/feedbacks/{fb_id}", headers=hdr(admin_jwt)
        )
        assert r3.status_code == 200

    async def test_list_feedbacks_forbidden_for_non_admin(
        self, client, commercial_jwt, tech_jwt
    ):
        for tok in (commercial_jwt, tech_jwt):
            r = await client.get("/api/feedbacks", headers=hdr(tok))
            assert r.status_code == 403

    async def test_delete_feedback_forbidden_for_non_admin(
        self, client, commercial_jwt, tech_jwt
    ):
        # Create one as tech
        r = await client.post(
            "/api/feedbacks",
            headers=hdr(tech_jwt),
            json={
                "page_context": f"{PYTEST_TAG}delete_attempt",
                "user_comment": "test",
            },
        )
        fb_id = r.json()["id"]
        r2 = await client.delete(
            f"/api/feedbacks/{fb_id}", headers=hdr(commercial_jwt)
        )
        assert r2.status_code == 403


# ============================================================================
# routes/auth.py  (61% → ~95%)
# ============================================================================
class TestUserManagement:
    async def test_register_new_user(self, client):
        email = f"PYTEST_user_{uuid.uuid4().hex[:8]}@example.com"
        r = await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST New User",
                "email": email,
                "password": "pass1234",
                "role": "technician",
                "company_id": "default",
            },
        )
        assert r.status_code == 200
        data = r.json()
        # Backend lowercases emails on register
        assert data["user"]["email"] == email.lower()
        assert "access_token" in data

    async def test_register_invalid_role(self, client):
        r = await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST Bad",
                "email": f"PYTEST_bad_{uuid.uuid4().hex[:8]}@example.com",
                "password": "pass1234",
                "role": "superhero",
            },
        )
        assert r.status_code == 400

    async def test_register_duplicate_email(self, client):
        email = f"PYTEST_dup_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/auth/register",
            json={"name": "a", "email": email, "password": "x12345",
                  "role": "technician"},
        )
        r = await client.post(
            "/api/auth/register",
            json={"name": "b", "email": email, "password": "x12345",
                  "role": "technician"},
        )
        assert r.status_code == 400

    async def test_list_users_visible_to_authenticated(
        self, client, admin_jwt, commercial_jwt, tech_jwt
    ):
        for tok in (admin_jwt, commercial_jwt, tech_jwt):
            r = await client.get("/api/users", headers=hdr(tok))
            assert r.status_code == 200
            assert isinstance(r.json(), list)
            assert len(r.json()) >= 3  # admin + commercial + tech seeded

    async def test_set_push_token(self, client, tech_jwt):
        r = await client.post(
            "/api/auth/push-token",
            headers=hdr(tech_jwt),
            json={"push_token": "ExponentPushToken[fake_test]"},
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_set_push_token_null(self, client, tech_jwt):
        """Logout-side : on doit pouvoir effacer le token (push_token=null)."""
        r = await client.post(
            "/api/auth/push-token",
            headers=hdr(tech_jwt),
            json={"push_token": None},
        )
        assert r.status_code == 200


# ============================================================================
# routes/mesures.py  (46% → ~85%)  — cas non couverts
# ============================================================================
@pytest_asyncio.fixture
async def chantier_for_mesures(client, commercial_jwt):
    r = await client.post(
        "/api/chantiers",
        headers=hdr(commercial_jwt),
        json={
            "client_name": f"{PYTEST_TAG}mesure_cov",
            "address": "9 rue Couverture",
        },
    )
    return r.json()["id"]


class TestMesuresEdgeCases:
    async def test_invalid_block_type_returns_400(
        self, client, tech_jwt, chantier_for_mesures
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": chantier_for_mesures,
                "block_type": "hexagon",  # invalid
                "label": "X",
            },
        )
        assert r.status_code == 400

    async def test_mesure_on_nonexistent_chantier_returns_404(
        self, client, tech_jwt
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": "does-not-exist",
                "block_type": "standard",
                "label": "X",
            },
        )
        assert r.status_code == 404

    async def test_get_mesure_by_id(
        self, client, tech_jwt, chantier_for_mesures
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": chantier_for_mesures,
                "block_type": "standard",
                "label": "GetByID",
                "bay_width": 1000,
            },
        )
        mid = r.json()["id"]
        r2 = await client.get(
            f"/api/mesures/{mid}", headers=hdr(tech_jwt)
        )
        assert r2.status_code == 200
        assert r2.json()["label"] == "GetByID"

    async def test_get_mesure_nonexistent_returns_404(
        self, client, tech_jwt
    ):
        r = await client.get(
            "/api/mesures/does-not-exist", headers=hdr(tech_jwt)
        )
        assert r.status_code == 404

    async def test_list_mesures_for_chantier(
        self, client, tech_jwt, chantier_for_mesures
    ):
        await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": chantier_for_mesures,
                "block_type": "trapeze",
                "label": "TrapTest",
                "width_small": 1000,
                "width_intermediate": 1200,
                "height_small": 1500,
                "height_large": 1700,
            },
        )
        r = await client.get(
            f"/api/chantiers/{chantier_for_mesures}/mesures",
            headers=hdr(tech_jwt),
        )
        assert r.status_code == 200
        assert len(r.json()) >= 1
        # Trapèze : vérifier que slope_angle_deg est calculé
        trap = next(
            (m for m in r.json() if m["block_type"] == "trapeze"), None
        )
        if trap:
            assert trap.get("slope_angle_deg") is not None

    async def test_invalid_wall_type_returns_422(
        self, client, tech_jwt, chantier_for_mesures
    ):
        r = await client.post(
            "/api/mesures",
            headers=hdr(tech_jwt),
            json={
                "chantier_id": chantier_for_mesures,
                "block_type": "standard",
                "label": "BadWall",
                "wall_type": "marshmallow",  # not in VALID_WALL_TYPES
            },
        )
        assert r.status_code == 422


# ============================================================================
# routes/chantiers.py  (60% → ~85%) — signature endpoints
# ============================================================================
@pytest_asyncio.fixture
async def chantier_for_signature(client, commercial_jwt):
    r = await client.post(
        "/api/chantiers",
        headers=hdr(commercial_jwt),
        json={
            "client_name": f"{PYTEST_TAG}signature_cov",
            "address": "10 rue Sign",
        },
    )
    return r.json()["id"]


class TestSignatures:
    async def test_save_and_delete_signature(
        self, client, commercial_jwt, chantier_for_signature
    ):
        r = await client.post(
            f"/api/chantiers/{chantier_for_signature}/signature",
            headers=hdr(commercial_jwt),
            json={"signature": "data:image/png;base64,iVBORw0KGgo="},
        )
        assert r.status_code == 200
        assert r.json()["client_signature"] is not None
        # Delete
        r2 = await client.delete(
            f"/api/chantiers/{chantier_for_signature}/signature",
            headers=hdr(commercial_jwt),
        )
        assert r2.status_code == 200
        assert r2.json()["client_signature"] is None

    async def test_empty_signature_returns_400(
        self, client, commercial_jwt, chantier_for_signature
    ):
        r = await client.post(
            f"/api/chantiers/{chantier_for_signature}/signature",
            headers=hdr(commercial_jwt),
            json={"signature": "   "},
        )
        assert r.status_code == 400

    async def test_signature_on_nonexistent_chantier_returns_404(
        self, client, commercial_jwt
    ):
        r = await client.post(
            "/api/chantiers/does-not-exist/signature",
            headers=hdr(commercial_jwt),
            json={"signature": "data:image/png;base64,iVBORw0KGgo="},
        )
        assert r.status_code == 404
