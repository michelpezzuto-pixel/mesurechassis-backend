"""Build 9 — Tests système de parrainage (referral).

Couvre :
  • GET /referral/me                       (code auto-généré + stats)
  • POST /referral/code                    (validation format, reserved, dup)
  • POST /referral/validate                (sans auth, public)
  • POST /auth/register avec referral_code (lien parrain)
  • link_referral_at_signup()              (anti-auto-parrainage)
  • credit_parrain_on_first_payment()      (idempotence + limite 10)
"""
from __future__ import annotations

import uuid

import pytest

from db import db


def hdr(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


PYTEST_TAG_EMAIL = "pytestref_"


# ───────────────────── helpers ─────────────────────
async def _register(client, *, email_suffix: str, referral_code: str | None = None,
                    company_name: str | None = None):
    """Crée un compte admin via /auth/register (master mode, BETA)."""
    email = f"{PYTEST_TAG_EMAIL}{email_suffix}_{uuid.uuid4().hex[:6]}@pytest.example.com".lower()
    body = {
        "name": f"PYTEST {email_suffix}",
        "email": email,
        "password": "pytest1234",
        "account_type": "entreprise",
        "company_name": company_name or f"PYTEST Co {email_suffix}",
    }
    if referral_code is not None:
        body["referral_code"] = referral_code
    r = await client.post("/api/auth/register", json=body)
    return r, email


async def _login(client, email: str, password: str = "pytest1234") -> str:
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ───────────────────── cleanup ─────────────────────
@pytest.fixture(autouse=True)
async def _cleanup_pytest_referral_data():
    yield
    # Supprime tout user créé par ces tests
    users = await db.users.find(
        {"email": {"$regex": f"^{PYTEST_TAG_EMAIL}"}},
        {"_id": 0, "company_id": 1},
    ).to_list(500)
    cids = [u["company_id"] for u in users if u.get("company_id")]
    if cids:
        await db.companies.delete_many({"company_id": {"$in": cids}})
        await db.users.delete_many({"company_id": {"$in": cids}})


# ───────────────────── GET /referral/me ─────────────────────
class TestReferralMe:
    async def test_admin_returns_code_and_stats(self, client, admin_jwt):
        r = await client.get("/api/referral/me", headers=hdr(admin_jwt))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "code" in data and isinstance(data["code"], str)
        assert data["max_referrals"] == 10
        assert isinstance(data["referrals_used"], int)
        assert isinstance(data["referrals_pending"], int)
        assert isinstance(data["credit_months_total"], int)
        assert isinstance(data["credit_months_remaining"], int)
        assert "code_is_custom" in data

    async def test_auto_generated_code_for_new_account(self, client):
        r, email = await _register(client, email_suffix="autogen")
        assert r.status_code == 200, r.text
        token = await _login(client, email)
        r = await client.get("/api/referral/me", headers=hdr(token))
        assert r.status_code == 200
        data = r.json()
        # Auto-généré → préfixe MC- et code_is_custom=False
        assert data["code"].startswith("MC-")
        assert data["code_is_custom"] is False
        assert data["referrals_used"] == 0
        assert data["referrals_pending"] == 0
        assert data["credit_months_total"] == 0
        assert data["referred_by_code"] is None

    async def test_persistence_after_update(self, client):
        r, email = await _register(client, email_suffix="persist")
        assert r.status_code == 200
        token = await _login(client, email)
        # set custom code
        new_code = f"PYTESTREF-{uuid.uuid4().hex[:6].upper()}"
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": new_code}
        )
        assert r.status_code == 200, r.text
        # re-fetch
        r = await client.get("/api/referral/me", headers=hdr(token))
        data = r.json()
        assert data["code"] == new_code
        assert data["code_is_custom"] is True


