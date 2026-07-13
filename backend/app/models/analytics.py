"""
IntelliDesk AI — Analytics & Metrics Models
Pre-aggregated daily snapshots for fast dashboard and reporting queries.
"""

from datetime import datetime, timezone, date

from app.extensions import db


class DailyMetricSnapshot(db.Model):
    """
    Daily pre-aggregated KPI snapshot.
    Computed by Celery Beat every night at midnight UTC.
    Eliminates expensive COUNT queries on the tickets table for historical data.
    """

    __tablename__ = "daily_metric_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True
    )  # NULL = platform-wide

    # Ticket metrics
    tickets_created = db.Column(db.Integer, default=0, nullable=False)
    tickets_resolved = db.Column(db.Integer, default=0, nullable=False)
    tickets_closed = db.Column(db.Integer, default=0, nullable=False)
    tickets_open = db.Column(db.Integer, default=0, nullable=False)  # Cumulative open
    tickets_overdue = db.Column(db.Integer, default=0, nullable=False)

    # SLA metrics
    sla_breached_count = db.Column(db.Integer, default=0, nullable=False)
    sla_met_count = db.Column(db.Integer, default=0, nullable=False)
    sla_compliance_rate = db.Column(db.Float, default=100.0, nullable=False)  # 0.0-100.0

    # Resolution time (hours)
    avg_resolution_time_hours = db.Column(db.Float, nullable=True)
    median_resolution_time_hours = db.Column(db.Float, nullable=True)

    # Incident metrics
    incidents_created = db.Column(db.Integer, default=0, nullable=False)
    incidents_resolved = db.Column(db.Integer, default=0, nullable=False)
    critical_incidents = db.Column(db.Integer, default=0, nullable=False)

    # Knowledge base metrics
    articles_published = db.Column(db.Integer, default=0, nullable=False)
    article_views = db.Column(db.Integer, default=0, nullable=False)
    ai_sessions = db.Column(db.Integer, default=0, nullable=False)
    ai_tokens_used = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("snapshot_date", "department_id", name="uq_snapshot_date_dept"),
    )

    department = db.relationship("Department", foreign_keys=[department_id])

    def __repr__(self) -> str:
        dept = f"dept={self.department_id}" if self.department_id else "platform-wide"
        return f"<DailyMetricSnapshot {self.snapshot_date} [{dept}]>"


class AgentDailyMetric(db.Model):
    """
    Per-agent daily performance metric.
    Used for agent leaderboard and performance review reports.
    """

    __tablename__ = "agent_daily_metrics"

    id = db.Column(db.Integer, primary_key=True)
    metric_date = db.Column(db.Date, nullable=False, index=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    tickets_assigned = db.Column(db.Integer, default=0, nullable=False)
    tickets_resolved = db.Column(db.Integer, default=0, nullable=False)
    tickets_sla_breached = db.Column(db.Integer, default=0, nullable=False)
    avg_resolution_time_hours = db.Column(db.Float, nullable=True)
    first_response_time_minutes = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("metric_date", "agent_id", name="uq_agent_daily_metric"),
    )

    agent = db.relationship("User", foreign_keys=[agent_id], backref="daily_metrics")

    def __repr__(self) -> str:
        return f"<AgentDailyMetric {self.metric_date} agent={self.agent_id}>"
