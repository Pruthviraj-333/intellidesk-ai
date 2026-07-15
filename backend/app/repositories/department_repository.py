"""
IntelliDesk AI — Department & AuditLog Repositories
Data access layer for organizational and audit entities.
"""

from typing import Optional

from flask import request

from app.extensions import db
from app.models.department import AuditLog, Department, Setting


class DepartmentRepository:
    """Repository for Department entity data access."""

    @staticmethod
    def get_by_id(dept_id: int) -> Optional[Department]:
        return Department.query.filter_by(id=dept_id, deleted_at=None).first()

    @staticmethod
    def get_by_name(name: str) -> Optional[Department]:
        return Department.query.filter_by(name=name, deleted_at=None).first()

    @staticmethod
    def get_all_active() -> list[Department]:
        return Department.query.filter_by(deleted_at=None, is_active=True).all()

    @staticmethod
    def list_with_filters(
        is_active: Optional[bool] = None,
        sort_by: str = "name",
        order: str = "asc",
        page: int = 1,
        per_page: int = 20,
    ):
        query = Department.query.filter_by(deleted_at=None)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        sort_column = getattr(Department, sort_by, Department.name)
        query = query.order_by(sort_column.asc() if order == "asc" else sort_column.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def create(
        name: str, description: Optional[str] = None, manager_id: Optional[int] = None
    ) -> Department:
        dept = Department(name=name, description=description, manager_id=manager_id)
        db.session.add(dept)
        db.session.commit()
        return dept

    @staticmethod
    def update(dept: Department, data: dict) -> Department:
        allowed = {"name", "description", "manager_id", "sla_config", "is_active"}
        for key, value in data.items():
            if key in allowed:
                setattr(dept, key, value)
        db.session.commit()
        return dept

    @staticmethod
    def soft_delete(dept: Department) -> None:
        dept.soft_delete()


class AuditLogRepository:
    """Repository for immutable AuditLog entries."""

    @staticmethod
    def create(
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
    ) -> AuditLog:
        """Create and persist an audit log entry. Never raises — audit must not break requests."""
        try:
            ip_address = None
            user_agent = None
            try:
                ip_address = request.remote_addr
                user_agent = request.user_agent.string[:500] if request.user_agent else None
            except RuntimeError:
                pass  # Outside request context (e.g., Celery task)

            log = AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception:
            db.session.rollback()
            return None  # Audit failure must never break the request

    @staticmethod
    def list_with_filters(
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        from_date=None,
        to_date=None,
        page: int = 1,
        per_page: int = 50,
    ):
        query = AuditLog.query.order_by(AuditLog.created_at.desc())
        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)
        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)
        return query.paginate(page=page, per_page=per_page, error_out=False)


class SettingRepository:
    """Repository for system Setting key-value pairs."""

    @staticmethod
    def get(key: str) -> Optional[Setting]:
        return Setting.query.filter_by(key=key).first()

    @staticmethod
    def get_value(key: str, default=None):
        setting = Setting.query.filter_by(key=key).first()
        if setting is None:
            return default
        return setting.typed_value

    @staticmethod
    def set_value(
        key: str,
        value,
        value_type: str = "string",
        description: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        setting = Setting.query.filter_by(key=key).first()
        str_value = str(value) if value is not None else None

        if setting:
            setting.value = str_value
            setting.updated_by = user_id
        else:
            setting = Setting(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description,
                updated_by=user_id,
            )
            db.session.add(setting)

        db.session.commit()
        return setting

    @staticmethod
    def get_all() -> list[Setting]:
        return Setting.query.order_by(Setting.key).all()
