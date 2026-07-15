"""
IntelliDesk AI — Incident, Problem & Notification Repositories
Data access for ITIL incident/problem management entities.
"""

from typing import Optional

from app.extensions import db
from app.models.incident import (
    Incident,
    IncidentTimeline,
    Notification,
    Problem,
    incident_tickets,
    problem_incidents,
)
from app.utils.helpers import generate_incident_number, generate_problem_number


class IncidentRepository:
    """Repository for Incident entity."""

    @staticmethod
    def get_by_id(incident_id: int) -> Optional[Incident]:
        return Incident.query.filter_by(id=incident_id, deleted_at=None).first()

    @staticmethod
    def get_by_number(incident_number: str) -> Optional[Incident]:
        return Incident.query.filter_by(incident_number=incident_number, deleted_at=None).first()

    @staticmethod
    def create(
        title: str,
        description: str,
        severity: str,
        reporter_id: int,
        impact: Optional[str] = None,
        affected_services: Optional[str] = None,
        department_id: Optional[int] = None,
        linked_ticket_ids: Optional[list[int]] = None,
    ) -> Incident:
        for _ in range(5):
            inc_number = generate_incident_number()
            if not Incident.query.filter_by(incident_number=inc_number).first():
                break

        incident = Incident(
            incident_number=inc_number,
            title=title.strip(),
            description=description.strip(),
            severity=severity,
            impact=impact,
            affected_services=affected_services,
            reporter_id=reporter_id,
            department_id=department_id,
        )
        db.session.add(incident)
        db.session.flush()  # Get ID before linking tickets

        if linked_ticket_ids:
            from app.models.ticket import Ticket

            tickets = Ticket.query.filter(Ticket.id.in_(linked_ticket_ids)).all()
            incident.linked_tickets.extend(tickets)

        db.session.commit()
        return incident

    @staticmethod
    def update(incident: Incident, data: dict) -> Incident:
        from datetime import datetime, timezone

        allowed = {
            "title",
            "description",
            "severity",
            "status",
            "impact",
            "affected_services",
            "assignee_id",
            "department_id",
            "problem_id",
            "resolution_notes",
        }
        for key, value in data.items():
            if key in allowed:
                setattr(incident, key, value)

        if data.get("status") in ("resolved", "closed") and not incident.resolved_at:
            incident.resolved_at = datetime.now(timezone.utc)

        db.session.commit()
        return incident

    @staticmethod
    def add_timeline_entry(
        incident: Incident,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> IncidentTimeline:
        entry = IncidentTimeline(
            incident_id=incident.id,
            user_id=user_id,
            event_type=event_type,
            description=description,
            event_metadata=metadata or {},
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def list_with_filters(
        status: Optional[str] = None,
        severity: Optional[str] = None,
        department_id: Optional[int] = None,
        from_date=None,
        to_date=None,
        page: int = 1,
        per_page: int = 20,
    ):
        query = Incident.query.filter_by(deleted_at=None).order_by(Incident.created_at.desc())
        if status:
            query = query.filter(Incident.status == status)
        if severity:
            query = query.filter(Incident.severity == severity)
        if department_id:
            query = query.filter(Incident.department_id == department_id)
        if from_date:
            query = query.filter(Incident.created_at >= from_date)
        if to_date:
            query = query.filter(Incident.created_at <= to_date)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def soft_delete(incident: Incident) -> None:
        incident.soft_delete()


class ProblemRepository:
    """Repository for Problem entity."""

    @staticmethod
    def get_by_id(problem_id: int) -> Optional[Problem]:
        return Problem.query.filter_by(id=problem_id, deleted_at=None).first()

    @staticmethod
    def create(
        title: str,
        description: str,
        linked_incident_ids: Optional[list[int]] = None,
        owner_id: Optional[int] = None,
    ) -> Problem:
        for _ in range(5):
            prb_number = generate_problem_number()
            if not Problem.query.filter_by(problem_number=prb_number).first():
                break

        problem = Problem(
            problem_number=prb_number,
            title=title.strip(),
            description=description.strip(),
            owner_id=owner_id,
        )
        db.session.add(problem)
        db.session.flush()

        if linked_incident_ids:
            incidents = Incident.query.filter(Incident.id.in_(linked_incident_ids)).all()
            problem.linked_incidents.extend(incidents)

        db.session.commit()
        return problem

    @staticmethod
    def update(problem: Problem, data: dict) -> Problem:
        allowed = {
            "title",
            "description",
            "status",
            "root_cause",
            "workaround",
            "resolution",
            "owner_id",
        }
        for key, value in data.items():
            if key in allowed:
                setattr(problem, key, value)
        db.session.commit()
        return problem

    @staticmethod
    def list_with_filters(
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ):
        query = Problem.query.filter_by(deleted_at=None).order_by(Problem.created_at.desc())
        if status:
            query = query.filter(Problem.status == status)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def soft_delete(problem: Problem) -> None:
        problem.soft_delete()


class NotificationRepository:
    """Repository for Notification entity."""

    @staticmethod
    def create(
        user_id: int,
        type: str,
        title: str,
        body: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        db.session.add(notif)
        db.session.commit()
        return notif

    @staticmethod
    def list_for_user(
        user_id: int,
        is_read: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20,
    ):
        query = Notification.query.filter_by(user_id=user_id).order_by(
            Notification.created_at.desc()
        )
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def mark_read(notification: Notification) -> None:
        notification.mark_read()

    @staticmethod
    def mark_all_read(user_id: int) -> int:
        from datetime import datetime, timezone

        count = Notification.query.filter_by(user_id=user_id, is_read=False).update(
            {"is_read": True, "read_at": datetime.now(timezone.utc)},
            synchronize_session="fetch",
        )
        db.session.commit()
        return count

    @staticmethod
    def get_unread_count(user_id: int) -> int:
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
