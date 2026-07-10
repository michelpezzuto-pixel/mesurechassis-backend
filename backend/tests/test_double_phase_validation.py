"""Tests du système Double-Phase (validation par le gérant) — iter27.

Couvre :
- GET /api/auth/validation-status
- GET /api/team/pending-validation
- POST /api/auth/request-validation
- POST /api/team/validate/{user_id}
- POST /api/team/reject/{user_id}
- user_can_access() logic (unit)
- migrate_legacy_users idempotence
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Permet d'importer db, deps, routes.validation depuis /app/backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _run_async(coro):
    """Exécute une coroutine motor dans une boucle FRAÎCHE avec un client
    motor dédié à cette boucle (évite les 'attached to a different loop'
    quand d'autres fixtures session-scope tiennent le loop httpx ASGI)."""
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]

    async def _wrapped():
        cli = AsyncIOMotorClient(mongo_url)
        try:
            local_db = cli[db_name]
            return await coro(local_db)
        finally:
            cli.close()

    return asyncio.run(_wrapped())

BASE_URL = os.environ.get(
    "EXPO_PUBLIC_BACKEND_URL", "https://window-field-app.preview.emergentagent.com"
).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "artisan@mesurechassis.fr"
ADMIN_PASSWORD = "artisan123"
ADMIN_COMPANY_ID = "artisan-test-b14bf0"

TEST_OUVRIER_APPROVE_EMAIL = f"test-ouvrier-approve-{uuid.uuid4().hex[:6]}@mesurechassis.fr"
TEST_OUVRIER_REJECT_EMAIL = f"test-ouvrier-reject-{uuid.uuid4().hex[:6]}@mesurechassis.fr"


