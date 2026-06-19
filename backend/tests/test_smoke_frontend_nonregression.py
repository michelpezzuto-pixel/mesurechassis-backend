"""Smoke tests — Backend non-regression après changements frontend (Jan 2026).

Confirme que les flows core ne sont pas cassés par les modifs frontend de
cette session :
  - subscription.tsx (pricing grid + Platform !== ios)
  - chantier/[id]/index.tsx (action buttons fix)
  - me.tsx + help.tsx (nouveau "Centre d'aide")
  - faq_data.json (6 nouvelles entrées)

Endpoints couverts (per review-request) :
  1. POST /api/auth/login (succès cousin.admin)
  2. POST /api/auth/login (mauvais password → 401)
  3. GET /api/auth/me (token cousin.artisan)
  4. GET /api/company/profile (artisan_mode=true pour cousin.artisan)
  5. GET /api/stripe/subscription-status
  6. GET /api/referral/me
  7. GET /api/chantiers
"""
from __future__ import annotations

import pytest

COUSIN_ARTISAN = ("cousin.artisan@test.mesurechassis.com", "Cousin2026!")
COUSIN_ADMIN = ("cousin.admin@test.mesurechassis.com", "Cousin2026!")


def hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def artisan_token(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": COUSIN_ARTISAN[0], "password": COUSIN_ARTISAN[1]},
    )
    assert r.status_code == 200, f"Login cousin.artisan failed: {r.text}"
    return r.json()["access_token"]


# 6. POST /api/auth/login OK (cousin.admin)
async def test_login_cousin_admin_returns_jwt(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": COUSIN_ADMIN[0], "password": COUSIN_ADMIN[1]},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert "access_token" in d and isinstance(d["access_token"], str)
    # JWT has 3 dot-separated segments
    assert d["access_token"].count(".") == 2
    assert d.get("token_type") == "bearer"
    assert d.get("user", {}).get("email") == COUSIN_ADMIN[0]


# 7. POST /api/auth/login wrong password → 401
async def test_login_wrong_password_returns_401(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": COUSIN_ADMIN[0], "password": "DEFINITELY_WRONG_pw!"},
    )
    assert r.status_code == 401, r.text


# 1. GET /api/auth/me
async def test_auth_me_returns_user(client, artisan_token):
    r = await client.get("/api/auth/me", headers=hdr(artisan_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("email") == COUSIN_ARTISAN[0]
    assert d.get("status") == "active"
    assert d.get("id")
    assert d.get("company_id")


# 2. GET /api/company/profile — artisan_mode=true pour cousin.artisan
async def test_company_profile_artisan_mode_true(client, artisan_token):
    r = await client.get("/api/company/profile", headers=hdr(artisan_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("artisan_mode") is True, (
        f"cousin.artisan should have artisan_mode=true, got {d.get('artisan_mode')}"
    )
    # Sanity: company_id present
    assert d.get("company_id") or d.get("id")


# 3. GET /api/stripe/subscription-status
async def test_stripe_subscription_status(client, artisan_token):
    r = await client.get(
        "/api/stripe/subscription-status", headers=hdr(artisan_token)
    )
    assert r.status_code == 200, r.text
    d = r.json()
    # Tolerant assertion: at least one of common status fields must exist
    assert isinstance(d, dict)
    assert any(
        k in d for k in ("status", "plan", "subscription_status", "active", "is_active")
    ), f"Unexpected subscription-status payload: {d}"


# 4. GET /api/referral/me — must return a code
async def test_referral_me_returns_code(client, artisan_token):
    r = await client.get("/api/referral/me", headers=hdr(artisan_token))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("code") and isinstance(d["code"], str)
    assert len(d["code"]) >= 4


# 5. GET /api/chantiers
async def test_chantiers_list_ok(client, artisan_token):
    r = await client.get("/api/chantiers", headers=hdr(artisan_token))
    assert r.status_code == 200, r.text
    d = r.json()
    # Accept either {items:[...]} or [...]
    if isinstance(d, dict):
        assert "items" in d or "chantiers" in d or "data" in d or "results" in d, (
            f"Unexpected chantiers payload shape: {list(d.keys())}"
        )
    else:
        assert isinstance(d, list)
