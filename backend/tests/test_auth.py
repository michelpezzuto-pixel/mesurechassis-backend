"""Tests authentification + RBAC + JWT."""
from __future__ import annotations

import pytest

from tests.conftest import hdr

pytestmark = pytest.mark.asyncio


class TestLogin:
    async def test_admin_login_ok(self, client):
        r = await client.post(
            "/api/auth/login",
            json={
                "email": "admin@mesurechassis.fr",
                "password": "admin123",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"

    async def test_login_wrong_password(self, client):
        r = await client.post(
            "/api/auth/login",
            json={
                "email": "admin@mesurechassis.fr",
                "password": "wrong",
            },
        )
        assert r.status_code == 401

    async def test_login_unknown_email(self, client):
        r = await client.post(
            "/api/auth/login",
            json={"email": "ghost@nowhere.fr", "password": "x"},
        )
        assert r.status_code == 401


class TestAuthMe:
    async def test_me_with_valid_token(self, client, admin_jwt):
        r = await client.get("/api/auth/me", headers=hdr(admin_jwt))
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    async def test_me_without_token(self, client):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401

    async def test_me_with_garbage_token(self, client):
        r = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer garbage.token.x"}
        )
        assert r.status_code == 401


class TestRolePerProfile:
    async def test_commercial_role(self, client, commercial_jwt):
        r = await client.get("/api/auth/me", headers=hdr(commercial_jwt))
        assert r.status_code == 200
        assert r.json()["role"] == "commercial"

    async def test_tech_role(self, client, tech_jwt):
        r = await client.get("/api/auth/me", headers=hdr(tech_jwt))
        assert r.status_code == 200
        assert r.json()["role"] == "technician"
