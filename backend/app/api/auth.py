from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional

from app.models.request import RegisterRequest, LoginRequest
from app.services.auth_service import AuthService
from app.utils.logging import get_logger

logger = get_logger("api.auth")
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

auth_service = AuthService()

def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Extracts user payload from Bearer token if provided."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        return auth_service.verify_token(token)
    return None

def get_current_user_required(authorization: Optional[str] = Header(None)) -> dict:
    """Enforces valid authentication token."""
    user = get_current_user_optional(authorization)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in to your account."
        )
    return user

@router.post("/register")
def register(request: RegisterRequest):
    try:
        resolved_name = request.display_name or request.full_name
        result = auth_service.register(
            email=request.email,
            password=request.password,
            display_name=resolved_name
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration service temporarily unavailable.")

@router.post("/login")
def login(request: LoginRequest):
    try:
        result = auth_service.login(
            email=request.email,
            password=request.password
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication service temporarily unavailable.")

@router.get("/me")
def get_me(user: dict = Depends(get_current_user_required)):
    return {"user": user}

