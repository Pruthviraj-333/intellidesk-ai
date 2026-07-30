"""
IntelliDesk AI — Admin & Settings Controller (Blueprint)
HTTP handlers for system setting management and audit log review.
Route prefix: /api/v1/admin
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields

from app.dtos.auth_dto import AuditLogResponseSchema
from app.repositories.department_repository import AuditLogRepository, SettingRepository
from app.services.audit_service import AuditService
from app.utils.constants import AuditAction, UserRole
from app.utils.decorators import get_current_user_id, role_required, validate_body, validate_query
from app.utils.exceptions import NotFoundError
from app.utils.response import build_pagination_meta, paginated_response, success_response

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


class AuditLogQuerySchema(Schema):
    user_id = fields.Int()
    action = fields.Str()
    resource_type = fields.Str()
    from_date = fields.Date()
    to_date = fields.Date()
    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=50)


class UpdateSettingSchema(Schema):
    value = fields.Raw(required=True)
    value_type = fields.Str(load_default="string")
    description = fields.Str(allow_none=True)


# ─── System Settings Endpoints ──────────────────────────────────────────────────


@admin_bp.route("/settings", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_settings():
    """GET /api/v1/admin/settings — List all system settings (Admin+)."""
    settings = SettingRepository.get_all()
    results = [
        {
            "key": s.key,
            "value": s.typed_value,
            "value_type": s.value_type,
            "description": s.description,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "updated_by": s.updated_by,
        }
        for s in settings
    ]
    return success_response(results)


@admin_bp.route("/settings/<key>", methods=["PUT"])
@role_required(UserRole.SUPER_ADMIN)
@validate_body(UpdateSettingSchema)
def update_setting(data: dict, key: str):
    """PUT /api/v1/admin/settings/:key — Update or set system setting (Super Admin)."""
    user_id = get_current_user_id()
    old_setting = SettingRepository.get(key)
    old_val = old_setting.typed_value if old_setting else None

    setting = SettingRepository.set_value(
        key=key,
        value=data["value"],
        value_type=data.get("value_type", "string"),
        description=data.get("description"),
        user_id=user_id,
    )

    AuditService.log(
        action=AuditAction.SETTINGS_UPDATED.value,
        resource_type="setting",
        resource_id=setting.id,
        user_id=user_id,
        old_values={key: old_val},
        new_values={key: setting.typed_value},
    )

    return success_response(
        {
            "key": setting.key,
            "value": setting.typed_value,
            "value_type": setting.value_type,
            "description": setting.description,
        }
    )


# ─── Audit Log Endpoints ───────────────────────────────────────────────────────


@admin_bp.route("/audit-logs", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(AuditLogQuerySchema)
def list_audit_logs(params: dict):
    """GET /api/v1/admin/audit-logs — Query audit logs with pagination and filters (Admin+)."""
    pagination = AuditLogRepository.list_with_filters(**params)
    return paginated_response(
        data=AuditLogResponseSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )
