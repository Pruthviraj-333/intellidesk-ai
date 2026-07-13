"""
IntelliDesk AI — Document Management Controller
HTTP handlers for document upload, status tracking, and processing.
Route prefix: /api/v1/documents
"""

from flask import Blueprint, request, send_from_directory
from flask_jwt_extended import jwt_required

from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.dtos.knowledge_dto import (
    DocumentResponseSchema, DocumentListQuerySchema,
)
from app.utils.decorators import (
    validate_query, role_required,
    get_current_user_id, get_current_user_role,
)
from app.utils.response import (
    success_response, created_response, no_content_response,
    paginated_response, build_pagination_meta,
)
from app.utils.constants import UserRole
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.utils.helpers import get_file_extension, sanitize_filename

document_bp = Blueprint("documents", __name__, url_prefix="/api/v1/documents")


@document_bp.route("/", methods=["POST"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def upload_document():
    """
    POST /api/v1/documents
    Upload a document for RAG pipeline processing.
    Accepts multipart/form-data with 'file' field.
    """
    user_id = get_current_user_id()

    if "file" not in request.files:
        raise ValidationError("No file provided. Use multipart/form-data with key 'file'.")

    file = request.files["file"]
    if not file.filename:
        raise ValidationError("Empty filename.")

    # Read metadata from form data
    title = request.form.get("title", "").strip()
    if not title:
        title = sanitize_filename(file.filename)

    description = request.form.get("description", "").strip() or None
    is_public = request.form.get("is_public", "false").lower() == "true"

    file_data = file.read()
    file_size = len(file_data)
    file_name = sanitize_filename(file.filename)

    document = DocumentService.upload_document(
        file_data=file_data,
        file_name=file_name,
        file_size=file_size,
        title=title,
        uploaded_by=user_id,
        description=description,
        is_public=is_public,
        process_immediately=False,  # Always async in production
    )
    return created_response(DocumentResponseSchema().dump(document))


@document_bp.route("/", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(DocumentListQuerySchema)
def list_documents(params: dict):
    """GET /api/v1/documents — List uploaded documents (Agent+)."""
    user_id = get_current_user_id()
    role = get_current_user_role()

    # Agents only see their own uploads
    if role == UserRole.AGENT.value:
        params["uploaded_by"] = user_id

    pagination = DocumentRepository.list_with_filters(**params)
    return paginated_response(
        data=DocumentResponseSchema(many=True).dump(pagination.items),
        pagination=build_pagination_meta(pagination),
    )


@document_bp.route("/<int:doc_id>", methods=["GET"])
@role_required(UserRole.AGENT, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_document(doc_id: int):
    """GET /api/v1/documents/:id — Get document detail and processing status."""
    user_id = get_current_user_id()
    role = get_current_user_role()
    doc = DocumentRepository.get_by_id(doc_id)
    if not doc:
        raise NotFoundError("Document", doc_id)

    if role == UserRole.AGENT.value and doc.uploaded_by != user_id:
        raise AuthorizationError("Agents can only view their own documents.")

    return success_response(DocumentResponseSchema().dump(doc))


@document_bp.route("/<int:doc_id>/reprocess", methods=["POST"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def reprocess_document(doc_id: int):
    """
    POST /api/v1/documents/:id/reprocess
    Re-queue a failed or pending document for RAG processing (Manager+).
    """
    doc = DocumentRepository.get_by_id(doc_id)
    if not doc:
        raise NotFoundError("Document", doc_id)
    if not doc.can_be_processed:
        raise ValidationError(
            f"Document in '{doc.status}' state cannot be reprocessed. "
            "Only 'pending' or 'failed' documents can be requeued."
        )

    from app.tasks.document_tasks import process_document_task
    process_document_task.delay(doc_id)
    return success_response({"message": "Document queued for reprocessing.", "document_id": doc_id})


@document_bp.route("/<int:doc_id>", methods=["DELETE"])
@role_required(UserRole.ADMIN, UserRole.SUPER_ADMIN)
def delete_document(doc_id: int):
    """DELETE /api/v1/documents/:id — Soft delete document (Admin+)."""
    doc = DocumentRepository.get_by_id(doc_id)
    if not doc:
        raise NotFoundError("Document", doc_id)
    DocumentRepository.soft_delete(doc)
    return no_content_response()


@document_bp.route("/local/<path:filename>", methods=["GET"])
def serve_local_document(filename: str):
    """
    GET /api/v1/documents/local/<filename>
    Serve locally stored documents (used when Cloudinary is not configured).
    No auth required so the processing pipeline can download files internally.
    """
    import os
    upload_dir = os.path.join("/app", "uploads")
    return send_from_directory(upload_dir, filename)

