"""
IntelliDesk AI — Department, Setting, and AuditLog Models
Organizational structure and system-level entities.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin


class Department(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Department model — represents organizational teams.
    Each department can have a manager and custom SLA config.
    """

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sla_config = db.Column(db.JSON, default=dict, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    manager = db.relationship("User", foreign_keys=[manager_id], backref="managed_departments")
    members = db.relationship(
        "User",
        back_populates="department",
        foreign_keys="User.department_id",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"

    @property
    def member_count(self) -> int:
        return self.members.filter_by(deleted_at=None).count()


class Setting(db.Model):
    """
    Setting model — key-value store for system-wide configuration.
    All values stored as text; type casting handled in SettingsService.
    """

    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default="string", nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Setting {self.key}={self.value}>"

    @property
    def typed_value(self):
        """Return value cast to its declared type."""
        if self.value is None:
            return None
        if self.value_type == "int":
            return int(self.value)
        if self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        if self.value_type == "json":
            import json

            return json.loads(self.value)
        return self.value  # string (default)


class AuditLog(db.Model):
    """
    AuditLog model — immutable record of all significant system events.
    Never updated or deleted — append-only for compliance.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # Supports IPv6
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by user={self.user_id}>"
