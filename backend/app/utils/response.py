"""
IntelliDesk AI — Response Helpers
Standardized API response envelope for all endpoints.
"""

import uuid
from datetime import datetime, timezone

from flask import jsonify


def _build_meta() -> dict:
    """Build metadata object for response envelope."""
    return {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def success_response(data, status_code: int = 200, meta: dict | None = None):
    """
    Build a successful single-resource API response.

    Args:
        data: Serialized resource data (dict or list).
        status_code: HTTP status code (default 200).
        meta: Optional additional metadata.

    Returns:
        Flask JSON response with standard envelope.
    """
    payload = {
        "status": "success",
        "data": data,
        "meta": {**_build_meta(), **(meta or {})},
    }
    return jsonify(payload), status_code


def created_response(data, meta: dict | None = None):
    """Convenience wrapper for 201 Created responses."""
    return success_response(data, status_code=201, meta=meta)


def paginated_response(data, pagination: dict, meta: dict | None = None):
    """
    Build a paginated collection response.

    Args:
        data: List of serialized resources.
        pagination: Pagination metadata dict.
        meta: Optional additional metadata.

    Returns:
        Flask JSON response with pagination envelope.
    """
    payload = {
        "status": "success",
        "data": data,
        "pagination": pagination,
        "meta": {**_build_meta(), **(meta or {})},
    }
    return jsonify(payload), 200


def no_content_response():
    """Build a 204 No Content response (e.g., for DELETE)."""
    return "", 204


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: list | None = None,
):
    """
    Build a standardized error API response.

    Args:
        code: Machine-readable error code (e.g., 'VALIDATION_ERROR').
        message: Human-readable error description.
        status_code: HTTP status code.
        details: Optional list of field-level error details.

    Returns:
        Flask JSON response with error envelope.
    """
    error_payload = {
        "code": code,
        "message": message,
    }
    if details:
        error_payload["details"] = details

    payload = {
        "status": "error",
        "error": error_payload,
        "meta": _build_meta(),
    }
    return jsonify(payload), status_code


def build_pagination_meta(pagination_obj) -> dict:
    """
    Convert SQLAlchemy pagination object to dict.

    Args:
        pagination_obj: SQLAlchemy Pagination instance.

    Returns:
        Pagination metadata dict.
    """
    return {
        "page": pagination_obj.page,
        "per_page": pagination_obj.per_page,
        "total_items": pagination_obj.total,
        "total_pages": pagination_obj.pages,
        "has_next": pagination_obj.has_next,
        "has_prev": pagination_obj.has_prev,
    }
