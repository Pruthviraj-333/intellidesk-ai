"""
IntelliDesk AI — Project Controller (Blueprint)
HTTP handlers for project management (ticket grouping).
Route prefix: /api/v1/projects
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.models.incident import Project
from app.services.audit_service import AuditService
from app.utils.constants import UserRole
from app.utils.decorators import get_current_user_id, role_required, validate_body, validate_query
from app.utils.exceptions import NotFoundError
from app.utils.response import (
    build_pagination_meta,
    created_response,
    no_content_response,
    paginated_response,
    success_response,
)

project_bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")


class CreateProjectSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    description = fields.Str(allow_none=True)
    status = fields.Str(load_default="active")
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)


class UpdateProjectSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=200))
    description = fields.Str(allow_none=True)
    status = fields.Str()
    start_date = fields.Date(allow_none=True)
    end_date = fields.Date(allow_none=True)


class ProjectQuerySchema(Schema):
    status = fields.Str()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=20)


def _serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "created_by": project.created_by,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "member_count": len(project.members),
    }


@project_bp.route("/", methods=["POST"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateProjectSchema)
def create_project(data: dict):
    """POST /api/v1/projects — Create a new project (Manager+)."""
    user_id = get_current_user_id()
    project = Project(
        name=data["name"],
        description=data.get("description"),
        status=data.get("status", "active"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        created_by=user_id,
    )
    db.session.add(project)
    db.session.commit()

    AuditService.log(
        action="project_created",
        resource_type="project",
        resource_id=project.id,
        user_id=user_id,
        new_values={"name": project.name},
    )

    return created_response(_serialize_project(project))


@project_bp.route("/", methods=["GET"])
@jwt_required()
@validate_query(ProjectQuerySchema)
def list_projects(params: dict):
    """GET /api/v1/projects — List projects (All roles)."""
    query = Project.query.filter_by(deleted_at=None)
    if params.get("status"):
        query = query.filter_by(status=params["status"])

    pagination = query.order_by(Project.created_at.desc()).paginate(
        page=params["page"], per_page=params["per_page"], error_out=False
    )
    return paginated_response(
        data=[_serialize_project(p) for p in pagination.items],
        pagination=build_pagination_meta(pagination),
    )


@project_bp.route("/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id: int):
    """GET /api/v1/projects/:id — Get project detail."""
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        raise NotFoundError("Project", project_id)
    return success_response(_serialize_project(project))


@project_bp.route("/<int:project_id>", methods=["PUT"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateProjectSchema)
def update_project(data: dict, project_id: int):
    """PUT /api/v1/projects/:id — Update project (Manager+)."""
    user_id = get_current_user_id()
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        raise NotFoundError("Project", project_id)

    for field_name in ["name", "description", "status", "start_date", "end_date"]:
        if field_name in data:
            setattr(project, field_name, data[field_name])

    db.session.commit()
    AuditService.log(
        action="project_updated",
        resource_type="project",
        resource_id=project.id,
        user_id=user_id,
        new_values=data,
    )
    return success_response(_serialize_project(project))


@project_bp.route("/<int:project_id>", methods=["DELETE"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def delete_project(project_id: int):
    """DELETE /api/v1/projects/:id — Soft delete project (Admin+)."""
    user_id = get_current_user_id()
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        raise NotFoundError("Project", project_id)

    project.soft_delete()
    AuditService.log(
        action="project_deleted",
        resource_type="project",
        resource_id=project_id,
        user_id=user_id,
    )
    return no_content_response()
