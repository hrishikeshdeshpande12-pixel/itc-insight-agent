from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from app.models.request import ChatRequest
from app.models.response import ChatResponse
from app.agent.agent import ITCAgent
from app.api.auth import get_current_user_required
from app.services.firestore_chat_service import FirestoreChatService
from app.utils.logging import get_logger

logger = get_logger("api.chat")
router = APIRouter()

# Instantiate single agent instance & chat history service
agent = ITCAgent()
chat_service = FirestoreChatService()

@router.post("/chat", response_model=ChatResponse)
def handle_chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    q = request.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    # Require authentication - guest inquiries are disallowed
    user = get_current_user_required(authorization)
    user_id = user["sub"]


    try:
        response = agent.run(question=q, session_id=request.session_id)

        # Persist conversation turn to Firestore
        try:
            chat_service.save_turn(
                user_id=user_id,
                session_id=response.session_id,
                question=q,
                answer=response.answer,
                citations=[c.dict() for c in response.citations] if response.citations else [],
                related_images=response.related_images or [],
                source_type=response.source_type
            )
        except Exception as save_err:
            logger.warning(f"Could not persist chat turn to Firestore: {save_err}")

        return response
    except Exception as e:
        logger.error(f"Error handling chat request: {e}", exc_info=True)
        # Never expose raw stack trace to user
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request. Please try again or rephrase your question."
        )

