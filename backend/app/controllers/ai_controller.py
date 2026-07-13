"""
IntelliDesk AI — AI Assistant Controller (Blueprint)
HTTP handlers for chat, ticket classification, suggestions, and session management.
Route prefix: /api/v1/ai
"""

from datetime import datetime, timezone
from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.services.ai_service import AIChatService, AITicketClassifier
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.repositories.ticket_repository import TicketRepository
from app.repositories.knowledge_repository import ArticleRepository
from app.models.ai import AIClassification
from app.dtos.ai_dto import (
    ChatRequestSchema, ChatResponseSchema, ChatSessionSchema,
    ChatMessageSchema, SessionListQuerySchema,
    TicketSuggestionRequestSchema, SummarizeThreadRequestSchema,
    ClassificationResponseSchema, FeedbackClassificationSchema,
    ResolutionGuideRequestSchema,
)
from app.utils.decorators import (
    validate_body, validate_query, role_required,
    get_current_user_id, get_current_user_role,
)
from app.utils.response import (
    success_response, created_response, no_content_response,
    paginated_response, build_pagination_meta,
)
from app.utils.constants import UserRole
from app.utils.exceptions import NotFoundError, BusinessLogicError

ai_bp = Blueprint("ai", __name__, url_prefix="/api/v1/ai")


# ─── Chat Endpoints ───────────────────────────────────────────────────────────

@ai_bp.route("/chat", methods=["POST"])
@jwt_required()
@validate_body(ChatRequestSchema)
def chat(data: dict):
    """
    POST /api/v1/ai/chat
    Send a message to the AI assistant. Uses RAG + LLM pipeline.
    Continues an existing session or creates a new one.
    """
    user_id = get_current_user_id()
    result = AIChatService.chat(
        user_id=user_id,
        query=data["query"],
        session_uuid=data.get("session_uuid"),
        ticket_id=data.get("ticket_id"),
        n_rag_results=data.get("n_rag_results", 4),
    )
    return success_response(result)


