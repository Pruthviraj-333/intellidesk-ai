"""
IntelliDesk AI — Incident, Problem & Project Models
ITIL-aligned incident and problem management entities.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.base import SoftDeleteMixin, TimestampMixin
from app.utils.constants import IncidentSeverity, IncidentStatus

# ─── Association Table: incidents ↔ tickets ────────────────────────────────────
incident_tickets = db.Table(
    "incident_tickets",
    db.Column("incident_id", db.Integer, db.ForeignKey("incidents.id"), primary_key=True),
    db.Column("ticket_id", db.Integer, db.ForeignKey("tickets.id"), primary_key=True),
)

# ─── Association Table: problems ↔ incidents ──────────────────────────────────
problem_incidents = db.Table(
    "problem_incidents",
    db.Column("problem_id", db.Integer, db.ForeignKey("problems.id"), primary_key=True),
    db.Column("incident_id", db.Integer, db.ForeignKey("incidents.id"), primary_key=True),
)

# ─── Association Table: projects ↔ users (members) ────────────────────────────
project_members = db.Table(
    "project_members",
    db.Column("project_id", db.Integer, db.ForeignKey("projects.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role", db.String(20), default="member"),
)


class Project(db.Model, TimestampMixin, SoftDeleteMixin):
    """Project model — groups related tickets."""

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    creator = db.relationship("User", foreign_keys=[created_by], backref="created_projects")
    members = db.relationship("User", secondary=project_members, backref="projects")

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class Incident(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Incident model — unplanned service disruptions requiring rapid response.
    ITIL-aligned with severity levels and timeline tracking.
    """

    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, index=True)  # IncidentSeverity
    status = db.Column(db.String(30), nullable=False, default=IncidentStatus.OPEN.value, index=True)
    impact = db.Column(db.String(20), nullable=True)  # high | medium | low
    affected_services = db.Column(db.Text, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Ownership
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    problem_id = db.Column(db.Integer, db.ForeignKey("problems.id"), nullable=True)

    # Relationships
    reporter = db.relationship("User", foreign_keys=[reporter_id], backref="reported_incidents")
    assignee = db.relationship("User", foreign_keys=[assignee_id], backref="assigned_incidents")
    department = db.relationship("Department", foreign_keys=[department_id], backref="incidents")
    timeline = db.relationship(
        "IncidentTimeline",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimeline.created_at",
    )
    linked_tickets = db.relationship("Ticket", secondary=incident_tickets, backref="incidents")
    problem = db.relationship("Problem", foreign_keys=[problem_id], backref="incidents")

    def __repr__(self) -> str:
        return f"<Incident {self.incident_number} [{self.severity}]>"

    @property
    def is_resolved(self) -> bool:
        return self.status in (IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value)


class IncidentTimeline(db.Model):
    """
    Incident Timeline — chronological events for an incident.
    Append-only for audit integrity.
    """

    __tablename__ = "incident_timelines"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(
        db.Integer, db.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    # created | assigned | escalated | update | communication | resolved | postmortem
    description = db.Column(db.Text, nullable=False)
    event_metadata = db.Column("metadata", db.JSON, default=dict, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    incident = db.relationship("Incident", back_populates="timeline")
    user = db.relationship("User", foreign_keys=[user_id], backref="incident_timeline_entries")

    def __repr__(self) -> str:
        return f"<IncidentTimeline {self.event_type} on Incident {self.incident_id}>"


class Problem(db.Model, TimestampMixin, SoftDeleteMixin):
    """
    Problem model — root cause investigation for recurring incidents.
    ITIL Problem Management aligned.
    """

    __tablename__ = "problems"

    id = db.Column(db.Integer, primary_key=True)
    problem_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="open", index=True)
    root_cause = db.Column(db.Text, nullable=True)
    workaround = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = db.relationship("User", foreign_keys=[owner_id], backref="owned_problems")
    linked_incidents = db.relationship(
        "Incident", secondary=problem_incidents, backref="linked_problems"
    )

    def __repr__(self) -> str:
        return f"<Problem {self.problem_number} [{self.status}]>"


class Notification(db.Model):
    """
    Notification model — in-app notification delivery.
    Never updated; read_at tracks consumption.
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.String(50), nullable=True)  # ticket | incident | etc.
    resource_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    user = db.relationship("User", foreign_keys=[user_id], backref="notifications")

    def __repr__(self) -> str:
        return f"<Notification [{self.type}] for user={self.user_id}>"

    def mark_read(self) -> None:
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)
        db.session.commit()
