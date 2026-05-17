"""Tests email verification + invitations workflow."""
import uuid

import pytest


def hdr(jwt: str) -> dict:
    return {"Authorization": f"Bearer {jwt}"}


# ============================================================================
# Master Admin self-signup with email verification
# ============================================================================
class TestMasterAdminVerification:
    async def test_register_master_admin_pending(self, client):
        email = f"PYTEST_master_{uuid.uuid4().hex[:8]}@example.com"
        r = await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST Master",
                "email": email,
                "password": "secret12",
                "company_name": "PYTEST Société",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # Pas de token : compte pending
        assert "access_token" not in data
        assert data["user"]["status"] == "pending_verification"
        assert data["user"]["role"] == "admin"
        assert "verification_link" in data
        assert "token=" in data["verification_link"]

    async def test_login_pending_user_blocked(self, client):
        email = f"PYTEST_login_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST Pending",
                "email": email,
                "password": "secret12",
                "company_name": "PYTEST Co",
            },
        )
        r = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "secret12"},
        )
        assert r.status_code == 403
        detail = r.json().get("detail", {})
        assert detail.get("code") == "email_not_verified"

    async def test_verify_then_login_ok(self, client):
        email = f"PYTEST_verif_{uuid.uuid4().hex[:8]}@example.com"
        reg = await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST Verif",
                "email": email,
                "password": "secret12",
                "company_name": "PYTEST Verify Co",
            },
        )
        link = reg.json()["verification_link"]
        # Le lien est de la forme `/verify?token=xxx`
        token = link.split("token=", 1)[1]

        r = await client.post("/api/auth/verify", json={"token": token})
        assert r.status_code == 200, r.text
        assert "access_token" in r.json()
        assert r.json()["user"]["status"] == "active"

        # Token réutilisé → 400
        r2 = await client.post("/api/auth/verify", json={"token": token})
        assert r2.status_code == 400

        # Login fonctionne désormais
        r3 = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "secret12"},
        )
        assert r3.status_code == 200
        assert r3.json()["user"]["status"] == "active"

    async def test_verify_invalid_token(self, client):
        r = await client.post(
            "/api/auth/verify", json={"token": "not-a-real-token"}
        )
        assert r.status_code == 400

    async def test_resend_verification(self, client):
        email = f"PYTEST_resend_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST Resend",
                "email": email,
                "password": "secret12",
                "company_name": "PYTEST Resend Co",
            },
        )
        r = await client.post(
            "/api/auth/resend-verification", json={"email": email}
        )
        assert r.status_code == 200
        assert "verification_link" in r.json()


# ============================================================================
# Team invitations (Commercial / Technicien)
# ============================================================================
class TestInvitations:
    async def test_invite_requires_admin(
        self, client, commercial_jwt, tech_jwt
    ):
        body = {
            "name": "Invité",
            "email": f"PYTEST_inv_{uuid.uuid4().hex[:8]}@example.com",
            "role": "commercial",
        }
        for tok in [commercial_jwt, tech_jwt]:
            r = await client.post(
                "/api/admin/invitations", json=body, headers=hdr(tok)
            )
            # Si artisan_mode actif sur 'default', le commercial/tech aurait
            # le bypass. Sur conftest, l'artisan_mode est désactivé.
            assert r.status_code in (403,)

    async def test_invite_invalid_role(self, client, admin_jwt):
        r = await client.post(
            "/api/admin/invitations",
            json={
                "name": "X",
                "email": f"PYTEST_inv_{uuid.uuid4().hex[:8]}@example.com",
                "role": "superhero",
            },
            headers=hdr(admin_jwt),
        )
        assert r.status_code == 400

    async def test_invite_and_accept_flow(self, client, admin_jwt):
        email = f"PYTEST_invflow_{uuid.uuid4().hex[:8]}@example.com"
        inv = await client.post(
            "/api/admin/invitations",
            json={"name": "Nouveau Tech", "email": email, "role": "technician"},
            headers=hdr(admin_jwt),
        )
        assert inv.status_code == 200, inv.text
        data = inv.json()
        assert data["user"]["status"] == "pending_verification"
        link = data["verification_link"]
        token = link.split("token=", 1)[1]

        # GET invitation info (public) — email lowercased server-side
        info = await client.get(f"/api/admin/invitations/{token}")
        assert info.status_code == 200
        assert info.json()["email"] == email.lower()
        assert info.json()["role"] == "technician"

        # Accept invitation
        acc = await client.post(
            f"/api/admin/invitations/{token}/accept",
            json={"password": "newpass12", "name": "Nouveau Tech V2"},
        )
        assert acc.status_code == 200
        assert acc.json()["user"]["status"] == "active"
        assert acc.json()["user"]["name"] == "Nouveau Tech V2"

        # Le token est consommé
        info2 = await client.get(f"/api/admin/invitations/{token}")
        assert info2.status_code == 400

        # Le user peut désormais se connecter
        login = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "newpass12"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["status"] == "active"
        assert login.json()["user"]["role"] == "technician"

    async def test_invite_duplicate_email(self, client, admin_jwt):
        email = f"PYTEST_dup_inv_{uuid.uuid4().hex[:8]}@example.com"
        r1 = await client.post(
            "/api/admin/invitations",
            json={"name": "X", "email": email, "role": "commercial"},
            headers=hdr(admin_jwt),
        )
        assert r1.status_code == 200
        r2 = await client.post(
            "/api/admin/invitations",
            json={"name": "Y", "email": email, "role": "commercial"},
            headers=hdr(admin_jwt),
        )
        assert r2.status_code == 400


# ============================================================================
# Auth middleware enforcement
# ============================================================================
class TestStatusMiddleware:
    async def test_pending_user_cannot_access_api(self, client):
        # Crée un user via legacy puis force son status à pending
        from db import db
        email = f"PYTEST_mw_{uuid.uuid4().hex[:8]}@example.com"
        r = await client.post(
            "/api/auth/register",
            json={
                "name": "PYTEST MW", "email": email,
                "password": "pass1234", "role": "technician",
                "company_id": "default",
            },
        )
        assert r.status_code == 200
        token = r.json()["access_token"]
        # Bloque en pending
        await db.users.update_one(
            {"email": email.lower()},
            {"$set": {"status": "pending_verification"}},
        )
        r2 = await client.get("/api/auth/me", headers=hdr(token))
        assert r2.status_code == 403
        assert r2.json()["detail"]["code"] == "email_not_verified"
