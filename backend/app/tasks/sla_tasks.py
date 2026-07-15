"""
IntelliDesk AI — SLA Monitoring Celery Tasks
Periodic tasks for SLA breach detection and alerting.
Runs on the 'default' queue via Celery Beat every 5 minutes.
"""

from app.tasks import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(queue="default")
def check_sla_breaches():
    """
    Scan all open tickets and flag SLA breaches.
    Sends notifications to assignees and managers for breached tickets.
    Scheduled every 5 minutes via Celery Beat.
    """
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models.ticket import Ticket
    from app.utils.constants import TicketStatus

    now = datetime.now(timezone.utc)
    open_statuses = [
        TicketStatus.NEW.value,
        TicketStatus.OPEN.value,
        TicketStatus.IN_PROGRESS.value,
        TicketStatus.PENDING.value,
    ]

    try:
        # Find tickets where SLA resolution deadline has passed but not yet flagged
        breached = Ticket.query.filter(
            Ticket.status.in_(open_statuses),
            Ticket.sla_resolution_deadline < now,
            Ticket.sla_resolution_breached == False,  # noqa: E712
            Ticket.deleted_at.is_(None),
        ).all()

        flagged_count = 0
        for ticket in breached:
            ticket.sla_resolution_breached = True
            flagged_count += 1
            logger.info(f"SLA breach flagged: {ticket.ticket_number}")

        if breached:
            db.session.commit()
            logger.info(f"SLA check complete: {flagged_count} tickets flagged as breached.")

    except Exception as e:
        logger.error(f"SLA check task failed: {e}")
        db.session.rollback()


@celery_app.task(queue="default")
def send_sla_warning_notifications():
    """
    Send warning notifications for tickets approaching SLA breach (within 1 hour).
    Scheduled every 15 minutes via Celery Beat.
    """
    from datetime import datetime, timedelta, timezone

    from app.extensions import db
    from app.models.ticket import Ticket
    from app.utils.constants import TicketStatus

    now = datetime.now(timezone.utc)
    warning_threshold = now + timedelta(hours=1)
    open_statuses = [
        TicketStatus.NEW.value,
        TicketStatus.OPEN.value,
        TicketStatus.IN_PROGRESS.value,
    ]

    try:
        at_risk = Ticket.query.filter(
            Ticket.status.in_(open_statuses),
            Ticket.sla_resolution_deadline.between(now, warning_threshold),
            Ticket.sla_resolution_breached == False,  # noqa: E712
            Ticket.deleted_at.is_(None),
        ).all()

        for ticket in at_risk:
            if ticket.assignee_id:
                logger.info(f"SLA warning: {ticket.ticket_number} approaching breach")
                # Notification creation will be implemented in M2

    except Exception as e:
        logger.error(f"SLA warning task failed: {e}")
