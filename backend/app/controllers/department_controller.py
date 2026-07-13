"""
IntelliDesk AI — Department Controller & Health Controller
HTTP handlers for department management and system health endpoints.
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required

from app.repositories.department_repository import DepartmentRepository, AuditLogRepository
from app.services.audit_service import AuditService
from app.dtos.auth_dto import (
    DepartmentResponseSchema,
    CreateDepartmentSchema,
    UpdateDepartmentSchema,
    AuditLogResponseSchema,
)
from app.utils.decorators import role_required, validate_body, validate_query
from app.utils.response import (
    success_response, created_response, no_content_response,
    paginated_response, build_pagination_meta,
)
from app.utils.constants import UserRole, AuditAction
from app.utils.exceptions import NotFoundError, ConflictError
from marshmallow import Schema, fields, validate

department_bp = Blueprint("departments", __name__, url_prefix="/api/v1/departments")


class DepartmentListQuerySchema(Schema):
    is_active = fields.Bool(load_default=None)
    sort_by = fields.Str(load_default="name", validate=validate.OneOf(["name", "created_at"]))
    order = fields.Str(load_default="asc", validate=validate.OneOf(["asc", "desc"]))
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


@department_bp.route("/", methods=["GET"])
@jwt_required()
@validate_query(DepartmentListQuerySchema)
def list_departments(params: dict):
    """GET /api/v1/departments — List departments (all authenticated users)."""
    pagination = DepartmentRepository.list_with_filters(
        is_active=params.get("is_active"),
        sort_by=params.get("sort_by", "name"),
        order=params.get("order", "asc"),
        page=params.get("page", 1),
        per_page=params.get("per_page", 20),
    )
    return paginated_response(
        data=DepartmentResponseSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@department_bp.route("/<int:dept_id>", methods=["GET"])
@jwt_required()
def get_department(dept_id: int):
    """GET /api/v1/departments/:id — Get department detail."""
    dept = DepartmentRepository.get_by_id(dept_id)
    if not dept:
        raise NotFoundError("Department", dept_id)
    return success_response(DepartmentResponseSchema().dump(dept))


@department_bp.route("/", methods=["POST"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreateDepartmentSchema)
def create_department(data: dict):
    """POST /api/v1/departments — Create department (Admin+)."""
    existing = DepartmentRepository.get_by_name(data["name"])
    if existing:
        raise ConflictError(f"Department '{data['name']}' already exists.")

    dept = DepartmentRepository.create(
        name=data["name"],
        description=data.get("description"),
        manager_id=data.get("manager_id"),
    )
    AuditService.log(
        action="department_created",
        resource_type="department",
        resource_id=dept.id,
        new_values={"name": dept.name},
    )
    return created_response(DepartmentResponseSchema().dump(dept))


@department_bp.route("/<int:dept_id>", methods=["PUT"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateDepartmentSchema)
def update_department(data: dict, dept_id: int):
    """PUT /api/v1/departments/:id — Update department (Admin+)."""
    dept = DepartmentRepository.get_by_id(dept_id)
    if not dept:
        raise NotFoundError("Department", dept_id)

    if "name" in data and data["name"] != dept.name:
        existing = DepartmentRepository.get_by_name(data["name"])
        if existing:
            raise ConflictError(f"Department '{data['name']}' already exists.")

    old_values = {k: getattr(dept, k) for k in data if hasattr(dept, k)}
    dept = DepartmentRepository.update(dept, data)
    AuditService.log(
        action="department_updated",
        resource_type="department",
        resource_id=dept.id,
        old_values=old_values,
        new_values=data,
    )
    return success_response(DepartmentResponseSchema().dump(dept))


@department_bp.route("/<int:dept_id>", methods=["DELETE"])
@role_required(UserRole.SUPER_ADMIN)
def delete_department(dept_id: int):
    """DELETE /api/v1/departments/:id — Soft delete department (Super Admin only)."""
    dept = DepartmentRepository.get_by_id(dept_id)
    if not dept:
        raise NotFoundError("Department", dept_id)

    AuditService.log(
        action="department_deleted",
        resource_type="department",
        resource_id=dept.id,
        old_values={"name": dept.name},
    )
    DepartmentRepository.soft_delete(dept)
    return no_content_response()


# ─── Health Controller ────────────────────────────────────────────────────────

health_bp = Blueprint("health", __name__, url_prefix="/api/v1")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """GET /api/v1/health — Public health check endpoint."""
    import os
    return success_response({
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.environ.get("FLASK_ENV", "development"),
    })


@health_bp.route("/health/detailed", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def health_detailed():
    """GET /api/v1/health/detailed — Detailed health status (Admin+)."""
    import time
    import redis as redis_lib
    from flask import current_app

    results = {}

    # Database check
    try:
        start = time.time()
        from app.extensions import db
        db.session.execute(db.text("SELECT 1"))
        results["database"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        results["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis check
    try:
        start = time.time()
        r = redis_lib.from_url(current_app.config["REDIS_URL"])
        r.ping()
        results["redis"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        results["redis"] = {"status": "unhealthy", "error": str(e)}

    # ChromaDB check (optional — may not be running in dev)
    try:
        import chromadb
        start = time.time()
        client = chromadb.HttpClient(
            host=current_app.config["CHROMA_HOST"],
            port=current_app.config["CHROMA_PORT"],
        )
        client.heartbeat()
        results["chromadb"] = {"status": "healthy", "latency_ms": round((time.time() - start) * 1000)}
    except Exception:
        results["chromadb"] = {"status": "unavailable"}

    # Groq API check (just validates key presence)
    groq_key = current_app.config.get("GROQ_API_KEY", "")
    results["groq_api"] = {
        "status": "configured" if groq_key else "not_configured",
    }

    overall = "healthy" if all(
        v.get("status") in ("healthy", "configured", "unavailable")
        for v in results.values()
    ) else "degraded"

    return success_response({
        "status": overall,
        "version": "1.0.0",
        "services": results,
    })
