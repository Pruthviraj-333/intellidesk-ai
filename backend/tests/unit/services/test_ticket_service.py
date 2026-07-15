"""
IntelliDesk AI — Ticket Service Unit Tests
Tests for TicketService business logic with mocked dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.constants import TicketStatus, UserRole
from app.utils.exceptions import (
    AuthorizationError,
    BusinessLogicError,
    NotFoundError,
    ValidationError,
)


class TestTicketServiceRBAC:
    """Tests for RBAC enforcement in TicketService.update_ticket()"""

    def _make_ticket(self, requester_id=1, assignee_id=None, department_id=1):
        ticket = MagicMock()
        ticket.requester_id = requester_id
        ticket.assignee_id = assignee_id
        ticket.department_id = department_id
        ticket.status = TicketStatus.NEW.value
        ticket.resolution_notes = None
        return ticket

    def test_employee_cannot_update_ticket(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = self._make_ticket()
            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                with pytest.raises(AuthorizationError) as exc_info:
                    TicketService.update_ticket(
                        ticket_id=1,
                        current_user_id=1,
                        current_user_role=UserRole.EMPLOYEE.value,
                        current_user_department_id=1,
                        data={"priority": "high"},
                    )
                assert "Employees" in str(exc_info.value)

    def test_agent_cannot_update_unassigned_ticket(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = self._make_ticket(assignee_id=99)  # different agent
            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                with pytest.raises(AuthorizationError) as exc_info:
                    TicketService.update_ticket(
                        ticket_id=1,
                        current_user_id=5,  # different from assignee_id=99
                        current_user_role=UserRole.AGENT.value,
                        current_user_department_id=1,
                        data={"status": "open"},
                    )
                assert "Agents" in str(exc_info.value)

    def test_manager_cannot_update_other_department_ticket(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = self._make_ticket(department_id=10)
            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                with pytest.raises(AuthorizationError) as exc_info:
                    TicketService.update_ticket(
                        ticket_id=1,
                        current_user_id=3,
                        current_user_role=UserRole.MANAGER.value,
                        current_user_department_id=1,  # Different department
                        data={"status": "open"},
                    )
                assert "department" in str(exc_info.value).lower()


class TestTicketStatusTransitions:
    """Tests for valid/invalid status transition enforcement."""

    def _make_admin_update(self, app, current_status, new_status, extra_data=None):
        from app.services.ticket_service import TicketService

        mock_ticket = MagicMock()
        mock_ticket.status = current_status
        mock_ticket.assignee_id = 1
        mock_ticket.department_id = 1
        mock_ticket.resolution_notes = None

        data = {"status": new_status}
        if extra_data:
            data.update(extra_data)

        with (
            patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ),
            patch("app.services.ticket_service.TicketRepository.update", return_value=mock_ticket),
            patch("app.services.ticket_service.NotificationRepository.create"),
            patch("app.services.ticket_service.AuditService.log"),
        ):
            return TicketService.update_ticket(
                ticket_id=1,
                current_user_id=1,
                current_user_role=UserRole.ADMIN.value,
                current_user_department_id=1,
                data=data,
            )

    def test_valid_transition_new_to_open(self, app):
        with app.app_context():
            result = self._make_admin_update(app, TicketStatus.NEW.value, TicketStatus.OPEN.value)
            assert result is not None

    def test_invalid_transition_new_to_closed_raises(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            with pytest.raises(BusinessLogicError) as exc_info:
                self._make_admin_update(app, TicketStatus.NEW.value, TicketStatus.CLOSED.value)
            assert "Cannot transition" in str(exc_info.value)

    def test_resolve_without_notes_raises(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = MagicMock()
            mock_ticket.status = TicketStatus.IN_PROGRESS.value
            mock_ticket.assignee_id = 1
            mock_ticket.department_id = 1
            mock_ticket.resolution_notes = None  # No notes

            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                with pytest.raises(ValidationError) as exc_info:
                    from app.services.ticket_service import TicketService

                    TicketService.update_ticket(
                        ticket_id=1,
                        current_user_id=1,
                        current_user_role=UserRole.ADMIN.value,
                        current_user_department_id=1,
                        data={"status": TicketStatus.RESOLVED.value},
                    )
                assert "resolution notes" in str(exc_info.value).lower()


class TestTicketServiceGetTicket:
    """Tests for TicketService.get_ticket() visibility."""

    def test_employee_cannot_see_other_user_ticket(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = MagicMock()
            mock_ticket.requester_id = 99  # Different user
            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                with pytest.raises(NotFoundError):
                    TicketService.get_ticket(
                        ticket_id=1,
                        current_user_id=5,  # Not the requester
                        current_user_role=UserRole.EMPLOYEE.value,
                    )

    def test_agent_can_see_any_ticket(self, app):
        with app.app_context():
            from app.services.ticket_service import TicketService

            mock_ticket = MagicMock()
            mock_ticket.requester_id = 99
            with patch(
                "app.services.ticket_service.TicketRepository.get_by_id", return_value=mock_ticket
            ):
                result = TicketService.get_ticket(
                    ticket_id=1,
                    current_user_id=5,
                    current_user_role=UserRole.AGENT.value,
                )
                assert result is not None
