"""IntelliDesk AI — Utils package."""

from .response import success_response, created_response, paginated_response, no_content_response, error_response
from .exceptions import (
    IntelliDeskError, ValidationError, NotFoundError,
    AuthorizationError, AuthenticationError, ConflictError,
    BusinessLogicError, AIServiceError, StorageError,
)
from .constants import UserRole, TicketStatus, TicketPriority, AuditAction
from .decorators import jwt_required, role_required, validate_body, validate_query
from .helpers import generate_ticket_number, generate_incident_number, generate_problem_number

__all__ = [
    "success_response", "created_response", "paginated_response",
    "no_content_response", "error_response",
    "IntelliDeskError", "ValidationError", "NotFoundError",
    "AuthorizationError", "AuthenticationError", "ConflictError",
    "BusinessLogicError", "AIServiceError", "StorageError",
    "UserRole", "TicketStatus", "TicketPriority", "AuditAction",
    "jwt_required", "role_required", "validate_body", "validate_query",
    "generate_ticket_number", "generate_incident_number", "generate_problem_number",
]
