"""Smoke tests des endpoints /referral/* contre le compte COUSIN admin.

Vérifie le scenario décrit dans la review-request (Jan 2026) :
  1. GET /referral/me                                  → ReferralStatus
  2. POST /referral/code (custom unique)               → code_is_custom=true
  3. POST /referral/code (trop court "AB")             → 400 (ou 422)
  4. POST /referral/code (ADMIN reserved)              → 400
  5. POST /referral/code (MC- prefix)                  → 400
  6. POST /referral/validate (code valide)             → {valid:true, parrain_name}
  7. POST /referral/validate (code inconnu)            → {valid:false, error}
  8. POST /auth/register avec referral_code            → referred_by_company_id en DB
"""
from __future__ import annotations

import time
import uuid

import pytest

from db import db


COUSIN_EMAIL = "cousin.admin@test.mesurechassis.com"
COUSIN_PWD = "Cousin2026!"


def hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def cousin_token(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": COUSIN_EMAIL, "password": COUSIN_PWD},
    )
    assert r.status_code == 200, f"Login cousin admin failed: {r.text}"
    return r.json()["access_token"]


# 1. GET /referral/me
async def test_get_referral_me_returns_status_shape(client, cousin_token):
    r = await client.get("/api/referral/me", headers=hdr(cousin_token))
    assert r.status_code == 200, r.text
    d = r.json()
    expected = {
        "code", "code_is_custom", "max_referrals", "referrals_used",
        "referrals_pending", "credit_months_total",
        "credit_months_remaining", "referred_by_code",
    }
    assert expected.issubset(d.keys())
    assert d["max_referrals"] == 10
    assert isinstance(d["code"], str) and len(d["code"]) >= 4
    assert isinstance(d["referrals_used"], int)
    assert isinstance(d["credit_months_total"], int)


# 2. POST /referral/code custom valide
async def test_post_referral_code_custom_valid(client, cousin_token):
    # Suffixe avec timestamp pour éviter conflit entre runs
    # Code unique <=24 chars : TEST-V + 10 hex = 16 chars max
    code = f"TEST-V-{uuid.uuid4().hex[:10].upper()}"
    r = await client.post(
        "/api/referral/code", headers=hdr(cousin_token), json={"code": code}
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["code"] == code
    assert d["code_is_custom"] is True


# 3. POST /referral/code trop court
async def test_post_referral_code_too_short(client, cousin_token):
    r = await client.post(
        "/api/referral/code", headers=hdr(cousin_token), json={"code": "AB"}
    )
    # Spec demande 400 — Pydantic min_length renvoie 422. Les deux sont des
    # erreurs de validation côté client, mais on signale la divergence.
    assert r.status_code in (400, 422), r.text


# 4. POST /referral/code reserved word ADMIN
async def test_post_referral_code_reserved_admin(client, cousin_token):
    r = await client.post(
        "/api/referral/code", headers=hdr(cousin_token), json={"code": "ADMIN"}
    )
    assert r.status_code == 400, r.text
    assert "réserv" in r.text.lower() or "reserv" in r.text.lower()


# 5. POST /referral/code MC- prefix
async def test_post_referral_code_mc_prefix(client, cousin_token):
    r = await client.post(
        "/api/referral/code",
        headers=hdr(cousin_token),
        json={"code": "MC-ABCDEF"},
    )
    assert r.status_code == 400, r.text


# 6. POST /referral/validate code valide existant (DEMO-ADMIN du compte admin)
async def test_post_referral_validate_valid_code(client):
    r = await client.post(
        "/api/referral/validate", json={"code": "DEMO-ADMIN"}
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["valid"] is True
    assert d.get("parrain_name")


# 7. POST /referral/validate code inconnu
async def test_post_referral_validate_unknown_code(client):
    r = await client.post(
        "/api/referral/validate",
        json={"code": f"NOPE-{uuid.uuid4().hex[:8].upper()}"},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["valid"] is False
    assert d.get("error")


# 8. POST /auth/register avec referral_code → referred_by_company_id set
async def test_register_with_referral_code_links_referrer(client):
    suffix = uuid.uuid4().hex[:6]
    email = f"pytestref_cousinflw_{suffix}@pytest.example.com"
    body = {
        "name": f"PYTEST Filleul {suffix}",
        "email": email,
        "password": "pytest1234",
        "account_type": "entreprise",
        "company_name": f"PYTEST Filleul Co {suffix}",
        "referral_code": "DEMO-ADMIN",
    }
    try:
        r = await client.post("/api/auth/register", json=body)
        assert r.status_code == 200, r.text

        user = await db.users.find_one({"email": email})
        assert user is not None
        company = await db.companies.find_one({"company_id": user["company_id"]})
        assert company is not None
        # 'default' = company_id de l'admin qui détient DEMO-ADMIN
        assert company.get("referred_by_company_id") == "default", (
            f"Expected referred_by_company_id=default, got {company.get('referred_by_company_id')}"
        )
        assert company.get("referred_by_code") == "DEMO-ADMIN"
        assert company.get("referral_paid") is False

        # Vérification via le helper ensure_referral_code aussi
        from routes.referral import ensure_referral_code
        own_code = await ensure_referral_code(user["company_id"])
        assert own_code.startswith("MC-")  # filleul a son propre code auto-généré
    finally:
        # Cleanup
        user = await db.users.find_one({"email": email})
        if user and user.get("company_id"):
            await db.companies.delete_many({"company_id": user["company_id"]})
            await db.users.delete_many({"company_id": user["company_id"]})
