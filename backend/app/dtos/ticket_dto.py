"""
IntelliDesk AI — Ticket & Comment DTOs (Marshmallow Schemas)
Request validation and response serialization for ticket endpoints.
"""

from marshmallow import Schema, fields, validate, validates, ValidationError

from app.utils.constants import (
    TicketStatus, TicketPriority, TicketCategory,
    IncidentSeverity, IncidentStatus,
)


# ─── Nested summary schemas (reused across resources) ─────────────────────────

class UserMiniSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Method("get_full_name")
    email = fields.Email(dump_only=True)
    avatar_url = fields.Str(dump_only=True, allow_none=True)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class DeptMiniSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


# ─── Attachment Schema ─────────────────────────────────────────────────────────

class AttachmentSchema(Schema):
    id = fields.Int(dump_only=True)
    file_name = fields.Str(dump_only=True)
    file_url = fields.Str(dump_only=True)
    file_size = fields.Int(dump_only=True)
    file_type = fields.Str(dump_only=True)
    uploader = fields.Nested(UserMiniSchema, dump_only=True)
    created_at = fields.DateTime(dump_only=True)


# ─── Comment Schemas ──────────────────────────────────────────────────────────

class CommentResponseSchema(Schema):
    id = fields.Int(dump_only=True)
    ticket_id = fields.Int(dump_only=True)
    author = fields.Nested(UserMiniSchema, dump_only=True)
    body = fields.Str(dump_only=True)
    is_internal = fields.Bool(dump_only=True)
    attachments = fields.Nested(AttachmentSchema, many=True, dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreateCommentSchema(Schema):
    body = fields.Str(required=True, validate=validate.Length(min=1, max=10000))
    is_internal = fields.Bool(load_default=False)


# ─── Ticket Response Schema ────────────────────────────────────────────────────

class TicketSummarySchema(Schema):
    """Compact ticket representation for list views."""
    id = fields.Int(dump_only=True)
    ticket_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True, allow_none=True)
    category = fields.Str(dump_only=True, allow_none=True)
    requester = fields.Nested(UserMiniSchema, dump_only=True)
    assignee = fields.Nested(UserMiniSchema, dump_only=True, allow_none=True)
    department = fields.Nested(DeptMiniSchema, dump_only=True, allow_none=True)
    sla_response_deadline = fields.DateTime(dump_only=True, allow_none=True)
    sla_resolution_deadline = fields.DateTime(dump_only=True, allow_none=True)
    sla_response_breached = fields.Bool(dump_only=True)
    sla_resolution_breached = fields.Bool(dump_only=True)
    comment_count = fields.Int(dump_only=True)
    ai_confidence = fields.Float(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class TicketDetailSchema(TicketSummarySchema):
    """Full ticket representation for detail view — includes comments and attachments."""
    description = fields.Str(dump_only=True)
    resolution_notes = fields.Str(dump_only=True, allow_none=True)
    first_responded_at = fields.DateTime(dump_only=True, allow_none=True)
    resolved_at = fields.DateTime(dump_only=True, allow_none=True)
    closed_at = fields.DateTime(dump_only=True, allow_none=True)
    ai_category_suggestion = fields.Str(dump_only=True, allow_none=True)
    ai_priority_suggestion = fields.Str(dump_only=True, allow_none=True)
    ai_metadata = fields.Dict(dump_only=True)
    comments = fields.Nested(CommentResponseSchema, many=True, dump_only=True)
    attachments = fields.Nested(AttachmentSchema, many=True, dump_only=True)


# ─── Ticket Request Schemas ────────────────────────────────────────────────────

class CreateTicketSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(required=True, validate=validate.Length(min=10, max=10000))
    priority = fields.Str(
        load_default=None,
        validate=validate.OneOf([p.value for p in TicketPriority])
    )
    category = fields.Str(load_default=None, validate=validate.Length(max=50))
    department_id = fields.Int(load_default=None)
    project_id = fields.Int(load_default=None)


class UpdateTicketSchema(Schema):
    title = fields.Str(validate=validate.Length(min=5, max=200))
    description = fields.Str(validate=validate.Length(min=10, max=10000))
    status = fields.Str(validate=validate.OneOf([s.value for s in TicketStatus]))
    priority = fields.Str(validate=validate.OneOf([p.value for p in TicketPriority]))
    category = fields.Str(validate=validate.Length(max=50))
    assignee_id = fields.Int(allow_none=True)
    department_id = fields.Int(allow_none=True)
    project_id = fields.Int(allow_none=True)
    resolution_notes = fields.Str(validate=validate.Length(max=5000))


class AssignTicketSchema(Schema):
    assignee_id = fields.Int(required=True, allow_none=True)


class BulkUpdateTicketSchema(Schema):
    ticket_ids = fields.List(fields.Int(), required=True, validate=validate.Length(min=1, max=100))
    updates = fields.Dict(required=True)


class TicketListQuerySchema(Schema):
    status = fields.Str(validate=validate.OneOf([s.value for s in TicketStatus]))
    priority = fields.Str(validate=validate.OneOf([p.value for p in TicketPriority]))
    category = fields.Str()
    department_id = fields.Int()
    assignee_id = fields.Int()
    requester_id = fields.Int()
    sla_breached = fields.Bool()
    from_date = fields.Date()
    to_date = fields.Date()
    search = fields.Str(validate=validate.Length(max=200))
    sort_by = fields.Str(
        load_default="created_at",
        validate=validate.OneOf(["created_at", "updated_at", "priority", "sla_resolution_deadline"]),
    )
    order = fields.Str(load_default="desc", validate=validate.OneOf(["asc", "desc"]))
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


# ─── Incident Schemas ─────────────────────────────────────────────────────────

class IncidentTimelineSchema(Schema):
    id = fields.Int(dump_only=True)
    event_type = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    user = fields.Nested(UserMiniSchema, dump_only=True, allow_none=True)
    metadata = fields.Dict(dump_only=True, attribute="event_metadata")
    created_at = fields.DateTime(dump_only=True)


class IncidentSummarySchema(Schema):
    id = fields.Int(dump_only=True)
    incident_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    severity = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    impact = fields.Str(dump_only=True, allow_none=True)
    reporter = fields.Nested(UserMiniSchema, dump_only=True)
    assignee = fields.Nested(UserMiniSchema, dump_only=True, allow_none=True)
    department = fields.Nested(DeptMiniSchema, dump_only=True, allow_none=True)
    resolved_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class IncidentDetailSchema(IncidentSummarySchema):
    description = fields.Str(dump_only=True)
    affected_services = fields.Str(dump_only=True, allow_none=True)
    resolution_notes = fields.Str(dump_only=True, allow_none=True)
    timeline = fields.Nested(IncidentTimelineSchema, many=True, dump_only=True)
    linked_tickets = fields.Nested(TicketSummarySchema, many=True, dump_only=True)


class CreateIncidentSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(required=True, validate=validate.Length(min=10))
    severity = fields.Str(
        required=True,
        validate=validate.OneOf([s.value for s in IncidentSeverity])
    )
    impact = fields.Str(
        load_default=None,
        validate=validate.OneOf(["high", "medium", "low"])
    )
    affected_services = fields.Str(load_default=None)
    department_id = fields.Int(load_default=None)
    linked_ticket_ids = fields.List(fields.Int(), load_default=[])


class UpdateIncidentSchema(Schema):
    title = fields.Str(validate=validate.Length(min=5, max=200))
    description = fields.Str()
    severity = fields.Str(validate=validate.OneOf([s.value for s in IncidentSeverity]))
    status = fields.Str(validate=validate.OneOf([s.value for s in IncidentStatus]))
    impact = fields.Str(validate=validate.OneOf(["high", "medium", "low"]))
    affected_services = fields.Str(allow_none=True)
    assignee_id = fields.Int(allow_none=True)
    department_id = fields.Int(allow_none=True)
    problem_id = fields.Int(allow_none=True)
    resolution_notes = fields.Str(allow_none=True)


class AddTimelineEntrySchema(Schema):
    event_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            "created", "assigned", "escalated", "update",
            "communication", "resolved", "postmortem",
        ])
    )
    description = fields.Str(required=True, validate=validate.Length(min=5, max=2000))
    metadata = fields.Dict(load_default={})


