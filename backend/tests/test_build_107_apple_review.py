"""Build 107 — Apple Review 5th rejection fix.

Validates that:
- POST /api/auth/login works for Apple reviewer demo account.
- Wrong password returns 401 with detail.
- No regression for admin@mesurechassis.fr and tech@mesurechassis.fr.
- Trim() behaviour: trailing whitespace in email/password (legacy backend may
  not strip, but frontend strips before sending — see /app/frontend/app/index.tsx).
"""
import os
import pytest
import requests

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"


APPLE = ("applereview@mesurechassis.com", "MesureChassis2026")
ADMIN_LOCAL = ("admin@mesurechassis.fr", "admin123")
TECH_LOCAL = ("tech@mesurechassis.fr", "tech123")


class TestAppleReviewLogin:
    """Apple Reviewer demo credentials — Build 107."""

    def test_apple_login_success(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": APPLE[0], "password": APPLE[1]},
            timeout=30,
        )
        assert r.status_code == 200, f"Apple login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "access_token" in data and data["access_token"]
        # Validate JWT shape (3 dot-separated segments)
        assert data["access_token"].count(".") == 2
        assert "user" in data
        assert data["user"].get("role") == "admin", f"Expected admin, got {data['user'].get('role')}"
        # Email returned matches request (case-insensitive)
        assert data["user"].get("email", "").lower() == APPLE[0].lower()

    def test_apple_login_wrong_password_401(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": APPLE[0], "password": "WrongPassword!"},
            timeout=30,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code} {r.text}"
        body = r.json()
        assert "detail" in body, "Response must include 'detail' on 401"

    def test_apple_login_unknown_user_401(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "nobody.unknown.107@example.com", "password": "anything"},
            timeout=30,
        )
        assert r.status_code == 401
        assert "detail" in r.json()


class TestRegressionLocalAccounts:
    """Make sure Build 107 changes did not break existing logins."""

    def test_admin_local_login(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": ADMIN_LOCAL[0], "password": ADMIN_LOCAL[1]},
            timeout=30,
        )
        assert r.status_code == 200, f"admin@mesurechassis.fr broken: {r.text}"
        data = r.json()
        assert data["user"]["role"] in ("admin", "owner")

    def test_tech_local_login(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": TECH_LOCAL[0], "password": TECH_LOCAL[1]},
            timeout=30,
        )
        assert r.status_code == 200, f"tech@mesurechassis.fr broken: {r.text}"
        data = r.json()
        # tech account should have technician role
        assert data["user"]["role"] in ("technician", "tech", "admin")


class TestLoginEdgeCases:
    """Edge cases relevant to the iPad keyboard trim() fix."""

    def test_login_uppercase_email_accepted(self):
        # Email normalization: the backend should accept any case.
        r = requests.post(
            f"{API}/auth/login",
            json={"email": APPLE[0].upper(), "password": APPLE[1]},
            timeout=30,
        )
        assert r.status_code == 200, f"Uppercase email rejected: {r.text}"

    def test_login_missing_fields_4xx(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "", "password": ""},
            timeout=30,
        )
        # Pydantic validation OR 401, anything in 4xx is acceptable
        assert 400 <= r.status_code < 500, f"Expected 4xx, got {r.status_code}"
