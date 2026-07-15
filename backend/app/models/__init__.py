"""IntelliDesk AI — Models Package (updated for M3)."""

from app.models.ai import AIClassification, AIMessage, AISession
from app.models.analytics import AgentDailyMetric, DailyMetricSnapshot
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.models.department import AuditLog, Department, Setting
from app.models.document import Document, DocumentChunk
from app.models.incident import (
    Incident,
    IncidentTimeline,
    Notification,
    Problem,
    Project,
    incident_tickets,
    problem_incidents,
    project_members,
)
from app.models.knowledge import (
    ArticleCategory,
    ArticleTag,
    ArticleVote,
    KnowledgeArticle,
    article_categories,
    article_tags,
)
from app.models.ticket import Attachment, Comment, Ticket
from app.models.user import Role, User, UserToken

__all__ = [
    "TimestampMixin",
    "SoftDeleteMixin",
    "User",
    "Role",
    "UserToken",
    "Department",
    "Setting",
    "AuditLog",
    "Ticket",
    "Comment",
    "Attachment",
    "Incident",
    "IncidentTimeline",
    "Problem",
    "Project",
    "Notification",
    "incident_tickets",
    "problem_incidents",
    "project_members",
    "KnowledgeArticle",
    "ArticleCategory",
    "ArticleTag",
    "ArticleVote",
    "article_tags",
    "article_categories",
    "Document",
    "DocumentChunk",
    "AISession",
    "AIMessage",
    "AIClassification",
    "DailyMetricSnapshot",
    "AgentDailyMetric",
]
