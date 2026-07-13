"""
IntelliDesk AI — AI DTOs (Marshmallow Schemas)
Request validation and response serialization for AI assistant endpoints.
"""

from marshmallow import Schema, fields, validate


# ─── Chat Schemas ─────────────────────────────────────────────────────────────

class ChatMessageSchema(Schema):
    """Single chat message for history responses."""
    id = fields.Int(dump_only=True)
    role = fields.Str(dump_only=True)
    content = fields.Str(dump_only=True)
    tokens_used = fields.Int(dump_only=True)
    rag_sources = fields.List(fields.Dict(), dump_only=True)
    model_used = fields.Str(dump_only=True, allow_none=True)
    latency_ms = fields.Int(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class ChatSessionSchema(Schema):
    """AI conversation session summary."""
    session_uuid = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True, allow_none=True)
    ticket_id = fields.Int(dump_only=True, allow_none=True)
    message_count = fields.Int(dump_only=True)
    total_tokens_used = fields.Int(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ChatRequestSchema(Schema):
    """Incoming chat request from user."""
    query = fields.Str(required=True, validate=validate.Length(min=3, max=2000))
    session_uuid = fields.Str(load_default=None)
    ticket_id = fields.Int(load_default=None)
    n_rag_results = fields.Int(load_default=4, validate=validate.Range(min=1, max=10))


class ChatResponseSchema(Schema):
    """AI assistant response envelope."""
    session_uuid = fields.Str(dump_only=True)
    session_title = fields.Str(dump_only=True)
    response = fields.Str(dump_only=True)
    sources = fields.List(fields.Dict(), dump_only=True)
    model = fields.Str(dump_only=True)
    tokens_used = fields.Int(dump_only=True)
    latency_ms = fields.Int(dump_only=True)


class SessionListQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=50))


# ─── Ticket Suggestion Schemas ────────────────────────────────────────────────

class TicketSuggestionRequestSchema(Schema):
    """Request for AI-powered agent response suggestion."""
    ticket_id = fields.Int(required=True)
    include_rag = fields.Bool(load_default=True)


class SummarizeThreadRequestSchema(Schema):
    """Request to summarize a ticket's comment thread."""
    ticket_id = fields.Int(required=True)


class ClassificationResponseSchema(Schema):
    """AI classification result."""
    ticket_id = fields.Int(dump_only=True)
    predicted_category = fields.Str(dump_only=True, allow_none=True)
    predicted_priority = fields.Str(dump_only=True, allow_none=True)
    confidence_score = fields.Float(dump_only=True)
    reasoning = fields.Str(dump_only=True, allow_none=True)
    model_used = fields.Str(dump_only=True, allow_none=True)
    was_accepted = fields.Bool(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class FeedbackClassificationSchema(Schema):
    """Human feedback on AI classification accuracy."""
    was_accepted = fields.Bool(required=True)


# ─── Resolution Guide Schema ──────────────────────────────────────────────────

class ResolutionGuideRequestSchema(Schema):
    """Request for step-by-step AI resolution guide."""
    issue_description = fields.Str(required=True, validate=validate.Length(min=10, max=2000))
    include_rag = fields.Bool(load_default=True)
