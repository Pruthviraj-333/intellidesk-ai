"""
IntelliDesk AI — Incident, Problem & Notification Controllers
HTTP handlers for ITIL incident/problem management and notifications.
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields
from marshmallow import validate as ma_validate

from app.dtos.ticket_dto import (
    AddTimelineEntrySchema,
    CreateIncidentSchema,
    CreateProblemSchema,
    IncidentDetailSchema,
    IncidentSummarySchema,
    IncidentTimelineSchema,
    NotificationListQuerySchema,
    NotificationSchema,
    ProblemDetailSchema,
    ProblemSummarySchema,
    UpdateIncidentSchema,
    UpdateProblemSchema,
)
from app.repositories.incident_repository import (
    IncidentRepository,
    NotificationRepository,
    ProblemRepository,
)
from app.services.audit_service import AuditService
from app.utils.constants import AuditAction, UserRole
from app.utils.decorators import (
    get_current_user_id,
    get_current_user_role,
    role_required,
    validate_body,
    validate_query,
)
from app.utils.exceptions import AuthorizationError, NotFoundError
from app.utils.response import (
    build_pagination_meta,
    created_response,
    no_content_response,
    paginated_response,
    success_response,
)

incident_bp = Blueprint("incidents", __name__, url_prefix="/api/v1/incidents")
problem_bp = Blueprint("problems", __name__, url_prefix="/api/v1/problems")
notification_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


# ─── Incident Filter Schema ────────────────────────────────────────────────────
class IncidentListQuerySchema(Schema):
    status = fields.Str()
    severity = fields.Str()
    department_id = fields.Int()
    from_date = fields.Date()
    to_date = fields.Date()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=20)


class ProblemListQuerySchema(Schema):
    status = fields.Str()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=20)


# ─── Incident Endpoints ───────────────────────────────────────────────────────


@incident_bp.route("/", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateIncidentSchema)
def create_incident(data: dict):
    """POST /api/v1/incidents — Create incident (Agent+)."""
    user_id = get_current_user_id()
    incident = IncidentRepository.create(
        title=data["title"],
        description=data["description"],
        severity=data["severity"],
        reporter_id=user_id,
        impact=data.get("impact"),
        affected_services=data.get("affected_services"),
        department_id=data.get("department_id"),
        linked_ticket_ids=data.get("linked_ticket_ids", []),
    )
    # Add creation timeline entry automatically
    IncidentRepository.add_timeline_entry(
        incident=incident,
        event_type="created",
        description=f"Incident created with severity: {incident.severity}",
        user_id=user_id,
    )
    AuditService.log(
        action=AuditAction.INCIDENT_CREATED.value,
        resource_type="incident",
        resource_id=incident.id,
        new_values={"incident_number": incident.incident_number, "severity": incident.severity},
    )
    return created_response(IncidentDetailSchema().dump(incident))


@incident_bp.route("/", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(IncidentListQuerySchema)
def list_incidents(params: dict):
    """GET /api/v1/incidents — List incidents (Agent+)."""
    pagination = IncidentRepository.list_with_filters(**params)
    return paginated_response(
        data=IncidentSummarySchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@incident_bp.route("/<int:incident_id>", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_incident(incident_id: int):
    """GET /api/v1/incidents/:id — Get incident detail."""
    incident = IncidentRepository.get_by_id(incident_id)
    if not incident:
        raise NotFoundError("Incident", incident_id)
    return success_response(IncidentDetailSchema().dump(incident))


@incident_bp.route("/<int:incident_id>", methods=["PUT"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateIncidentSchema)
def update_incident(data: dict, incident_id: int):
    """PUT /api/v1/incidents/:id — Update incident."""
    user_id = get_current_user_id()
    incident = IncidentRepository.get_by_id(incident_id)
    if not incident:
        raise NotFoundError("Incident", incident_id)

    old_status = incident.status
    incident = IncidentRepository.update(incident, data)

    if "status" in data and data["status"] != old_status:
        IncidentRepository.add_timeline_entry(
            incident=incident,
            event_type="update",
            description=f"Status changed from '{old_status}' to '{data['status']}'.",
            user_id=user_id,
        )
    AuditService.log(
        action=AuditAction.INCIDENT_UPDATED.value,
        resource_type="incident",
        resource_id=incident.id,
        user_id=user_id,
        new_values=data,
    )
    return success_response(IncidentDetailSchema().dump(incident))


@incident_bp.route("/<int:incident_id>/timeline", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(AddTimelineEntrySchema)
def add_timeline_entry(data: dict, incident_id: int):
    """POST /api/v1/incidents/:id/timeline — Add timeline entry."""
    user_id = get_current_user_id()
    incident = IncidentRepository.get_by_id(incident_id)
    if not incident:
        raise NotFoundError("Incident", incident_id)

    entry = IncidentRepository.add_timeline_entry(
        incident=incident,
        event_type=data["event_type"],
        description=data["description"],
        user_id=user_id,
        metadata=data.get("metadata", {}),
    )
    return created_response(IncidentTimelineSchema().dump(entry))


# ─── Problem Endpoints ────────────────────────────────────────────────────────


@problem_bp.route("/", methods=["POST"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateProblemSchema)
def create_problem(data: dict):
    """POST /api/v1/problems — Create problem record (Manager+)."""
    user_id = get_current_user_id()
    problem = ProblemRepository.create(
        title=data["title"],
        description=data["description"],
        linked_incident_ids=data.get("linked_incident_ids", []),
        owner_id=data.get("owner_id") or user_id,
    )
    AuditService.log(
        action="problem_created",
        resource_type="problem",
        resource_id=problem.id,
        new_values={"problem_number": problem.problem_number},
    )
    return created_response(ProblemDetailSchema().dump(problem))


@problem_bp.route("/", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(ProblemListQuerySchema)
def list_problems(params: dict):
    """GET /api/v1/problems — List problems (Manager+)."""
    pagination = ProblemRepository.list_with_filters(**params)
    return paginated_response(
        data=ProblemSummarySchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@problem_bp.route("/<int:problem_id>", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_problem(problem_id: int):
    """GET /api/v1/problems/:id — Get problem detail."""
    problem = ProblemRepository.get_by_id(problem_id)
    if not problem:
        raise NotFoundError("Problem", problem_id)
    return success_response(ProblemDetailSchema().dump(problem))


@problem_bp.route("/<int:problem_id>", methods=["PUT"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateProblemSchema)
def update_problem(data: dict, problem_id: int):
    """PUT /api/v1/problems/:id — Update problem root cause and resolution."""
    problem = ProblemRepository.get_by_id(problem_id)
    if not problem:
        raise NotFoundError("Problem", problem_id)

    problem = ProblemRepository.update(problem, data)
    return success_response(ProblemDetailSchema().dump(problem))


# ─── Notification Endpoints ───────────────────────────────────────────────────


@notification_bp.route("/", methods=["GET"])
@jwt_required()
@validate_query(NotificationListQuerySchema)
def list_notifications(params: dict):
    """GET /api/v1/notifications — List own notifications."""
    user_id = get_current_user_id()
    pagination = NotificationRepository.list_for_user(
        user_id=user_id,
        is_read=params.get("is_read"),
        page=params.get("page", 1),
        per_page=params.get("per_page", 20),
    )
    unread_count = NotificationRepository.get_unread_count(user_id)
    return paginated_response(
        data=NotificationSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
        meta={"unread_count": unread_count},
    )


@notification_bp.route("/<int:notif_id>/read", methods=["PUT"])
@jwt_required()
def mark_notification_read(notif_id: int):
    """PUT /api/v1/notifications/:id/read — Mark notification as read."""
    user_id = get_current_user_id()
    notif = NotificationRepository.list_for_user(user_id).items  # validate ownership
    from app.models.incident import Notification

    notif_obj = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif_obj:
        raise NotFoundError("Notification", notif_id)
    NotificationRepository.mark_read(notif_obj)
    return success_response({"message": "Notification marked as read."})


@notification_bp.route("/read-all", methods=["PUT"])
@jwt_required()
def mark_all_notifications_read():
    """PUT /api/v1/notifications/read-all — Mark all notifications as read."""
    user_id = get_current_user_id()
    count = NotificationRepository.mark_all_read(user_id)
    return success_response({"marked_read": count})


@notification_bp.route("/<int:notif_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notif_id: int):
    """DELETE /api/v1/notifications/:id — Dismiss and delete a notification."""
    from app.extensions import db
    from app.models.incident import Notification

    user_id = get_current_user_id()
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not notif:
        raise NotFoundError("Notification", notif_id)
    db.session.delete(notif)
    db.session.commit()
    return success_response({"message": "Notification deleted."})
