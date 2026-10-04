"""
IntelliDesk AI — Document Processing Celery Tasks
Async document ingestion into the RAG pipeline.
"""

from app.tasks import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, queue="documents", max_retries=2, default_retry_delay=30)
def process_document_task(self, document_id: int):
    """
    Extract text from an uploaded document, chunk it, embed it,
    and store the vectors in ChromaDB.
    Retries up to 2 times on failure with 30s delay.
    """
    try:
        from app.repositories.document_repository import DocumentRepository
        from app.services.document_service import DocumentService

        doc = DocumentRepository.get_by_id(document_id)
        if not doc:
            logger.warning(f"Document {document_id} not found — skipping task.")
            return

        logger.info(f"Processing document: {doc.file_name} (id={document_id})")
        success = DocumentService.process_document(doc)

        if success:
            logger.info(f"Document {document_id} processed successfully.")
        else:
            logger.error(f"Document {document_id} processing failed.")

    except Exception as exc:
        logger.error(f"Document task failed for doc={document_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="documents", max_retries=3, default_retry_delay=15)
def purge_document_vectors_task(self, document_id: int):
    """
    Async ChromaDB vector cleanup for a deleted or re-queued document.

    Triggered non-blocking after:
      - DELETE /api/v1/documents/:id  (prevent stale vectors post-deletion)
      - POST   /api/v1/documents/:id/reprocess  (clear old chunks before re-indexing)

    Retries up to 3 times with 15s delay to handle transient ChromaDB unavailability.
    Idempotent — delete on a non-existent where-clause is a no-op in ChromaDB.
    """
    try:
        from app.services.rag_service import RAGService

        logger.info(f"Purging ChromaDB vectors for document {document_id}.")
        success = RAGService.remove_document_from_index(document_id)

        if success:
            logger.info(f"Vectors purged successfully for document {document_id}.")
        else:
            logger.error(f"Vector purge returned False for document {document_id}.")

    except Exception as exc:
        logger.error(f"Vector purge task failed for doc={document_id}: {exc}")
        raise self.retry(exc=exc)

