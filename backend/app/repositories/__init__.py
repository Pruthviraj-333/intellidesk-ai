"""IntelliDesk AI — Repositories package."""

from .user_repository import UserRepository, RoleRepository, UserTokenRepository
from .department_repository import DepartmentRepository, AuditLogRepository, SettingRepository
from .ticket_repository import TicketRepository, CommentRepository, AttachmentRepository
from .incident_repository import IncidentRepository, ProblemRepository, NotificationRepository
from .knowledge_repository import (
    ArticleRepository, ArticleCategoryRepository,
    ArticleTagRepository,
)
from .document_repository import DocumentRepository

__all__ = [
    "UserRepository", "RoleRepository", "UserTokenRepository",
    "DepartmentRepository", "AuditLogRepository", "SettingRepository",
    "TicketRepository", "CommentRepository", "AttachmentRepository",
    "IncidentRepository", "ProblemRepository", "NotificationRepository",
    "ArticleRepository", "ArticleCategoryRepository",
    "ArticleTagRepository",
    "DocumentRepository",
]
