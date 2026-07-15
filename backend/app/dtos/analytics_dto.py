"""
IntelliDesk AI — Analytics & Report DTOs
Marshmallow schemas for request validation and response serialization.
"""

from datetime import date, timedelta

from marshmallow import Schema, ValidationError, fields, validate, validates


class DateRangeSchema(Schema):
    """Common date range query parameters."""

    from_date = fields.Date(load_default=None)
    to_date = fields.Date(load_default=None)
    department_id = fields.Int(load_default=None)

    @validates("to_date")
    def validate_date_range(self, value):
        if value and value > date.today() + timedelta(days=1):
            raise ValidationError("to_date cannot be in the future.")


class TrendQuerySchema(Schema):
    """Query parameters for trend chart data."""

    days = fields.Int(load_default=30, validate=validate.Range(min=7, max=365))
    department_id = fields.Int(load_default=None)


class LeaderboardQuerySchema(Schema):
    """Query parameters for agent leaderboard."""

    days = fields.Int(load_default=30, validate=validate.Range(min=7, max=365))
    limit = fields.Int(load_default=10, validate=validate.Range(min=1, max=50))


class HeatmapQuerySchema(Schema):
    """Query parameters for ticket creation heatmap."""

    days = fields.Int(load_default=90, validate=validate.Range(min=7, max=365))


class ReportQuerySchema(Schema):
    """Query parameters for downloadable reports."""

    from_date = fields.Date(required=True)
    to_date = fields.Date(required=True)
    department_id = fields.Int(load_default=None)
    format = fields.Str(
        load_default="pdf",
        validate=validate.OneOf(["pdf", "csv", "excel"]),
    )

    @validates("to_date")
    def validate_range(self, value):
        if value > date.today() + timedelta(days=1):
            raise ValidationError("to_date cannot be in the future.")


# ─── Response Schemas ─────────────────────────────────────────────────────────


class DailyTrendPointSchema(Schema):
    date = fields.Str(dump_only=True)
    tickets_created = fields.Int(dump_only=True)
    tickets_resolved = fields.Int(dump_only=True)
    tickets_open = fields.Int(dump_only=True)
    tickets_overdue = fields.Int(dump_only=True)
    sla_compliance_rate = fields.Float(dump_only=True)
    avg_resolution_hours = fields.Float(dump_only=True, allow_none=True)
    incidents_created = fields.Int(dump_only=True)
    critical_incidents = fields.Int(dump_only=True)
    ai_sessions = fields.Int(dump_only=True)


class AgentLeaderboardItemSchema(Schema):
    agent_id = fields.Int(dump_only=True)
    agent_name = fields.Str(dump_only=True)
    avatar_url = fields.Str(dump_only=True, allow_none=True)
    tickets_resolved = fields.Int(dump_only=True)
    tickets_assigned = fields.Int(dump_only=True)
    sla_breached = fields.Int(dump_only=True)
    resolution_rate = fields.Float(dump_only=True)
    avg_resolution_hours = fields.Float(dump_only=True, allow_none=True)


class SLAComplianceItemSchema(Schema):
    total = fields.Int(dump_only=True)
    compliant = fields.Int(dump_only=True)
    breached = fields.Int(dump_only=True)
    compliance_rate = fields.Float(dump_only=True)


class HeatmapPointSchema(Schema):
    day = fields.Int(dump_only=True)  # 0=Sun, 6=Sat
    hour = fields.Int(dump_only=True)
    count = fields.Int(dump_only=True)


class TicketVolumeItemSchema(Schema):
    category = fields.Str(dump_only=True)
    count = fields.Int(dump_only=True)


class PlatformSummarySchema(Schema):
    total_tickets = fields.Int(dump_only=True)
    open_tickets = fields.Int(dump_only=True)
    total_incidents = fields.Int(dump_only=True)
    total_articles = fields.Int(dump_only=True)
    total_agents = fields.Int(dump_only=True)
    ai_sessions_total = fields.Int(dump_only=True)
    overall_sla_compliance = fields.Float(dump_only=True)
