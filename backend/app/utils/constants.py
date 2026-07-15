"""
IntelliDesk AI — Constants & Enums
Central registry for all application-level enumerations and constants.
"""

from enum import Enum


# ─── User Roles ─────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    EMPLOYEE = "employee"


# ─── User Status ─────────────────────────────────────────────────────────────────
class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"


# ─── Token Types ─────────────────────────────────────────────────────────────────
class TokenType(str, Enum):
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"
    REFRESH = "refresh"


# ─── Ticket Status ───────────────────────────────────────────────────────────────
class TicketStatus(str, Enum):
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    ESCALATED = "escalated"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ─── Ticket Priority ─────────────────────────────────────────────────────────────
class TicketPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ─── Ticket Category ─────────────────────────────────────────────────────────────
class TicketCategory(str, Enum):
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network"
    ACCESS = "Access/Permissions"
    EMAIL = "Email"
    DATABASE = "Database"
    SECURITY = "Security"
    GENERAL = "General"


# ─── Valid Ticket Status Transitions ─────────────────────────────────────────────
VALID_TICKET_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.NEW: {TicketStatus.OPEN},
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {
        TicketStatus.PENDING,
        TicketStatus.RESOLVED,
        TicketStatus.ESCALATED,
        TicketStatus.ON_HOLD,
    },
    TicketStatus.PENDING: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED},
    TicketStatus.ESCALATED: {TicketStatus.IN_PROGRESS, TicketStatus.PENDING},
    TicketStatus.ON_HOLD: {TicketStatus.IN_PROGRESS},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: {TicketStatus.IN_PROGRESS},
}


# ─── SLA Defaults (hours) ────────────────────────────────────────────────────────
SLA_DEFAULTS: dict[str, dict[str, float]] = {
    TicketPriority.CRITICAL: {"response": 0.25, "resolution": 4.0},
    TicketPriority.HIGH: {"response": 1.0, "resolution": 8.0},
    TicketPriority.MEDIUM: {"response": 4.0, "resolution": 24.0},
    TicketPriority.LOW: {"response": 8.0, "resolution": 72.0},
}


# ─── Incident Severity ───────────────────────────────────────────────────────────
class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ─── Incident Status ─────────────────────────────────────────────────────────────
class IncidentStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# ─── Article Status ──────────────────────────────────────────────────────────────
class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ─── Document Processing Status ──────────────────────────────────────────────────
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# ─── Notification Types ──────────────────────────────────────────────────────────
class NotificationType(str, Enum):
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_UPDATED = "ticket_updated"
    TICKET_COMMENT = "ticket_comment"
    TICKET_RESOLVED = "ticket_resolved"
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"
    MENTION = "mention"
    GENERAL = "general"


# ─── Audit Log Actions ───────────────────────────────────────────────────────────
class AuditAction(str, Enum):
    # Auth
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    EMAIL_VERIFIED = "email_verified"
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ROLE_CHANGED = "user_role_changed"
    # Tickets
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_DELETED = "ticket_deleted"
    COMMENT_ADDED = "comment_added"
    # Incidents
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    # Settings
    SETTINGS_UPDATED = "settings_updated"


# ─── Allowed Upload Extensions ───────────────────────────────────────────────────
ALLOWED_DOCUMENT_EXTENSIONS: set = {"pdf", "docx", "txt", "md"}
ALLOWED_IMAGE_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_ATTACHMENT_EXTENSIONS: set = ALLOWED_DOCUMENT_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS


# ─── AI Assistant ─────────────────────────────────────────────────────────────────
CHAT_HISTORY_LIMIT: int = 10  # Max messages included in LLM context window
MAX_RAG_RESULTS: int = 5  # Default number of RAG chunks per query
MIN_CLASSIFICATION_CONFIDENCE: float = 0.65  # Minimum confidence to auto-apply AI classification
