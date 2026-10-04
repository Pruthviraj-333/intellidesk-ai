"""
IntelliDesk AI — WSGI Entry Point
Production entry point for Gunicorn.

IMPORTANT: eventlet.monkey_patch() MUST be the very first statement in this
module — before any other import. Eventlet intercepts the standard library's
blocking socket/select calls by swapping them for cooperative greenlet
equivalents at import time. If anything is imported first, those modules
cache references to the original (blocking) sockets, and the monkey-patch
has no effect on them — causing intermittent 'Bad file descriptor' errors
on WebSocket close and silent message drops in the Socket.IO handler.
"""

import eventlet  # noqa: E402 — must be first
eventlet.monkey_patch()  # noqa: E402 — must run before any other import

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    from app.extensions import socketio
    socketio.run(app, host="0.0.0.0", port=8000)
