"""
IntelliDesk AI — Email Service
Handles all outgoing emails via Gmail SMTP using Flask-Mail.
"""

from flask import current_app, render_template_string
from flask_mail import Message

from app.extensions import mail
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Email Templates ──────────────────────────────────────────────────────────

VERIFY_EMAIL_TEMPLATE = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background: #1e40af; padding: 24px; text-align: center;">
    <h1 style="color: white; margin: 0;">IntelliDesk AI</h1>
  </div>
  <div style="padding: 32px; background: #f8fafc;">
    <h2 style="color: #1e293b;">Verify Your Email Address</h2>
    <p style="color: #475569;">Hi {{ name }},</p>
    <p style="color: #475569;">
      Thank you for registering with IntelliDesk AI. Please click the button
      below to verify your email address and activate your account.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{{ verify_url }}"
         style="background: #1e40af; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; font-weight: bold;">
        Verify Email Address
      </a>
    </div>
    <p style="color: #94a3b8; font-size: 14px;">
      This link expires in 24 hours. If you did not register, please ignore this email.
    </p>
    <p style="color: #94a3b8; font-size: 12px;">
      Or copy this link: <a href="{{ verify_url }}">{{ verify_url }}</a>
    </p>
  </div>
</div>
"""

PASSWORD_RESET_TEMPLATE = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
  <div style="background: #1e40af; padding: 24px; text-align: center;">
    <h1 style="color: white; margin: 0;">IntelliDesk AI</h1>
  </div>
  <div style="padding: 32px; background: #f8fafc;">
    <h2 style="color: #1e293b;">Reset Your Password</h2>
    <p style="color: #475569;">Hi {{ name }},</p>
    <p style="color: #475569;">
      We received a request to reset your password. Click the button below
      to create a new password.
    </p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{{ reset_url }}"
         style="background: #dc2626; color: white; padding: 14px 28px;
                text-decoration: none; border-radius: 6px; font-weight: bold;">
        Reset Password
      </a>
    </div>
    <p style="color: #94a3b8; font-size: 14px;">
      This link expires in 1 hour. If you did not request a password reset,
      please ignore this email.
    </p>
  </div>
</div>
"""


class EmailService:
    """Service for sending transactional emails via Gmail SMTP."""

    @staticmethod
    def _send(to: str, subject: str, html_body: str) -> bool:
        """
        Internal email sender. Returns True on success, False on failure.
        Email failures are logged but never raise to caller.
        """
        try:
            msg = Message(
                subject=subject,
                recipients=[to],
                html=html_body,
                sender=(
                    current_app.config.get("MAIL_FROM_NAME", "IntelliDesk AI"),
                    current_app.config.get("MAIL_USERNAME", ""),
                ),
            )
            mail.send(msg)
            logger.info(f"Email sent to {to}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    @staticmethod
    def send_verification_email(user_email: str, user_name: str, token: str) -> bool:
        """Send email verification link to a newly registered user."""
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
        verify_url = f"{frontend_url}/verify-email?token={token}"

        html = render_template_string(VERIFY_EMAIL_TEMPLATE, name=user_name, verify_url=verify_url)
        return EmailService._send(
            to=user_email,
            subject="Verify your IntelliDesk AI account",
            html_body=html,
        )

    @staticmethod
    def send_password_reset_email(user_email: str, user_name: str, token: str) -> bool:
        """Send password reset link."""
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        html = render_template_string(PASSWORD_RESET_TEMPLATE, name=user_name, reset_url=reset_url)
        return EmailService._send(
            to=user_email,
            subject="Reset your IntelliDesk AI password",
            html_body=html,
        )
