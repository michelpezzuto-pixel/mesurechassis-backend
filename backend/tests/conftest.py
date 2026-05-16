"""Shared fixtures for MesureChâssis backend tests."""
import os
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


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


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(session):
    return _login(session, "admin@mesurechassis.fr", "admin123")


@pytest.fixture(scope="session")
def commercial_token(session):
    return _login(session, "commercial@mesurechassis.fr", "commercial123")


@pytest.fixture(scope="session")
def tech_token(session):
    return _login(session, "tech@mesurechassis.fr", "tech123")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def commercial_headers(commercial_token):
    return {"Authorization": f"Bearer {commercial_token}", "Content-Type": "application/json"}


@pytest.fixture
def tech_headers(tech_token):
    return {"Authorization": f"Bearer {tech_token}", "Content-Type": "application/json"}
