"""
IntelliDesk AI — User Controller (Blueprint)
HTTP handlers for user management and profile endpoints.
Route prefix: /api/v1/users
"""

from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.dtos.auth_dto import (
    UpdateProfileSchema,
    UpdateUserAdminSchema,
    UserListQuerySchema,
    UserResponseSchema,
    UserSummarySchema,
)
from app.repositories.user_repository import RoleRepository, UserRepository
from app.services.audit_service import AuditService
from app.utils.constants import AuditAction, UserRole
from app.utils.decorators import get_current_user_id, role_required, validate_body, validate_query
from app.utils.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.utils.response import (
    build_pagination_meta,
    no_content_response,
    paginated_response,
    success_response,
)

user_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@user_bp.route("/", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(UserListQuerySchema)
def list_users(params: dict):
    """GET /api/v1/users — List all users (Admin+)."""
    pagination = UserRepository.list_with_filters(
        role=params.get("role"),
        department_id=params.get("department_id"),
        status=params.get("status"),
        search=params.get("search"),
        sort_by=params.get("sort_by", "created_at"),
        order=params.get("order", "desc"),
        page=params.get("page", 1),
        per_page=params.get("per_page", 20),
    )
    return paginated_response(
        data=UserResponseSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@user_bp.route("/assignable", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def list_assignable_users():
    """
    GET /api/v1/users/assignable
    Returns all active agents and managers who can be assigned to tickets.
    Accessible to any authenticated staff member (Agent+).
    This avoids exposing the full user directory (Admin-only).
    """
    from app.models.user import User
    from app.utils.constants import UserStatus

    assignable = (
        User.query.filter(
            User.role.has(name=UserRole.AGENT.value) | User.role.has(name=UserRole.MANAGER.value),
            User.status == UserStatus.ACTIVE.value,
            User.deleted_at.is_(None),
        )
        .order_by(User.first_name.asc())
        .all()
    )
    return success_response(UserResponseSchema(many=True).dump(assignable))


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def get_my_profile():
    """GET /api/v1/users/me — Get authenticated user's profile."""
    user_id = get_current_user_id()
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return success_response(UserResponseSchema().dump(user))


@user_bp.route("/me", methods=["PUT"])
@jwt_required()
@validate_body(UpdateProfileSchema)
def update_my_profile(data: dict):
    """PUT /api/v1/users/me — Update authenticated user's own profile."""
    user_id = get_current_user_id()
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    old_values = {k: getattr(user, k) for k in data if hasattr(user, k)}
    user = UserRepository.update(user, data)

    AuditService.log(
        action=AuditAction.USER_UPDATED.value,
        resource_type="user",
        resource_id=user.id,
        old_values=old_values,
        new_values=data,
    )
    return success_response(UserResponseSchema().dump(user))


@user_bp.route("/me/change-password", methods=["PUT"])
@jwt_required()
@validate_body(
    type(
        "ChangePasswordSchema",
        (),
        {
            "__module__": __name__,
        },
    )
)
def change_password(data: dict):
    """PUT /api/v1/users/me/change-password — Change own password."""
    # Import here to avoid circular
    from app.dtos.auth_dto import ChangePasswordSchema
    from app.utils.exceptions import AuthenticationError

    user_id = get_current_user_id()
    user = UserRepository.get_by_id(user_id)

    if not user.check_password(data["current_password"]):
        raise AuthenticationError("Current password is incorrect.")

    user.set_password(data["new_password"])
    from app.extensions import db

    db.session.commit()

    AuditService.log(
        action="password_changed",
        resource_type="user",
        resource_id=user.id,
    )
    return success_response(
        {"message": "Password changed successfully. All other sessions have been invalidated."}
    )


@user_bp.route("/<int:user_id>", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_user(user_id: int):
    """GET /api/v1/users/:id — Get specific user (Admin+)."""
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return success_response(UserResponseSchema().dump(user))


@user_bp.route("/<int:user_id>", methods=["PUT"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdateUserAdminSchema)
def update_user(data: dict, user_id: int):
    """PUT /api/v1/users/:id — Admin update of user role/department/status."""
    user = UserRepository.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    # Prevent admin from modifying super_admin
    from app.utils.decorators import get_current_user_role

    current_role = get_current_user_role()
    if user.role_name == UserRole.SUPER_ADMIN.value and current_role != UserRole.SUPER_ADMIN.value:
        raise AuthorizationError("Cannot modify a Super Admin account.")

    # Validate role_id if provided
    if "role_id" in data:
        role = RoleRepository.get_by_id(data["role_id"])
        if not role:
            raise ValidationError("Invalid role_id.")
        if role.name == UserRole.SUPER_ADMIN.value and current_role != UserRole.SUPER_ADMIN.value:
            raise AuthorizationError("Only Super Admin can assign the Super Admin role.")

    old_values = {k: getattr(user, k) for k in data if hasattr(user, k)}
    user = UserRepository.update(user, data)

    AuditService.log(
        action=AuditAction.USER_UPDATED.value,
        resource_type="user",
        resource_id=user.id,
        old_values=old_values,
        new_values=data,
    )
    return success_response(UserResponseSchema().dump(user))


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@role_required(UserRole.SUPER_ADMIN)
def delete_user(user_id: int):
    """DELETE /api/v1/users/:id — Soft delete a user (Super Admin only)."""
    current_id = get_current_user_id()
    if user_id == current_id:
        raise AuthorizationError("You cannot delete your own account.")

    user = UserRepository.get_by_id(user_id)
    if not user:
        raise NotFoundError("User", user_id)

    AuditService.log(
        action=AuditAction.USER_DELETED.value,
        resource_type="user",
        resource_id=user.id,
        old_values={"email": user.email, "role": user.role_name},
    )
    UserRepository.soft_delete(user)
    return no_content_response()


@user_bp.route("/roles", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def list_roles():
    """GET /api/v1/users/roles — List all available roles (Admin+)."""
    from app.dtos.auth_dto import RoleSchema

    roles = RoleRepository.get_all()
    return success_response(RoleSchema(many=True).dump(roles))
