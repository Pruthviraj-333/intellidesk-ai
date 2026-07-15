"""
IntelliDesk AI — Ticket Repository
Data access layer for Ticket, Comment, and Attachment entities.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, or_

from app.extensions import db
from app.models.ticket import Attachment, Comment, Ticket
from app.utils.constants import SLA_DEFAULTS, TicketPriority, TicketStatus
from app.utils.helpers import generate_ticket_number


class TicketRepository:
    """Repository for Ticket entity — all DB operations."""

    @staticmethod
    def get_by_id(ticket_id: int) -> Optional[Ticket]:
        return Ticket.query.filter_by(id=ticket_id, deleted_at=None).first()

    @staticmethod
    def get_by_number(ticket_number: str) -> Optional[Ticket]:
        return Ticket.query.filter_by(ticket_number=ticket_number, deleted_at=None).first()

    @staticmethod
    def create(
        title: str,
        description: str,
        requester_id: int,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        department_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> Ticket:
        """
        Create a ticket with a unique ticket number and auto-calculated SLA deadlines.
        Retries ticket number generation on collision (extremely rare).
        """
        # Generate unique ticket number (retry on collision)
        max_attempts = 5
        for _ in range(max_attempts):
            ticket_number = generate_ticket_number()
            if not Ticket.query.filter_by(ticket_number=ticket_number).first():
                break

        # Calculate SLA deadlines
        now = datetime.now(timezone.utc)
        sla_response_deadline = None
        sla_resolution_deadline = None

        if priority and priority in SLA_DEFAULTS:
            sla_config = SLA_DEFAULTS[priority]
            sla_response_deadline = now + timedelta(hours=sla_config["response"])
            sla_resolution_deadline = now + timedelta(hours=sla_config["resolution"])

        ticket = Ticket(
            ticket_number=ticket_number,
            title=title.strip(),
            description=description.strip(),
            requester_id=requester_id,
            status=TicketStatus.NEW.value,
            priority=priority,
            category=category,
            department_id=department_id,
            project_id=project_id,
            sla_response_deadline=sla_response_deadline,
            sla_resolution_deadline=sla_resolution_deadline,
        )
        db.session.add(ticket)
        db.session.commit()
        return ticket

    @staticmethod
    def update(ticket: Ticket, data: dict) -> Ticket:
        """Update allowed ticket fields. Handles resolved_at / closed_at timestamps."""
        allowed_fields = {
            "title",
            "description",
            "status",
            "priority",
            "category",
            "assignee_id",
            "department_id",
            "project_id",
            "resolution_notes",
            "sla_response_breached",
            "sla_resolution_breached",
            "ai_confidence",
            "ai_category_suggestion",
            "ai_priority_suggestion",
            "ai_metadata",
        }
        now = datetime.now(timezone.utc)
        for key, value in data.items():
            if key in allowed_fields:
                setattr(ticket, key, value)

        # Auto-set timestamp fields based on status transition
        new_status = data.get("status")
        if new_status == TicketStatus.RESOLVED.value and not ticket.resolved_at:
            ticket.resolved_at = now
        if new_status == TicketStatus.CLOSED.value and not ticket.closed_at:
            ticket.closed_at = now
        if new_status == TicketStatus.IN_PROGRESS.value and not ticket.first_responded_at:
            ticket.first_responded_at = now

        # Recalculate SLA if priority changed
        if "priority" in data and data["priority"] in SLA_DEFAULTS:
            sla_config = SLA_DEFAULTS[data["priority"]]
            if not ticket.sla_response_deadline:
                ticket.sla_response_deadline = now + timedelta(hours=sla_config["response"])
            if not ticket.sla_resolution_deadline:
                ticket.sla_resolution_deadline = now + timedelta(hours=sla_config["resolution"])

        db.session.commit()
        return ticket

    @staticmethod
    def update_ai_metadata(
        ticket: Ticket,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        department_id: Optional[int] = None,
        confidence: float = 0.0,
        metadata: Optional[dict] = None,
    ) -> Ticket:
        """Update AI suggestion fields after classification."""
        if category:
            ticket.ai_category_suggestion = category
        if priority:
            ticket.ai_priority_suggestion = priority
        if department_id:
            ticket.ai_department_suggestion = department_id
        ticket.ai_confidence = confidence
        if metadata:
            ticket.ai_metadata = metadata
        db.session.commit()
        return ticket

    @staticmethod
    def soft_delete(ticket: Ticket) -> None:
        ticket.soft_delete()

    @staticmethod
    def list_with_filters(
        requester_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        sla_breached: Optional[bool] = None,
        from_date=None,
        to_date=None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ):
        query = Ticket.query.filter_by(deleted_at=None)

        if requester_id:
            query = query.filter(Ticket.requester_id == requester_id)
        if assignee_id:
            query = query.filter(Ticket.assignee_id == assignee_id)
        if department_id:
            query = query.filter(Ticket.department_id == department_id)
        if status:
            query = query.filter(Ticket.status == status)
        if priority:
            query = query.filter(Ticket.priority == priority)
        if category:
            query = query.filter(Ticket.category == category)
        if sla_breached is not None:
            query = query.filter(Ticket.sla_resolution_breached == sla_breached)
        if from_date:
            query = query.filter(Ticket.created_at >= from_date)
        if to_date:
            query = query.filter(Ticket.created_at <= to_date)
        if search:
            term = f"%{search}%"
            from sqlalchemy.orm import aliased

            from app.models.user import User

            RequesterUser = aliased(User)
            AssigneeUser = aliased(User)

            query = query.outerjoin(RequesterUser, Ticket.requester_id == RequesterUser.id)
            query = query.outerjoin(AssigneeUser, Ticket.assignee_id == AssigneeUser.id)

            query = query.filter(
                or_(
                    Ticket.title.ilike(term),
                    Ticket.description.ilike(term),
                    Ticket.ticket_number.ilike(term),
                    RequesterUser.first_name.ilike(term),
                    RequesterUser.last_name.ilike(term),
                    RequesterUser.email.ilike(term),
                    AssigneeUser.first_name.ilike(term),
                    AssigneeUser.last_name.ilike(term),
                    AssigneeUser.email.ilike(term),
                )
            )

        sort_col = getattr(Ticket, sort_by, Ticket.created_at)
        query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def bulk_update(ticket_ids: list[int], updates: dict) -> int:
        """Update multiple tickets at once. Returns count updated."""
        allowed = {"status", "assignee_id", "priority", "department_id"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed}
        if not safe_updates:
            return 0
        count = Ticket.query.filter(Ticket.id.in_(ticket_ids), Ticket.deleted_at.is_(None)).update(
            safe_updates, synchronize_session="fetch"
        )
        db.session.commit()
        return count

    @staticmethod
    def get_dashboard_stats(department_id: Optional[int] = None) -> dict:
        """Aggregate ticket statistics for dashboard KPIs."""
        from datetime import date

        from sqlalchemy import func

        base = Ticket.query.filter_by(deleted_at=None)
        if department_id:
            base = base.filter(Ticket.department_id == department_id)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "open_tickets": base.filter(
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value])
            ).count(),
            "resolved_today": base.filter(Ticket.resolved_at >= today_start).count(),
            "overdue_tickets": base.filter(
                Ticket.sla_resolution_breached == True,  # noqa: E712
                Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
            ).count(),
            "by_status": dict(
                db.session.query(Ticket.status, func.count(Ticket.id))
                .filter(Ticket.deleted_at.is_(None))
                .group_by(Ticket.status)
                .all()
            ),
            "by_priority": dict(
                db.session.query(Ticket.priority, func.count(Ticket.id))
                .filter(Ticket.deleted_at.is_(None))
                .group_by(Ticket.priority)
                .all()
            ),
        }


class CommentRepository:
    """Repository for Comment entity."""

    @staticmethod
    def get_by_id(comment_id: int) -> Optional[Comment]:
        return Comment.query.filter_by(id=comment_id, deleted_at=None).first()

    @staticmethod
    def create(
        ticket_id: int,
        author_id: int,
        body: str,
        is_internal: bool = False,
    ) -> Comment:
        comment = Comment(
            ticket_id=ticket_id,
            author_id=author_id,
            body=body.strip(),
            is_internal=is_internal,
        )
        db.session.add(comment)
        # Update denormalized counter
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket.comment_count += 1
        db.session.commit()
        return comment

    @staticmethod
    def list_for_ticket(ticket_id: int, include_internal: bool = True) -> list[Comment]:
        query = Comment.query.filter_by(ticket_id=ticket_id, deleted_at=None)
        if not include_internal:
            query = query.filter_by(is_internal=False)
        return query.order_by(Comment.created_at.asc()).all()

    @staticmethod
    def soft_delete(comment: Comment) -> None:
        comment.soft_delete()


class AttachmentRepository:
    """Repository for Attachment entity."""

    @staticmethod
    def create(
        uploader_id: int,
        file_url: str,
        file_name: str,
        file_size: int,
        file_type: str,
        ticket_id: Optional[int] = None,
        comment_id: Optional[int] = None,
    ) -> Attachment:
        attachment = Attachment(
            ticket_id=ticket_id,
            comment_id=comment_id,
            uploader_id=uploader_id,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
        )
        db.session.add(attachment)
        db.session.commit()
        return attachment

    @staticmethod
    def list_for_ticket(ticket_id: int) -> list[Attachment]:
        return Attachment.query.filter_by(ticket_id=ticket_id).all()
