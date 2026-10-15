from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, List, Dict, Any

from app.api.auth import get_current_user_optional, get_current_user_required
from app.services.firestore_chat_service import FirestoreChatService
from app.utils.logging import get_logger

logger = get_logger("api.sessions")
router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

chat_service = FirestoreChatService()

@router.get("")
def list_user_sessions(user: dict = Depends(get_current_user_required)):
    """Retrieves all historical chat sessions for the authenticated user."""
    user_id = user["sub"]
    sessions = chat_service.get_user_sessions(user_id)
    return {"sessions": sessions}

@router.get("/{session_id}")
def get_session_messages(
    session_id: str,
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """Loads all chat messages for a given session."""
    user_id = user["sub"] if user else "guest"
    messages = chat_service.get_session_messages(user_id, session_id)
    return {
        "session_id": session_id,
        "messages": messages
    }

@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user_required)
):
    """Deletes a conversation session from Firestore."""
    user_id = user["sub"]
    success = chat_service.delete_session(user_id, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized.")
    return {"status": "deleted", "session_id": session_id}

