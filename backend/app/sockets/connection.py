"""
IntelliDesk AI — WebSocket Connection Handlers
Manages Socket.IO connect/disconnect events with JWT authentication.
"""

from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import emit, join_room, leave_room, disconnect

from app.extensions import socketio
from app.utils.logger import get_logger

logger = get_logger(__name__)


@socketio.on("connect")
def handle_connect(auth):
    """
    Handle new WebSocket connection.
    Requires valid JWT access token in the auth payload.
    Joins the user's personal room and their department room.

    Auth payload format: { "token": "<access_token>" }
    """
    token = None
    if auth and isinstance(auth, dict):
        token = auth.get("token")

    if not token:
        logger.warning("WebSocket connection rejected — no token provided")
        disconnect()
        return False

    try:
        decoded = decode_token(token)
        user_id = decoded.get("sub")
        role = decoded.get("role", "employee")

        # Join personal notification room
        join_room(f"user:{user_id}")

        # Join role-wide room for broadcast updates
        join_room(f"role:{role}")

        logger.info(f"WebSocket connected: user={user_id} sid={request.sid}")
        emit("connected", {
            "status": "connected",
            "user_id": user_id,
            "message": "Real-time connection established.",
        })

    except Exception as e:
        logger.warning(f"WebSocket connection rejected — invalid token: {e}")
        disconnect()
        return False


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket client disconnection."""
    logger.info(f"WebSocket disconnected: sid={request.sid}")


@socketio.on("join_department")
def handle_join_department(data):
    """
    Join a department-specific room for department-scoped events.
    Data: { "department_id": 3 }
    """
    dept_id = data.get("department_id")
    if dept_id:
        join_room(f"department:{dept_id}")
        emit("joined_department", {"department_id": dept_id})


@socketio.on("leave_department")
def handle_leave_department(data):
    """Leave a department room."""
    dept_id = data.get("department_id")
    if dept_id:
        leave_room(f"department:{dept_id}")