# ─── Problem Schemas ──────────────────────────────────────────────────────────

class ProblemSummarySchema(Schema):
    id = fields.Int(dump_only=True)
    problem_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    root_cause = fields.Str(dump_only=True, allow_none=True)
    owner = fields.Nested(UserMiniSchema, dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class ProblemDetailSchema(ProblemSummarySchema):
    description = fields.Str(dump_only=True)
    workaround = fields.Str(dump_only=True, allow_none=True)
    resolution = fields.Str(dump_only=True, allow_none=True)
    linked_incidents = fields.Nested(IncidentSummarySchema, many=True, dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreateProblemSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(required=True, validate=validate.Length(min=10))
    linked_incident_ids = fields.List(fields.Int(), load_default=[])
    owner_id = fields.Int(load_default=None)


class UpdateProblemSchema(Schema):
    title = fields.Str(validate=validate.Length(min=5, max=200))
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf(["open", "in_progress", "resolved", "closed"]))
    root_cause = fields.Str(allow_none=True)
    workaround = fields.Str(allow_none=True)
    resolution = fields.Str(allow_none=True)
    owner_id = fields.Int(allow_none=True)


# ─── Notification Schema ───────────────────────────────────────────────────────

class NotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    type = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    body = fields.Str(dump_only=True, allow_none=True)
    resource_type = fields.Str(dump_only=True, allow_none=True)
    resource_id = fields.Int(dump_only=True, allow_none=True)
    is_read = fields.Bool(dump_only=True)
    read_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class NotificationListQuerySchema(Schema):
    is_read = fields.Bool()
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=50))
