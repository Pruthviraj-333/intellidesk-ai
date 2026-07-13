"""IntelliDesk AI — Models Package (updated for M3)."""

from app.models.base import TimestampMixin, SoftDeleteMixin
from app.models.user import User, Role, UserToken
from app.models.department import Department, Setting, AuditLog
from app.models.ticket import Ticket, Comment, Attachment
from app.models.incident import (
    Incident, IncidentTimeline, Problem, Project,
    Notification, incident_tickets, problem_incidents, project_members,
)
from app.models.knowledge import (
    KnowledgeArticle, ArticleCategory, ArticleTag, ArticleVote,
    article_tags, article_categories,
)
from app.models.document import Document, DocumentChunk
from app.models.ai import AISession, AIMessage, AIClassification
from app.models.analytics import DailyMetricSnapshot, AgentDailyMetric

__all__ = [
    "TimestampMixin", "SoftDeleteMixin",
    "User", "Role", "UserToken",
    "Department", "Setting", "AuditLog",
    "Ticket", "Comment", "Attachment",
    "Incident", "IncidentTimeline", "Problem", "Project",
    "Notification",
    "incident_tickets", "problem_incidents", "project_members",
    "KnowledgeArticle", "ArticleCategory", "ArticleTag", "ArticleVote",
    "article_tags", "article_categories",
    "Document", "DocumentChunk",
    "AISession", "AIMessage", "AIClassification",
    "DailyMetricSnapshot", "AgentDailyMetric",
]
