"""IntelliDesk AI — Sockets package."""

from app.extensions import socketio

# Import handlers to register them with SocketIO
from . import ai_socket  # noqa: F401
from . import connection  # noqa: F401

__all__ = ["socketio"]
