"""IntelliDesk AI — Services package."""

from .auth_service import AuthService
from .email_service import EmailService
from .audit_service import AuditService

__all__ = ["AuthService", "EmailService", "AuditService"]
