"""
IntelliDesk AI — Database Models
Base mixin classes shared across all models.
"""

from datetime import datetime, timezone

from app.extensions import db


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.
    updated_at is automatically updated on every save.
    """

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete capability via deleted_at timestamp.
    Records are never physically deleted — set deleted_at to mark as deleted.
    """

    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        """Returns True if this record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark this record as deleted without physical deletion."""
        self.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
