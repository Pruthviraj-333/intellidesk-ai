"""
IntelliDesk AI — Auth Controller (Blueprint)
HTTP request handlers for all authentication endpoints.
Route prefix: /api/v1/auth
"""

from flask import Blueprint
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.services.auth_service import AuthService
from app.dtos.auth_dto import (
    RegisterSchema,
    LoginSchema,
    RefreshSchema,
    LogoutSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    VerifyEmailSchema,
    ResendVerificationSchema,
    UserResponseSchema,
)
from app.utils.decorators import validate_body
from app.utils.response import success_response, created_response
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10/hour")
@validate_body(RegisterSchema)
def register(data: dict):
    """
    POST /api/v1/auth/register
    Register a new user account. Returns user object.
    Rate limited to 10 registrations per hour per IP.
    """
    user = AuthService.register(
        email=data["email"],
        password=data["password"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        department_id=data.get("department_id"),
        phone=data.get("phone"),
    )
    return created_response(
        {
            "message": "Registration successful. Please check your email to verify your account.",
            "user": UserResponseSchema().dump(user),
        }
    )


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20/minute")
@validate_body(LoginSchema)
def login(data: dict):
    """
    POST /api/v1/auth/login
    Authenticate with email and password. Returns JWT token pair.
    """
    result = AuthService.login(email=data["email"], password=data["password"])
    return success_response(
        {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": result["token_type"],
            "expires_in": result["expires_in"],
            "user": UserResponseSchema().dump(result["user"]),
        }
    )


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    POST /api/v1/auth/refresh
    Exchange a valid refresh token for a new access + refresh token pair.
    Requires: Authorization: Bearer <refresh_token>
    """
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_role = claims.get("role", "")

    # Blacklist the current refresh token
    jti = claims.get("jti")
    from flask import current_app
    import redis
    redis_client = redis.from_url(current_app.config["REDIS_URL"], decode_responses=True)
    refresh_ttl = int(current_app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds())
    redis_client.setex(f"blocklist:{jti}", refresh_ttl, "revoked")

    tokens = AuthService.refresh_tokens(user_id=user_id, user_role=user_role)
    return success_response(tokens)


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
@validate_body(LogoutSchema)
def logout(data: dict):
    """
    POST /api/v1/auth/logout
    Revoke current access and refresh tokens via Redis blocklist.
    """
    claims = get_jwt()
    access_jti = claims.get("jti")
    AuthService.logout(
        access_jti=access_jti,
        refresh_token=data.get("refresh_token"),
    )
    return success_response({"message": "Logged out successfully."})


@auth_bp.route("/verify-email", methods=["POST"])
@validate_body(VerifyEmailSchema)
def verify_email(data: dict):
    """
    POST /api/v1/auth/verify-email
    Verify email address using one-time token from registration email.
    """
    user = AuthService.verify_email(token=data["token"])
    return success_response(
        {
            "message": "Email verified successfully. You can now log in.",
            "user": UserResponseSchema().dump(user),
        }
    )


@auth_bp.route("/resend-verification", methods=["POST"])
@limiter.limit("3/hour")
@validate_body(ResendVerificationSchema)
def resend_verification(data: dict):
    """
    POST /api/v1/auth/resend-verification
    Resend email verification link. Silent if email not found.
    """
    AuthService.resend_verification(email=data["email"])
    return success_response(
        {"message": "If that email is registered and unverified, a new link has been sent."}
    )


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5/hour")
@validate_body(ForgotPasswordSchema)
def forgot_password(data: dict):
    """
    POST /api/v1/auth/forgot-password
    Request a password reset email. Always returns success (no enumeration).
    """
    AuthService.request_password_reset(email=data["email"])
    return success_response(
        {"message": "If that email exists in our system, a reset link has been sent."}
    )


@auth_bp.route("/reset-password", methods=["POST"])
@validate_body(ResetPasswordSchema)
def reset_password(data: dict):
    """
    POST /api/v1/auth/reset-password
    Reset password using one-time token from email.
    """
    AuthService.reset_password(token=data["token"], new_password=data["password"])
    return success_response(
        {"message": "Password reset successfully. Please log in with your new password."}
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    """
    GET /api/v1/auth/me
    Return current authenticated user profile.
    """
    from app.repositories.user_repository import UserRepository

    user_id = int(get_jwt_identity())
    user = UserRepository.get_by_id(user_id)
    return success_response(UserResponseSchema().dump(user))
