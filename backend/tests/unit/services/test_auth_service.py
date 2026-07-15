"""
IntelliDesk AI — Auth Service Unit Tests
Tests for AuthService business logic with mocked dependencies.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.utils.exceptions import (
    AuthenticationError,
    BusinessLogicError,
    ConflictError,
    ValidationError,
)


class TestAuthServiceRegister:
    """Unit tests for AuthService.register()"""

    def test_register_raises_conflict_if_email_exists(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch("app.services.auth_service.UserRepository.email_exists", return_value=True):
                with pytest.raises(ConflictError) as exc_info:
                    AuthService.register(
                        email="existing@test.com",
                        password="Test@12345!",
                        first_name="Test",
                        last_name="User",
                    )
                assert "already exists" in str(exc_info.value)

    def test_register_raises_validation_error_if_no_role(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch("app.services.auth_service.UserRepository.email_exists", return_value=False):
                with patch(
                    "app.services.auth_service.RoleRepository.get_employee_role", return_value=None
                ):
                    with pytest.raises(ValidationError) as exc_info:
                        AuthService.register(
                            email="new@test.com",
                            password="Test@12345!",
                            first_name="New",
                            last_name="User",
                        )
                    assert "role" in str(exc_info.value).lower()

    def test_register_creates_user_and_sends_email(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            mock_role = MagicMock(id=5)
            mock_user = MagicMock(id=99, email="new2@test.com", first_name="New")

            with (
                patch("app.services.auth_service.UserRepository.email_exists", return_value=False),
                patch(
                    "app.services.auth_service.RoleRepository.get_employee_role",
                    return_value=mock_role,
                ),
                patch("app.services.auth_service.UserRepository.create", return_value=mock_user),
                patch(
                    "app.services.auth_service.UserTokenRepository.create_token",
                    return_value="test_token",
                ),
                patch(
                    "app.services.auth_service.EmailService.send_verification_email",
                    return_value=True,
                ) as mock_email,
                patch("app.services.auth_service.AuditService.log"),
            ):

                result = AuthService.register(
                    email="new2@test.com",
                    password="Test@12345!",
                    first_name="New",
                    last_name="User",
                )
                assert result == mock_user
                mock_email.assert_called_once_with(
                    user_email="new2@test.com",
                    user_name="New",
                    token="test_token",
                )


class TestAuthServiceLogin:
    """Unit tests for AuthService.login()"""

    def test_login_raises_auth_error_for_wrong_password(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            mock_user = MagicMock()
            mock_user.check_password.return_value = False
            mock_user.is_locked = False
            mock_user.is_email_verified = True

            with patch(
                "app.services.auth_service.UserRepository.get_by_email", return_value=mock_user
            ):
                with pytest.raises(AuthenticationError):
                    AuthService.login("test@test.com", "wrongpassword")

    def test_login_raises_business_error_for_locked_account(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            mock_user = MagicMock()
            mock_user.check_password.return_value = True
            mock_user.is_locked = True

            with patch(
                "app.services.auth_service.UserRepository.get_by_email", return_value=mock_user
            ):
                with pytest.raises(BusinessLogicError) as exc_info:
                    AuthService.login("test@test.com", "Test@12345!")
                assert "locked" in str(exc_info.value).lower()

    def test_login_raises_business_error_for_unverified_email(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            mock_user = MagicMock()
            mock_user.check_password.return_value = True
            mock_user.is_locked = False
            mock_user.is_email_verified = False

            with patch(
                "app.services.auth_service.UserRepository.get_by_email", return_value=mock_user
            ):
                with pytest.raises(BusinessLogicError) as exc_info:
                    AuthService.login("test@test.com", "Test@12345!")
                assert "verify" in str(exc_info.value).lower()

    def test_login_raises_auth_error_for_nonexistent_user(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch("app.services.auth_service.UserRepository.get_by_email", return_value=None):
                with pytest.raises(AuthenticationError):
                    AuthService.login("ghost@test.com", "Test@12345!")


class TestAuthServiceVerifyEmail:
    """Unit tests for AuthService.verify_email()"""

    def test_verify_email_raises_on_invalid_token(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch(
                "app.services.auth_service.UserTokenRepository.verify_token", return_value=None
            ):
                with pytest.raises(ValidationError) as exc_info:
                    AuthService.verify_email("bad-token")
                assert "Invalid" in str(exc_info.value)

    def test_verify_email_raises_on_already_verified(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            mock_token = MagicMock(user_id=1)
            mock_user = MagicMock()
            mock_user.is_email_verified = True

            with (
                patch(
                    "app.services.auth_service.UserTokenRepository.verify_token",
                    return_value=mock_token,
                ),
                patch("app.services.auth_service.UserRepository.get_by_id", return_value=mock_user),
            ):
                with pytest.raises(BusinessLogicError) as exc_info:
                    AuthService.verify_email("valid-token")
                assert "already been verified" in str(exc_info.value)


class TestAuthServicePasswordReset:
    """Unit tests for AuthService.reset_password()"""

    def test_reset_password_raises_on_invalid_token(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch(
                "app.services.auth_service.UserTokenRepository.verify_token", return_value=None
            ):
                with pytest.raises(ValidationError):
                    AuthService.reset_password("bad-token", "NewPass@123!")

    def test_forgot_password_is_silent_for_nonexistent_email(self, app):
        with app.app_context():
            from app.services.auth_service import AuthService

            with patch(
                "app.services.auth_service.UserRepository.get_by_email", return_value=None
            ) as mock_get:
                # Should not raise — just silently return
                result = AuthService.request_password_reset("ghost@test.com")
                assert result is None
