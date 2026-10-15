import os
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from google.cloud import firestore

from app.config import settings
from app.services.email_service import email_service
from app.utils.logging import get_logger

logger = get_logger("service.auth")

JWT_SECRET = os.getenv("JWT_SECRET", "itc-corporate-intelligence-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 14

class AuthService:
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or settings.GOOGLE_CLOUD_PROJECT
        self._db: Optional[firestore.Client] = None

    @property
    def db(self) -> firestore.Client:
        if self._db is None:
            self._db = firestore.Client(project=self.project_id)
        return self._db

    def is_admin_email(self, email: str) -> bool:
        clean = (email or "").strip().lower()
        admin_emails = {
            settings.ADMIN_EMAIL.strip().lower(),
            "hrishikeshdeshpande23@gmail.com",
            "hrishikesh@itc.in"
        }
        return clean in admin_emails

    def _create_token(self, user_id: str, email: str, display_name: str, role: str = "user") -> str:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=JWT_EXPIRATION_DAYS)
        payload = {
            "sub": user_id,
            "email": email,
            "name": display_name,
            "role": role,
            "iat": now.timestamp(),
            "exp": exp.timestamp()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def register(self, email: str, password: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Registers a new user.
        If user is admin (hrishikeshdeshpande23@gmail.com): auto-approved with role='admin'.
        If other user: created with status='pending', dispatches email alert to admin.
        """
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Please provide a valid email address.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        clean_name = (display_name or "").strip() or clean_email.split("@")[0].capitalize()

        # Check for existing user by email query
        existing = list(self.db.collection("users").where("email", "==", clean_email).limit(1).stream())
        if existing:
            raise ValueError("An account with this email address already exists. Please sign in.")

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        now_iso = datetime.now(timezone.utc).isoformat()

        is_admin = self.is_admin_email(clean_email)
        role = "admin" if is_admin else "user"
        status = "approved" if is_admin else "pending"

        user_data = {
            "id": user_id,
            "email": clean_email,
            "display_name": clean_name,
            "password_hash": hashed_pw,
            "role": role,
            "status": status,
            "created_at": now_iso,
            "last_login": now_iso if is_admin else None,
            "approved_at": now_iso if is_admin else None,
            "approved_by": "system" if is_admin else None
        }

        self.db.collection("users").document(user_id).set(user_data)
        logger.info(f"Registered new user '{clean_email}' (id: {user_id}, role: {role}, status: {status})")

        # If admin, issue token immediately
        if is_admin:
            token = self._create_token(user_id, clean_email, clean_name, role=role)
            return {
                "status": "approved",
                "token": token,
                "user": {
                    "id": user_id,
                    "email": clean_email,
                    "display_name": clean_name,
                    "full_name": clean_name,
                    "role": role,
                    "status": status,
                    "created_at": now_iso
                }
            }

        # For normal users, trigger email notification to administrator in background
        email_service.send_admin_new_user_notification(user_data)

        return {
            "status": "pending",
            "message": f"Registration request submitted successfully. A notification has been dispatched to {settings.ADMIN_EMAIL}. You will be able to log in once your account is approved.",
            "user": {
                "id": user_id,
                "email": clean_email,
                "display_name": clean_name,
                "full_name": clean_name,
                "role": role,
                "status": status,
                "created_at": now_iso
            }
        }

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticates user against Firestore credentials.
        Rejects unapproved or pending users with clear notices.
        """
        clean_email = email.strip().lower()
        users_stream = list(self.db.collection("users").where("email", "==", clean_email).limit(1).stream())
        if not users_stream:
            raise ValueError("Invalid email or password.")

        doc = users_stream[0]
        user_data = doc.to_dict() or {}
        hashed_pw = user_data.get("password_hash", "").encode("utf-8")

        if not bcrypt.checkpw(password.encode("utf-8"), hashed_pw):
            raise ValueError("Invalid email or password.")

        # Resolve role & status
        is_admin = self.is_admin_email(clean_email)
        role = "admin" if is_admin else user_data.get("role", "user")
        status = "approved" if is_admin else user_data.get("status", "approved")

        # Backfill existing users if role/status were missing
        if user_data.get("role") != role or user_data.get("status") != status:
            doc.reference.update({"role": role, "status": status})

        # Check approval status
        if status == "pending":
            raise ValueError(
                f"Your account registration is currently pending administrator approval. "
                f"A notification has been sent to {settings.ADMIN_EMAIL}. "
                f"Please wait for your request to be approved before signing in."
            )
        elif status == "rejected":
            raise ValueError(
                f"Your account registration request was declined by the administrator. "
                f"Please contact {settings.ADMIN_EMAIL} if you believe this is an error."
            )

        # Update last login
        now_iso = datetime.now(timezone.utc).isoformat()
        doc.reference.update({"last_login": now_iso})

        user_id = user_data["id"]
        display_name = user_data.get("display_name", clean_email.split("@")[0].capitalize())
        token = self._create_token(user_id, clean_email, display_name, role=role)

        logger.info(f"User '{clean_email}' ({role}, {status}) successfully authenticated.")
        return {
            "token": token,
            "user": {
                "id": user_id,
                "email": clean_email,
                "display_name": display_name,
                "full_name": display_name,
                "role": role,
                "status": status,
                "created_at": user_data.get("created_at")
            }
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies JWT token and returns decoded payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    # Admin Management Methods
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Retrieves all users sorted by registration date."""
        users_stream = self.db.collection("users").stream()
        user_list = []
        for doc in users_stream:
            data = doc.to_dict() or {}
            clean_email = data.get("email", "")
            is_admin = self.is_admin_email(clean_email)
            role = "admin" if is_admin else data.get("role", "user")
            status = "approved" if is_admin else data.get("status", "approved")

            user_list.append({
                "id": data.get("id", doc.id),
                "email": clean_email,
                "display_name": data.get("display_name", clean_email.split("@")[0].capitalize()),
                "role": role,
                "status": status,
                "created_at": data.get("created_at"),
                "last_login": data.get("last_login"),
                "approved_at": data.get("approved_at"),
                "approved_by": data.get("approved_by")
            })

        user_list.sort(key=lambda u: u.get("created_at") or "", reverse=True)
        return user_list

    def approve_user(self, user_id: str, admin_email: str) -> Dict[str, Any]:
        """Approves a pending user account and sends confirmation email."""
        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError(f"User with ID '{user_id}' does not exist.")

        data = doc.to_dict() or {}
        now_iso = datetime.now(timezone.utc).isoformat()

        update_payload = {
            "status": "approved",
            "approved_at": now_iso,
            "approved_by": admin_email
        }
        doc_ref.update(update_payload)
        data.update(update_payload)
        data.pop("password_hash", None)

        logger.info(f"User '{data.get('email')}' approved by admin '{admin_email}'.")

        # Send approval email to user
        email_service.send_user_approved_notification(data)
        return data

    def reject_user(self, user_id: str, admin_email: str) -> Dict[str, Any]:
        """Rejects a user account."""
        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError(f"User with ID '{user_id}' does not exist.")

        data = doc.to_dict() or {}
        now_iso = datetime.now(timezone.utc).isoformat()

        update_payload = {
            "status": "rejected",
            "rejected_at": now_iso,
            "rejected_by": admin_email
        }
        doc_ref.update(update_payload)
        data.update(update_payload)
        data.pop("password_hash", None)

        logger.info(f"User '{data.get('email')}' rejected by admin '{admin_email}'.")
        return data

    def delete_user(self, user_id: str, current_user_email: str) -> bool:
        """Deletes a user account from Firestore (cannot delete self)."""
        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        data = doc.to_dict() or {}
        if data.get("email", "").lower() == current_user_email.lower():
            raise ValueError("You cannot delete your own administrator account.")

        doc_ref.delete()
        logger.info(f"User '{data.get('email')}' deleted by admin '{current_user_email}'.")
        return True

    def get_admin_stats(self) -> Dict[str, Any]:
        """Calculates user statistics for the Admin Portal."""
        users = self.get_all_users()
        total = len(users)
        pending = sum(1 for u in users if u.get("status") == "pending")
        approved = sum(1 for u in users if u.get("status") == "approved")
        rejected = sum(1 for u in users if u.get("status") == "rejected")
        return {
            "total_users": total,
            "pending_approvals": pending,
            "approved_users": approved,
            "rejected_users": rejected
        }

    def get_admin_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent admin notifications from Firestore."""
        notifs_stream = self.db.collection("admin_notifications").limit(limit).stream()
        notifs = [d.to_dict() for d in notifs_stream]
        notifs.sort(key=lambda n: n.get("created_at") or "", reverse=True)
        return notifs

auth_service = AuthService()
