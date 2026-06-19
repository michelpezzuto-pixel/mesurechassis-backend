"""Yann AI Assistant — backend integration tests (iteration 10).

Tests the new POST /api/yann/chat, GET /api/yann/history, GET /api/yann/quota
routes using emergentintegrations + Claude Sonnet 4.5.
"""
from __future__ import annotations

import os
import sys
import pytest
import requests
from pymongo import MongoClient

# Allow direct mongo access (verify persistence) — sync client to avoid
# event-loop conflicts inside pytest.
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
_sync_client = MongoClient(MONGO_URL)
sync_db = _sync_client[DB_NAME]

BASE_URL = "https://window-field-app.preview.emergentagent.com"
API = f"{BASE_URL}/api"

EMAIL = "cousin.admin@test.mesurechassis.com"
PASSWORD = "Cousin2026!"


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=20,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def user_id(auth_token):
    r = requests.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("id") or data.get("user_id")


# --- Test 1 : quota endpoint ------------------------------------------------
def test_quota_endpoint(headers):
    r = requests.get(f"{API}/yann/quota", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["limit"] == 30
    assert "used" in data
    assert "remaining" in data
    assert data["remaining"] == 30 - data["used"]


# --- Test 6 : auth required -------------------------------------------------
def test_chat_requires_auth():
    r = requests.post(
        f"{API}/yann/chat", json={"message": "hello"}, timeout=10
    )
    assert r.status_code in (401, 403), r.text


# --- Test 4 : empty message -------------------------------------------------
def test_chat_empty_message_400(headers):
    r = requests.post(
        f"{API}/yann/chat", json={"message": ""}, headers=headers, timeout=10
    )
    assert r.status_code == 400, r.text


# --- Test 5 : message too long ----------------------------------------------
def test_chat_long_message_400(headers):
    r = requests.post(
        f"{API}/yann/chat",
        json={"message": "x" * 2001},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 400, r.text


# --- Test 2 : first chat (LLM call, slow) -----------------------------------
@pytest.fixture(scope="module")
def first_chat(headers):
    r = requests.post(
        f"{API}/yann/chat",
        json={"message": "Bonjour Yann"},
        headers=headers,
        timeout=60,
    )
    assert r.status_code == 200, f"Chat failed: {r.status_code} {r.text}"
    data = r.json()
    assert "reply" in data and "session_id" in data and "quota_remaining" in data
    assert len(data["reply"]) > 0
    return data


def test_chat_first_message_french(first_chat):
    reply_low = first_chat["reply"].lower()
    # French markers — at least one should be present
    french_markers = ["bonjour", "salut", "comment", "puis", "vous", "je"]
    assert any(m in reply_low for m in french_markers), f"Reply doesn't look French: {first_chat['reply']}"


# --- Test 3 : follow-up references prices -----------------------------------
def test_chat_followup_mentions_prices(headers, first_chat):
    session_id = first_chat["session_id"]
    r = requests.post(
        f"{API}/yann/chat",
        json={
            "message": "Quels sont les prix des formules ?",
            "session_id": session_id,
        },
        headers=headers,
        timeout=60,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    reply = data["reply"]
    # The system prompt teaches these values
    has_solo = "19,99" in reply or "19.99" in reply
    has_ent = "59,99" in reply or "59.99" in reply
    has_pro = "249" in reply
    assert has_solo or has_ent or has_pro, f"No price in reply: {reply}"


# --- Test 9 : persistence in MongoDB ----------------------------------------
def test_conversation_persisted_mongo(first_chat):
    session_id = first_chat["session_id"]
    doc = sync_db.yann_conversations.find_one({"session_id": session_id})
    assert doc is not None, "Conversation not persisted"
    assert "messages" in doc
    assert len(doc["messages"]) >= 2  # at least user + assistant


# --- Test 10 : quota counter increments -------------------------------------
def test_quota_increments(headers, first_chat, user_id):
    from datetime import datetime, timezone
    today_iso = datetime.now(timezone.utc).date().isoformat()
    doc = sync_db.yann_quota.find_one({"user_id": user_id, "date": today_iso})
    assert doc is not None, "Quota doc missing"
    assert doc.get("count", 0) >= 1


# --- Test 7 : history endpoint ----------------------------------------------
def test_history_for_own_session(headers, first_chat):
    session_id = first_chat["session_id"]
    r = requests.get(
        f"{API}/yann/history",
        params={"session_id": session_id},
        headers=headers,
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["session_id"] == session_id
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) >= 2


# --- Test 8 : cross-user history forbidden ----------------------------------
def test_history_cross_user_forbidden(headers):
    """Insert a session belonging to a different user, then try to read it."""

    fake_session_id = "yann_otheruser_999999"
    sync_db.yann_conversations.update_one(
        {"session_id": fake_session_id},
        {"$set": {
            "session_id": fake_session_id,
            "user_id": "some-other-user-id-not-mine",
            "messages": [{"role": "user", "content": "test"}],
        }},
        upsert=True,
    )
    try:
        r = requests.get(
            f"{API}/yann/history",
            params={"session_id": fake_session_id},
            headers=headers,
            timeout=10,
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
    finally:
        sync_db.yann_conversations.delete_one({"session_id": fake_session_id})
