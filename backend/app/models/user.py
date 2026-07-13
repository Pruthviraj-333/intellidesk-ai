"""
IntelliDesk AI — User, Role, and Token Models
Core authentication and authorization entities.
"""

import uuid
from datetime import datetime, timezone

import bcrypt

from app.extensions import db
from app.models.base import TimestampMixin, SoftDeleteMixin
from app.utils.constants import UserRole, UserStatus, TokenType


class Role(db.Model, TimestampMixin):
    """
    Role model — defines the 5 permission tiers.
    Roles are seeded on first deployment and rarely modified.
    """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    permissions = db.Column(db.JSON, default=dict, nullable=False)

    # Relationships
    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"

    @classmethod
    def get_by_name(cls, name: str) -> "Role | None":
        """Fetch a role by its name string."""
        return cls.query.filter_by(name=name).first()


class User(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    User model — represents all platform users regardless of role.
    Passwords are stored as bcrypt hashes. Emails are unique per platform.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    # Foreign keys
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)

    # Account state
    status = db.Column(
        db.String(30),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION.value,
        index=True,
    )
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)

    # Preferences
    timezone = db.Column(db.String(50), default="UTC", nullable=False)
    notification_prefs = db.Column(db.JSON, default={"email": True, "in_app": True}, nullable=False)

    # Relationships
    role = db.relationship("Role", back_populates="users")
    department = db.relationship("Department", back_populates="members", foreign_keys=[department_id])
    tokens = db.relationship("UserToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    # ─── Password Management ───────────────────────────────────────────────────
    def set_password(self, plain_password: str) -> None:
        """Hash and store password using bcrypt with cost factor 12."""
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(
            plain_password.encode("utf-8"), salt
        ).decode("utf-8")

    def check_password(self, plain_password: str) -> bool:
        """Verify a plain password against the stored hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            self.password_hash.encode("utf-8"),
        )

    # ─── Account State Helpers ─────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_locked(self) -> bool:
        if self.status == UserStatus.LOCKED.value and self.locked_until:
            return datetime.now(timezone.utc) < self.locked_until
        return False

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else None

    def increment_failed_login(self) -> None:
        """Increment failed login counter. Lock account after 5 failures."""
        from datetime import timedelta

        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.status = UserStatus.LOCKED.value
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.session.commit()

    def reset_failed_login(self) -> None:
        """Reset failed login counter after successful authentication."""
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

    def verify_email(self) -> None:
        """Mark email as verified and activate account."""
        self.email_verified_at = datetime.now(timezone.utc)
        self.status = UserStatus.ACTIVE.value
        db.session.commit()


class UserToken(db.Model):
    """
    UserToken model — stores email verification and password reset tokens.
    Tokens are hashed before storage. One-time use.
    """

    __tablename__ = "user_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_type = db.Column(db.String(30), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", back_populates="tokens")

    def __repr__(self) -> str:
        return f"<UserToken {self.token_type} user={self.user_id}>"

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_used

    def mark_used(self) -> None:
        """Mark this token as consumed."""
        self.used_at = datetime.now(timezone.utc)
        db.session.commit()
