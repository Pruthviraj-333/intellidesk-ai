"""
IntelliDesk AI — Prompt Template Controller (Blueprint)
HTTP handlers for dynamic prompt template management (Admin+).
Route prefix: /api/v1/prompts
"""

from flask import Blueprint
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate

from app.extensions import db
from app.models.ai import PromptTemplate
from app.services.audit_service import AuditService
from app.utils.constants import UserRole
from app.utils.decorators import get_current_user_id, role_required, validate_body
from app.utils.exceptions import NotFoundError
from app.utils.response import created_response, no_content_response, success_response

prompt_bp = Blueprint("prompts", __name__, url_prefix="/api/v1/prompts")


class CreatePromptTemplateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    template_text = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    is_active = fields.Bool(load_default=True)


class UpdatePromptTemplateSchema(Schema):
    template_text = fields.Str()
    description = fields.Str(allow_none=True)
    is_active = fields.Bool()


def _serialize_prompt(p: PromptTemplate) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "template_text": p.template_text,
        "description": p.description,
        "is_active": p.is_active,
        "updated_by": p.updated_by,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@prompt_bp.route("/", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def list_prompt_templates():
    """GET /api/v1/prompts — List prompt templates (Admin+)."""
    prompts = PromptTemplate.query.order_by(PromptTemplate.name).all()
    return success_response([_serialize_prompt(p) for p in prompts])


@prompt_bp.route("/<string:name>", methods=["GET"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_prompt_template(name: str):
    """GET /api/v1/prompts/:name — Get prompt template by name."""
    p = PromptTemplate.query.filter_by(name=name).first()
    if not p:
        raise NotFoundError("PromptTemplate", name)
    return success_response(_serialize_prompt(p))


@prompt_bp.route("/", methods=["POST"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(CreatePromptTemplateSchema)
def create_prompt_template(data: dict):
    """POST /api/v1/prompts — Create prompt template (Admin+)."""
    user_id = get_current_user_id()
    p = PromptTemplate(
        name=data["name"],
        template_text=data["template_text"],
        description=data.get("description"),
        is_active=data.get("is_active", True),
        updated_by=user_id,
    )
    db.session.add(p)
    db.session.commit()

    AuditService.log(
        action="prompt_template_created",
        resource_type="prompt_template",
        resource_id=p.id,
        user_id=user_id,
        new_values={"name": p.name},
    )

    return created_response(_serialize_prompt(p))


@prompt_bp.route("/<string:name>", methods=["PUT"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_body(UpdatePromptTemplateSchema)
def update_prompt_template(data: dict, name: str):
    """PUT /api/v1/prompts/:name — Update prompt template text/status (Admin+)."""
    user_id = get_current_user_id()
    p = PromptTemplate.query.filter_by(name=name).first()
    if not p:
        raise NotFoundError("PromptTemplate", name)

    old_val = p.template_text
    if "template_text" in data:
        p.template_text = data["template_text"]
    if "description" in data:
        p.description = data["description"]
    if "is_active" in data:
        p.is_active = data["is_active"]
    p.updated_by = user_id

    db.session.commit()
    AuditService.log(
        action="prompt_template_updated",
        resource_type="prompt_template",
        resource_id=p.id,
        user_id=user_id,
        old_values={"template_text": old_val},
        new_values=data,
    )

    return success_response(_serialize_prompt(p))
