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

# Signal phrases the LLM uses when it is ready to raise a ticket.
# Defined once at module level so chat() and chat_stream() always
# share the same list — a local copy in each method caused silent
# detection drift whenever one list was updated but not the other.
_TICKET_SIGNAL_PHRASES = [
    "i'm raising a ticket for you now",
    "i am raising a ticket for you now",
    "raising a ticket for you now",
    "i have all the details i need",
    "i'll raise a ticket",
    "i will raise a ticket",
    "creating a ticket for you",
    "i've raised a ticket",
    "i have raised a ticket",
    "ticket has been raised",
]


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

        # 3. RAG retrieval — single search call, reuse results for context string
        rag_results = RAGService.semantic_search(query=query, n_results=n_rag_results)
        if rag_results:
            context_parts = []
            for i, r in enumerate(rag_results):
                meta = r["metadata"]
                label = meta.get("title") or meta.get("file_name") or "Knowledge Base"
                context_parts.append(f"[Source {i+1}: {label} (score: {r['score']})]\n{r['content']}")
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = ""

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

        # 10. Agentic Ticket Creation — run intent detector on full conversation
        ticket_created_meta = None
        try:
            full_history = AIChatService._build_history(session)
            response_lower = response_text.lower()

            # DB-backed duplicate prevention: check if any PREVIOUS assistant messages
            # already contained a signal phrase (means ticket was already created earlier)
            # full_history[-2:] are the current user+assistant messages just committed
            earlier_messages = full_history[:-2] if len(full_history) >= 2 else []
            already_signalled_before = any(
                any(phrase in m["content"].lower() for phrase in _TICKET_SIGNAL_PHRASES)
                for m in earlier_messages
                if m["role"] == "assistant"
            )

            if already_signalled_before:
                logger.info(
                    f"Skipping ticket creation — already signalled in earlier message "
                    f"for session={session.session_uuid}"
                )
            else:
                # Check if current AI response signals readiness to raise ticket
                ai_signalled = any(phrase in response_lower for phrase in _TICKET_SIGNAL_PHRASES)

                if ai_signalled:
                    # Force mode: AI signalled readiness — extract fields from conversation
                    logger.info(
                        f"AI ticket signal detected for session={session.session_uuid}, "
                        f"forcing field extraction"
                    )
                    ticket_fields = LLMService.extract_ticket_intent(full_history, force=True)
                else:
                    # Standard mode: detect explicit user intent ("please create a ticket")
                    ticket_fields = LLMService.extract_ticket_intent(full_history, force=False)

                if ticket_fields:
                    from app.services.ticket_service import TicketService
                    new_ticket = TicketService.create_ticket(
                        title=ticket_fields["title"],
                        description=ticket_fields["description"],
                        requester_id=user_id,
                        priority=ticket_fields.get("priority"),
                        category=ticket_fields.get("category"),
                    )
                    ticket_created_meta = {
                        "id": new_ticket.id,
                        "ticket_number": new_ticket.ticket_number,
                        "title": new_ticket.title,
                        "priority": new_ticket.priority,
                        "category": new_ticket.category,
                        "status": new_ticket.status,
                    }
                    assistant_msg.ticket_created = ticket_created_meta
                    db.session.commit()
                    logger.info(

                        f"Agentic ticket created: {new_ticket.ticket_number} "
                        f"session={session.session_uuid} user={user_id} force={ai_signalled}"
                    )
        except Exception as e:
            logger.error(f"Agentic ticket creation failed: {e}")



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
            "ticket_created": ticket_created_meta,
        }

    @staticmethod
    def chat_stream(
        user_id: int,
        query: str,
        sid: str,
        app=None,
        session_uuid: Optional[str] = None,
        ticket_id: Optional[int] = None,
        n_rag_results: int = 4,
    ) -> None:
        """
        Streaming variant of chat(). Runs the same RAG → LLM pipeline but
        emits tokens to the caller's SocketIO room as they arrive.

        IMPORTANT: Must receive the Flask `app` object and push its context
        manually because this runs in an eventlet background greenlet that
        does NOT inherit the request's app context.

        SocketIO events emitted to room f"user:{user_id}":
            ai:stream:start  — {"session_uuid": ..., "session_title": ...}
            ai:stream:chunk  — {"chunk": "<token text>"}
            ai:stream:done   — {session_uuid, model, tokens_used, latency_ms,
                                sources, ticket_created}
            ai:stream:error  — {"message": "<error text>"}
        """
        from app.extensions import socketio
        room = f"user:{user_id}"

        # Push Flask app context for this greenlet
        ctx = app.app_context() if app else None
        if ctx:
            ctx.push()

        try:
            # 1. Get or create session
            session = AIChatService.get_or_create_session(
                user_id=user_id,
                session_uuid=session_uuid,
                ticket_id=ticket_id,
            )

            # 2. Auto-title from first message
            if session.message_count == 0:
                session.title = query[:100]
                db.session.commit()

            # 3. RAG retrieval — single search call, reuse results for context string
            rag_results = RAGService.semantic_search(query=query, n_results=n_rag_results)
            # Build context inline from the already-fetched results (avoids a second ChromaDB call)
            if rag_results:
                context_parts = []
                for i, r in enumerate(rag_results):
                    meta = r["metadata"]
                    label = meta.get("title") or meta.get("file_name") or "Knowledge Base"
                    context_parts.append(f"[Source {i+1}: {label} (score: {r['score']})]\n{r['content']}")
                context = "\n\n---\n\n".join(context_parts)
            else:
                context = ""

            # 4. Build conversation history
            history = AIChatService._build_history(session)

            # 5. Assemble messages
            messages = [{"role": "system", "content": LLMService.SYSTEM_PROMPT}]
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Use the following knowledge base context to answer the user's question:\n\n{context}",
                })
            messages.extend(history)
            messages.append({"role": "user", "content": query})

            # 6. Notify client stream is starting
            socketio.emit("ai:stream:start", {
                "session_uuid": session.session_uuid,
                "session_title": session.title,
            }, to=room)

            # 7. Stream LLM response token by token
            response_chunks = []
            model_used = None
            prompt_tokens = 0
            completion_tokens = 0
            latency_ms = 0

            for item in LLMService.chat_completion_stream(
                messages=messages,
                temperature=0.6,
                max_tokens=1024,
            ):
                if "model" in item and not item.get("done"):
                    # First yield — model name confirmed
                    model_used = item["model"]

                elif "chunk" in item:
                    # Token chunk — emit immediately
                    chunk_text = item["chunk"]
                    response_chunks.append(chunk_text)
                    socketio.emit("ai:stream:chunk", {"chunk": chunk_text}, to=room)

                elif item.get("done"):
                    # Stream finished — collect metadata
                    model_used = item.get("model", model_used)
                    prompt_tokens = item.get("prompt_tokens", 0)
                    completion_tokens = item.get("completion_tokens", len(response_chunks))
                    latency_ms = item.get("latency_ms", 0)

            response_text = "".join(response_chunks)
            total_tokens = prompt_tokens + completion_tokens

            # 8. Persist user message
            user_msg = AIMessage(
                session_id=session.id,
                role="user",
                content=query,
                tokens_used=prompt_tokens,
                model_used=model_used,
            )
            db.session.add(user_msg)

            # 9. Persist assistant response with RAG sources
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
                tokens_used=completion_tokens,
                rag_sources=rag_source_meta,
                model_used=model_used,
                latency_ms=latency_ms,
            )
            db.session.add(assistant_msg)

            # 10. Update session counters
            session.message_count += 2
            session.total_tokens_used += total_tokens
            db.session.commit()

            # 11. Agentic Ticket Creation (same logic as chat())
            ticket_created_meta = None
            try:
                full_history = AIChatService._build_history(session)
                response_lower = response_text.lower()
                earlier_messages = full_history[:-2] if len(full_history) >= 2 else []
                already_signalled_before = any(
                    any(phrase in m["content"].lower() for phrase in _TICKET_SIGNAL_PHRASES)
                    for m in earlier_messages
                    if m["role"] == "assistant"
                )

                if not already_signalled_before:
                    ai_signalled = any(phrase in response_lower for phrase in _TICKET_SIGNAL_PHRASES)
                    if ai_signalled:
                        ticket_fields = LLMService.extract_ticket_intent(full_history, force=True)
                    else:
                        ticket_fields = LLMService.extract_ticket_intent(full_history, force=False)

                    if ticket_fields:
                        from app.services.ticket_service import TicketService
                        new_ticket = TicketService.create_ticket(
                            title=ticket_fields["title"],
                            description=ticket_fields["description"],
                            requester_id=user_id,
                            priority=ticket_fields.get("priority"),
                            category=ticket_fields.get("category"),
                        )
                        ticket_created_meta = {
                            "id": new_ticket.id,
                            "ticket_number": new_ticket.ticket_number,
                            "title": new_ticket.title,
                            "priority": new_ticket.priority,
                            "category": new_ticket.category,
                            "status": new_ticket.status,
                        }
                        assistant_msg.ticket_created = ticket_created_meta
                        db.session.commit()
                        logger.info(
                            f"Agentic ticket created (stream): {new_ticket.ticket_number} "
                            f"session={session.session_uuid} user={user_id}"
                        )
            except Exception as e:
                logger.error(f"Agentic ticket creation failed (stream): {e}")

            logger.info(
                f"AI stream: session={session.session_uuid} tokens={total_tokens} "
                f"latency={latency_ms}ms rag_hits={len(rag_results)}"
            )

            # 12. Emit completion event with full metadata
            socketio.emit("ai:stream:done", {
                "session_uuid": session.session_uuid,
                "session_title": session.title,
                "model": model_used,
                "tokens_used": total_tokens,
                "latency_ms": latency_ms,
                "sources": rag_source_meta,
                "ticket_created": ticket_created_meta,
            }, to=room)

        except Exception as e:
            import traceback
            logger.error(f"chat_stream failed for user={user_id}: {e}\n{traceback.format_exc()}")
            try:
                socketio.emit("ai:stream:error", {"message": str(e)}, to=room)
            except Exception:
                pass
        finally:
            # Always pop the manually pushed app context when greenlet exits
            if ctx:
                ctx.pop()


    @staticmethod
    def generate_chat_sse(
        user_id: int,
        query: str,
        session_uuid: Optional[str] = None,
        ticket_id: Optional[int] = None,
        n_rag_results: int = 4,
    ):
        """
        Server-Sent Events generator for chat streaming.

        Runs the full RAG → LLM pipeline SYNCHRONOUSLY inside the Flask
        request context (no background greenlet needed). Yields SSE-formatted
        byte strings so Flask can stream them directly to the client via
        Response(stream_with_context(generator), mimetype='text/event-stream').

        This approach is production-grade and works with:
          - Any HTTP/1.1 or HTTP/2 connection
          - AWS ALB (set idle timeout > max LLM latency, e.g. 300 s)
          - Nginx (proxy_buffering off already set)
          - CloudFront (disable compression for text/event-stream)
          - No WebSocket negotiation, no socket.io handshake

        SSE event types emitted:
          data: {"type": "start",  "session_uuid": ..., "session_title": ...}
          data: {"type": "chunk",  "content": "<token>"}
          data: {"type": "done",   "session_uuid": ..., "session_title": ...,
                                   "model": ..., "tokens_used": ...,
                                   "latency_ms": ..., "sources": [...],
                                   "ticket_created": {...} | null}
          data: {"type": "error",  "message": "<error text>"}
        """
        import json

        def _sse(payload: dict) -> bytes:
            """Encode a dict as an SSE data line."""
            return f"data: {json.dumps(payload)}\n\n".encode()

        try:
            # ── 1. Session ────────────────────────────────────────────────────
            session = AIChatService.get_or_create_session(
                user_id=user_id,
                session_uuid=session_uuid,
                ticket_id=ticket_id,
            )

            # ── 2. Auto-title on first message ────────────────────────────────
            if session.message_count == 0:
                session.title = query[:100]
                db.session.commit()

            # ── 3. RAG retrieval ──────────────────────────────────────────────
            rag_results = RAGService.semantic_search(query=query, n_results=n_rag_results)
            if rag_results:
                context_parts = []
                for i, r in enumerate(rag_results):
                    meta = r["metadata"]
                    label = meta.get("title") or meta.get("file_name") or "Knowledge Base"
                    context_parts.append(
                        f"[Source {i+1}: {label} (score: {r['score']})]\n{r['content']}"
                    )
                context = "\n\n---\n\n".join(context_parts)
            else:
                context = ""

            # ── 4. Conversation history ───────────────────────────────────────
            history = AIChatService._build_history(session)

            # ── 5. Assemble messages ──────────────────────────────────────────
            messages = [{"role": "system", "content": LLMService.SYSTEM_PROMPT}]
            if context:
                messages.append({
                    "role": "system",
                    "content": (
                        "Use the following knowledge base context to answer "
                        f"the user's question:\n\n{context}"
                    ),
                })
            messages.extend(history)
            messages.append({"role": "user", "content": query})

            # ── 6. Persist user message and assistant placeholder BEFORE streaming ──
            # Production pattern: save both turns immediately so the conversation is
            # never lost if the client disconnects mid-stream. The assistant message
            # is marked is_truncated=True until the done event confirms clean finish.
            rag_source_meta = [
                {
                    "content_preview": r["content"][:150],
                    "score": r["score"],
                    "collection": r["collection"],
                    "metadata": r["metadata"],
                }
                for r in rag_results
            ]
            user_msg = AIMessage(
                session_id=session.id,
                role="user",
                content=query,
                tokens_used=0,
                model_used=None,
            )
            db.session.add(user_msg)
            assistant_msg = AIMessage(
                session_id=session.id,
                role="assistant",
                content="",
                tokens_used=0,
                rag_sources=rag_source_meta,
                model_used=None,
                latency_ms=None,
                is_truncated=True,   # assume interrupted; flipped to False on done
            )
            db.session.add(assistant_msg)
            session.message_count += 2
            db.session.commit()

            # ── 7. Emit start event ───────────────────────────────────────────
            yield _sse({"type": "start", "session_uuid": session.session_uuid,
                         "session_title": session.title})

            # ── 8. Stream LLM tokens ──────────────────────────────────────────
            response_chunks = []
            model_used = None
            prompt_tokens = 0
            completion_tokens = 0
            latency_ms = 0

            try:
                for item in LLMService.chat_completion_stream(
                    messages=messages,
                    temperature=0.6,
                    max_tokens=1024,
                ):
                    if "model" in item and not item.get("done"):
                        model_used = item["model"]

                    elif "chunk" in item:
                        chunk_text = item["chunk"]
                        response_chunks.append(chunk_text)
                        yield _sse({"type": "chunk", "content": chunk_text})

                    elif item.get("done"):
                        model_used        = item.get("model", model_used)
                        prompt_tokens     = item.get("prompt_tokens", 0)
                        completion_tokens = item.get("completion_tokens", len(response_chunks))
                        latency_ms        = item.get("latency_ms", 0)

            except GeneratorExit:
                # Client disconnected mid-stream (browser tab closed, network cut,
                # NGINX timeout, etc.). Save whatever was generated so far.
                partial_text = "".join(response_chunks)
                logger.warning(
                    f"SSE stream interrupted (GeneratorExit) for user={user_id} "
                    f"session={session.session_uuid} — saving {len(partial_text)} chars as truncated"
                )
                try:
                    assistant_msg.content    = partial_text if partial_text else "[Response interrupted before any content was generated.]"
                    assistant_msg.model_used = model_used
                    assistant_msg.is_truncated = True   # already True; be explicit
                    user_msg.model_used = model_used
                    db.session.commit()
                except Exception as save_err:
                    logger.error(f"Failed to save truncated message: {save_err}")
                    db.session.rollback()
                return  # generator must return (not raise) after GeneratorExit

            response_text = "".join(response_chunks)
            total_tokens  = prompt_tokens + completion_tokens

            # ── 9. Update persisted messages with final content ───────────────
            # is_truncated flips to False — clean completion confirmed.
            assistant_msg.content      = response_text
            assistant_msg.tokens_used  = completion_tokens
            assistant_msg.model_used   = model_used
            assistant_msg.latency_ms   = latency_ms
            assistant_msg.is_truncated = False
            user_msg.tokens_used       = prompt_tokens
            user_msg.model_used        = model_used

            # ── 10. Update session token counter ─────────────────────────────
            session.total_tokens_used += total_tokens
            db.session.commit()

            # ── 11. Agentic Ticket Creation ───────────────────────────────────
            ticket_created_meta = None
            try:
                full_history   = AIChatService._build_history(session)
                response_lower = response_text.lower()
                earlier_messages = full_history[:-2] if len(full_history) >= 2 else []
                already_signalled_before = any(
                    any(phrase in m["content"].lower() for phrase in _TICKET_SIGNAL_PHRASES)
                    for m in earlier_messages
                    if m["role"] == "assistant"
                )

                if not already_signalled_before:
                    ai_signalled = any(phrase in response_lower for phrase in _TICKET_SIGNAL_PHRASES)
                    ticket_fields = LLMService.extract_ticket_intent(
                        full_history, force=ai_signalled
                    )
                    if ticket_fields:
                        from app.services.ticket_service import TicketService
                        new_ticket = TicketService.create_ticket(
                            title=ticket_fields["title"],
                            description=ticket_fields["description"],
                            requester_id=user_id,
                            priority=ticket_fields.get("priority"),
                            category=ticket_fields.get("category"),
                        )
                        ticket_created_meta = {
                            "id":            new_ticket.id,
                            "ticket_number": new_ticket.ticket_number,
                            "title":         new_ticket.title,
                            "priority":      new_ticket.priority,
                            "category":      new_ticket.category,
                            "status":        new_ticket.status,
                        }
                        assistant_msg.ticket_created = ticket_created_meta
                        db.session.commit()
                        logger.info(
                            f"Agentic ticket created (SSE): {new_ticket.ticket_number} "
                            f"session={session.session_uuid} user={user_id}"
                        )
            except Exception as e:
                logger.error(f"Agentic ticket creation failed (SSE): {e}")

            logger.info(
                f"AI SSE stream: session={session.session_uuid} tokens={total_tokens} "
                f"latency={latency_ms}ms rag_hits={len(rag_results)}"
            )

            # ── 12. Emit done event ───────────────────────────────────────────
            yield _sse({
                "type":          "done",
                "session_uuid":  session.session_uuid,
                "session_title": session.title,
                "model":         model_used,
                "tokens_used":   total_tokens,
                "latency_ms":    latency_ms,
                "sources":       rag_source_meta,
                "ticket_created": ticket_created_meta,
            })

        except Exception as e:
            import traceback
            logger.error(f"generate_chat_sse failed for user={user_id}: {e}\n{traceback.format_exc()}")
            try:
                db.session.rollback()
            except Exception:
                pass
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode()


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
