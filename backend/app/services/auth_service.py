"""
IntelliDesk AI — Authentication Service
Core business logic for registration, login, token management, and password flows.
"""

from datetime import timedelta
from typing import Optional

import redis
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token, get_jti

from app.extensions import db
from app.models.user import User
from app.repositories.user_repository import UserRepository, RoleRepository, UserTokenRepository
from app.services.email_service import EmailService
from app.services.audit_service import AuditService
from app.utils.constants import UserStatus, UserRole, TokenType, AuditAction
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    BusinessLogicError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service handling all authentication and authorization business logic."""

    @staticmethod
    def register(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        department_id: Optional[int] = None,
        phone: Optional[str] = None,
    ) -> User:
        """
        Register a new user account.

        Steps:
          1. Check email uniqueness
          2. Get default employee role
          3. Create user with hashed password
          4. Generate email verification token
          5. Send verification email (async-safe)
          6. Create audit log entry

        Returns:
            Newly created User instance.
        Raises:
            ConflictError: If email already exists.
            ValidationError: If role setup fails.
        """
        # 1. Check email uniqueness
        if UserRepository.email_exists(email):
            raise ConflictError(f"An account with email '{email}' already exists.")

        # 2. Get the default employee role
        employee_role = RoleRepository.get_employee_role()
        if not employee_role:
            raise ValidationError("System configuration error: default role not found.")

        # 3. Create user
        user = UserRepository.create(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role_id=employee_role.id,
            department_id=department_id,
            phone=phone,
        )
        logger.info(f"New user registered: {user.email} (id={user.id})")

        # 4. Generate email verification token
        token = UserTokenRepository.create_token(
            user_id=user.id,
            token_type=TokenType.EMAIL_VERIFY.value,
            expiry_hours=current_app.config.get("TOKEN_EXPIRY_HOURS", 24),
        )

        # 5. Send verification email (failure does not abort registration)
        EmailService.send_verification_email(
            user_email=user.email,
            user_name=user.first_name,
            token=token,
        )

        # 6. Audit log
        AuditService.log(
            action=AuditAction.USER_REGISTERED.value,
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
        )

        return user

    @staticmethod
    def login(email: str, password: str) -> dict:
        """
        Authenticate a user and issue JWT tokens.

        Returns:
            Dict with access_token, refresh_token, expires_in, and user data.
        Raises:
            AuthenticationError: For invalid credentials.
            BusinessLogicError: If account is locked or unverified.
        """
        user = UserRepository.get_by_email(email)

        # Always run password check to prevent timing attacks
        password_valid = user.check_password(password) if user else False

        if not user or not password_valid:
            if user:
                user.increment_failed_login()
                AuditService.log(
                    action=AuditAction.USER_LOGIN_FAILED.value,
                    resource_type="user",
                    resource_id=user.id,
                    user_id=user.id,
                )
            raise AuthenticationError("Invalid email or password.")

        # Check account state
        if user.is_locked:
            raise BusinessLogicError(
                "Your account is temporarily locked due to multiple failed login attempts. "
                "Please try again in 15 minutes."
            )

        if not user.is_email_verified:
            raise BusinessLogicError(
                "Please verify your email address before logging in. "
                "Check your inbox for the verification link."
            )

        if user.status == UserStatus.INACTIVE.value:
            raise BusinessLogicError(
                "Your account has been deactivated. Please contact an administrator."
            )

        # Reset failed login counter
        user.reset_failed_login()

        # Generate JWT tokens with role claim
        additional_claims = {"role": user.role_name}
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims,
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),
            additional_claims=additional_claims,
        )

        # Audit log
        AuditService.log(
            action=AuditAction.USER_LOGIN.value,
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": int(
                current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()
            ),
            "user": user,
        }

    @staticmethod
    def refresh_tokens(user_id: int, user_role: str) -> dict:
        """
        Issue a new access + refresh token pair.

        Args:
            user_id: From the validated refresh token identity.
            user_role: From the validated refresh token claims.

        Returns:
            Dict with new access_token and refresh_token.
        """
        additional_claims = {"role": user_role}
        access_token = create_access_token(
            identity=str(user_id), additional_claims=additional_claims
        )
        new_refresh_token = create_refresh_token(
            identity=str(user_id), additional_claims=additional_claims
        )
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "expires_in": int(
                current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()
            ),
        }

    @staticmethod
    def logout(access_jti: str, refresh_token: Optional[str] = None) -> None:
        """
        Blacklist current tokens in Redis to invalidate the session.

        Args:
            access_jti: JTI claim from the current access token.
            refresh_token: Raw refresh token to also blacklist.
        """
        redis_client = redis.from_url(
            current_app.config["REDIS_URL"], decode_responses=True
        )
        access_ttl = int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
        redis_client.setex(f"blocklist:{access_jti}", access_ttl, "revoked")

        # Also blacklist the refresh token if provided
        if refresh_token:
            try:
                from flask_jwt_extended import decode_token
                decoded = decode_token(refresh_token)
                refresh_jti = decoded["jti"]
                refresh_ttl = int(
                    current_app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds()
                )
                redis_client.setex(f"blocklist:{refresh_jti}", refresh_ttl, "revoked")
            except Exception:
                pass  # Invalid refresh token — ignore

        AuditService.log(
            action=AuditAction.USER_LOGOUT.value,
            resource_type="user",
        )

    @staticmethod
    def verify_email(token: str) -> User:
        """
        Verify a user's email address using a one-time token.

        Returns:
            The verified User instance.
        Raises:
            ValidationError: If token is invalid or expired.
        """
        user_token = UserTokenRepository.verify_token(token, TokenType.EMAIL_VERIFY.value)
        if not user_token:
            raise ValidationError(
                "Invalid or expired verification link. Please request a new one."
            )

        user = UserRepository.get_by_id(user_token.user_id)
        if not user:
            raise NotFoundError("User")

        if user.is_email_verified:
            raise BusinessLogicError("This email address has already been verified.")

        user.verify_email()
        user_token.mark_used()

        AuditService.log(
            action=AuditAction.EMAIL_VERIFIED.value,
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
        )
        return user

    @staticmethod
    def request_password_reset(email: str) -> None:
        """
        Initiate password reset flow. Always succeeds (no email enumeration).
        If email exists, sends reset link. If not, silently returns.
        """
        user = UserRepository.get_by_email(email)
        if not user or not user.is_email_verified:
            return  # Silent — do not reveal whether email exists

        token = UserTokenRepository.create_token(
            user_id=user.id,
            token_type=TokenType.PASSWORD_RESET.value,
            expiry_hours=1,
        )
        EmailService.send_password_reset_email(
            user_email=user.email,
            user_name=user.first_name,
            token=token,
        )
        AuditService.log(
            action=AuditAction.PASSWORD_RESET_REQUESTED.value,
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
        )

    @staticmethod
    def reset_password(token: str, new_password: str) -> None:
        """
        Reset user password via verified token.

        Raises:
            ValidationError: If token is invalid or expired.
        """
        user_token = UserTokenRepository.verify_token(token, TokenType.PASSWORD_RESET.value)
        if not user_token:
            raise ValidationError("Invalid or expired reset link. Please request a new one.")

        user = UserRepository.get_by_id(user_token.user_id)
        if not user:
            raise NotFoundError("User")

        user.set_password(new_password)
        user_token.mark_used()
        db.session.commit()

        # Invalidate all existing sessions via Redis
        AuditService.log(
            action=AuditAction.PASSWORD_RESET_COMPLETED.value,
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
        )

    @staticmethod
    def resend_verification(email: str) -> None:
        """
        Resend email verification link. Silent if email not found or already verified.
        """
        user = UserRepository.get_by_email(email)
        if not user or user.is_email_verified:
            return

        token = UserTokenRepository.create_token(
            user_id=user.id,
            token_type=TokenType.EMAIL_VERIFY.value,
            expiry_hours=24,
        )
        EmailService.send_verification_email(user.email, user.first_name, token)
