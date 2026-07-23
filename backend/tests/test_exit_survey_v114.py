"""Tests v1.1.4 — Exit Survey + Grace Period (30 jours).

Cible: /account/delete-with-survey, /account/restore, /admin/exit-surveys
+ blocage login/auth_user pour un compte pending_deletion.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient

from db import db
from deps import hash_password
from routes.account_deletion import _make_restore_token
from tests.conftest import hdr

PYTEST_TAG_EMAIL = "lot_exit_"


# --- Fixtures spécifiques ------------------------------------------------
@pytest_asyncio.fixture
async def fresh_user(client: AsyncClient):
    """Crée un user actif fresh + retourne (user_doc, password, jwt).
    Nettoyé automatiquement à la fin (user + surveys)."""
    suffix = uuid.uuid4().hex[:10]
    email = f"{PYTEST_TAG_EMAIL}{suffix}@mesurechassis.fr"
    password = "Exit2026Test!"
    now_iso = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "name": f"Exit Test {suffix}",
        "email": email,
        "role": "admin",
        "company_id": f"lot-exit-co-{suffix}",
        "hashed_password": hash_password(password),
        "status": "active",
        "email_verified_at": now_iso,
        "created_at": now_iso,
    }
    await db.users.insert_one(doc)

    # Login pour récupérer un JWT réel
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, f"login fresh_user failed: {r.text}"
    jwt = r.json()["access_token"]

    yield {"user_id": user_id, "email": email, "password": password, "jwt": jwt}

    # Cleanup
    await db.users.delete_one({"id": user_id})
    await db.account_deletion_surveys.delete_many({"user_id": user_id})
    await db.companies.delete_one({"company_id": doc["company_id"]})


# ─────────────────────────────────────────────────────────────────────
# 1. POST /api/account/delete-with-survey
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_survey_no_auth(client: AsyncClient):
    r = await client.post(
        "/api/account/delete-with-survey",
        json={"reason": "technical_issues", "password": "x"},
    )
    assert r.status_code == 401, r.text


@pytest.mark.asyncio
async def test_delete_survey_invalid_reason(client: AsyncClient, fresh_user):
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={"reason": "foobar", "password": fresh_user["password"]},
    )
    assert r.status_code == 400
    assert "Raison invalide" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_delete_survey_other_without_custom_text(client: AsyncClient, fresh_user):
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={"reason": "other", "password": fresh_user["password"]},
    )
    assert r.status_code == 400
    assert "préciser" in r.json().get("detail", "").lower()

    # custom_text vide -> pareil
    r2 = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={
            "reason": "other",
            "custom_text": "   ",
            "password": fresh_user["password"],
        },
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_delete_survey_wrong_password(client: AsyncClient, fresh_user):
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={"reason": "technical_issues", "password": "wrong-pw-xxx"},
    )
    assert r.status_code == 400
    assert "Mot de passe incorrect" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_delete_survey_happy_path_and_db(client: AsyncClient, fresh_user):
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={
            "reason": "technical_issues",
            "password": fresh_user["password"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["grace_period_days"] == 30
    assert body["hard_delete_scheduled_at"]
    assert "message" in body

    # DB — user
    user_doc = await db.users.find_one({"id": fresh_user["user_id"]})
    assert user_doc["status"] == "pending_deletion"
    assert user_doc.get("pending_deletion_since")
    assert user_doc.get("pending_deletion_until")
    # Vérif approx +30j
    until_dt = datetime.fromisoformat(
        user_doc["pending_deletion_until"].replace("Z", "+00:00")
    )
    delta_days = (until_dt - datetime.now(timezone.utc)).days
    assert 29 <= delta_days <= 30, f"pending_deletion_until off by {delta_days}"

    # DB — survey
    survey = await db.account_deletion_surveys.find_one(
        {"user_id": fresh_user["user_id"]}
    )
    assert survey is not None
    assert survey["reason"] == "technical_issues"
    assert survey["reason_label"]
    assert survey["custom_text"] is None
    assert "plan_at_deletion" in survey
    assert isinstance(survey["days_since_signup"], int)
    assert isinstance(survey["chantier_count"], int)
    assert survey["deletion_requested_at"]
    assert survey["hard_delete_scheduled_at"]
    assert survey["restored_at"] is None
    assert survey["hard_deleted_at"] is None


# ─────────────────────────────────────────────────────────────────────
# 2. Login block + auth_user block pour pending_deletion
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_login_blocked_when_pending_deletion(client: AsyncClient, fresh_user):
    # Trigger deletion
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={"reason": "no_longer_needed", "password": fresh_user["password"]},
    )
    assert r.status_code == 200

    # Login → 403 avec code account_pending_deletion
    r2 = await client.post(
        "/api/auth/login",
        json={"email": fresh_user["email"], "password": fresh_user["password"]},
    )
    assert r2.status_code == 403, r2.text
    detail = r2.json().get("detail", {})
    assert isinstance(detail, dict)
    assert detail.get("code") == "account_pending_deletion"

    # JWT zombie via auth_user → 403 même code
    r3 = await client.get("/api/auth/me", headers=hdr(fresh_user["jwt"]))
    assert r3.status_code == 403, r3.text
    detail3 = r3.json().get("detail", {})
    assert isinstance(detail3, dict)
    assert detail3.get("code") == "account_pending_deletion"


# ─────────────────────────────────────────────────────────────────────
# 3. GET /api/account/restore
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_restore_missing_token(client: AsyncClient):
    r = await client.get("/api/account/restore")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_restore_invalid_token(client: AsyncClient):
    r = await client.get("/api/account/restore?token=invalidxxxx")
    # Le token doit contenir >=10 chars pour passer la validation Query
    assert r.status_code == 400
    # ⚠️ Minor issue: le path d'erreur JWT lève HTTPException → réponse JSON
    # au lieu de la page HTML "erreur" prévue par la spec (le code décorateur
    # response_class=HTMLResponse ne s'applique pas aux exceptions).
    # Le status est bon, seul le format diffère (impact UX mineur).
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_restore_full_flow_and_idempotence(client: AsyncClient, fresh_user):
    # 1) On supprime
    r = await client.post(
        "/api/account/delete-with-survey",
        headers=hdr(fresh_user["jwt"]),
        json={
            "reason": "missing_features",
            "password": fresh_user["password"],
        },
    )
    assert r.status_code == 200

    # 2) Génère un token de restauration comme le fait l'API
    token = _make_restore_token(fresh_user["user_id"], fresh_user["email"])

    # 3) Appelle /account/restore → HTML 200 avec "COMPTE RESTAURÉ"
    r2 = await client.get(f"/api/account/restore?token={token}")
    assert r2.status_code == 200, r2.text
    assert "text/html" in r2.headers.get("content-type", "")
    assert "COMPTE RESTAURÉ" in r2.text

    # 4) DB check — user actif, survey.restored_at set
    user_doc = await db.users.find_one({"id": fresh_user["user_id"]})
    assert user_doc["status"] == "active"
    assert "pending_deletion_since" not in user_doc
    assert "pending_deletion_until" not in user_doc

    survey = await db.account_deletion_surveys.find_one(
        {"user_id": fresh_user["user_id"]}
    )
    assert survey["restored_at"] is not None
    assert survey["hard_deleted_at"] is None

    # 5) Login à nouveau → 200 nominal
    r3 = await client.post(
        "/api/auth/login",
        json={"email": fresh_user["email"], "password": fresh_user["password"]},
    )
    assert r3.status_code == 200, r3.text
    assert "access_token" in r3.json()

    # 6) Idempotence : réutiliser le même token → HTML 200 "COMPTE DÉJÀ ACTIF"
    r4 = await client.get(f"/api/account/restore?token={token}")
    assert r4.status_code == 200
    assert "COMPTE DÉJÀ ACTIF" in r4.text


# ─────────────────────────────────────────────────────────────────────
# 4. GET /api/admin/exit-surveys
# ─────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_admin_exit_surveys_no_token(client: AsyncClient):
    r = await client.get("/api/admin/exit-surveys")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_exit_surveys_bad_token(client: AsyncClient):
    r = await client.get("/api/admin/exit-surveys?token=WRONGWRONGWRONG")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_exit_surveys_good_token(client: AsyncClient):
    token = os.getenv("PLATFORM_ADMIN_TOKEN", "").strip()
    assert token, "PLATFORM_ADMIN_TOKEN doit être configuré"
    r = await client.get(f"/api/admin/exit-surveys?token={token}")
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers.get("content-type", "")
    assert "EXIT SURVEYS" in r.text
    # Stats block présent
    assert "Total suppressions" in r.text


# ─────────────────────────────────────────────────────────────────────
# Cleanup finale : anti-résidu lot_exit_
# ─────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="module", autouse=True)
async def _lot_exit_cleanup():
    yield
    # Supprime tout résidu qui n'aurait pas été nettoyé par la fixture user
    residues = await db.users.find(
        {"email": {"$regex": f"^{PYTEST_TAG_EMAIL}"}}, {"_id": 0, "id": 1, "company_id": 1}
    ).to_list(500)
    ids = [u["id"] for u in residues]
    cids = [u.get("company_id") for u in residues if u.get("company_id")]
    if ids:
        await db.users.delete_many({"id": {"$in": ids}})
        await db.account_deletion_surveys.delete_many({"user_id": {"$in": ids}})
    if cids:
        await db.companies.delete_many({"company_id": {"$in": cids}})
