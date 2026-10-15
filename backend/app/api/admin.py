from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List, Dict, Any

from app.services.auth_service import AuthService
from app.api.auth import get_current_user_required
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("api.admin")
router = APIRouter(prefix="/api/admin", tags=["Admin"])
auth_service = AuthService()

def get_current_admin_required(user: dict = Depends(get_current_user_required)) -> dict:
    """Enforces that the current authenticated user has administrator privileges."""
    user_email = user.get("email", "").lower()
    user_role = user.get("role", "")

    is_admin = (
        user_role == "admin"
        or user_email == settings.ADMIN_EMAIL.lower()
        or user_email in ["hrishikeshdeshpande23@gmail.com", "hrishikesh@itc.in"]
    )

    if not is_admin:
        logger.warning(f"Unauthorized admin access attempt by user '{user_email}'")
        raise HTTPException(
            status_code=403,
            detail="Access denied. Administrator privileges required to access this portal."
        )
    return user

@router.get("/users")
def list_users(admin: dict = Depends(get_current_admin_required)):
    """Lists all registered users and their approval status."""
    try:
        users = auth_service.get_all_users()
        return {"users": users}
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve user directory.")

@router.post("/users/{user_id}/approve")
def approve_user(user_id: str, admin: dict = Depends(get_current_admin_required)):
    """Approves a pending user account."""
    try:
        admin_email = admin.get("email", settings.ADMIN_EMAIL)
        updated_user = auth_service.approve_user(user_id, admin_email)
        return {
            "success": True,
            "message": f"User '{updated_user.get('email')}' has been successfully approved.",
            "user": updated_user
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve user account.")

@router.post("/users/{user_id}/reject")
def reject_user(user_id: str, admin: dict = Depends(get_current_admin_required)):
    """Rejects a user account request."""
    try:
        admin_email = admin.get("email", settings.ADMIN_EMAIL)
        updated_user = auth_service.reject_user(user_id, admin_email)
        return {
            "success": True,
            "message": f"User '{updated_user.get('email')}' request has been declined.",
            "user": updated_user
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error rejecting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject user account.")

@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(get_current_admin_required)):
    """Deletes a user account from Firestore."""
    try:
        admin_email = admin.get("email", "")
        success = auth_service.delete_user(user_id, admin_email)
        if not success:
            raise HTTPException(status_code=404, detail="User not found.")
        return {"success": True, "message": "User account successfully deleted."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user account.")

@router.get("/stats")
def get_stats(admin: dict = Depends(get_current_admin_required)):
    """Retrieves high-level user statistics for the Admin Portal."""
    try:
        stats = auth_service.get_admin_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve admin metrics.")

@router.get("/notifications")
def get_notifications(admin: dict = Depends(get_current_admin_required)):
    """Retrieves recent account registration requests and alerts."""
    try:
        notifs = auth_service.get_admin_notifications()
        return {"notifications": notifs}
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve notifications.")

