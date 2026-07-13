"""
IntelliDesk AI — Auth & User DTOs (Marshmallow Schemas)
Request validation and response serialization for auth and user endpoints.
"""

import re
from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError


# ─── Password Validator ────────────────────────────────────────────────────────

def validate_password(password: str):
    """
    Enforce password strength: min 8 chars, 1 uppercase, 1 lowercase,
    1 digit, 1 special character.
    """
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        raise ValidationError("Password must contain at least one special character.")


# ─── Auth Request Schemas ──────────────────────────────────────────────────────

class RegisterSchema(Schema):
    """Validates user registration input."""
    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.Str(required=True, load_only=True, validate=validate_password)
    confirm_password = fields.Str(required=True, load_only=True)
    first_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    department_id = fields.Int(load_default=None)
    phone = fields.Str(load_default=None, validate=validate.Length(max=20))

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match.", field_name="confirm_password")


class LoginSchema(Schema):
    """Validates login credentials."""
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class RefreshSchema(Schema):
    """Validates token refresh request."""
    refresh_token = fields.Str(required=True)


class LogoutSchema(Schema):
    """Validates logout request."""
    refresh_token = fields.Str(load_default=None)


class ForgotPasswordSchema(Schema):
    """Validates forgot password request."""
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    """Validates password reset."""
    token = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True, validate=validate_password)
    confirm_password = fields.Str(required=True, load_only=True)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match.", field_name="confirm_password")


class VerifyEmailSchema(Schema):
    """Validates email verification request."""
    token = fields.Str(required=True)


class ResendVerificationSchema(Schema):
    """Validates resend verification request."""
    email = fields.Email(required=True)


class ChangePasswordSchema(Schema):
    """Validates password change for authenticated users."""
    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, load_only=True, validate=validate_password)
    confirm_password = fields.Str(required=True, load_only=True)

    @validates_schema
    def validate_passwords_match(self, data, **kwargs):
        if data.get("new_password") != data.get("confirm_password"):
            raise ValidationError("Passwords do not match.", field_name="confirm_password")


# ─── User Response Schemas ─────────────────────────────────────────────────────

class RoleSchema(Schema):
    """Serializes Role for embedding in User responses."""
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)


class DepartmentSummarySchema(Schema):
    """Minimal Department representation for embedding."""
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class UserSummarySchema(Schema):
    """Minimal User representation for embedding in other resources."""
    id = fields.Int(dump_only=True)
    uuid = fields.Str(dump_only=True)
    full_name = fields.Method("get_full_name")
    email = fields.Email(dump_only=True)
    avatar_url = fields.Str(dump_only=True, allow_none=True)
    role = fields.Method("get_role_name")

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_role_name(self, obj):
        return obj.role.name if obj.role else None


class UserResponseSchema(Schema):
    """Full User serialization for API responses."""
    id = fields.Int(dump_only=True)
    uuid = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    first_name = fields.Str(dump_only=True)
    last_name = fields.Str(dump_only=True)
    full_name = fields.Method("get_full_name")
    phone = fields.Str(dump_only=True, allow_none=True)
    avatar_url = fields.Str(dump_only=True, allow_none=True)
    role = fields.Method("get_role_name")
    department = fields.Nested(DepartmentSummarySchema, dump_only=True, allow_none=True)
    status = fields.Str(dump_only=True)
    timezone = fields.Str(dump_only=True)
    notification_prefs = fields.Dict(dump_only=True)
    email_verified_at = fields.DateTime(dump_only=True, allow_none=True)
    last_login_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_role_name(self, obj):
        return obj.role.name if obj.role else None


class UpdateProfileSchema(Schema):
    """Validates profile update input."""
    first_name = fields.Str(validate=validate.Length(min=2, max=100))
    last_name = fields.Str(validate=validate.Length(min=2, max=100))
    phone = fields.Str(allow_none=True, validate=validate.Length(max=20))
    timezone = fields.Str(validate=validate.Length(max=50))
    notification_prefs = fields.Dict()


class UpdateUserAdminSchema(Schema):
    """Validates admin user update (role, department, status)."""
    role_id = fields.Int()
    department_id = fields.Int(allow_none=True)
    status = fields.Str(validate=validate.OneOf(["active", "inactive", "locked"]))
    first_name = fields.Str(validate=validate.Length(min=2, max=100))
    last_name = fields.Str(validate=validate.Length(min=2, max=100))


class UserListQuerySchema(Schema):
    """Validates query parameters for user list endpoint."""
    role = fields.Str()
    department_id = fields.Int()
    status = fields.Str()
    search = fields.Str()
    sort_by = fields.Str(
        load_default="created_at",
        validate=validate.OneOf(["created_at", "first_name", "last_name", "email"]),
    )
    order = fields.Str(load_default="desc", validate=validate.OneOf(["asc", "desc"]))
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


# ─── Department Schemas ────────────────────────────────────────────────────────

class DepartmentResponseSchema(Schema):
    """Full Department serialization."""
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    manager = fields.Nested(UserSummarySchema, dump_only=True, allow_none=True)
    sla_config = fields.Dict(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    member_count = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreateDepartmentSchema(Schema):
    """Validates department creation."""
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    description = fields.Str(load_default=None, validate=validate.Length(max=500))
    manager_id = fields.Int(load_default=None)


class UpdateDepartmentSchema(Schema):
    """Validates department update."""
    name = fields.Str(validate=validate.Length(min=2, max=100))
    description = fields.Str(allow_none=True)
    manager_id = fields.Int(allow_none=True)
    sla_config = fields.Dict()
    is_active = fields.Bool()


# ─── AuditLog Schema ──────────────────────────────────────────────────────────

class AuditLogResponseSchema(Schema):
    """Serializes AuditLog for admin API responses."""
    id = fields.Int(dump_only=True)
    user = fields.Nested(UserSummarySchema, dump_only=True, allow_none=True)
    action = fields.Str(dump_only=True)
    resource_type = fields.Str(dump_only=True)
    resource_id = fields.Int(dump_only=True, allow_none=True)
    old_values = fields.Dict(dump_only=True, allow_none=True)
    new_values = fields.Dict(dump_only=True, allow_none=True)
    ip_address = fields.Str(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
