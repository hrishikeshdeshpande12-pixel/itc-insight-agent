from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from google.cloud import firestore

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("service.chat_history")

def _generate_title(question: str) -> str:
    """Generates a clean session title from the initial user query."""
    clean = question.strip()
    # Strip leading conversational words
    for prefix in ["show me the ", "tell me about ", "what is the ", "what is ", "can you explain ", "explain "]:
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):].strip()
            break
    if clean:
        clean = clean[0].upper() + clean[1:]
    if len(clean) > 55:
        return clean[:52] + "..."
    return clean or "ITC Corporate Inquiry"


class FirestoreChatService:
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or settings.GOOGLE_CLOUD_PROJECT
        self._db: Optional[firestore.Client] = None

    @property
    def db(self) -> firestore.Client:
        if self._db is None:
            self._db = firestore.Client(project=self.project_id)
        return self._db

    def save_turn(
        self,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        citations: Optional[List[Any]] = None,
        related_images: Optional[List[Dict[str, Any]]] = None,
        source_type: str = "document",
        diagram: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Persists a complete conversation exchange (user query & assistant synthesis) in Firestore."""
        now_iso = datetime.now(timezone.utc).isoformat()
        doc_ref = self.db.collection("conversations").document(session_id)
        doc = doc_ref.get()

        # Serialize citations safely if passed as Pydantic models
        serialized_citations = []
        if citations:
            for c in citations:
                if hasattr(c, "model_dump"):
                    serialized_citations.append(c.model_dump())
                elif hasattr(c, "dict"):
                    serialized_citations.append(c.dict())
                elif isinstance(c, dict):
                    serialized_citations.append(c)
                else:
                    serialized_citations.append(str(c))

        user_msg = {
            "role": "user",
            "content": question,
            "timestamp": now_iso
        }
        assistant_msg = {
            "role": "assistant",
            "content": answer,
            "citations": serialized_citations,
            "related_images": related_images or [],
            "source_type": source_type,
            "diagram": diagram,
            "metadata": metadata or {},
            "timestamp": now_iso
        }

        if doc.exists:
            data = doc.to_dict() or {}
            existing_messages = data.get("messages", [])
            existing_messages.extend([user_msg, assistant_msg])

            doc_ref.update({
                "updated_at": now_iso,
                "message_count": len(existing_messages),
                "messages": existing_messages
            })
        else:
            title = _generate_title(question)
            doc_ref.set({
                "session_id": session_id,
                "user_id": user_id,
                "title": title,
                "created_at": now_iso,
                "updated_at": now_iso,
                "message_count": 2,
                "messages": [user_msg, assistant_msg]
            })

        logger.info(f"Persisted chat turn to Firestore for user '{user_id}', session '{session_id}'")
        return {
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "citations": serialized_citations,
            "timestamp": now_iso
        }

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves summary metadata for all sessions belonging to a specific user."""
        try:
            # Query conversations filtered by user_id
            docs = self.db.collection("conversations").where("user_id", "==", user_id).stream()
            sessions = []
            for d in docs:
                data = d.to_dict() or {}
                sessions.append({
                    "id": data.get("session_id", d.id),
                    "session_id": data.get("session_id", d.id),
                    "title": data.get("title", "ITC Inquiry"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": data.get("message_count", 0)
                })
            # Sort newest first by updated_at
            sessions.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
            return sessions
        except Exception as e:
            logger.error(f"Error fetching sessions for user '{user_id}': {e}")
            return []

    def get_session_messages(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Loads all chat messages for a specific session."""
        try:
            doc = self.db.collection("conversations").document(session_id).get()
            if not doc.exists:
                return []
            data = doc.to_dict() or {}
            # Verify user ownership or allow if guest session
            if data.get("user_id") and data.get("user_id") != user_id and data.get("user_id") != "guest":
                logger.warning(f"Unauthorized session access attempt: session '{session_id}' does not belong to '{user_id}'")
                return []
            return data.get("messages", [])
        except Exception as e:
            logger.error(f"Error loading messages for session '{session_id}': {e}")
            return []

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Deletes a conversation session from Firestore."""
        try:
            doc_ref = self.db.collection("conversations").document(session_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            data = doc.to_dict() or {}
            if data.get("user_id") != user_id and data.get("user_id") != "guest":
                return False
            doc_ref.delete()
            logger.info(f"Deleted session '{session_id}' for user '{user_id}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting session '{session_id}': {e}")
            return False

# Export default singleton instance
firestore_chat_service = FirestoreChatService()


