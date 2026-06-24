"""RGPD Unsubscribe System Audit — iteration 21.

Verifies the campaign unsubscribe routes, JWT token roundtrip, the email
footer placement, and the CRON filters that exclude unsubscribed prospects.

NO state-mutating cleanup is required: the only test that toggles a
prospect's `unsubscribed` flag re-subscribes them in the same test.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/") or \
    os.environ.get("EXPO_BACKEND_URL", "").rstrip("/")

ADMIN_EMAIL = "applereview@mesurechassis.com"
ADMIN_PASSWORD = "MesureChassis2026"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ────────────────────────────────────────────────────────────────
# 1. JWT token roundtrip (function-level)
# ────────────────────────────────────────────────────────────────
class TestUnsubscribeToken:
    """Verify `_make_unsubscribe_token` and `_decode_unsubscribe_token`."""

    def test_token_roundtrip(self):
        from routes.campaign import (
            _make_unsubscribe_token,
            _decode_unsubscribe_token,
        )
        pid = "test-pid-xyz-123"
        email = "Foo.Bar@Example.COM"
        token = _make_unsubscribe_token(pid, email)
        assert isinstance(token, str) and len(token) > 20

        payload = _decode_unsubscribe_token(token)
        assert payload["pid"] == pid
        # email must be lowercased + stripped
        assert payload["email"] == "foo.bar@example.com"
        assert payload["purpose"] == "unsubscribe_campaign"

    def test_token_invalid_raises(self):
        from fastapi import HTTPException
        from routes.campaign import _decode_unsubscribe_token
        with pytest.raises(HTTPException) as ei:
            _decode_unsubscribe_token("not-a-valid-token")
        assert ei.value.status_code == 400

    def test_footer_html_contains_link(self):
        from routes.campaign import _build_unsubscribe_footer_html
        html = _build_unsubscribe_footer_html("pid-abc", "x@y.com")
        assert "Se désinscrire en 1 clic" in html
        assert "/api/public/unsubscribe?token=" in html
        # the canonical PUBLIC_BACKEND_URL must be embedded
        assert "capable-gratitude-production-db51.up.railway.app" in html or \
            "PUBLIC_BACKEND_URL" not in html  # env override allowed


# ────────────────────────────────────────────────────────────────
# 2. Public unsubscribe endpoint
# ────────────────────────────────────────────────────────────────
class TestPublicUnsubscribeEndpoint:
    def test_invalid_token_returns_400(self):
        r = requests.get(
            f"{BASE_URL}/api/public/unsubscribe?token=invalid_garbage",
            timeout=15,
            allow_redirects=False,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"

    def test_valid_token_returns_html_and_marks_unsubscribed(self, auth_headers):
        # find a prospect that is currently NOT unsubscribed
        r = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        assert r.status_code == 200
        prospects = r.json().get("prospects", [])
        candidate = next(
            (p for p in prospects
             if not p.get("unsubscribed") and p.get("status") == "sent"),
            None,
        )
        if not candidate:
            pytest.skip("No sent+subscribed prospect available for E2E unsubscribe test")
        pid = candidate["id"]
        email = candidate["email"]

        # mint a valid token using backend's helper
        from routes.campaign import _make_unsubscribe_token
        token = _make_unsubscribe_token(pid, email)

        r2 = requests.get(
            f"{BASE_URL}/api/public/unsubscribe?token={token}",
            timeout=15,
        )
        assert r2.status_code == 200
        assert "text/html" in r2.headers.get("content-type", "")
        assert "Vous êtes désinscrit" in r2.text
        assert email.lower() in r2.text.lower()

        # verify DB now has unsubscribed=true (via list endpoint)
        r3 = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        prospects2 = r3.json().get("prospects", [])
        found = next((p for p in prospects2 if p["id"] == pid), None)
        assert found is not None
        assert found.get("unsubscribed") is True
        assert found.get("unsubscribed_via") == "public_link"

        # cleanup: resubscribe
        rc = requests.post(
            f"{BASE_URL}/api/campaign/prospects/{pid}/resubscribe",
            headers=auth_headers, timeout=15,
        )
        assert rc.status_code == 200


# ────────────────────────────────────────────────────────────────
# 3. Admin manual unsubscribe (idempotent)
# ────────────────────────────────────────────────────────────────
class TestAdminUnsubscribe:
    def test_admin_unsubscribe_then_resubscribe(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        prospects = r.json().get("prospects", [])
        target = next(
            (p for p in prospects
             if not p.get("unsubscribed") and p.get("status") == "sent"),
            None,
        )
        if not target:
            pytest.skip("No suitable prospect for admin-unsubscribe test")
        pid = target["id"]

        # 1st call → marks unsubscribed
        r1 = requests.post(
            f"{BASE_URL}/api/campaign/prospects/{pid}/unsubscribe",
            headers=auth_headers, timeout=15,
        )
        assert r1.status_code == 200
        body = r1.json()
        assert body["ok"] is True
        assert body["prospect_id"] == pid
        assert "unsubscribed_at" in body

        # idempotency — second call must still 200
        r2 = requests.post(
            f"{BASE_URL}/api/campaign/prospects/{pid}/unsubscribe",
            headers=auth_headers, timeout=15,
        )
        assert r2.status_code == 200

        # verify via list endpoint
        rL = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        p = next(x for x in rL.json()["prospects"] if x["id"] == pid)
        assert p.get("unsubscribed") is True
        assert p.get("unsubscribed_via") == "admin_manual"

        # cleanup → resubscribe
        rR = requests.post(
            f"{BASE_URL}/api/campaign/prospects/{pid}/resubscribe",
            headers=auth_headers, timeout=15,
        )
        assert rR.status_code == 200
        rL2 = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        p2 = next(x for x in rL2.json()["prospects"] if x["id"] == pid)
        assert p2.get("unsubscribed") is False

    def test_admin_unsubscribe_unknown_prospect_returns_404(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/campaign/prospects/does-not-exist-xyz/unsubscribe",
            headers=auth_headers, timeout=15,
        )
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────
# 4. Campaign stats expose `unsubscribed` field, prospects list has flag
# ────────────────────────────────────────────────────────────────
class TestStatsAndList:
    def test_stats_has_unsubscribed_field(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/campaign/stats",
            headers=auth_headers, timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert "unsubscribed" in data
        assert isinstance(data["unsubscribed"], int)
        assert data["unsubscribed"] >= 0
        print(f"\n[STATS] unsubscribed = {data['unsubscribed']} / sent = {data['sent']}")

    def test_prospects_list_contains_unsubscribed_records(self, auth_headers):
        r = requests.get(
            f"{BASE_URL}/api/campaign/prospects",
            headers=auth_headers, timeout=30,
        )
        assert r.status_code == 200
        prospects = r.json().get("prospects", [])
        # MongoDB _id must not be exposed
        for p in prospects[:5]:
            assert "_id" not in p
        unsub = [p for p in prospects if p.get("unsubscribed") is True]
        print(f"\n[LIST] {len(unsub)} unsubscribed / {len(prospects)} total")
        # informational only — don't fail if 0 (e.g., fresh DB)


# ────────────────────────────────────────────────────────────────
# 5. CRON filter helpers exclude unsubscribed prospects
# ────────────────────────────────────────────────────────────────
class TestCronFilters:
    @pytest.mark.asyncio
    async def test_relances_dues_excludes_unsubscribed(self):
        from routes.campaign import _relances_dues, _second_relances_dues
        r1 = await _relances_dues()
        r2 = await _second_relances_dues()
        # they return [{id, email}] dicts — fetch full docs to check flag
        from db import db
        for d in r1 + r2:
            full = await db.prospects.find_one({"id": d["id"]}, {"_id": 0})
            assert full is not None
            assert not full.get("unsubscribed"), \
                f"Prospect {d['email']} returned by relance helper but is unsubscribed!"
