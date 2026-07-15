"""
IntelliDesk AI — AI Chat Service
Business logic for the multi-turn AI assistant conversation engine.
Combines RAG retrieval with Groq LLM for grounded responses.
"""

import uuid
from typing import Optional

from app.extensions import db
from app.models.ai import AIClassification, AIMessage, AISession
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.utils.constants import CHAT_HISTORY_LIMIT
from app.utils.exceptions import BusinessLogicError, NotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIChatService:
    """
    Orchestrates the full RAG → LLM pipeline for the AI assistant.

    Flow:
    1. Load conversation history from DB
    2. Run semantic search on user query (RAG retrieval)
    3. Build context-augmented prompt
    4. Call LLM via LLMService
    5. Persist message pair to DB
    6. Return response with metadata
    """

    @staticmethod
    def get_or_create_session(
        user_id: int,
        session_uuid: Optional[str] = None,
        ticket_id: Optional[int] = None,
    ) -> AISession:
        """
        Get existing session by UUID or create a new one.
        Each ticket can have its own dedicated session.
        """
        if session_uuid:
            session = AISession.query.filter_by(
                session_uuid=session_uuid,
                user_id=user_id,
                deleted_at=None,
            ).first()
            if session:
                return session

        # Create new session
        new_session = AISession(
            session_uuid=str(uuid.uuid4()),
            user_id=user_id,
            ticket_id=ticket_id,
            title="New Conversation",
        )
        db.session.add(new_session)
        db.session.commit()
        logger.info(f"AI session created: {new_session.session_uuid} for user={user_id}")
        return new_session

    @staticmethod
    def chat(
        user_id: int,
        query: str,
        session_uuid: Optional[str] = None,
        ticket_id: Optional[int] = None,
        n_rag_results: int = 4,
    ) -> dict:
        """
        Process a user query through the RAG → LLM pipeline.

        Args:
            user_id: Authenticated user ID.
            query: User's question or problem description.
            session_uuid: Existing session UUID (continues conversation).
            ticket_id: Optional ticket context for scoped conversations.
            n_rag_results: Number of knowledge base chunks to retrieve.

        Returns:
            {
                session_uuid, response, sources,
                model, tokens_used, latency_ms
            }
        """
        # 1. Get or create session
        session = AIChatService.get_or_create_session(
            user_id=user_id,
            session_uuid=session_uuid,
            ticket_id=ticket_id,
        )

        # 2. Auto-title the session from first message
        if session.message_count == 0:
            session.title = query[:100]
            db.session.commit()

        # 3. RAG retrieval — find relevant context chunks
        rag_results = RAGService.semantic_search(query=query, n_results=n_rag_results)
        context = RAGService.build_context_for_query(query=query, n_results=n_rag_results)

        # 4. Build conversation history for multi-turn context
        history = AIChatService._build_history(session)

        # 5. Assemble messages array
        messages = [
            {"role": "system", "content": LLMService.SYSTEM_PROMPT},
        ]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Use the following knowledge base context to answer the user's question:\n\n{context}",
                }
            )

        messages.extend(history)
        messages.append({"role": "user", "content": query})

        # 6. LLM call
        try:
            llm_result = LLMService.chat_completion(
                messages=messages,
                temperature=0.6,
                max_tokens=1024,
            )
        except RuntimeError as e:
            raise BusinessLogicError(str(e))

        response_text = llm_result["content"]
        total_tokens = llm_result["prompt_tokens"] + llm_result["completion_tokens"]

        # 7. Persist user message
        user_msg = AIMessage(
            session_id=session.id,
            role="user",
            content=query,
            tokens_used=llm_result["prompt_tokens"],
            model_used=llm_result["model"],
        )
        db.session.add(user_msg)

        # 8. Persist assistant response with RAG sources
        rag_source_meta = [
            {
                "content_preview": r["content"][:150],
                "score": r["score"],
                "collection": r["collection"],
                "metadata": r["metadata"],
            }
            for r in rag_results
        ]
        assistant_msg = AIMessage(
            session_id=session.id,
            role="assistant",
            content=response_text,
            tokens_used=llm_result["completion_tokens"],
            rag_sources=rag_source_meta,
            model_used=llm_result["model"],
            latency_ms=llm_result["latency_ms"],
        )
        db.session.add(assistant_msg)

        # 9. Update session counters
        session.message_count += 2
        session.total_tokens_used += total_tokens
        db.session.commit()

        logger.info(
            f"AI chat: session={session.session_uuid} tokens={total_tokens} "
            f"latency={llm_result['latency_ms']}ms rag_hits={len(rag_results)}"
        )

        return {
            "session_uuid": session.session_uuid,
            "session_title": session.title,
            "response": response_text,
            "sources": rag_source_meta,
            "model": llm_result["model"],
            "tokens_used": total_tokens,
            "latency_ms": llm_result["latency_ms"],
        }

    @staticmethod
    def _build_history(session: AISession) -> list[dict]:
        """
        Build the last N messages as history for multi-turn context.
        Limits history to prevent excessive context length.
        """
        limit = CHAT_HISTORY_LIMIT  # e.g. last 10 messages
        recent_messages = (
            AIMessage.query.filter_by(session_id=session.id)
            .order_by(AIMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        # Return in chronological order
        return [{"role": msg.role, "content": msg.content} for msg in reversed(recent_messages)]

    @staticmethod
    def get_session_history(session_uuid: str, user_id: int) -> list[AIMessage]:
        """Retrieve all messages for a session, scoped to the user."""
        session = AISession.query.filter_by(
            session_uuid=session_uuid,
            user_id=user_id,
            deleted_at=None,
        ).first()
        if not session:
            raise NotFoundError("AI Session", session_uuid)
        return session.messages

    @staticmethod
    def list_user_sessions(user_id: int, page: int = 1, per_page: int = 20):
        """List all active sessions for a user."""
        return (
            AISession.query.filter_by(user_id=user_id, deleted_at=None)
            .order_by(AISession.updated_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    @staticmethod
    def delete_session(session_uuid: str, user_id: int) -> None:
        """Soft delete a session and all its messages."""
        session = AISession.query.filter_by(
            session_uuid=session_uuid, user_id=user_id, deleted_at=None
        ).first()
        if not session:
            raise NotFoundError("AI Session", session_uuid)
        session.soft_delete()


class AITicketClassifier:
    """Classifies new tickets using the LLM and persists classification results."""

    @staticmethod
    def classify_and_persist(ticket) -> Optional[AIClassification]:
        """
        Classify a ticket and update its AI metadata fields.

        Args:
            ticket: Ticket model instance.

        Returns:
            AIClassification record, or None on failure.
        """
        try:
            classification = LLMService.classify_ticket(
                ticket_title=ticket.title,
                ticket_description=ticket.description,
            )

            # Find department by suggested name (best-effort)
            dept_id = None
            if classification.get("department_name"):
                from app.models.department import Department

                dept = Department.query.filter(
                    Department.name.ilike(f"%{classification['department_name']}%"),
                    Department.deleted_at.is_(None),
                ).first()
                if dept:
                    dept_id = dept.id

            # Persist classification record
            record = AIClassification(
                ticket_id=ticket.id,
                predicted_category=classification.get("category"),
                predicted_priority=classification.get("priority"),
                predicted_department_id=dept_id,
                confidence_score=classification.get("confidence", 0.0),
                reasoning=classification.get("reasoning"),
                model_used=classification.get("model"),
                prompt_tokens=classification.get("prompt_tokens", 0),
                completion_tokens=classification.get("completion_tokens", 0),
                latency_ms=classification.get("latency_ms"),
            )
            db.session.add(record)

            # Update ticket's AI suggestion fields
            from app.repositories.ticket_repository import TicketRepository

            TicketRepository.update_ai_metadata(
                ticket=ticket,
                category=classification.get("category"),
                priority=classification.get("priority"),
                department_id=dept_id,
                confidence=classification.get("confidence", 0.0),
                metadata=classification,
            )

            logger.info(
                f"Ticket {ticket.ticket_number} classified: "
                f"category={classification.get('category')} "
                f"priority={classification.get('priority')} "
                f"confidence={classification.get('confidence', 0.0):.2f}"
            )
            return record

        except Exception as e:
            logger.error(f"Failed to classify ticket {ticket.id}: {e}")
            return None
