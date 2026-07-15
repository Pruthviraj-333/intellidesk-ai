"""
IntelliDesk AI — Pytest Configuration & Fixtures
Shared test fixtures for the entire test suite.
"""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.department import Department, Setting
from app.models.user import Role, User
from app.utils.constants import UserRole, UserStatus


@pytest.fixture(scope="session")
def app():
    """Create test Flask application with in-memory SQLite database."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        _seed_test_data()
        yield app
        _db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Database session with rollback after each test."""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        yield _db
        transaction.rollback()
        connection.close()


def _seed_test_data():
    """Seed minimal test data: roles and one user per role."""
    from datetime import datetime, timezone

    roles_data = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("agent", "Agent"),
        ("employee", "Employee"),
    ]
    roles = {}
    for name, desc in roles_data:
        role = Role(name=name, description=desc)
        _db.session.add(role)
        _db.session.flush()
        roles[name] = role

    dept = Department(name="IT Support", description="Test department")
    _db.session.add(dept)
    _db.session.flush()

    users_data = [
        ("super@test.com", "Super", "Admin", "super_admin"),
        ("admin@test.com", "Test", "Admin", "admin"),
        ("manager@test.com", "Test", "Manager", "manager"),
        ("agent@test.com", "Test", "Agent", "agent"),
        ("employee@test.com", "Test", "Employee", "employee"),
    ]
    for email, first, last, role_name in users_data:
        user = User(
            email=email,
            first_name=first,
            last_name=last,
            role_id=roles[role_name].id,
            department_id=dept.id if role_name in ("agent", "manager") else None,
            status=UserStatus.ACTIVE.value,
            email_verified_at=datetime.now(timezone.utc),
        )
        user.set_password("Test@12345!")
        _db.session.add(user)

    _db.session.commit()


# ─── Auth Header Helpers ───────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def auth_headers_employee(client):
    """JWT auth headers for employee user."""
    return _get_auth_headers(client, "employee@test.com", "Test@12345!")


@pytest.fixture(scope="session")
def auth_headers_agent(client):
    return _get_auth_headers(client, "agent@test.com", "Test@12345!")


@pytest.fixture(scope="session")
def auth_headers_manager(client):
    return _get_auth_headers(client, "manager@test.com", "Test@12345!")


@pytest.fixture(scope="session")
def auth_headers_admin(client):
    return _get_auth_headers(client, "admin@test.com", "Test@12345!")


@pytest.fixture(scope="session")
def auth_headers_super_admin(client):
    return _get_auth_headers(client, "super@test.com", "Test@12345!")


def _get_auth_headers(client, email: str, password: str) -> dict:
    """Helper to login and return authorization headers."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.get_json()}"
    token = resp.get_json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
