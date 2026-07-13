"""
IntelliDesk AI — Document Processing Service
Extracts text from uploaded files and queues embedding in ChromaDB.
"""

import io
from typing import Optional

from flask import current_app
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.services.rag_service import RAGService
from app.utils.exceptions import ValidationError, BusinessLogicError
from app.utils.helpers import get_file_extension
from app.utils.constants import ALLOWED_DOCUMENT_EXTENSIONS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for document upload, parsing, and RAG pipeline ingestion."""

    @staticmethod
    def upload_document(
        file_data: bytes,
        file_name: str,
        file_size: int,
        title: str,
        uploaded_by: int,
        description: Optional[str] = None,
        is_public: bool = False,
        process_immediately: bool = False,
    ) -> Document:
        """
        Upload a document: validate, store on Cloudinary, persist metadata,
        and optionally trigger immediate processing.

        Args:
            file_data: Raw file bytes.
            file_name: Original filename with extension.
            file_size: File size in bytes.
            title: Human-readable document title.
            uploaded_by: User ID of the uploader.
            description: Optional description.
            is_public: Visibility to all authenticated users.
            process_immediately: Process inline (for dev). In prod, use Celery task.
        """
        # Validate extension
        ext = get_file_extension(file_name)
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise ValidationError(
                f"File type '{ext}' is not supported. "
                f"Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}."
            )

        # Validate file size
        max_bytes = current_app.config.get("MAX_UPLOAD_SIZE_MB", 25) * 1024 * 1024
        if file_size > max_bytes:
            raise ValidationError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds the "
                f"{current_app.config.get('MAX_UPLOAD_SIZE_MB', 25)} MB limit."
            )

        # Upload to Cloudinary
        file_url, public_id = DocumentService._upload_to_cloudinary(
            file_data=file_data,
            file_name=file_name,
            resource_type="raw",
        )

        # Create DB record
        document = DocumentRepository.create(
            title=title,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            file_type=ext,
            uploaded_by=uploaded_by,
            description=description,
            cloudinary_public_id=public_id,
            is_public=is_public,
        )

        logger.info(f"Document uploaded: {file_name} (id={document.id}) by user={uploaded_by}")

        if process_immediately:
            DocumentService.process_document(document)
        else:
            # Queue Celery task for async processing
            from app.tasks.document_tasks import process_document_task
            process_document_task.delay(document.id)

        return document

    @staticmethod
    def process_document(document: Document) -> bool:
        """
        Extract text, chunk, embed, and index a document.
        This is what the Celery worker executes.

        Returns:
            True on success, False on failure.
        """
        if not document.can_be_processed:
            raise BusinessLogicError(
                f"Document '{document.file_name}' cannot be processed in its current state: {document.status}."
            )

        document.mark_processing()

        try:
            # 1. Extract text
            text = DocumentService._extract_text(
                file_url=document.file_url,
                file_type=document.file_type,
            )
            if not text.strip():
                document.mark_failed("Document appears to be empty or could not be parsed.")
                return False

            # 2. Chunk text
            chunks = RAGService.chunk_text(text, chunk_size=500, overlap=50)
            if not chunks:
                document.mark_failed("No indexable content found after chunking.")
                return False

            # 3. Persist chunks to DB
            model_name = current_app.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            collection = RAGService.DOCUMENT_COLLECTION
            chunk_objects = DocumentRepository.save_chunks(document.id, chunks)

            # 4. Embed and index in ChromaDB
            chroma_ids = RAGService.index_document(document=document, chunks=chunks)
            if not chroma_ids:
                document.mark_failed("ChromaDB indexing failed — see logs for details.")
                return False

            # 5. Link ChromaDB IDs back to chunk records
            DocumentRepository.update_chunk_chroma_ids(chunk_objects, chroma_ids)

            # 6. Mark document as processed
            document.mark_processed(
                chunk_count=len(chunks),
                model=model_name,
                collection=collection,
            )
            logger.info(f"Document processed: {document.file_name} ({len(chunks)} chunks).")
            return True

        except Exception as e:
            logger.error(f"Document processing failed for doc={document.id}: {e}")
            document.mark_failed(str(e))
            return False

    @staticmethod
    def _extract_text(file_url: str, file_type: str) -> str:
        """
        Download document from Cloudinary and extract plain text.
        Supports: pdf, docx, txt, md.
        """
        import requests

        try:
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            content = response.content
        except Exception as e:
            raise BusinessLogicError(f"Failed to download document: {e}")

        if file_type == "pdf":
            return DocumentService._extract_from_pdf(content)
        elif file_type == "docx":
            return DocumentService._extract_from_docx(content)
        elif file_type in ("txt", "md"):
            return content.decode("utf-8", errors="replace")
        else:
            raise ValidationError(f"Unsupported file type for text extraction: {file_type}")

    @staticmethod
    def _extract_from_pdf(content: bytes) -> str:
        """Extract text from PDF bytes using PyPDF2."""
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except Exception as e:
            raise BusinessLogicError(f"PDF parsing failed: {e}")

    @staticmethod
    def _extract_from_docx(content: bytes) -> str:
        """Extract text from DOCX bytes using python-docx."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise BusinessLogicError(f"DOCX parsing failed: {e}")

    @staticmethod
    def _upload_to_cloudinary(
        file_data: bytes,
        file_name: str,
        resource_type: str = "raw",
    ) -> tuple[str, str]:
        """
        Upload file to Cloudinary, or fall back to local storage if
        Cloudinary is not configured (placeholder URL in .env).
        Returns: (secure_url, public_id)
        """
        cloudinary_url = current_app.config.get("CLOUDINARY_URL", "")

        # Detect unconfigured / placeholder Cloudinary credentials
        is_placeholder = (
            not cloudinary_url
            or "api_key" in cloudinary_url
            or "api_secret" in cloudinary_url
            or cloudinary_url == "cloudinary://api_key:api_secret@cloud_name"
        )

        if is_placeholder:
            # ── Local storage fallback (development only) ──────────────────
            import os
            upload_dir = os.path.join("/app", "uploads")
            os.makedirs(upload_dir, exist_ok=True)

            # Avoid collisions with a simple counter suffix
            base, ext = os.path.splitext(file_name)
            target_path = os.path.join(upload_dir, file_name)
            counter = 0
            while os.path.exists(target_path):
                counter += 1
                target_path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
            final_name = os.path.basename(target_path)

            with open(target_path, "wb") as f:
                f.write(file_data)

            # Build a URL accessible via the backend itself so ChromaDB can
            # download it during processing (same host, no auth required).
            local_url = f"http://localhost:8000/api/v1/documents/local/{final_name}"
            public_id = f"local/{final_name}"
            logger.info(f"[Local storage] Saved '{file_name}' → {target_path}")
            return local_url, public_id

        # ── Real Cloudinary upload ─────────────────────────────────────────
        try:
            import cloudinary.uploader

            result = cloudinary.uploader.upload(
                io.BytesIO(file_data),
                public_id=f"intellidesk/documents/{file_name}",
                resource_type=resource_type,
                use_filename=True,
                unique_filename=True,
            )
            return result["secure_url"], result["public_id"]

        except Exception as e:
            logger.error(f"Cloudinary upload failed for {file_name}: {e}")
            raise BusinessLogicError(f"File upload failed: {e}")

