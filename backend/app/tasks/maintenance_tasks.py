"""
IntelliDesk AI — Maintenance Celery Tasks
Scheduled jobs: token cleanup, daily metric snapshots, SLA monitoring.
"""

from datetime import datetime, timezone, timedelta, date

from app.tasks import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(queue="default")
def cleanup_expired_tokens():
    """
    Remove expired, used tokens from user_tokens table.
    Scheduled nightly via Celery Beat.
    """
    from app.extensions import db
    from app.models.user import UserToken

    try:
        now = datetime.now(timezone.utc)
        deleted = UserToken.query.filter(UserToken.expires_at < now).delete()
        db.session.commit()
        logger.info(f"Maintenance: removed {deleted} expired tokens.")
    except Exception as e:
        logger.error(f"Token cleanup task failed: {e}")
        db.session.rollback()


@celery_app.task(queue="default")
def compute_daily_metrics_snapshot():
    """
    Compute and persist yesterday's daily metric snapshot.
    Runs every night at 00:05 UTC via Celery Beat to capture complete day data.
    Also computes per-agent daily metrics.
    """
    from app.services.analytics_service import AnalyticsService
    from app.models.department import Department

    yesterday = date.today() - timedelta(days=1)

    try:
        # Platform-wide snapshot
        snapshot = AnalyticsService.compute_daily_snapshot(yesterday)
        logger.info(f"Platform snapshot computed: {yesterday}")

        # Per-department snapshots
        depts = Department.query.filter_by(deleted_at=None, is_active=True).all()
        for dept in depts:
            AnalyticsService.compute_daily_snapshot(yesterday, department_id=dept.id)
        logger.info(f"Department snapshots computed: {len(depts)} departments")

        # Per-agent daily metrics
        agent_metrics = AnalyticsService.compute_agent_daily_metric(yesterday)
        logger.info(f"Agent metrics computed: {len(agent_metrics)} agents")

    except Exception as e:
        logger.error(f"Daily snapshot task failed: {e}")
        raise


@celery_app.task(queue="default")
def check_sla_breaches():
    """
    Check for SLA breaches every 15 minutes.
    Sends in-app + email notifications for tickets approaching or breaching SLA.
    """
    from app.extensions import db
    from app.models.ticket import Ticket
    from app.models.incident import Notification
    from app.utils.constants import TicketStatus, NotificationType

    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(minutes=30)  # Warn 30 min before breach

    # ── Approaching SLA breach (warning) ──────────────────────────────────────
    approaching = Ticket.query.filter(
        Ticket.sla_resolution_deadline <= warning_threshold,
        Ticket.sla_resolution_deadline > now,
        Ticket.sla_resolution_breached == False,  # noqa: E712
        Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
        Ticket.deleted_at.is_(None),
    ).all()

    for ticket in approaching:
        if ticket.assignee_id:
            notif = Notification(
                user_id=ticket.assignee_id,
                title="⚠️ SLA Warning",
                body=f"Ticket {ticket.ticket_number} is approaching its SLA deadline.",
                notification_type=NotificationType.SLA_WARNING.value,
                related_type="ticket",
                related_id=ticket.id,
            )
            db.session.add(notif)
    logger.info(f"SLA warnings sent for {len(approaching)} tickets.")

    # ── Mark newly breached tickets ───────────────────────────────────────────
    breached = Ticket.query.filter(
        Ticket.sla_resolution_deadline <= now,
        Ticket.sla_resolution_breached == False,  # noqa: E712
        Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
        Ticket.deleted_at.is_(None),
    ).all()

    for ticket in breached:
        ticket.sla_resolution_breached = True
        if ticket.assignee_id:
            notif = Notification(
                user_id=ticket.assignee_id,
                title="🚨 SLA Breached",
                body=f"Ticket {ticket.ticket_number} has breached its SLA deadline.",
                notification_type=NotificationType.SLA_BREACH.value,
                related_type="ticket",
                related_id=ticket.id,
            )
            db.session.add(notif)

    db.session.commit()
    logger.info(f"SLA breaches marked and notified: {len(breached)} tickets.")

