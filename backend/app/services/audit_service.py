"""
IntelliDesk AI — Audit Service
Thin service wrapper over AuditLogRepository for clean imports in other services.
"""

from typing import Optional
from flask_jwt_extended import get_jwt_identity

from app.repositories.department_repository import AuditLogRepository
from app.utils.constants import AuditAction


class AuditService:
    """Service for creating audit log entries from any service layer."""

    @staticmethod
    def log(
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ):
        """
        Create an audit log entry.
        Automatically resolves user_id from JWT context if not provided.
        """
        if user_id is None:
            try:
                user_id = int(get_jwt_identity())
            except Exception:
                pass  # No JWT context (e.g., system tasks)

        return AuditLogRepository.create(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )

    @staticmethod
    def log_auth_event(action: str, user_id: int, extra: Optional[dict] = None):
        """Convenience for logging auth-specific events."""
        return AuditService.log(
            action=action,
            resource_type="user",
            resource_id=user_id,
            user_id=user_id,
            new_values=extra,
        )