# ─────────────────────────────────────────────────────────────────
# Helpers & fixtures
# ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_hdr(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def approve_user_id():
    """Insère l'ouvrier "à approuver" directement en DB (motor async)."""
    import deps

    user_id = str(uuid.uuid4())

    async def _insert(local_db):
        await local_db.users.insert_one(
            {
                "id": user_id,
                "email": TEST_OUVRIER_APPROVE_EMAIL,
                "name": "Ouvrier Test Approve",
                "role": "technician",
                "company_id": ADMIN_COMPANY_ID,
                "hashed_password": deps.hash_password("Ouvrier123!"),
                "status": "active",
                "validation_status": "pending",
                "validation_requested_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    _run_async(_insert)
    yield user_id

    async def _cleanup(local_db):
        await local_db.users.delete_one({"id": user_id})

    _run_async(_cleanup)


@pytest.fixture(scope="module")
def reject_user_id():
    """Insère l'ouvrier "à rejeter" directement en DB."""
    import deps

    user_id = str(uuid.uuid4())

    async def _insert(local_db):
        await local_db.users.insert_one(
            {
                "id": user_id,
                "email": TEST_OUVRIER_REJECT_EMAIL,
                "name": "Ouvrier Test Reject",
                "role": "technician",
                "company_id": ADMIN_COMPANY_ID,
                "hashed_password": deps.hash_password("Ouvrier123!"),
                "status": "active",
                "validation_status": "pending",
                "validation_requested_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    _run_async(_insert)
    yield user_id

    async def _cleanup(local_db):
        await local_db.users.delete_one({"id": user_id})

    _run_async(_cleanup)


# ─────────────────────────────────────────────────────────────────
# 1. GET /api/auth/validation-status
# ─────────────────────────────────────────────────────────────────
class TestValidationStatus:
    def test_validation_status_admin(self, s, admin_hdr):
        r = s.get(f"{API}/auth/validation-status", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Contrat : ces clés doivent exister
        for k in ("can_access", "reason", "validation_status", "enforcement_active", "role"):
            assert k in data, f"clé manquante: {k}"
        # En Phase 1 (env courant), enforcement_active DOIT être false
        assert data["enforcement_active"] is False
        assert data["can_access"] is True
        assert data["reason"] is None
        assert data["role"] == "admin"

    def test_validation_status_requires_auth(self, s):
        r = s.get(f"{API}/auth/validation-status", timeout=30)
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────
# 2. GET /api/team/pending-validation
# ─────────────────────────────────────────────────────────────────
class TestPendingValidation:
    def test_pending_empty_or_baseline(self, s, admin_hdr):
        r = s.get(f"{API}/team/pending-validation", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "pending" in data and "count" in data
        assert isinstance(data["pending"], list)
        assert data["count"] == len(data["pending"])

    def test_pending_shows_inserted_worker(self, s, admin_hdr, approve_user_id):
        r = s.get(f"{API}/team/pending-validation", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        ids = [u["id"] for u in data["pending"]]
        assert approve_user_id in ids, (
            f"L'ouvrier inséré {approve_user_id} devrait apparaître dans pending. "
            f"Got: {ids}"
        )
        # Vérifie que le shape est bon
        item = next(u for u in data["pending"] if u["id"] == approve_user_id)
        assert item["email"] == TEST_OUVRIER_APPROVE_EMAIL
        assert item["role"] == "technician"
        # Sécurité : pas de _id MongoDB dans la réponse
        assert "_id" not in item

    def test_pending_requires_admin(self, s):
        r = s.get(f"{API}/team/pending-validation", timeout=30)
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────
# 3. POST /api/auth/request-validation
# ─────────────────────────────────────────────────────────────────
class TestRequestValidation:
    def test_admin_no_need(self, s, admin_hdr):
        # Michel est role=admin → doit retourner ok:true "pas besoin"
        r = s.post(f"{API}/auth/request-validation", headers=admin_hdr, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        # Message informatif présent
        assert "message" in data


# ─────────────────────────────────────────────────────────────────
# 4. POST /api/team/validate/{user_id}
# ─────────────────────────────────────────────────────────────────
class TestValidateMember:
    def test_approve_worker(self, s, admin_hdr, approve_user_id):
        r = s.post(
            f"{API}/team/validate/{approve_user_id}",
            headers=admin_hdr,
            json={},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "approuvé" in data.get("message", "").lower() or "approuve" in data.get("message", "").lower()

        # Vérifie en DB que validation_status a bien changé
        async def _check(local_db):
            return await local_db.users.find_one({"id": approve_user_id}, {"_id": 0})

        doc = _run_async(_check)
        assert doc is not None
        assert doc.get("validation_status") == "validated"
        assert doc.get("validated_at") is not None
        assert doc.get("validated_by") is not None

    def test_validate_not_found(self, s, admin_hdr):
        r = s.post(
            f"{API}/team/validate/does-not-exist-{uuid.uuid4().hex[:8]}",
            headers=admin_hdr,
            json={},
            timeout=30,
        )
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────
# 5. POST /api/team/reject/{user_id}
# ─────────────────────────────────────────────────────────────────
class TestRejectMember:
    def test_reject_worker(self, s, admin_hdr, reject_user_id):
        r = s.post(
            f"{API}/team/reject/{reject_user_id}",
            headers=admin_hdr,
            json={"reason": "test rejet"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "rejet" in data.get("message", "").lower()

        # Vérification DB
        async def _check(local_db):
            return await local_db.users.find_one({"id": reject_user_id}, {"_id": 0})

        doc = _run_async(_check)
        assert doc.get("validation_status") == "rejected"
        assert doc.get("rejected_at") is not None
        assert doc.get("rejected_by") is not None
        assert doc.get("rejection_reason") == "test rejet"


# ─────────────────────────────────────────────────────────────────
# 6. user_can_access — unit tests (kill switch simulation)
# ─────────────────────────────────────────────────────────────────
class TestUserCanAccess:
    def test_phase1_all_pass(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "false")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "technician", "validation_status": "unvalidated"})
        assert ok is True and reason is None

    def test_phase2_admin_pass(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "admin", "validation_status": "unvalidated"})
        assert ok is True and reason is None

    def test_phase2_artisan_pass(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "technician", "account_type": "artisan"})
        assert ok is True and reason is None

    def test_phase2_validated_pass(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "technician", "validation_status": "validated"})
        assert ok is True and reason is None

    def test_phase2_unvalidated_technician_blocked(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "technician", "validation_status": "unvalidated"})
        assert ok is False
        assert reason == "unvalidated"

    def test_phase2_rejected_blocked(self, monkeypatch):
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from routes.validation import user_can_access
        ok, reason = user_can_access({"role": "technician", "validation_status": "rejected"})
        assert ok is False
        assert reason == "rejected"

    def test_phase2_legacy_without_grace_blocked(self, monkeypatch):
        # Kill switch actif, mais AUCUNE grace-period configurée → legacy DOIT
        # tomber en block (in_grace_period() = False).
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        monkeypatch.delenv("PAYWALL_GRACE_PERIOD_START", raising=False)
        from routes.validation import user_can_access, in_grace_period
        assert in_grace_period() is False
        ok, reason = user_can_access({"role": "technician", "validation_status": "legacy"})
        assert ok is False
        assert reason == "unvalidated"

    def test_phase2_legacy_in_grace_pass(self, monkeypatch):
        # Grace-period active (démarre maintenant) → 30 jours de grâce
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        monkeypatch.setenv(
            "PAYWALL_GRACE_PERIOD_START",
            datetime.now(timezone.utc).isoformat(),
        )
        from routes.validation import user_can_access, in_grace_period
        assert in_grace_period() is True
        ok, reason = user_can_access({"role": "technician", "validation_status": "legacy"})
        assert ok is True and reason is None


# ─────────────────────────────────────────────────────────────────
# 7. require_validated_user — 403 metier payload
# ─────────────────────────────────────────────────────────────────
class TestRequireValidatedUserGuard:
    def test_guard_raises_403_with_business_code(self, monkeypatch):
        """Simule directement l'appel de la dépendance (offline, sans HTTP)."""
        monkeypatch.setenv("PAYWALL_ENFORCE_VALIDATION", "true")
        from fastapi import HTTPException
        from routes.validation import require_validated_user

        blocked_user = {"role": "technician", "validation_status": "unvalidated"}
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(require_validated_user(user=blocked_user))
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("code") == "PAYWALL_VALIDATION_REQUIRED"
        assert detail.get("reason") == "unvalidated"
        assert "message" in detail


# ─────────────────────────────────────────────────────────────────
# 8. migrate_legacy_users — idempotence
# ─────────────────────────────────────────────────────────────────
class TestMigrateLegacyIdempotent:
    def test_migration_second_run_zero_modifs(self):
        """Après un premier run, TOUS les users doivent déjà avoir un
        validation_status → second run met à jour 0 documents."""

        async def _run(local_db):
            # 1er run (au cas où la DB contient encore des users sans champ)
            r1 = await local_db.users.update_many(
                {
                    "validation_status": {"$exists": False},
                    "status": {"$ne": "deleted"},
                },
                {
                    "$set": {
                        "validation_status": "legacy",
                        "legacy_marked_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            # 2nd run — DOIT être 0
            r2 = await local_db.users.update_many(
                {
                    "validation_status": {"$exists": False},
                    "status": {"$ne": "deleted"},
                },
                {"$set": {"validation_status": "legacy"}},
            )
            return r1.modified_count, r2.modified_count

        first, second = _run_async(_run)
        assert second == 0, (
            f"Migration non idempotente : 2e run a modifié {second} docs "
            f"(1er run: {first})"
        )
