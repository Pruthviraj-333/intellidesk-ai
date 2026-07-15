"""
IntelliDesk AI — Ticket Service
Business logic for the complete ticket lifecycle.
"""

from typing import Optional

from app.models.ticket import Ticket
from app.repositories.incident_repository import NotificationRepository
from app.repositories.ticket_repository import CommentRepository, TicketRepository
from app.services.audit_service import AuditService
from app.utils.constants import (
    VALID_TICKET_TRANSITIONS,
    AuditAction,
    NotificationType,
    TicketPriority,
    TicketStatus,
    UserRole,
)
from app.utils.exceptions import (
    AuthorizationError,
    BusinessLogicError,
    NotFoundError,
    ValidationError,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TicketService:
    """Service handling all ticket lifecycle business logic."""

    @staticmethod
    def create_ticket(
        title: str,
        description: str,
        requester_id: int,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        department_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> Ticket:
        """
        Create a new ticket. SLA deadlines auto-calculated from priority.
        Queues AI classification task if Groq is configured.
        """
        ticket = TicketRepository.create(
            title=title,
            description=description,
            requester_id=requester_id,
            priority=priority,
            category=category,
            department_id=department_id,
            project_id=project_id,
        )
        logger.info(f"Ticket created: {ticket.ticket_number} by user={requester_id}")

        AuditService.log(
            action=AuditAction.TICKET_CREATED.value,
            resource_type="ticket",
            resource_id=ticket.id,
            user_id=requester_id,
            new_values={
                "ticket_number": ticket.ticket_number,
                "title": ticket.title,
                "priority": ticket.priority,
            },
        )

        # Queue AI classification in background (M4 will implement the task)
        # classify_ticket_task.delay(ticket.id)

        return ticket

    @staticmethod
    def update_ticket(
        ticket_id: int,
        current_user_id: int,
        current_user_role: str,
        current_user_department_id: Optional[int],
        data: dict,
    ) -> Ticket:
        """
        Update ticket fields with RBAC enforcement and status transition validation.

        Authorization rules:
        - Employee: cannot update tickets (read-only)
        - Agent: can update own assigned tickets only
        - Manager: can update tickets in their department
        - Admin / Super Admin: can update any ticket
        """
        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        # RBAC check
        role = current_user_role
        if role == UserRole.EMPLOYEE.value:
            raise AuthorizationError("Employees cannot update tickets directly.")
        if role == UserRole.AGENT.value and ticket.assignee_id != current_user_id:
            raise AuthorizationError("Agents can only update tickets assigned to them.")
        if role == UserRole.MANAGER.value:
            if (
                ticket.department_id is not None
                and ticket.department_id != current_user_department_id
            ):
                raise AuthorizationError("Managers can only update tickets in their department.")

        # Validate status transition
        if "status" in data:
            new_status = data["status"]
            current_status = TicketStatus(ticket.status)
            try:
                new_status_enum = TicketStatus(new_status)
            except ValueError:
                raise ValidationError(f"Invalid ticket status: '{new_status}'.")

            allowed = VALID_TICKET_TRANSITIONS.get(current_status, set())
            if new_status_enum not in allowed:
                raise BusinessLogicError(
                    f"Cannot transition ticket from '{ticket.status}' to '{new_status}'. "
                    f"Allowed transitions: {[s.value for s in allowed]}."
                )

            # Resolution notes required when resolving
            if new_status == TicketStatus.RESOLVED.value:
                resolution_notes = data.get("resolution_notes") or ticket.resolution_notes
                if not resolution_notes:
                    raise ValidationError("Resolution notes are required when resolving a ticket.")

        old_values = {k: getattr(ticket, k) for k in data if hasattr(ticket, k)}
        updated_ticket = TicketRepository.update(ticket, data)

        # Notify assignee if ticket was just assigned
        if "assignee_id" in data and data["assignee_id"] != old_values.get("assignee_id"):
            if data["assignee_id"]:
                NotificationRepository.create(
                    user_id=data["assignee_id"],
                    type=NotificationType.TICKET_ASSIGNED.value,
                    title=f"Ticket assigned to you: {ticket.ticket_number}",
                    body=ticket.title,
                    resource_type="ticket",
                    resource_id=ticket.id,
                )

        AuditService.log(
            action=AuditAction.TICKET_UPDATED.value,
            resource_type="ticket",
            resource_id=ticket.id,
            user_id=current_user_id,
            old_values=old_values,
            new_values=data,
        )
        return updated_ticket

    @staticmethod
    def get_ticket(
        ticket_id: int,
        current_user_id: int,
        current_user_role: str,
    ) -> Ticket:
        """
        Fetch ticket with RBAC. Employees can only see their own tickets.
        """
        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        if current_user_role == UserRole.EMPLOYEE.value and ticket.requester_id != current_user_id:
            raise NotFoundError(
                "Ticket", ticket_id
            )  # Not Found (not Forbidden) to prevent enumeration

        return ticket

    @staticmethod
    def add_comment(
        ticket_id: int,
        author_id: int,
        author_role: str,
        body: str,
        is_internal: bool = False,
    ):
        """Add a comment. Internal notes restricted to Agent+."""
        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        if is_internal and author_role == UserRole.EMPLOYEE.value:
            raise AuthorizationError("Employees cannot post internal notes.")

        comment = CommentRepository.create(
            ticket_id=ticket_id,
            author_id=author_id,
            body=body,
            is_internal=is_internal,
        )

        # Notify requester of new public reply
        if not is_internal and ticket.requester_id != author_id:
            NotificationRepository.create(
                user_id=ticket.requester_id,
                type=NotificationType.TICKET_COMMENT.value,
                title=f"New reply on your ticket: {ticket.ticket_number}",
                body=body[:200],
                resource_type="ticket",
                resource_id=ticket_id,
            )

        AuditService.log(
            action=AuditAction.COMMENT_ADDED.value,
            resource_type="ticket",
            resource_id=ticket_id,
            user_id=author_id,
        )
        return comment

    @staticmethod
    def delete_ticket(ticket_id: int, current_user_id: int) -> None:
        """Soft delete a ticket."""
        ticket = TicketRepository.get_by_id(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket", ticket_id)

        AuditService.log(
            action=AuditAction.TICKET_DELETED.value,
            resource_type="ticket",
            resource_id=ticket_id,
            user_id=current_user_id,
            old_values={"ticket_number": ticket.ticket_number, "title": ticket.title},
        )
        TicketRepository.soft_delete(ticket)
