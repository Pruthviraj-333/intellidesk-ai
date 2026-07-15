"""IntelliDesk AI — Utils package."""

from .constants import AuditAction, TicketPriority, TicketStatus, UserRole
from .decorators import jwt_required, role_required, validate_body, validate_query
from .exceptions import (
    AIServiceError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConflictError,
    IntelliDeskError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from .helpers import generate_incident_number, generate_problem_number, generate_ticket_number
from .response import (
    created_response,
    error_response,
    no_content_response,
    paginated_response,
    success_response,
)

__all__ = [
    "success_response",
    "created_response",
    "paginated_response",
    "no_content_response",
    "error_response",
    "IntelliDeskError",
    "ValidationError",
    "NotFoundError",
    "AuthorizationError",
    "AuthenticationError",
    "ConflictError",
    "BusinessLogicError",
    "AIServiceError",
    "StorageError",
    "UserRole",
    "TicketStatus",
    "TicketPriority",
    "AuditAction",
    "jwt_required",
    "role_required",
    "validate_body",
    "validate_query",
    "generate_ticket_number",
    "generate_incident_number",
    "generate_problem_number",
]
