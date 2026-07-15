"""IntelliDesk AI — Repositories package."""

from .department_repository import AuditLogRepository, DepartmentRepository, SettingRepository
from .document_repository import DocumentRepository
from .incident_repository import IncidentRepository, NotificationRepository, ProblemRepository
from .knowledge_repository import (
    ArticleCategoryRepository,
    ArticleRepository,
    ArticleTagRepository,
)
from .ticket_repository import AttachmentRepository, CommentRepository, TicketRepository
from .user_repository import RoleRepository, UserRepository, UserTokenRepository

__all__ = [
    "UserRepository",
    "RoleRepository",
    "UserTokenRepository",
    "DepartmentRepository",
    "AuditLogRepository",
    "SettingRepository",
    "TicketRepository",
    "CommentRepository",
    "AttachmentRepository",
    "IncidentRepository",
    "ProblemRepository",
    "NotificationRepository",
    "ArticleRepository",
    "ArticleCategoryRepository",
    "ArticleTagRepository",
    "DocumentRepository",
]
