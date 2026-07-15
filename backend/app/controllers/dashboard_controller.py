"""
IntelliDesk AI — Dashboard Controller
Aggregated metrics and KPI endpoints for all dashboard views.
Route prefix: /api/v1/dashboard
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields

from app.repositories.incident_repository import IncidentRepository, NotificationRepository
from app.repositories.ticket_repository import TicketRepository
from app.utils.constants import IncidentStatus, TicketStatus, UserRole
from app.utils.decorators import (
    get_current_user_id,
    get_current_user_role,
    role_required,
    validate_query,
)
from app.utils.response import success_response

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


class DashboardQuerySchema(Schema):
    department_id = fields.Int()


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
@validate_query(DashboardQuerySchema)
def get_summary(params: dict):
    """
    GET /api/v1/dashboard/summary
    Aggregated KPI summary for the dashboard.

    Scoping:
    - Employee: own ticket stats
    - Agent: assigned ticket stats
    - Manager: department stats
    - Admin/Super Admin: platform-wide stats
    """
    user_id = get_current_user_id()
    role = get_current_user_role()

    from app.repositories.user_repository import UserRepository

    user = UserRepository.get_by_id(user_id)
    dept_id = params.get("department_id")

    # For agents/employees: scope to their own data
    if role == UserRole.EMPLOYEE.value:
        # Employee sees only their own tickets
        from app.extensions import db
        from app.models.ticket import Ticket

        own_tickets = Ticket.query.filter_by(requester_id=user_id, deleted_at=None)
        ticket_stats = {
            "open": own_tickets.filter(
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value])
            ).count(),
            "resolved": own_tickets.filter(Ticket.status == TicketStatus.RESOLVED.value).count(),
            "closed": own_tickets.filter(Ticket.status == TicketStatus.CLOSED.value).count(),
            "total": own_tickets.count(),
        }
        unread = NotificationRepository.get_unread_count(user_id)
        return success_response(
            {
                "ticket_stats": ticket_stats,
                "unread_notifications": unread,
            }
        )

    # For agents: show their assigned tickets
    if role == UserRole.AGENT.value:
        from app.extensions import db
        from app.models.ticket import Ticket

        assigned = Ticket.query.filter_by(assignee_id=user_id, deleted_at=None)
        ticket_stats = {
            "assigned_to_me": assigned.filter(
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value])
            ).count(),
            "resolved_by_me": assigned.filter(Ticket.status == TicketStatus.RESOLVED.value).count(),
            "overdue": assigned.filter(
                Ticket.sla_resolution_breached == True,  # noqa: E712
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
            ).count(),
        }
        unread = NotificationRepository.get_unread_count(user_id)
        return success_response(
            {
                "ticket_stats": ticket_stats,
                "unread_notifications": unread,
            }
        )

    # For managers/admins: full platform or department-scoped stats
    scope_dept_id = None
    if role == UserRole.MANAGER.value:
        scope_dept_id = user.department_id if user else None
    elif dept_id:
        scope_dept_id = dept_id

    ticket_stats = TicketRepository.get_dashboard_stats(department_id=scope_dept_id)

    # Incident stats
    from app.models.incident import Incident

    incident_query = Incident.query.filter_by(deleted_at=None)
    if scope_dept_id:
        incident_query = incident_query.filter_by(department_id=scope_dept_id)

    incident_stats = {
        "open": incident_query.filter(
            Incident.status.notin_([IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value])
        ).count(),
        "critical": incident_query.filter(Incident.severity == "critical").count(),
        "total": incident_query.count(),
    }

    unread = NotificationRepository.get_unread_count(user_id)
    return success_response(
        {
            "ticket_stats": ticket_stats,
            "incident_stats": incident_stats,
            "unread_notifications": unread,
        }
    )


@dashboard_bp.route("/ticket-trends", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_ticket_trends():
    """
    GET /api/v1/dashboard/ticket-trends?days=30
    Live daily ticket creation and resolution counts for the last N days.
    No snapshot dependency — queries tickets table directly.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func

    from app.extensions import db
    from app.models.ticket import Ticket

    days = int(request.args.get("days", 30))
    days = max(7, min(days, 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    created_rows = (
        db.session.query(
            func.date(Ticket.created_at).label("date"),
            func.count(Ticket.id).label("count"),
        )
        .filter(Ticket.created_at >= cutoff, Ticket.deleted_at.is_(None))
        .group_by(func.date(Ticket.created_at))
        .order_by(func.date(Ticket.created_at))
        .all()
    )
    resolved_rows = (
        db.session.query(
            func.date(Ticket.resolved_at).label("date"),
            func.count(Ticket.id).label("count"),
        )
        .filter(
            Ticket.resolved_at >= cutoff,
            Ticket.resolved_at.isnot(None),
            Ticket.deleted_at.is_(None),
        )
        .group_by(func.date(Ticket.resolved_at))
        .order_by(func.date(Ticket.resolved_at))
        .all()
    )

    merged = {}
    for row in created_rows:
        d = str(row.date)
        merged.setdefault(d, {"date": d, "tickets_created": 0, "tickets_resolved": 0})
        merged[d]["tickets_created"] = row.count
    for row in resolved_rows:
        d = str(row.date)
        merged.setdefault(d, {"date": d, "tickets_created": 0, "tickets_resolved": 0})
        merged[d]["tickets_resolved"] = row.count

    trend_list = sorted(merged.values(), key=lambda x: x["date"])
    return success_response(
        {
            "period_days": days,
            "data_points": len(trend_list),
            "trends": trend_list,
        }
    )


@dashboard_bp.route("/live-agent-leaderboard", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_live_agent_leaderboard():
    """
    GET /api/v1/dashboard/live-agent-leaderboard?days=30&limit=8
    Live agent performance stats — queries tickets directly, no snapshots needed.
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func

    from app.extensions import db
    from app.models.ticket import Ticket
    from app.models.user import User

    days = int(request.args.get("days", 30))
    limit = int(request.args.get("limit", 8))
    days = max(7, min(days, 365))
    limit = max(1, min(limit, 50))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        db.session.query(
            Ticket.assignee_id,
            func.count(Ticket.id).label("total_assigned"),
            func.sum(db.case((Ticket.status == TicketStatus.RESOLVED.value, 1), else_=0)).label(
                "resolved"
            ),
            func.sum(
                db.case((Ticket.sla_resolution_breached == True, 1), else_=0)  # noqa: E712
            ).label("breached"),
        )
        .filter(
            Ticket.assignee_id.isnot(None),
            Ticket.created_at >= cutoff,
            Ticket.deleted_at.is_(None),
        )
        .group_by(Ticket.assignee_id)
        .order_by(
            func.sum(db.case((Ticket.status == TicketStatus.RESOLVED.value, 1), else_=0)).desc()
        )
        .limit(limit)
        .all()
    )

    result = []
    for row in rows:
        agent = User.query.get(row.assignee_id)
        if not agent:
            continue
        assigned = row.total_assigned or 0
        resolved = int(row.resolved or 0)
        result.append(
            {
                "agent_id": row.assignee_id,
                "agent_name": f"{agent.first_name} {agent.last_name}",
                "tickets_resolved": resolved,
                "tickets_assigned": assigned,
                "sla_breached": int(row.breached or 0),
                "resolution_rate": round(resolved / assigned * 100, 1) if assigned > 0 else 0.0,
            }
        )

    return success_response({"period_days": days, "agents": result})


@dashboard_bp.route("/sla-compliance", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_sla_compliance():
    """
    GET /api/v1/dashboard/sla-compliance
    SLA compliance rates broken down by ticket priority.
    """
    from sqlalchemy import func

    from app.extensions import db
    from app.models.ticket import Ticket
    from app.utils.constants import TicketPriority

    result = {}
    for priority in TicketPriority:
        total = Ticket.query.filter_by(priority=priority.value, deleted_at=None).count()
        breached = Ticket.query.filter_by(
            priority=priority.value, sla_resolution_breached=True, deleted_at=None
        ).count()
        compliant = total - breached
        compliance_rate = round((compliant / total * 100), 1) if total > 0 else 100.0
        result[priority.value] = {
            "total": total,
            "compliant": compliant,
            "breached": breached,
            "compliance_rate": compliance_rate,
        }

    return success_response({"sla_compliance": result})


@dashboard_bp.route("/agent-performance", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_agent_performance():
    """
    GET /api/v1/dashboard/agent-performance
    Resolution stats per agent for performance tracking.
    """
    from sqlalchemy import func

    from app.extensions import db
    from app.models.ticket import Ticket
    from app.models.user import User

    stats = (
        db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            func.count(Ticket.id).label("total_assigned"),
            func.sum(db.case((Ticket.status == TicketStatus.RESOLVED.value, 1), else_=0)).label(
                "resolved"
            ),
            func.sum(
                db.case((Ticket.sla_resolution_breached == True, 1), else_=0)  # noqa: E712
            ).label("breached"),
        )
        .join(Ticket, Ticket.assignee_id == User.id)
        .filter(Ticket.deleted_at.is_(None))
        .group_by(User.id, User.first_name, User.last_name)
        .all()
    )

    return success_response(
        [
            {
                "agent_id": row.id,
                "agent_name": f"{row.first_name} {row.last_name}",
                "total_assigned": row.total_assigned,
                "resolved": row.resolved or 0,
                "sla_breached": row.breached or 0,
                "resolution_rate": (
                    round((row.resolved / row.total_assigned * 100), 1)
                    if row.total_assigned > 0
                    else 0.0
                ),
            }
            for row in stats
        ]
    )
