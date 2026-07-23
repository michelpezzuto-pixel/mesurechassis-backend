"""v1.1.4 Partie B — Tests fallback SIREN/SIRET/BCE pour auto-entrepreneurs.

Couvre :
  * POST /api/auth/validate-business-id (public, sans auth)
  * POST /api/company/complete-signup en mode fallback business_id
  * Régression mode TVA classique + /auth/validate-vat
"""
from __future__ import annotations

import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
BASE = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

LOT = f"lot_v114_biz_{int(time.time())}"


# --- helpers -----------------------------------------------------------
def _register_fresh_admin(session: requests.Session):
    """Crée un fresh user via legacy register (role=admin) sans TVA."""
    email = f"{LOT}_{uuid.uuid4().hex[:6]}@mesurechassis.fr"
    payload = {
        "name": "Test Biz Fallback",
        "email": email,
        "password": "TestPass2026!",
        "role": "admin",
        "company_id": f"co-{LOT}-{uuid.uuid4().hex[:6]}",
    }
    r = session.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    return {
        "email": email,
        "user_id": data["user"]["id"],
        "company_id": payload["company_id"],
        "token": data["access_token"],
    }


def _hdr(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ═════════════════════════════════════════════════════════════════════
# 1) POST /api/auth/validate-business-id (public)
# ═════════════════════════════════════════════════════════════════════
class TestValidateBusinessIdPublic:
    def test_missing_payload_400(self, session):
        r = session.post(f"{API}/auth/validate-business-id", json={}, timeout=15)
        assert r.status_code == 400
        assert "id_type" in r.text and "id_value" in r.text

    def test_missing_id_value_400(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siren"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_missing_id_type_400(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_value": "383474814"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_unknown_type(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "foobar", "id_value": "12345"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is False
        assert "foobar" in (j.get("message") or "")
        assert "non support" in (j.get("message") or "").lower()

    def test_siren_valid_airbus(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siren", "id_value": "383474814"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True
        assert j["normalized"] == "383474814"
        assert j["id_type"] == "siren"

    def test_siren_invalid_luhn(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siren", "id_value": "123456789"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is False
        assert "Luhn" in (j.get("message") or "") or "luhn" in (j.get("message") or "").lower()

    def test_siren_too_short(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siren", "id_value": "12345"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_siret_valid_google_fr(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siret", "id_value": "44306184100047"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True
        assert j["normalized"] == "44306184100047"
        assert j["id_type"] == "siret"

    def test_siret_la_poste_variant(self, session):
        """SIRET La Poste : Luhn KO sur 14 mais OK sur bloc SIREN+NIC."""
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siret", "id_value": "35600000000048"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True, f"La Poste SIRET should validate: {j}"

    def test_siret_invalid(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "siret", "id_value": "12345678901234"},
            timeout=15,
        )
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_bce_valid_no_spaces(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "bce", "id_value": "0403170701"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True
        assert j["normalized"] == "0403170701"

    def test_bce_valid_with_dashes(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "bce", "id_value": "0403-170-701"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is True
        assert j["normalized"] == "0403170701"

    def test_bce_bad_key(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "bce", "id_value": "0403170702"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is False
        assert "mod-97" in (j.get("message") or "").lower() or "97" in (j.get("message") or "")

    def test_bce_wrong_leading_digit(self, session):
        r = session.post(
            f"{API}/auth/validate-business-id",
            json={"id_type": "bce", "id_value": "2000000000"},
            timeout=15,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["valid"] is False
        msg = (j.get("message") or "").lower()
        assert "0" in msg and "1" in msg and "commence" in msg


# ═════════════════════════════════════════════════════════════════════
# 2) POST /api/company/complete-signup en mode fallback business_id
# ═════════════════════════════════════════════════════════════════════
class TestCompleteSignupFallback:
    def test_full_flow_siret(self, session):
        """Register → login /auth/me flag → complete-signup → verify DB → idempotence."""
        creds = _register_fresh_admin(session)
        tok = creds["token"]

        # /auth/me doit avoir vat_completion_required=true
        r = session.get(f"{API}/auth/me", headers=_hdr(tok), timeout=15)
        assert r.status_code == 200, r.text
        me_before = r.json()
        assert me_before.get("vat_completion_required") is True, (
            f"vat_completion_required attendu True: {me_before}"
        )

        # No body → 400
        r = session.post(
            f"{API}/company/complete-signup",
            json={},
            headers=_hdr(tok),
            timeout=15,
        )
        assert r.status_code == 400

        # Invalid business_id_value → 400
        r = session.post(
            f"{API}/company/complete-signup",
            json={"business_id_type": "siret", "business_id_value": "invalid"},
            headers=_hdr(tok),
            timeout=15,
        )
        assert r.status_code == 400

        # Happy path : SIRET Google FR
        r = session.post(
            f"{API}/company/complete-signup",
            json={
                "business_id_type": "siret",
                "business_id_value": "44306184100047",
                "company_name": "Menuiserie Test Solo",
            },
            headers=_hdr(tok),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        assert j["business_id_type"] == "siret"
        assert j["business_id_value"] == "44306184100047"
        assert j["company_name"] == "Menuiserie Test Solo"

        # Vérification DB directe via Motor
        import asyncio
        from db import db as _db

        async def _check():
            return await _db.companies.find_one(
                {"company_id": creds["company_id"]}, {"_id": 0}
            )

        doc = asyncio.get_event_loop().run_until_complete(_check())
        assert doc is not None, "Company doc missing"
        assert doc.get("business_id_value") == "44306184100047"
        assert doc.get("business_id_type") == "siret"
        assert doc.get("business_id_verified_at"), "business_id_verified_at manquant"
        assert doc.get("name") == "Menuiserie Test Solo"

        # /auth/me : vat_completion_required disparu
        r = session.get(f"{API}/auth/me", headers=_hdr(tok), timeout=15)
        assert r.status_code == 200
        me_after = r.json()
        assert not me_after.get("vat_completion_required"), (
            f"vat_completion_required doit être absent/False: {me_after}"
        )

        # 2ème appel → 400 idempotence
        r2 = session.post(
            f"{API}/company/complete-signup",
            json={
                "business_id_type": "siret",
                "business_id_value": "44306184100047",
                "company_name": "Autre nom",
            },
            headers=_hdr(tok),
            timeout=15,
        )
        assert r2.status_code == 400
        assert "déjà" in r2.text.lower() or "deja" in r2.text.lower() or "already" in r2.text.lower()


# ═════════════════════════════════════════════════════════════════════
# 3) Régression mode TVA sur complete-signup
# ═════════════════════════════════════════════════════════════════════
class TestCompleteSignupVatRegression:
    def test_vat_mode_still_works(self, session):
        creds = _register_fresh_admin(session)
        tok = creds["token"]

        r = session.post(
            f"{API}/company/complete-signup",
            json={"vat_number": "BE0403170701", "company_name": "Test Legacy SPRL"},
            headers=_hdr(tok),
            timeout=30,
        )
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        # Le champ vat_number normalisé doit être renvoyé (avec ou sans espaces).
        assert j.get("vat_number"), f"vat_number manquant dans response: {j}"

        # Vérif DB
        import asyncio
        from db import db as _db

        async def _check():
            return await _db.companies.find_one(
                {"company_id": creds["company_id"]}, {"_id": 0}
            )

        doc = asyncio.get_event_loop().run_until_complete(_check())
        assert doc is not None
        assert doc.get("vat_number"), f"vat_number pas stocké: {doc}"
        # Normalisation classique : "BE0403170701"
        assert doc["vat_number"].replace(" ", "").upper().startswith("BE")


# ═════════════════════════════════════════════════════════════════════
# 4) Régression /auth/validate-vat
# ═════════════════════════════════════════════════════════════════════
class TestValidateVatRegression:
    def test_validate_vat_be_valid(self, session):
        r = session.post(
            f"{API}/auth/validate-vat",
            json={"vat_number": "BE0403170701"},
            timeout=30,
        )
        assert r.status_code == 200
        j = r.json()
        # VIES peut être indispo → validation format seule doit passer
        assert "valid" in j and "normalized" in j and "message" in j

    def test_validate_vat_missing_400(self, session):
        r = session.post(
            f"{API}/auth/validate-vat", json={}, timeout=15
        )
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════════
# 5) Cleanup — supprime tous les users lot_v114_biz_* et leurs companies
# ═════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module", autouse=True)
def cleanup_lot_v114():
    yield
    import asyncio
    from db import db as _db

    async def _clean():
        users = await _db.users.find(
            {"email": {"$regex": f"^{LOT}"}}, {"_id": 0, "id": 1, "company_id": 1}
        ).to_list(500)
        company_ids = list({u.get("company_id") for u in users if u.get("company_id")})
        if users:
            await _db.users.delete_many({"email": {"$regex": f"^{LOT}"}})
        if company_ids:
            await _db.companies.delete_many({"company_id": {"$in": company_ids}})
        return len(users), len(company_ids)

    n_users, n_companies = asyncio.get_event_loop().run_until_complete(_clean())
    print(f"\n[cleanup] Removed {n_users} users and {n_companies} companies (lot={LOT})")
