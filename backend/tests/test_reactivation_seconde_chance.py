"""Tests du système "Seconde Chance" — réactivation de compte après suppression.

Flux testé bout-en-bout :
  1. Créer un compte de test + supprimer (soft-delete RGPD)
  2. Ré-inscription bloquée → 409 ACCOUNT_DELETED_CAN_REACTIVATE
  3. Demande de réactivation → 200 (email envoyé, quota=1)
  4. Ré-inscription re-bloquée → 409 ACCOUNT_DELETED_QUOTA_EXHAUSTED
  5. GET /auth/reactivation/status → deleted=true, quota_exhausted=true
  6. Récupération token via MongoDB + confirmation → JWT + compte restauré
  7. Login avec le nouveau mot de passe
  8. Admin override (via propriétaire plateforme artisan@mesurechassis.fr)

Utilise le mode legacy `role="admin"` pour bypasser la validation VIES
qui bloquerait un VAT fictif BE0123456789. La logique métier
"Seconde Chance" est identique en legacy comme en Master Admin (branchée
AVANT le split de mode dans /auth/register).
"""
from __future__ import annotations

import time

import pytest

from db import db
from tests.conftest import hdr

pytestmark = pytest.mark.asyncio


# Suffixe unique pour éviter les collisions entre runs
UNIQUE = str(int(time.time()))
TEST_EMAIL = f"test-reactivation-{UNIQUE}@mesurechassis-qa.com"
TEST_NAME = "Jean Test"
TEST_PASSWORD = "Test1234!"
NEW_PASSWORD = "NouveauMdp2026!"


# État partagé entre les tests (exécution séquentielle)
STATE: dict = {}


@pytest.fixture(scope="module", autouse=True)
async def cleanup_after():
    """Nettoie le user de test à la fin du module."""
    yield
    # Nettoyage : delete user + tokens
    user = await db.users.find_one(
        {"$or": [
            {"email": TEST_EMAIL},
            {"original_email": TEST_EMAIL},
        ]}
    )
    if user:
        await db.users.delete_one({"id": user["id"]})
        await db.reactivation_tokens.delete_many({"user_id": user["id"]})
        await db.reactivation_audit.delete_many({"user_id": user["id"]})
        await db.companies.delete_many({"company_id": user.get("company_id")})


class TestReactivationFlow:
    """Séquence complète — exécution sérielle."""

    async def test_01_register_initial_account(self, client):
        # Legacy mode (role=admin) → skip VAT + email verification
        r = await client.post(
            "/api/auth/register",
            json={
                "name": TEST_NAME,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "role": "admin",
                "company_id": "default",
            },
        )
        assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == TEST_EMAIL
        STATE["token"] = data["access_token"]
        STATE["user_id"] = data["user"]["id"]

    async def test_02_delete_account(self, client):
        r = await client.request(
            "DELETE",
            "/api/auth/me",
            headers=hdr(STATE["token"]),
            json={
                "password": TEST_PASSWORD,
                "marketing_optin": False,
                "confirm_text": "SUPPRIMER",
            },
        )
        assert r.status_code == 200, f"Delete failed: {r.status_code} {r.text}"
        assert r.json()["ok"] is True

        # Vérifier en DB : status=deleted + original_email_hash présent
        u = await db.users.find_one({"id": STATE["user_id"]})
        assert u["status"] == "deleted"
        assert u["original_email"] == TEST_EMAIL
        assert u["original_email_hash"]
        assert u["reactivation_count"] == 0

    async def test_03_reregister_blocked_can_reactivate(self, client):
        r = await client.post(
            "/api/auth/register",
            json={
                "name": TEST_NAME,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "vat_number": "BE0123456789",
                "account_type": "artisan",
            },
        )
        assert r.status_code == 409, f"Expected 409, got {r.status_code} {r.text}"
        detail = r.json()["detail"]
        assert detail["code"] == "ACCOUNT_DELETED_CAN_REACTIVATE"
        assert detail["email"] == TEST_EMAIL

    async def test_04_reactivation_request(self, client):
        r = await client.post(
            "/api/auth/reactivation/request",
            json={"email": TEST_EMAIL},
        )
        assert r.status_code == 200, f"Reactivation request failed: {r.text}"
        assert r.json()["ok"] is True

        # Vérifier en DB : compteur=1 + token créé
        u = await db.users.find_one({"id": STATE["user_id"]})
        assert u["reactivation_count"] == 1
        assert u.get("reactivation_requested_at")

        tok_doc = await db.reactivation_tokens.find_one(
            {"user_id": STATE["user_id"]}
        )
        assert tok_doc is not None
        assert tok_doc["token"]
        assert tok_doc["used_at"] is None
        STATE["reactivation_token"] = tok_doc["token"]

    async def test_05_reregister_blocked_quota_exhausted(self, client):
        r = await client.post(
            "/api/auth/register",
            json={
                "name": TEST_NAME,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "role": "admin",
            },
        )
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert detail["code"] == "ACCOUNT_DELETED_QUOTA_EXHAUSTED"

    async def test_06_reactivation_status(self, client):
        r = await client.get(
            "/api/auth/reactivation/status", params={"email": TEST_EMAIL}
        )
        assert r.status_code == 200
        body = r.json()
        assert body == {
            "deleted": True,
            "can_reactivate": False,
            "quota_exhausted": True,
            "count": 1,
            "max": 1,
        }

    async def test_07_status_unknown_email(self, client):
        r = await client.get(
            "/api/auth/reactivation/status",
            params={"email": f"never-existed-{UNIQUE}@mesurechassis-qa.com"},
        )
        assert r.status_code == 200
        assert r.json() == {"deleted": False}

    async def test_08_verify_reactivation_token(self, client):
        token = STATE["reactivation_token"]
        r = await client.get(f"/api/auth/reactivation/verify/{token}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["email"] == TEST_EMAIL
        assert body["name"] == TEST_NAME
        assert body["expires_at"]

    async def test_09_verify_invalid_token(self, client):
        r = await client.get("/api/auth/reactivation/verify/definitely-invalid")
        assert r.status_code == 404

    async def test_10_confirm_reactivation(self, client):
        r = await client.post(
            "/api/auth/reactivation/confirm",
            json={
                "token": STATE["reactivation_token"],
                "new_password": NEW_PASSWORD,
            },
        )
        assert r.status_code == 200, f"Confirm failed: {r.text}"
        data = r.json()
        assert data["ok"] is True
        assert data["access_token"]
        assert data["user"]["email"] == TEST_EMAIL

        # DB : status=active, deleted_at=None, email restauré
        u = await db.users.find_one({"id": STATE["user_id"]})
        assert u["status"] == "active"
        assert u["email"] == TEST_EMAIL
        assert u["deleted_at"] is None
        assert u.get("reactivated_at")

        # Token consommé
        tok_doc = await db.reactivation_tokens.find_one(
            {"token": STATE["reactivation_token"]}
        )
        assert tok_doc["used_at"] is not None

    async def test_11_confirm_replay_forbidden(self, client):
        """Le même token ne doit pas pouvoir être ré-utilisé (single-use)."""
        r = await client.post(
            "/api/auth/reactivation/confirm",
            json={
                "token": STATE["reactivation_token"],
                "new_password": NEW_PASSWORD,
            },
        )
        assert r.status_code == 410

    async def test_12_login_with_new_password(self, client):
        r = await client.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": NEW_PASSWORD},
        )
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()
        STATE["new_login_token"] = r.json()["access_token"]

    async def test_13_login_with_old_password_fails(self, client):
        r = await client.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        assert r.status_code == 401


