"""
IntelliDesk AI — AI Background Celery Tasks
Async AI classification and indexing tasks.
"""

from app.tasks import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, queue="ai", max_retries=2, default_retry_delay=30)
def classify_ticket_task(self, ticket_id: int):
    """
    Run AI classification on a newly created ticket.
    Updates ticket AI metadata fields and persists classification record.
    """
    try:
        from app.repositories.ticket_repository import TicketRepository
        from app.services.ai_service import AITicketClassifier

        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            logger.warning(f"Ticket {ticket_id} not found — skipping classification.")
            return

        logger.info(f"Classifying ticket: {ticket.ticket_number}")
        AITicketClassifier.classify_and_persist(ticket)

    except Exception as exc:
        logger.error(f"AI classification task failed for ticket={ticket_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="ai", max_retries=1)
def index_article_task(self, article_id: int):
    """
    Embed and index a published knowledge article in ChromaDB.
    Triggered when an article is published or updated.
    """
    try:
        from app.repositories.knowledge_repository import ArticleRepository
        from app.services.rag_service import RAGService

        article = ArticleRepository.get_by_id(article_id)
        if not article:
            logger.warning(f"Article {article_id} not found — skipping indexing.")
            return

        logger.info(f"Indexing article: {article.slug}")
        success = RAGService.index_article(article)
        if success:
            logger.info(f"Article {article_id} indexed successfully.")
        else:
            logger.error(f"Article {article_id} indexing failed.")

    except Exception as exc:
        logger.error(f"Article indexing task failed for article={article_id}: {exc}")
        raise self.retry(exc=exc)

