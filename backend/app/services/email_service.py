import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from google.cloud import firestore

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger("service.email")

class EmailService:
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or settings.GOOGLE_CLOUD_PROJECT
        self._db: Optional[firestore.Client] = None

    @property
    def db(self) -> firestore.Client:
        if self._db is None:
            self._db = firestore.Client(project=self.project_id)
        return self._db

    def _send_smtp_email(self, to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
        """Sends an email via SMTP. Returns True on success, False otherwise."""
        smtp_user = settings.SMTP_USER.strip()
        smtp_password = settings.SMTP_PASSWORD.strip().replace(" ", "")

        if not smtp_user or not smtp_password:
            logger.info(
                f"[Email Notice] SMTP credentials not yet provided in .env. "
                f"Simulating delivery: Email to '{to_email}' with subject '{subject}'. "
                f"To send live emails, set SMTP_USER and SMTP_PASSWORD in backend/.env."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"ITC Insight Intelligence <{smtp_user}>"
            msg["To"] = to_email

            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"Successfully sent email to '{to_email}' with subject: '{subject}'")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to '{to_email}': {e}", exc_info=True)
            return False

    def send_admin_new_user_notification(self, user_data: Dict[str, Any]) -> None:
        """
        Dispatches new account registration alert to the administrator (runs in a background thread).
        Also persists notification into Firestore 'admin_notifications' collection.
        """
        def _worker():
            user_name = user_data.get("display_name") or user_data.get("email", "New User")
            user_email = user_data.get("email", "")
            user_id = user_data.get("id", "")
            created_at = user_data.get("created_at", datetime.now(timezone.utc).isoformat())

            # 1. Persist notification in Firestore for Admin Portal display
            try:
                notif_ref = self.db.collection("admin_notifications").document(f"notif_{user_id}")
                notif_ref.set({
                    "id": f"notif_{user_id}",
                    "type": "new_user_registration",
                    "user_id": user_id,
                    "user_email": user_email,
                    "user_name": user_name,
                    "created_at": created_at,
                    "status": "unread"
                })
                logger.info(f"Recorded admin notification for new user '{user_email}' in Firestore.")
            except Exception as firestore_err:
                logger.warning(f"Could not record admin notification in Firestore: {firestore_err}")

            # 2. Build Executive HTML Notification Email
            admin_email = settings.ADMIN_EMAIL
            app_url = settings.APP_URL
            subject = f"[ITC Insight] Action Required: New Account Request from {user_name} ({user_email})"

            html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); }}
    .header {{ background: #0A192F; padding: 28px 32px; color: #FFFFFF; text-align: left; }}
    .logo-badge {{ display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; background: rgba(59, 130, 246, 0.2); color: #60A5FA; padding: 4px 10px; border-radius: 9999px; margin-bottom: 8px; }}
    .title {{ font-size: 20px; font-weight: 700; margin: 0; color: #FFFFFF; letter-spacing: -0.5px; }}
    .subtitle {{ font-size: 13px; color: #94A3B8; margin-top: 4px; }}
    .body {{ padding: 32px; }}
    .alert-banner {{ background: #FEF3C7; border: 1px solid #FDE68A; border-radius: 8px; padding: 14px 18px; color: #92400E; font-size: 14px; font-weight: 500; margin-bottom: 24px; display: flex; align-items: center; }}
    .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 28px; }}
    .details-table td {{ padding: 10px 0; border-bottom: 1px solid #F1F5F9; font-size: 14px; }}
    .details-label {{ color: #64748B; font-weight: 500; width: 140px; }}
    .details-val {{ color: #0F172A; font-weight: 600; }}
    .action-row {{ text-align: center; margin: 32px 0 16px; }}
    .btn {{ display: inline-block; background: #0A192F; color: #FFFFFF !important; text-decoration: none; font-size: 14px; font-weight: 600; padding: 14px 28px; border-radius: 8px; box-shadow: 0 2px 6px rgba(10, 25, 47, 0.15); }}
    .footer {{ background: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 20px 32px; font-size: 12px; color: #64748B; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-badge">ITC Limited &bull; Executive Portal</div>
      <h1 class="title">New Account Registration Request</h1>
      <div class="subtitle">Administrator Action Required</div>
    </div>
    <div class="body">
      <div class="alert-banner">
        ⚠️ A new corporate analyst / executive has requested access to the ITC Insight Intelligence platform.
      </div>
      <p style="font-size: 14px; line-height: 1.6; color: #334155; margin-bottom: 20px;">
        The following user registered an account and is awaiting your authorization before their credentials are activated:
      </p>
      <table class="details-table">
        <tr>
          <td class="details-label">Full Name</td>
          <td class="details-val">{user_name}</td>
        </tr>
        <tr>
          <td class="details-label">Email Address</td>
          <td class="details-val"><a href="mailto:{user_email}" style="color: #2563EB;">{user_email}</a></td>
        </tr>
        <tr>
          <td class="details-label">User ID</td>
          <td class="details-val" style="font-family: monospace; font-size: 12px;">{user_id}</td>
        </tr>
        <tr>
          <td class="details-label">Requested At</td>
          <td class="details-val">{created_at}</td>
        </tr>
        <tr>
          <td class="details-label">Current Status</td>
          <td class="details-val"><span style="background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 4px; font-size: 12px;">Pending Approval</span></td>
        </tr>
      </table>
      <div class="action-row">
        <a href="{app_url}" class="btn" target="_blank">
          Open Admin Portal to Approve &rarr;
        </a>
      </div>
      <p style="font-size: 12px; color: #94A3B8; text-align: center; margin-top: 16px;">
        Sign in to your administrator account ({admin_email}) to authorize or reject this request.
      </p>
    </div>
    <div class="footer">
      ITC Insight Enterprise Intelligence &bull; Google Cloud Firestore Protected &bull; Confidential
    </div>
  </div>
</body>
</html>"""

            text_body = f"""ITC INSIGHT - New Account Registration Request

A new user has requested access:
- Name: {user_name}
- Email: {user_email}
- User ID: {user_id}
- Requested At: {created_at}
- Status: Pending Approval

Please log in to the Administrator Portal at {app_url} to approve or decline this request.
"""
            self._send_smtp_email(admin_email, subject, html_body, text_body)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def send_user_approved_notification(self, user_data: Dict[str, Any]) -> None:
        """Sends an approval confirmation email to the user when admin approves their account."""
        def _worker():
            user_name = user_data.get("display_name") or user_data.get("email", "Executive")
            user_email = user_data.get("email", "")
            app_url = settings.APP_URL
            subject = "[ITC Insight] Your Account Request Has Been Approved"

            html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #0F172A; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; }}
    .header {{ background: #0A192F; padding: 28px 32px; color: #FFFFFF; }}
    .title {{ font-size: 20px; font-weight: 700; margin: 0; color: #FFFFFF; }}
    .body {{ padding: 32px; font-size: 14px; line-height: 1.6; color: #334155; }}
    .success-box {{ background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 14px 18px; color: #065F46; font-weight: 600; margin-bottom: 20px; }}
    .btn {{ display: inline-block; background: #0A192F; color: #FFFFFF !important; text-decoration: none; font-size: 14px; font-weight: 600; padding: 12px 24px; border-radius: 8px; margin: 20px 0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #60A5FA;">ITC Limited &bull; Intelligence Platform</div>
      <h1 class="title">Access Approved</h1>
    </div>
    <div class="body">
      <div class="success-box">
        ✅ Your account request has been approved by the administrator.
      </div>
      <p>Hello <strong>{user_name}</strong>,</p>
      <p>Your registration for the <strong>ITC Insight Enterprise Intelligence Platform</strong> has been authorized. You can now log in using your registered credentials to access official ITC FMCG strategy, financial intelligence, and governance records.</p>
      <div style="text-align: center;">
        <a href="{app_url}" class="btn" target="_blank">Sign In to ITC Insight &rarr;</a>
      </div>
      <p style="font-size: 12px; color: #64748B;">If you did not request this account, please ignore this email.</p>
    </div>
  </div>
</body>
</html>"""

            text_body = f"""Hello {user_name},

Your account registration for ITC Insight has been approved by the administrator.
You can now sign in at {app_url} with your registered credentials.
"""
            self._send_smtp_email(user_email, subject, html_body, text_body)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

email_service = EmailService()

