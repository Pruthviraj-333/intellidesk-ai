"""
IntelliDesk AI — AI Conversation Models
Stores AI assistant sessions, messages, and ticket classification results.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.base import TimestampMixin, SoftDeleteMixin


class AISession(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    AI Conversation Session — groups messages by user context.
    Each session is scoped to a user and optionally a ticket.
    """

    __tablename__ = "ai_sessions"

    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=True)
    title = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Metrics
    message_count = db.Column(db.Integer, default=0, nullable=False)
    total_tokens_used = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="ai_sessions")
    ticket = db.relationship("Ticket", foreign_keys=[ticket_id], backref="ai_sessions")
    messages = db.relationship(
        "AIMessage", back_populates="session",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<AISession {self.session_uuid} user={self.user_id}>"


class AIMessage(db.Model):
    """
    AI Message — individual turn in a conversation.
    Roles: 'user' | 'assistant' | 'system'
    """

    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role = db.Column(db.String(20), nullable=False)  # user | assistant | system
    content = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, default=0, nullable=False)

    # RAG metadata — sources used to generate this response
    rag_sources = db.Column(db.JSON, default=list, nullable=False)
    model_used = db.Column(db.String(100), nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)  # Response time tracking

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    session = db.relationship("AISession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<AIMessage [{self.role}] session={self.session_id}>"


class AIClassification(db.Model):
    """
    AI Classification Result — stores LLM-based ticket triage output.
    Linked to a ticket to track AI prediction accuracy over time.
    """

    __tablename__ = "ai_classifications"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Predictions
    predicted_category = db.Column(db.String(50), nullable=True)
    predicted_priority = db.Column(db.String(20), nullable=True)
    predicted_department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    confidence_score = db.Column(db.Float, default=0.0, nullable=False)
    reasoning = db.Column(db.Text, nullable=True)

    # Human feedback for model monitoring
    was_accepted = db.Column(db.Boolean, nullable=True)   # None = not reviewed yet
    feedback_at = db.Column(db.DateTime(timezone=True), nullable=True)
    feedback_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Model metadata
    model_used = db.Column(db.String(100), nullable=True)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    latency_ms = db.Column(db.Integer, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    ticket = db.relationship("Ticket", foreign_keys=[ticket_id], backref="classifications")
    predicted_department = db.relationship("Department", foreign_keys=[predicted_department_id])
    feedback_user = db.relationship("User", foreign_keys=[feedback_by])

    def __repr__(self) -> str:
        return f"<AIClassification ticket={self.ticket_id} [{self.predicted_priority}/{self.predicted_category}]>"