@ai_bp.route("/sessions", methods=["GET"])
@jwt_required()
@validate_query(SessionListQuerySchema)
def list_sessions(params: dict):
    """GET /api/v1/ai/sessions — List user's conversation sessions."""
    user_id = get_current_user_id()
    pagination = AIChatService.list_user_sessions(
        user_id=user_id,
        page=params.get("page", 1),
        per_page=params.get("per_page", 20),
    )
    return paginated_response(
        data=ChatSessionSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@ai_bp.route("/sessions/<session_uuid>", methods=["GET"])
@jwt_required()
def get_session_history(session_uuid: str):
    """GET /api/v1/ai/sessions/:uuid — Get full message history for a session."""
    user_id = get_current_user_id()
    messages = AIChatService.get_session_history(session_uuid, user_id)
    return success_response(ChatMessageSchema(many=True).dump(messages))


@ai_bp.route("/sessions/<session_uuid>", methods=["DELETE"])
@jwt_required()
def delete_session(session_uuid: str):
    """DELETE /api/v1/ai/sessions/:uuid — Delete a conversation session."""
    user_id = get_current_user_id()
    AIChatService.delete_session(session_uuid, user_id)
    return no_content_response()


# ─── Ticket AI Features ───────────────────────────────────────────────────────

@ai_bp.route("/tickets/<int:ticket_id>/classify", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def classify_ticket(ticket_id: int):
    """
    POST /api/v1/ai/tickets/:id/classify
    Run AI classification on a ticket (Agent+).
    Persists results and updates ticket AI metadata fields.
    """
    ticket = TicketRepository.get_by_id(ticket_id)
    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    classification = AITicketClassifier.classify_and_persist(ticket)
    if not classification:
        raise BusinessLogicError("AI classification failed — service may be unavailable.")

    return success_response(ClassificationResponseSchema().dump(classification))


@ai_bp.route("/tickets/<int:ticket_id>/suggest-response", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def suggest_ticket_response(ticket_id: int):
    """
    POST /api/v1/ai/tickets/:id/suggest-response
    Generate a suggested agent reply using RAG + LLM (Agent+).
    """
    ticket = TicketRepository.get_by_id(ticket_id)
    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    context = RAGService.build_context_for_query(
        query=f"{ticket.title} {ticket.description}",
        n_results=4,
    )

    suggestion = LLMService.generate_ticket_response_suggestion(
        ticket_title=ticket.title,
        ticket_description=ticket.description,
        context=context,
    )
    return success_response({
        "ticket_number": ticket.ticket_number,
        "suggestion": suggestion,
        "rag_context_used": bool(context),
    })


@ai_bp.route("/tickets/<int:ticket_id>/summarize", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def summarize_ticket(ticket_id: int):
    """
    POST /api/v1/ai/tickets/:id/summarize
    Summarize the comment thread for quick agent context (Agent+).
    """
    ticket = TicketRepository.get_by_id(ticket_id)
    if not ticket:
        raise NotFoundError("Ticket", ticket_id)

    if not ticket.comments:
        return success_response({
            "ticket_number": ticket.ticket_number,
            "summary": "No comments available to summarize.",
        })

    comments_data = [
        {
            "author": f"{c.author.first_name} {c.author.last_name}",
            "role": c.author.role.name if c.author.role else "Unknown",
            "body": c.body,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }
        for c in ticket.comments
        if not c.deleted_at
    ]

    summary = LLMService.summarize_ticket_thread(
        ticket_title=ticket.title,
        comments=comments_data,
    )
    return success_response({
        "ticket_number": ticket.ticket_number,
        "summary": summary,
        "comment_count": len(comments_data),
    })


@ai_bp.route("/tickets/<int:ticket_id>/classification", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_ticket_classification(ticket_id: int):
    """GET /api/v1/ai/tickets/:id/classification — Get latest AI classification."""
    classification = (
        AIClassification.query
        .filter_by(ticket_id=ticket_id)
        .order_by(AIClassification.created_at.desc())
        .first()
    )
    if not classification:
        raise NotFoundError("AIClassification", ticket_id)
    return success_response(ClassificationResponseSchema().dump(classification))


@ai_bp.route("/tickets/<int:ticket_id>/classification/feedback", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(FeedbackClassificationSchema)
def feedback_classification(data: dict, ticket_id: int):
    """
    POST /api/v1/ai/tickets/:id/classification/feedback
    Submit human feedback on AI classification accuracy.
    Used to track model quality over time.
    """
    user_id = get_current_user_id()
    classification = (
        AIClassification.query
        .filter_by(ticket_id=ticket_id)
        .order_by(AIClassification.created_at.desc())
        .first()
    )
    if not classification:
        raise NotFoundError("AIClassification", ticket_id)

    from app.extensions import db
    classification.was_accepted = data["was_accepted"]
    classification.feedback_by = user_id
    classification.feedback_at = datetime.now(timezone.utc)
    db.session.commit()

    return success_response({
        "message": "Feedback recorded. Thank you for improving IntelliDesk AI.",
        "was_accepted": classification.was_accepted,
    })


# ─── General AI Features ──────────────────────────────────────────────────────

@ai_bp.route("/resolution-guide", methods=["POST"])
@jwt_required()
@validate_body(ResolutionGuideRequestSchema)
def get_resolution_guide(data: dict):
    """
    POST /api/v1/ai/resolution-guide
    Get step-by-step AI troubleshooting guide for any issue.
    Optionally augmented with RAG context from the knowledge base.
    """
    issue = data["issue_description"]
    context = ""

    if data.get("include_rag", True):
        context = RAGService.build_context_for_query(query=issue, n_results=4)

    guide = LLMService.get_resolution_steps(
        issue_description=issue,
        context=context,
    )
    return success_response({
        "issue_description": issue,
        "resolution_guide": guide,
        "rag_context_used": bool(context),
    })
