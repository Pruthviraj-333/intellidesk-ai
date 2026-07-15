"""
IntelliDesk AI — Ticket, Comment & Attachment Models
Core ITSM entities with SLA tracking and AI metadata.
"""

import uuid
from datetime import datetime, timezone

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.utils.constants import TicketPriority, TicketStatus


class Ticket(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Ticket model — central entity of the ITSM platform.
    Tracks full lifecycle from creation to closure with SLA compliance.
    """

    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # Status & Priority
    status = db.Column(db.String(30), nullable=False, default=TicketStatus.NEW.value, index=True)
    priority = db.Column(db.String(20), nullable=True, index=True)
    category = db.Column(db.String(50), nullable=True, index=True)

    # Ownership
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True
    )
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), nullable=True)

    # SLA tracking
    sla_response_deadline = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    sla_resolution_deadline = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    first_responded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    sla_response_breached = db.Column(db.Boolean, default=False, nullable=False)
    sla_resolution_breached = db.Column(db.Boolean, default=False, nullable=False)
    resolution_notes = db.Column(db.Text, nullable=True)

    # AI metadata
    ai_confidence = db.Column(db.Float, default=0.0, nullable=False)
    ai_category_suggestion = db.Column(db.String(50), nullable=True)
    ai_priority_suggestion = db.Column(db.String(20), nullable=True)
    ai_department_suggestion = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    ai_metadata = db.Column(db.JSON, default=dict, nullable=False)

    # Denormalized counters (avoid COUNT queries on hot paths)
    comment_count = db.Column(db.Integer, default=0, nullable=False)
    reopen_count = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    requester = db.relationship("User", foreign_keys=[requester_id], backref="requested_tickets")
    assignee = db.relationship("User", foreign_keys=[assignee_id], backref="assigned_tickets")
    department = db.relationship("Department", foreign_keys=[department_id], backref="tickets")
    comments = db.relationship(
        "Comment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    attachments = db.relationship(
        "Attachment", back_populates="ticket", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_number} [{self.status}]>"

    @property
    def is_overdue(self) -> bool:
        """True if resolution SLA is breached or past deadline."""
        if self.sla_resolution_deadline:
            return datetime.now(timezone.utc) > self.sla_resolution_deadline
        return False

    @property
    def is_open(self) -> bool:
        return self.status not in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value)

    def increment_comment_count(self) -> None:
        self.comment_count += 1
        db.session.commit()


class Comment(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Comment model — public replies or internal notes on a ticket.
    is_internal=True means only agents/managers can see it.
    """

    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    ticket = db.relationship("Ticket", back_populates="comments")
    author = db.relationship("User", foreign_keys=[author_id], backref="comments")
    attachments = db.relationship("Attachment", back_populates="comment")

    def __repr__(self) -> str:
        return f"<Comment {self.id} on Ticket {self.ticket_id}>"


class Attachment(db.Model):
    """
    Attachment model — files uploaded to tickets or comments.
    Stored on Cloudinary; only URL and metadata stored in DB.
    """

    __tablename__ = "attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=True
    )
    comment_id = db.Column(
        db.Integer, db.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # bytes
    file_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    ticket = db.relationship("Ticket", back_populates="attachments")
    comment = db.relationship("Comment", back_populates="attachments")
    uploader = db.relationship("User", foreign_keys=[uploader_id], backref="attachments")

    def __repr__(self) -> str:
        return f"<Attachment {self.file_name}>"
