"""
IntelliDesk AI — AI Streaming Socket Handler
Handles the 'ai:chat' SocketIO event and drives the streaming LLM pipeline.
The handler runs chat_stream() in a background greenlet so the eventlet worker is not blocked.
"""

from flask import request

from app.extensions import socketio
from app.utils.logger import get_logger

logger = get_logger(__name__)


@socketio.on("ai:chat")
def handle_ai_chat(data):
    """
    SocketIO event: ai:chat
    Payload: {
        "query": "<user message>",
        "session_uuid": "<uuid or null>",
        "ticket_id": <int or null>
    }

    Auth: looks up the authenticated user_id from the sid→user_id registry
    populated in connection.py at handshake time. No JWT re-decode needed.

    Emits back to the caller's personal room (user:<id>):
        ai:stream:start  — stream beginning, includes session info
        ai:stream:chunk  — one text chunk per token batch
        ai:stream:done   — stream complete, includes metadata & ticket_created
        ai:stream:error  — on any failure
    """
    # ── Auth: look up user from the sid registry (set at connect time) ────────
    from app.sockets.connection import _sid_user_map

    user_id = _sid_user_map.get(request.sid)
    if not user_id:
        socketio.emit(
            "ai:stream:error",
            {"message": "Not authenticated. Please reconnect."},
            to=request.sid,
        )
        return

    # ── Parse payload ─────────────────────────────────────────────────────────
    if not isinstance(data, dict) or not data.get("query", "").strip():
        socketio.emit(
            "ai:stream:error",
            {"message": "query is required."},
            to=request.sid,
        )
        return

    query = data["query"].strip()
    session_uuid = data.get("session_uuid") or None
    ticket_id = data.get("ticket_id") or None

    logger.info(f"ai:chat received: user={user_id} sid={request.sid} query_len={len(query)}")

    # ── Run stream in a background greenlet (non-blocking) ───────────────────
    # IMPORTANT: capture the app object NOW (in handler context which has app context)
    # and pass it to the background task — Flask app context is NOT auto-pushed
    # in eventlet greenlets spawned by start_background_task.
    from flask import current_app
    from app.services.ai_service import AIChatService

    app = current_app._get_current_object()

    socketio.start_background_task(
        target=AIChatService.chat_stream,
        app=app,
        user_id=user_id,
        query=query,
        sid=request.sid,
        session_uuid=session_uuid,
        ticket_id=ticket_id,
    )

