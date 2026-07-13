"""
IntelliDesk AI — Utility Decorators
Reusable decorators for authentication, authorization, and input validation.
"""

import functools
from typing import Callable

from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from marshmallow import Schema, ValidationError as MarshmallowValidationError

from app.utils.exceptions import AuthorizationError, ValidationError
from app.utils.constants import UserRole


def jwt_required(f: Callable) -> Callable:
    """
    Decorator that ensures the request contains a valid JWT access token.
    Loads current user into Flask's g object.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        return f(*args, **kwargs)

    return decorated


def role_required(*roles: UserRole) -> Callable:
    """
    Decorator factory that restricts endpoint access to specified roles.

    Usage:
        @role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
        def admin_endpoint(): ...

    Args:
        *roles: One or more UserRole enum values allowed to access the endpoint.
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")

            allowed_roles = {role.value if isinstance(role, UserRole) else role for role in roles}

            if user_role not in allowed_roles:
                raise AuthorizationError(
                    f"Access denied. Required role(s): {', '.join(allowed_roles)}."
                )

            return f(*args, **kwargs)

        return decorated

    return decorator


def validate_body(schema_class: type[Schema]) -> Callable:
    """
    Decorator that validates the request JSON body against a Marshmallow schema.
    Passes validated data as the first argument to the wrapped function.

    Usage:
        @validate_body(CreateTicketSchema)
        def create_ticket(data: dict): ...

    Args:
        schema_class: Marshmallow Schema class for validation.
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Request body must be JSON.")

            raw_data = request.get_json(silent=True)
            if raw_data is None:
                raise ValidationError("Invalid JSON body.")

            schema = schema_class()
            try:
                validated_data = schema.load(raw_data)
            except MarshmallowValidationError as e:
                details = [
                    {"field": field, "message": "; ".join(messages)}
                    for field, messages in e.messages.items()
                ]
                raise ValidationError("Input validation failed.", details=details)

            return f(validated_data, *args, **kwargs)

        return decorated

    return decorator


def validate_query(schema_class: type[Schema]) -> Callable:
    """
    Decorator that validates URL query parameters against a Marshmallow schema.
    Passes validated params as the first argument to the wrapped function.
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            schema = schema_class()
            try:
                validated_params = schema.load(request.args.to_dict())
            except MarshmallowValidationError as e:
                details = [
                    {"field": field, "message": "; ".join(messages)}
                    for field, messages in e.messages.items()
                ]
                raise ValidationError("Query parameter validation failed.", details=details)

            return f(validated_params, *args, **kwargs)

        return decorated

    return decorator


def get_current_user_id() -> int:
    """Helper to get the current authenticated user's ID from JWT identity."""
    return int(get_jwt_identity())


def get_current_user_role() -> str:
    """Helper to get the current authenticated user's role from JWT claims."""
    claims = get_jwt()
    return claims.get("role", "")


def get_current_user_department_id() -> int | None:
    """Helper to get the current authenticated user's department_id from JWT claims."""
    claims = get_jwt()
    return claims.get("department_id")


# Alias: allows controllers to use @jwt_required_any when they apply
# role_required separately at the handler level rather than the route level.
jwt_required_any = jwt_required

