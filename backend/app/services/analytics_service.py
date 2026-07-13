"""
IntelliDesk AI — Analytics Service
Computes and retrieves platform KPI metrics with caching via Redis.
"""

from datetime import datetime, timezone, timedelta, date
from typing import Optional

from sqlalchemy import func, case, cast, Date, extract

from app.extensions import db
from app.models.analytics import DailyMetricSnapshot, AgentDailyMetric
from app.models.ticket import Ticket, Comment
from app.models.incident import Incident
from app.models.knowledge import KnowledgeArticle
from app.models.ai import AISession
from app.models.user import User
from app.utils.constants import TicketStatus, TicketPriority, IncidentSeverity
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """
    Service for computing and retrieving platform analytics.
    All heavy queries use pre-aggregated snapshots where available.
    Live queries used only for real-time / today's data.
    """

    # ─── Snapshot Aggregation (called by Celery Beat nightly) ─────────────────

    @staticmethod
    def compute_daily_snapshot(target_date: date, department_id: Optional[int] = None) -> DailyMetricSnapshot:
        """
        Compute and upsert the daily metric snapshot for a given date.
        Idempotent — safe to run multiple times for the same date.
        """
        start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # ── Ticket metrics ────────────────────────────────────────────────────
        base_q = Ticket.query.filter(Ticket.deleted_at.is_(None))
        if department_id:
            base_q = base_q.filter(Ticket.department_id == department_id)

        created_q = base_q.filter(Ticket.created_at.between(start, end))
        resolved_q = base_q.filter(Ticket.resolved_at.between(start, end))

        tickets_created = created_q.count()
        tickets_resolved = resolved_q.count()
        tickets_closed = base_q.filter(
            Ticket.closed_at.between(start, end)
        ).count()
        tickets_open = base_q.filter(
            Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value])
        ).count()
        tickets_overdue = base_q.filter(
            Ticket.sla_resolution_breached == True,  # noqa: E712
            Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
        ).count()

        # ── SLA metrics ───────────────────────────────────────────────────────
        sla_breached = resolved_q.filter(Ticket.sla_resolution_breached == True).count()  # noqa: E712
        sla_met = tickets_resolved - sla_breached
        compliance = round((sla_met / tickets_resolved * 100), 2) if tickets_resolved > 0 else 100.0

        # ── Avg resolution time (hours) ───────────────────────────────────────
        resolved_with_times = resolved_q.filter(
            Ticket.resolved_at.isnot(None),
            Ticket.created_at.isnot(None),
        ).with_entities(Ticket.created_at, Ticket.resolved_at).all()

        resolution_times = [
            (r.resolved_at - r.created_at).total_seconds() / 3600
            for r in resolved_with_times
        ]
        avg_res_time = (sum(resolution_times) / len(resolution_times)) if resolution_times else None

        # ── Incident metrics ──────────────────────────────────────────────────
        inc_base = Incident.query.filter(Incident.deleted_at.is_(None))
        if department_id:
            inc_base = inc_base.filter(Incident.department_id == department_id)

        incidents_created = inc_base.filter(Incident.created_at.between(start, end)).count()
        incidents_resolved = inc_base.filter(Incident.resolved_at.between(start, end)).count()
        critical_incidents = inc_base.filter(
            Incident.severity == IncidentSeverity.CRITICAL.value,
            Incident.created_at.between(start, end),
        ).count()

        # ── KB and AI metrics ─────────────────────────────────────────────────
        articles_published = KnowledgeArticle.query.filter(
            KnowledgeArticle.published_at.between(start, end),
            KnowledgeArticle.deleted_at.is_(None),
        ).count()
        article_views = KnowledgeArticle.query.filter(
            KnowledgeArticle.deleted_at.is_(None)
        ).with_entities(func.sum(KnowledgeArticle.view_count)).scalar() or 0
        ai_sess = AISession.query.filter(AISession.created_at.between(start, end)).count()
        ai_tokens = db.session.query(func.sum(AISession.total_tokens_used)).scalar() or 0

        # ── Upsert snapshot ───────────────────────────────────────────────────
        existing = DailyMetricSnapshot.query.filter_by(
            snapshot_date=target_date,
            department_id=department_id,
        ).first()

        snapshot_data = dict(
            snapshot_date=target_date,
            department_id=department_id,
            tickets_created=tickets_created,
            tickets_resolved=tickets_resolved,
            tickets_closed=tickets_closed,
            tickets_open=tickets_open,
            tickets_overdue=tickets_overdue,
            sla_breached_count=sla_breached,
            sla_met_count=sla_met,
            sla_compliance_rate=compliance,
            avg_resolution_time_hours=avg_res_time,
            incidents_created=incidents_created,
            incidents_resolved=incidents_resolved,
            critical_incidents=critical_incidents,
            articles_published=articles_published,
            article_views=article_views,
            ai_sessions=ai_sess,
            ai_tokens_used=ai_tokens,
        )

        if existing:
            for key, val in snapshot_data.items():
                setattr(existing, key, val)
            snapshot = existing
        else:
            snapshot = DailyMetricSnapshot(**snapshot_data)
            db.session.add(snapshot)

        db.session.commit()
        logger.info(f"Snapshot computed: {target_date} dept={department_id}")
        return snapshot

    @staticmethod
    def compute_agent_daily_metric(target_date: date) -> list[AgentDailyMetric]:
        """Compute per-agent daily performance metrics."""
        start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        from app.utils.constants import UserRole
        agents = User.query.filter(
            User.role.has(name=UserRole.AGENT.value),
            User.deleted_at.is_(None),
        ).all()

        created_metrics = []
        for agent in agents:
            assigned = Ticket.query.filter(
                Ticket.assignee_id == agent.id,
                Ticket.created_at.between(start, end),
                Ticket.deleted_at.is_(None),
            )
            resolved = Ticket.query.filter(
                Ticket.assignee_id == agent.id,
                Ticket.resolved_at.between(start, end),
                Ticket.deleted_at.is_(None),
            )

            assigned_count = assigned.count()
            resolved_count = resolved.count()
            breached_count = resolved.filter(Ticket.sla_resolution_breached == True).count()  # noqa: E712

            # Avg resolution time
            res_tickets = resolved.filter(
                Ticket.resolved_at.isnot(None), Ticket.created_at.isnot(None)
            ).with_entities(Ticket.created_at, Ticket.resolved_at).all()
            times = [(r.resolved_at - r.created_at).total_seconds() / 3600 for r in res_tickets]
            avg_res = sum(times) / len(times) if times else None

            existing = AgentDailyMetric.query.filter_by(
                metric_date=target_date, agent_id=agent.id
            ).first()

            fields = dict(
                metric_date=target_date,
                agent_id=agent.id,
                tickets_assigned=assigned_count,
                tickets_resolved=resolved_count,
                tickets_sla_breached=breached_count,
                avg_resolution_time_hours=avg_res,
            )
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
                created_metrics.append(existing)
            else:
                metric = AgentDailyMetric(**fields)
                db.session.add(metric)
                created_metrics.append(metric)

        db.session.commit()
        return created_metrics

    # ─── Query Methods (API-facing) ────────────────────────────────────────────

    @staticmethod
    def get_trend_data(
        days: int = 30,
        department_id: Optional[int] = None,
    ) -> list[dict]:
        """Fetch daily trend data from pre-aggregated snapshots."""
        from_date = date.today() - timedelta(days=days)
        query = DailyMetricSnapshot.query.filter(
            DailyMetricSnapshot.snapshot_date >= from_date,
            DailyMetricSnapshot.department_id == department_id,
        ).order_by(DailyMetricSnapshot.snapshot_date.asc())

        return [
            {
                "date": str(s.snapshot_date),
                "tickets_created": s.tickets_created,
                "tickets_resolved": s.tickets_resolved,
                "tickets_open": s.tickets_open,
                "tickets_overdue": s.tickets_overdue,
                "sla_compliance_rate": s.sla_compliance_rate,
                "avg_resolution_hours": s.avg_resolution_time_hours,
                "incidents_created": s.incidents_created,
                "critical_incidents": s.critical_incidents,
                "ai_sessions": s.ai_sessions,
            }
            for s in query.all()
        ]

    @staticmethod
    def get_sla_compliance_by_priority() -> dict:
        """Live SLA compliance rates broken down by priority."""
        result = {}
        for priority in TicketPriority:
            total = Ticket.query.filter_by(priority=priority.value, deleted_at=None).count()
            breached = Ticket.query.filter_by(
                priority=priority.value, sla_resolution_breached=True, deleted_at=None
            ).count()
            compliant = total - breached
            result[priority.value] = {
                "total": total,
                "compliant": compliant,
                "breached": breached,
                "compliance_rate": round((compliant / total * 100), 1) if total > 0 else 100.0,
            }
        return result

    @staticmethod
    def get_ticket_volume_by_category() -> list[dict]:
        """Aggregate ticket counts by category."""
        rows = (
            db.session.query(Ticket.category, func.count(Ticket.id).label("count"))
            .filter(Ticket.deleted_at.is_(None))
            .group_by(Ticket.category)
            .order_by(func.count(Ticket.id).desc())
            .all()
        )
        return [{"category": r.category or "Uncategorized", "count": r.count} for r in rows]

    @staticmethod
    def get_agent_leaderboard(days: int = 30, limit: int = 10) -> list[dict]:
        """Top agents by resolution count over the last N days."""
        from_date = date.today() - timedelta(days=days)
        rows = (
            db.session.query(
                AgentDailyMetric.agent_id,
                func.sum(AgentDailyMetric.tickets_resolved).label("resolved"),
                func.sum(AgentDailyMetric.tickets_assigned).label("assigned"),
                func.sum(AgentDailyMetric.tickets_sla_breached).label("breached"),
                func.avg(AgentDailyMetric.avg_resolution_time_hours).label("avg_res_time"),
            )
            .filter(AgentDailyMetric.metric_date >= from_date)
            .group_by(AgentDailyMetric.agent_id)
            .order_by(func.sum(AgentDailyMetric.tickets_resolved).desc())
            .limit(limit)
            .all()
        )

        result = []
        for row in rows:
            agent = User.query.get(row.agent_id)
            if not agent:
                continue
            assigned = row.assigned or 0
            resolved = row.resolved or 0
            result.append({
                "agent_id": row.agent_id,
                "agent_name": f"{agent.first_name} {agent.last_name}",
                "avatar_url": agent.avatar_url,
                "tickets_resolved": int(resolved),
                "tickets_assigned": int(assigned),
                "sla_breached": int(row.breached or 0),
                "resolution_rate": round(resolved / assigned * 100, 1) if assigned > 0 else 0.0,
                "avg_resolution_hours": round(float(row.avg_res_time), 1) if row.avg_res_time else None,
            })
        return result

    @staticmethod
    def get_heatmap_data(days: int = 90) -> list[dict]:
        """
        Ticket creation heatmap by hour-of-day and day-of-week.
        Used to identify peak support request times.
        """
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.session.query(
                extract("dow", Ticket.created_at).label("day_of_week"),  # 0=Sun, 6=Sat
                extract("hour", Ticket.created_at).label("hour_of_day"),
                func.count(Ticket.id).label("count"),
            )
            .filter(Ticket.created_at >= from_date, Ticket.deleted_at.is_(None))
            .group_by("day_of_week", "hour_of_day")
            .all()
        )
        return [
            {"day": int(r.day_of_week), "hour": int(r.hour_of_day), "count": r.count}
            for r in rows
        ]

    @staticmethod
    def get_platform_summary() -> dict:
        """High-level platform totals for the executive summary card."""
        return {
            "total_tickets": Ticket.query.filter_by(deleted_at=None).count(),
            "open_tickets": Ticket.query.filter(
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
                Ticket.deleted_at.is_(None),
            ).count(),
            "total_incidents": Incident.query.filter_by(deleted_at=None).count(),
            "total_articles": KnowledgeArticle.query.filter_by(
                status="published", deleted_at=None
            ).count(),
            "total_agents": User.query.filter(
                User.role.has(name="agent"), User.deleted_at.is_(None)
            ).count(),
            "ai_sessions_total": AISession.query.filter_by(deleted_at=None).count(),
            "overall_sla_compliance": AnalyticsService._compute_overall_sla(),
        }

    @staticmethod
    def _compute_overall_sla() -> float:
        total = Ticket.query.filter(
            Ticket.resolved_at.isnot(None), Ticket.deleted_at.is_(None)
        ).count()
        if total == 0:
            return 100.0
        met = Ticket.query.filter(
            Ticket.resolved_at.isnot(None),
            Ticket.sla_resolution_breached == False,  # noqa: E712
            Ticket.deleted_at.is_(None),
        ).count()
        return round(met / total * 100, 1)
