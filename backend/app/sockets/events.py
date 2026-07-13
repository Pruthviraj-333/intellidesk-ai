"""
IntelliDesk AI — WebSocket Event Emitters
Helper functions for emitting real-time events from the service layer.
Centralizes all SocketIO emit calls for consistent event naming.
"""

from app.extensions import socketio


# ─── Event Name Constants ──────────────────────────────────────────────────────
EVT_TICKET_CREATED = "ticket:created"
EVT_TICKET_UPDATED = "ticket:updated"
EVT_TICKET_ASSIGNED = "ticket:assigned"
EVT_TICKET_STATUS_CHANGED = "ticket:status_changed"
EVT_INCIDENT_CREATED = "incident:created"
EVT_INCIDENT_UPDATED = "incident:updated"
EVT_NOTIFICATION = "notification:new"
EVT_DASHBOARD_REFRESH = "dashboard:refresh"
EVT_COMMENT_ADDED = "ticket:comment_added"


def emit_to_user(user_id: int | str, event: str, data: dict) -> None:
    """Emit an event to a specific user's personal room."""
    socketio.emit(event, data, to=f"user:{user_id}")


def emit_to_department(dept_id: int, event: str, data: dict) -> None:
    """Emit an event to all users in a department room."""
    socketio.emit(event, data, to=f"department:{dept_id}")


def emit_to_role(role_name: str, event: str, data: dict) -> None:
    """Emit an event to all users with a specific role."""
    socketio.emit(event, data, to=f"role:{role_name}")


def emit_broadcast(event: str, data: dict) -> None:
    """Broadcast an event to all connected clients."""
    socketio.emit(event, data)


# ─── Convenience Emitters ──────────────────────────────────────────────────────

def emit_ticket_assigned(assignee_id: int, ticket_data: dict) -> None:
    """Notify an agent they have been assigned a ticket."""
    emit_to_user(assignee_id, EVT_TICKET_ASSIGNED, ticket_data)


def emit_ticket_updated(dept_id: int, ticket_data: dict) -> None:
    """Notify department members of a ticket update."""
    emit_to_department(dept_id, EVT_TICKET_UPDATED, ticket_data)


def emit_new_notification(user_id: int, notification_data: dict) -> None:
    """Send an in-app notification to a specific user."""
    emit_to_user(user_id, EVT_NOTIFICATION, notification_data)


def emit_dashboard_refresh(dept_id: int | None = None) -> None:
    """
    Signal connected dashboards to refresh their data.
    Scoped to department or broadcast to all if dept_id is None.
    """
    data = {"type": "refresh", "timestamp": __import__("time").time()}
    if dept_id:
        emit_to_department(dept_id, EVT_DASHBOARD_REFRESH, data)
    else:
        emit_broadcast(EVT_DASHBOARD_REFRESH, data)