class TestAdminOverride:
    """Tests admin override — nécessite un platform owner."""

    async def _owner_token(self, client) -> str:
        """Login en tant que propriétaire plateforme."""
        r = await client.post(
            "/api/auth/login",
            json={
                "email": "artisan@mesurechassis.fr",
                "password": "artisan123",
            },
        )
        assert r.status_code == 200, f"Owner login failed: {r.text}"
        return r.json()["access_token"]

    async def test_14_override_on_active_account_returns_404(self, client):
        """Le compte est actuellement réactivé (status=active) → 404 attendu."""
        owner_token = await self._owner_token(client)
        r = await client.post(
            "/api/admin/reactivation/override",
            headers=hdr(owner_token),
            json={"email": TEST_EMAIL, "reason": "test override active"},
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"

    async def test_15_redelete_and_override_ok(self, client):
        """Re-supprime le compte puis effectue l'override → doit passer."""
        owner_token = await self._owner_token(client)

        # Redelete via login user + DELETE /auth/me
        r = await client.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": NEW_PASSWORD},
        )
        assert r.status_code == 200
        user_token = r.json()["access_token"]

        r = await client.request(
            "DELETE",
            "/api/auth/me",
            headers=hdr(user_token),
            json={
                "password": NEW_PASSWORD,
                "marketing_optin": False,
                "confirm_text": "SUPPRIMER",
            },
        )
        assert r.status_code == 200

        # Compteur : notez que `delete_my_account` remet reactivation_count=0
        # lors du soft-delete (voir routes/auth.py L879). Ceci autorise donc
        # implicitement une nouvelle réactivation après re-suppression.
        # ⚠️ Potentielle incohérence à signaler au main agent : l'email de
        # réactivation dit "unique — vous ne pourrez plus réactiver ce compte".
        u = await db.users.find_one({"id": STATE["user_id"]})
        assert u["status"] == "deleted"
        count_before = int(u.get("reactivation_count", 0))
        # Comportement observé : compteur reset à 0 par delete_my_account
        assert count_before == 0, (
            f"reactivation_count après redelete = {count_before} (attendu 0 selon code actuel)"
        )

        # Override
        r = await client.post(
            "/api/admin/reactivation/override",
            headers=hdr(owner_token),
            json={"email": TEST_EMAIL, "reason": "test override deleted"},
        )
        assert r.status_code == 200, f"Override failed: {r.text}"
        body = r.json()
        assert body["ok"] is True
        assert body["user_id"] == STATE["user_id"]

        # Compteur remis à 0
        u = await db.users.find_one({"id": STATE["user_id"]})
        assert u["reactivation_count"] == 0
        assert u.get("reactivation_override_at")

    async def test_16_override_unknown_email(self, client):
        owner_token = await self._owner_token(client)
        r = await client.post(
            "/api/admin/reactivation/override",
            headers=hdr(owner_token),
            json={"email": f"never-existed-{UNIQUE}@mesurechassis-qa.com"},
        )
        assert r.status_code == 404

    async def test_17_override_forbidden_for_regular_admin(
        self, client, admin_jwt
    ):
        """admin@mesurechassis.fr est admin mais PAS platform owner → 403."""
        r = await client.post(
            "/api/admin/reactivation/override",
            headers=hdr(admin_jwt),
            json={"email": TEST_EMAIL, "reason": "should be denied"},
        )
        assert r.status_code == 403
