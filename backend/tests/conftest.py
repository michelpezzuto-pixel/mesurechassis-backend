"""Fixtures partagées — supporte 2 styles de tests :

1. **Legacy** (anciens tests) : `requests` synchrone contre le serveur réel
   tournant à `EXPO_PUBLIC_BACKEND_URL`. Fixtures: `api_url`, `session`,
   `admin_token`, `commercial_token`, `tech_token`, `*_headers`.

2. **Modern** (nouveaux tests) : `httpx.AsyncClient` sur l'ASGITransport
   in-process (pas de serveur réel requis, couverture mesurée).
   Fixtures: `client`, `admin_jwt`, `commercial_jwt`, `tech_jwt`. Helper `hdr()`.

Les deux peuvent coexister dans le même run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# --- chemins pour pouvoir importer server/db/routes depuis /app/backend ---
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from db import db  # noqa: E402
from server import app  # noqa: E402


# ============================================================================
# LEGACY (sync, via requests, contre le serveur public)
# ============================================================================
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api" if BASE_URL else "http://localhost:8001/api"


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    return API


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login_sync(session, email: str, password: str) -> str:
    r = session.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, (
        f"Login failed for {email}: {r.status_code} {r.text}"
    )
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(session):
    return _login_sync(session, "admin@mesurechassis.fr", "admin123")


@pytest.fixture(scope="session")
def commercial_token(session):
    return _login_sync(session, "commercial@mesurechassis.fr", "commercial123")


@pytest.fixture(scope="session")
def tech_token(session):
    return _login_sync(session, "tech@mesurechassis.fr", "tech123")


@pytest.fixture
def admin_headers(admin_token):
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def commercial_headers(commercial_token):
    return {
        "Authorization": f"Bearer {commercial_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def tech_headers(tech_token):
    return {
        "Authorization": f"Bearer {tech_token}",
        "Content-Type": "application/json",
    }


# ============================================================================
# MODERN (async, httpx ASGI in-process)
# ============================================================================
ADMIN = ("admin@mesurechassis.fr", "admin123")
COMMERCIAL = ("commercial@mesurechassis.fr", "commercial123")
TECH = ("tech@mesurechassis.fr", "tech123")

PYTEST_TAG = "PYTEST_"


@pytest_asyncio.fixture(scope="session")
async def client():
    """Client HTTP partagé sur l'ASGI in-process."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _login_async(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, f"Login {email} failed: {r.text}"
    return r.json()["access_token"]


@pytest_asyncio.fixture(scope="session")
async def admin_jwt(client):
    return await _login_async(client, *ADMIN)


@pytest_asyncio.fixture(scope="session")
async def commercial_jwt(client):
    return await _login_async(client, *COMMERCIAL)


@pytest_asyncio.fixture(scope="session")
async def tech_jwt(client):
    return await _login_async(client, *TECH)


def hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="session", autouse=True)
async def disable_artisan_mode(client, admin_jwt):
    """Désactive Mode Artisan le temps des tests modernes, puis restaure."""
    r = await client.get("/api/company/profile", headers=hdr(admin_jwt))
    initial = r.json().get("artisan_mode", False)
    await client.patch(
        "/api/company/profile",
        headers=hdr(admin_jwt),
        json={"artisan_mode": False},
    )
    yield
    await client.patch(
        "/api/company/profile",
        headers=hdr(admin_jwt),
        json={"artisan_mode": initial},
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_pytest_data(disable_artisan_mode):
    """Nettoie toutes les données taggées PYTEST_ à la fin de la session."""
    yield
    chantiers = await db.chantiers.find(
        {"client_name": {"$regex": f"^{PYTEST_TAG}"}},
        {"_id": 0, "id": 1},
    ).to_list(500)
    cids = [c["id"] for c in chantiers]
    if cids:
        await db.mesures.delete_many({"chantier_id": {"$in": cids}})
        await db.chantiers.delete_many({"id": {"$in": cids}})
