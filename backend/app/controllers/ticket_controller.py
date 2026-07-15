"""
IntelliDesk AI — Ticket Controller (Blueprint)
HTTP handlers for the complete ticket lifecycle.
Route prefix: /api/v1/tickets
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.dtos.ticket_dto import (
    AssignTicketSchema,
    BulkUpdateTicketSchema,
    CommentResponseSchema,
    CreateCommentSchema,
    CreateTicketSchema,
    TicketDetailSchema,
    TicketListQuerySchema,
    TicketSummarySchema,
    UpdateTicketSchema,
)
from app.repositories.ticket_repository import CommentRepository, TicketRepository
from app.services.ticket_service import TicketService
from app.utils.constants import UserRole
from app.utils.decorators import (
    get_current_user_id,
    get_current_user_role,
    role_required,
    validate_body,
    validate_query,
)
from app.utils.exceptions import NotFoundError
from app.utils.response import (
    build_pagination_meta,
    created_response,
    no_content_response,
    paginated_response,
    success_response,
)

ticket_bp = Blueprint("tickets", __name__, url_prefix="/api/v1/tickets")


@ticket_bp.route("/", methods=["POST"])
@jwt_required()
@validate_body(CreateTicketSchema)
def create_ticket(data: dict):
    """POST /api/v1/tickets — Create a new ticket (all users)."""
    user_id = get_current_user_id()
    ticket = TicketService.create_ticket(
        title=data["title"],
        description=data["description"],
        requester_id=user_id,
        priority=data.get("priority"),
        category=data.get("category"),
        department_id=data.get("department_id"),
        project_id=data.get("project_id"),
    )
    return created_response(TicketDetailSchema().dump(ticket))


@ticket_bp.route("/", methods=["GET"])
@jwt_required()
@validate_query(TicketListQuerySchema)
def list_tickets(params: dict):
    """GET /api/v1/tickets — List tickets (scoped by role)."""
    user_id = get_current_user_id()
    role = get_current_user_role()

    # Employees only see their own tickets
    if role == UserRole.EMPLOYEE.value:
        params["requester_id"] = user_id

    pagination = TicketRepository.list_with_filters(**params)
    return paginated_response(
        data=TicketSummarySchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@ticket_bp.route("/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id: int):
    """GET /api/v1/tickets/:id — Get ticket detail."""
    user_id = get_current_user_id()
    role = get_current_user_role()
    ticket = TicketService.get_ticket(ticket_id, user_id, role)
    return success_response(TicketDetailSchema().dump(ticket))


@ticket_bp.route("/<int:ticket_id>", methods=["PUT"])
@jwt_required()
@validate_body(UpdateTicketSchema)
def update_ticket(data: dict, ticket_id: int):
    """PUT /api/v1/tickets/:id — Update ticket (role-scoped)."""
    from app.repositories.user_repository import UserRepository

    user_id = get_current_user_id()
    role = get_current_user_role()
    user = UserRepository.get_by_id(user_id)
    dept_id = user.department_id if user else None

    ticket = TicketService.update_ticket(
        ticket_id=ticket_id,
        current_user_id=user_id,
        current_user_role=role,
        current_user_department_id=dept_id,
        data=data,
    )
    return success_response(TicketDetailSchema().dump(ticket))


@ticket_bp.route("/<int:ticket_id>", methods=["DELETE"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def delete_ticket(ticket_id: int):
    """DELETE /api/v1/tickets/:id — Soft delete (Admin+)."""
    user_id = get_current_user_id()
    TicketService.delete_ticket(ticket_id, user_id)
    return no_content_response()


@ticket_bp.route("/<int:ticket_id>/assign", methods=["PUT"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(AssignTicketSchema)
def assign_ticket(data: dict, ticket_id: int):
    """PUT /api/v1/tickets/:id/assign — Assign/reassign ticket."""
    user_id = get_current_user_id()
    role = get_current_user_role()
    from app.repositories.user_repository import UserRepository

    user = UserRepository.get_by_id(user_id)
    ticket = TicketService.update_ticket(
        ticket_id=ticket_id,
        current_user_id=user_id,
        current_user_role=role,
        current_user_department_id=user.department_id if user else None,
        data={"assignee_id": data["assignee_id"]},
    )
    return success_response(TicketDetailSchema().dump(ticket))


@ticket_bp.route("/bulk-update", methods=["POST"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(BulkUpdateTicketSchema)
def bulk_update_tickets(data: dict):
    """POST /api/v1/tickets/bulk-update — Bulk update tickets (Manager+)."""
    count = TicketRepository.bulk_update(data["ticket_ids"], data["updates"])
    return success_response({"updated_count": count})


# ─── Comment Endpoints ────────────────────────────────────────────────────────


@ticket_bp.route("/<int:ticket_id>/comments", methods=["POST"])
@jwt_required()
@validate_body(CreateCommentSchema)
def add_comment(data: dict, ticket_id: int):
    """POST /api/v1/tickets/:id/comments — Add comment or internal note."""
    user_id = get_current_user_id()
    role = get_current_user_role()
    comment = TicketService.add_comment(
        ticket_id=ticket_id,
        author_id=user_id,
        author_role=role,
        body=data["body"],
        is_internal=data.get("is_internal", False),
    )
    return created_response(CommentResponseSchema().dump(comment))


@ticket_bp.route("/<int:ticket_id>/comments", methods=["GET"])
@jwt_required()
def list_comments(ticket_id: int):
    """GET /api/v1/tickets/:id/comments — List ticket comments."""
    role = get_current_user_role()
    include_internal = role != UserRole.EMPLOYEE.value
    comments = CommentRepository.list_for_ticket(ticket_id, include_internal=include_internal)
    return success_response(CommentResponseSchema(many=True).dump(comments))