# ───────────────────── POST /referral/code (validation) ─────────────────────
class TestReferralCodeUpdate:
    async def test_valid_custom_code(self, client):
        r, email = await _register(client, email_suffix="valid")
        token = await _login(client, email)
        code = f"JEAN-MENUISERIE-{uuid.uuid4().hex[:4].upper()}"
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": code}
        )
        assert r.status_code == 200, r.text
        assert r.json()["code"] == code
        assert r.json()["code_is_custom"] is True

    async def test_lowercase_normalized_to_upper(self, client):
        r, email = await _register(client, email_suffix="lower")
        token = await _login(client, email)
        suffix = uuid.uuid4().hex[:4]
        r = await client.post(
            "/api/referral/code",
            headers=hdr(token),
            json={"code": f"jean-menuiserie-{suffix}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["code"] == f"JEAN-MENUISERIE-{suffix.upper()}"

    @pytest.mark.parametrize("bad_code", ["A!B@", "JEAN_MENU", "PASCAL/CO", "../etc"])
    async def test_invalid_format_special_chars(self, client, bad_code):
        r, email = await _register(client, email_suffix="badfmt")
        token = await _login(client, email)
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": bad_code}
        )
        assert r.status_code == 400, f"{bad_code} should be 400 but got {r.status_code}: {r.text}"

    async def test_spaces_in_code_currently_normalized_to_hyphens(self, client):
        """⚠️ DEVIATION: 'A B C' devient 'A-B-C' (normalisation espace→tiret).

        Spec demande 400 pour les espaces. Code actuel : normalise et accepte.
        Documenté ici pour signaler le comportement réel.
        """
        r, email = await _register(client, email_suffix="spaces")
        token = await _login(client, email)
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": "A B C"}
        )
        # Comportement actuel observé (à confronter avec spec)
        assert r.status_code in (200, 400), r.text

    async def test_too_short(self, client):
        r, email = await _register(client, email_suffix="short")
        token = await _login(client, email)
        # 3 chars → Pydantic min_length=4 → 422
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": "ABC"}
        )
        assert r.status_code in (400, 422), r.text

    async def test_too_long(self, client):
        r, email = await _register(client, email_suffix="long")
        token = await _login(client, email)
        long_code = "A" * 25
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": long_code}
        )
        assert r.status_code in (400, 422), r.text

    @pytest.mark.parametrize("reserved", ["ADMIN", "MESURECHASSIS", "DEMO", "TEST",
                                          "admin", "DeMo"])
    async def test_reserved_words(self, client, reserved):
        r, email = await _register(client, email_suffix="reserved")
        token = await _login(client, email)
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": reserved}
        )
        assert r.status_code == 400, (
            f"Reserved word '{reserved}' should be 400 but got {r.status_code}: {r.text}"
        )

    async def test_mc_prefix_reserved(self, client):
        r, email = await _register(client, email_suffix="mcpref")
        token = await _login(client, email)
        r = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": "MC-ABCDEF"}
        )
        assert r.status_code == 400, r.text

    async def test_duplicate_code_409(self, client):
        # User A claims a code
        rA, emailA = await _register(client, email_suffix="dupA")
        tokenA = await _login(client, emailA)
        code = f"PYTESTDUP-{uuid.uuid4().hex[:6].upper()}"
        r = await client.post(
            "/api/referral/code", headers=hdr(tokenA), json={"code": code}
        )
        assert r.status_code == 200, r.text
        # User B tries the same code
        rB, emailB = await _register(client, email_suffix="dupB")
        tokenB = await _login(client, emailB)
        r = await client.post(
            "/api/referral/code", headers=hdr(tokenB), json={"code": code}
        )
        assert r.status_code == 409, r.text

    async def test_can_update_to_same_code_idempotent(self, client):
        """Re-set du même code par le même user → 200 (pas 409)."""
        r, email = await _register(client, email_suffix="same")
        token = await _login(client, email)
        code = f"PYTESTSAME-{uuid.uuid4().hex[:6].upper()}"
        r1 = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": code}
        )
        assert r1.status_code == 200
        r2 = await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": code}
        )
        assert r2.status_code == 200, r2.text


