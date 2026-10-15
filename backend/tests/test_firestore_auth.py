import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.firestore_chat_service import firestore_chat_service
from app.services.firestore_knowledge_service import firestore_knowledge_service
from app.models.response import Citation

client = TestClient(app)

def test_firestore_knowledge_uploaded():
    """Verify that document chunks and embeddings exist in Firestore."""
    count = firestore_knowledge_service.get_chunk_count()
    assert count >= 1955, f"Expected at least 1955 chunks in Firestore, found {count}"


def test_auth_registration_and_login_flow():
    """Test user registration, duplicate prevention, login, and profile lookup."""
    unique_suffix = int(time.time())
    email = f"analyst_{unique_suffix}@itc.in"
    password = "StrongPassword@123"
    name = f"ITC Analyst {unique_suffix}"

    # 1. Register new user
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": name}
    )
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "token" in reg_data
    assert reg_data["user"]["email"] == email
    assert reg_data["user"]["display_name"] == name
    assert reg_data["user"]["full_name"] == name
    token = reg_data["token"]
    user_id = reg_data["user"]["id"]

    # 2. Prevent duplicate email
    dup_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": name}
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json().get("detail", "")

    # 3. Test login with correct password
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert login_data["user"]["id"] == user_id

    # 4. Test login with incorrect password
    bad_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword"}
    )
    assert bad_login.status_code == 401

    # 5. Test GET /api/auth/me with Bearer token
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == email


def test_firestore_conversation_persistence():
    """Test saving chat turns, fetching session lists, retrieving turns, and session deletion."""
    test_user_id = f"test_user_{int(time.time())}"
    session_id = f"test_sess_{int(time.time())}"

    # 1. Save turn 1
    citations = [
        Citation(
            source_type="document",
            title="ITC-Report-and-Accounts-2026.pdf",
            page_number=42,
            snippet="FMCG segment revenue grew by 12% in FY 2025-26."
        )
    ]
    turn_1 = firestore_chat_service.save_turn(
        user_id=test_user_id,
        session_id=session_id,
        question="What was FMCG revenue growth in 2026?",
        answer="According to the Report and Accounts 2026, FMCG revenue grew by 12%.",
        citations=citations,
        diagram=None,
        metadata={"confidence": "HIGH", "score": 0.88}
    )
    assert turn_1 is not None
    assert turn_1["question"] == "What was FMCG revenue growth in 2026?"

    # 2. Save turn 2
    turn_2 = firestore_chat_service.save_turn(
        user_id=test_user_id,
        session_id=session_id,
        question="How does this compare to hotels?",
        answer="Hotels segment recorded a 15% revenue expansion over the same period.",
        citations=[],
        diagram=None
    )
    assert turn_2 is not None

    # 3. List user sessions
    sessions = firestore_chat_service.get_user_sessions(test_user_id)
    assert len(sessions) >= 1
    target_session = next((s for s in sessions if s["id"] == session_id), None)
    assert target_session is not None
    assert "FMCG revenue growth in 2026?" in target_session["title"]
    assert target_session["message_count"] == 4  # 2 questions + 2 answers

    # 4. Fetch session messages
    messages = firestore_chat_service.get_session_messages(test_user_id, session_id)
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What was FMCG revenue growth in 2026?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["citations"][0]["title"] == "ITC-Report-and-Accounts-2026.pdf"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == "How does this compare to hotels?"

    # 5. Delete session
    delete_ok = firestore_chat_service.delete_session(test_user_id, session_id)
    assert delete_ok is True

    # 6. Verify session messages gone
    remaining = firestore_chat_service.get_session_messages(test_user_id, session_id)
    assert len(remaining) == 0

