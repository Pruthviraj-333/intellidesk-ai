"""
IntelliDesk AI — User Repository
Data access layer for User, Role, and UserToken entities.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_

from app.extensions import db
from app.models.user import User, Role, UserToken
from app.utils.constants import UserStatus, UserRole, TokenType


class UserRepository:
    """Repository for User entity data access operations."""

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        return User.query.filter_by(id=user_id, deleted_at=None).first()

    @staticmethod
    def get_by_uuid(user_uuid: str) -> Optional[User]:
        return User.query.filter_by(uuid=user_uuid, deleted_at=None).first()

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return User.query.filter_by(email=email.lower().strip(), deleted_at=None).first()

    @staticmethod
    def email_exists(email: str) -> bool:
        return User.query.filter_by(email=email.lower().strip()).first() is not None

    @staticmethod
    def create(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role_id: int,
        department_id: Optional[int] = None,
        phone: Optional[str] = None,
    ) -> User:
        """Create and persist a new user with a hashed password."""
        user = User(
            email=email.lower().strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role_id=role_id,
            department_id=department_id,
            phone=phone,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(user: User, data: dict) -> User:
        """Update allowed user fields."""
        allowed_fields = {
            "first_name", "last_name", "phone", "avatar_url",
            "timezone", "notification_prefs", "role_id",
            "department_id", "status",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(user, key, value)
        db.session.commit()
        return user

    @staticmethod
    def soft_delete(user: User) -> None:
        user.soft_delete()

    @staticmethod
    def list_with_filters(
        role: Optional[str] = None,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ):
        """List users with optional filtering, search, and pagination."""
        query = User.query.filter_by(deleted_at=None)

        if role:
            query = query.join(Role).filter(Role.name == role)
        if department_id:
            query = query.filter(User.department_id == department_id)
        if status:
            query = query.filter(User.status == status)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                )
            )

        # Sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        return query.paginate(page=page, per_page=per_page, error_out=False)


class RoleRepository:
    """Repository for Role entity data access operations."""

    @staticmethod
    def get_by_id(role_id: int) -> Optional[Role]:
        return Role.query.get(role_id)

    @staticmethod
    def get_by_name(name: str) -> Optional[Role]:
        return Role.query.filter_by(name=name).first()

    @staticmethod
    def get_all() -> list[Role]:
        return Role.query.all()

    @staticmethod
    def get_employee_role() -> Optional[Role]:
        """Return the default 'employee' role for new registrations."""
        return Role.query.filter_by(name=UserRole.EMPLOYEE.value).first()


class UserTokenRepository:
    """Repository for UserToken — email verification and password reset tokens."""

    @staticmethod
    def create_token(user_id: int, token_type: str, expiry_hours: int = 24) -> str:
        """
        Generate, hash, and store a one-time token.

        Returns:
            The raw (unhashed) token string to send to the user.
        """
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Invalidate any existing tokens of the same type for this user
        UserToken.query.filter_by(
            user_id=user_id, token_type=token_type, used_at=None
        ).delete()

        token = UserToken(
            user_id=user_id,
            token_type=token_type,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )
        db.session.add(token)
        db.session.commit()
        return raw_token

    @staticmethod
    def verify_token(raw_token: str, token_type: str) -> Optional[UserToken]:
        """
        Verify a raw token against stored hashes.

        Returns:
            UserToken if valid and not expired/used, else None.
        """
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = UserToken.query.filter_by(
            token_hash=token_hash,
            token_type=token_type,
            used_at=None,
        ).first()

        if token and token.is_valid:
            return token
        return None