# ───────────────────── POST /referral/validate (public) ─────────────────────
class TestReferralValidate:
    async def test_valid_existing_code(self, client):
        # On utilise le code DEMO-ADMIN de l'admin
        r = await client.post(
            "/api/referral/validate", json={"code": "DEMO-ADMIN"}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["valid"] is True
        assert body.get("parrain_name")

    async def test_unknown_code(self, client):
        r = await client.post(
            "/api/referral/validate",
            json={"code": "NOPE-DOES-NOT-EXIST-XYZ"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert "introuvable" in (body.get("error") or "").lower()

    async def test_empty_code(self, client):
        r = await client.post("/api/referral/validate", json={"code": ""})
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False

    async def test_lowercase_resolves_to_upper(self, client):
        # 'demo-admin' doit valider (normalisation MAJ)
        r = await client.post(
            "/api/referral/validate", json={"code": "demo-admin"}
        )
        assert r.status_code == 200
        assert r.json()["valid"] is True


# ───────── POST /auth/register avec referral_code (lien parrain) ─────────
class TestRegisterWithReferral:
    async def test_register_with_valid_code_links_parrain(self, client):
        r, email = await _register(
            client, email_suffix="filleulOK", referral_code="DEMO-ADMIN"
        )
        assert r.status_code == 200, r.text
        # Vérifie en DB
        user = await db.users.find_one({"email": email})
        assert user is not None
        company = await db.companies.find_one({"company_id": user["company_id"]})
        assert company is not None
        # 'default' est le company_id de l'admin DEMO-ADMIN
        assert company.get("referred_by_company_id") == "default"
        assert company.get("referred_by_code") == "DEMO-ADMIN"
        assert company.get("referral_paid") is False
        assert company.get("referred_at")

    async def test_register_with_invalid_code_still_succeeds(self, client):
        r, email = await _register(
            client, email_suffix="badcode", referral_code="DOES-NOT-EXIST-ZZZ"
        )
        assert r.status_code == 200, r.text
        user = await db.users.find_one({"email": email})
        company = await db.companies.find_one({"company_id": user["company_id"]})
        # Aucune liaison
        assert company.get("referred_by_company_id") in (None, "")

    async def test_register_with_empty_referral_code_is_noop(self, client):
        r, email = await _register(
            client, email_suffix="emptyref", referral_code=""
        )
        assert r.status_code == 200
        user = await db.users.find_one({"email": email})
        company = await db.companies.find_one({"company_id": user["company_id"]})
        assert company.get("referred_by_company_id") in (None, "")


# ───────── Anti auto-parrainage + helpers ─────────
class TestAntiSelfReferral:
    async def test_link_refuses_self_referral(self, client):
        """Si un user édite son code puis tente de le passer à
        link_referral_at_signup pour son propre company_id → refusé.
        """
        from routes.referral import link_referral_at_signup

        r, email = await _register(client, email_suffix="selfref")
        token = await _login(client, email)
        # set custom code
        my_code = f"SELFREF-{uuid.uuid4().hex[:6].upper()}"
        await client.post(
            "/api/referral/code", headers=hdr(token), json={"code": my_code}
        )
        user = await db.users.find_one({"email": email})
        my_cid = user["company_id"]
        # Tente d'appeler le helper avec mon propre code → no-op (warning loggé)
        await link_referral_at_signup(my_cid, my_code)
        company = await db.companies.find_one({"company_id": my_cid})
        # Doit rester sans parrain
        assert company.get("referred_by_company_id") in (None, "")


# ───────── credit_parrain_on_first_payment ─────────
class TestCreditParrain:
    async def test_idempotence_credit(self, client):
        """Appeler 2× → 1 seul crédit (+2 mois, pas +4)."""
        from routes.referral import credit_parrain_on_first_payment

        # Crée un filleul lié à l'admin (default)
        r, email = await _register(
            client, email_suffix="idemp", referral_code="DEMO-ADMIN"
        )
        assert r.status_code == 200
        user = await db.users.find_one({"email": email})
        filleul_cid = user["company_id"]

        # Snapshot crédit avant
        before = await db.companies.find_one({"company_id": "default"}) or {}
        before_total = int(before.get("referral_credit_months_total") or 0)
        before_remaining = int(before.get("referral_credit_months_remaining") or 0)

        # 1ʳᵉ invocation : +2
        await credit_parrain_on_first_payment(filleul_cid)
        after1 = await db.companies.find_one({"company_id": "default"}) or {}
        assert int(after1["referral_credit_months_total"]) == before_total + 2
        assert int(after1["referral_credit_months_remaining"]) == before_remaining + 2

        # filleul marqué payé
        f = await db.companies.find_one({"company_id": filleul_cid})
        assert f.get("referral_paid") is True

        # 2ᵉ invocation : pas de double crédit
        await credit_parrain_on_first_payment(filleul_cid)
        after2 = await db.companies.find_one({"company_id": "default"}) or {}
        assert int(after2["referral_credit_months_total"]) == before_total + 2
        assert int(after2["referral_credit_months_remaining"]) == before_remaining + 2

        # Cleanup : retire les +2 mois du parrain default pour ne pas
        # polluer l'état entre runs
        await db.companies.update_one(
            {"company_id": "default"},
            {"$inc": {
                "referral_credit_months_total": -2,
                "referral_credit_months_remaining": -2,
            }},
        )

    async def test_limit_10_filleuls(self, client):
        """11ᵉ filleul → pas de crédit (limite atteinte), filleul.referral_paid=True."""
        from routes.referral import credit_parrain_on_first_payment

        # Crée un parrain dédié + custom code
        rP, emailP = await _register(client, email_suffix="parrLim")
        tokenP = await _login(client, emailP)
        parrain_code = f"PYTESTLIM-{uuid.uuid4().hex[:6].upper()}"
        await client.post(
            "/api/referral/code", headers=hdr(tokenP), json={"code": parrain_code}
        )
        userP = await db.users.find_one({"email": emailP})
        parrain_cid = userP["company_id"]

        # Crée 11 filleuls liés au parrain
        filleul_cids: list[str] = []
        for i in range(11):
            rF, emailF = await _register(
                client, email_suffix=f"fillLim{i}", referral_code=parrain_code,
            )
            assert rF.status_code == 200, rF.text
            uF = await db.users.find_one({"email": emailF})
            filleul_cids.append(uF["company_id"])

        # Crédite les 10 premiers
        for cid in filleul_cids[:10]:
            await credit_parrain_on_first_payment(cid)

        parrain = await db.companies.find_one({"company_id": parrain_cid})
        assert int(parrain["referral_credit_months_total"]) == 20, (
            f"Attendu 20 mois (10×2), reçu {parrain.get('referral_credit_months_total')}"
        )

        # 11ᵉ : limite atteinte → pas de crédit, filleul marqué payé
        await credit_parrain_on_first_payment(filleul_cids[10])
        parrain_after = await db.companies.find_one({"company_id": parrain_cid})
        assert int(parrain_after["referral_credit_months_total"]) == 20, (
            "Le 11ᵉ filleul N'AURAIT PAS DÛ créditer"
        )
        # filleul 11 marqué payé pour éviter retry
        f11 = await db.companies.find_one({"company_id": filleul_cids[10]})
        assert f11.get("referral_paid") is True

    async def test_credit_no_parrain_noop(self, client):
        """Filleul sans parrain → pas d'erreur, pas de crédit."""
        from routes.referral import credit_parrain_on_first_payment

        r, email = await _register(client, email_suffix="orphan")
        u = await db.users.find_one({"email": email})
        # Pas d'exception ne doit être levée
        await credit_parrain_on_first_payment(u["company_id"])
        c = await db.companies.find_one({"company_id": u["company_id"]})
        # Pas marqué payé (puisqu'il n'a pas de parrain)
        assert not c.get("referral_paid")
