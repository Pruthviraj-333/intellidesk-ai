"""
IntelliDesk AI — Flask CLI Commands
Custom management commands for database seeding, maintenance, and development.
"""

import click
from flask import Flask


def register_commands(app: Flask) -> None:
    """Register all CLI commands with the Flask app."""

    @app.cli.command("seed-db")
    def seed_db():
        """Seed the database with initial roles, admin user, and demo data."""
        click.echo("Seeding database...")
        _seed_roles()
        _seed_departments()
        _seed_admin_user()
        _seed_demo_users()
        _seed_settings()
        click.echo("✅ Database seeded successfully.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--first-name", prompt=True)
    @click.option("--last-name", prompt=True)
    def create_admin(email, password, first_name, last_name):
        """Create a Super Admin user interactively."""
        from app.extensions import db
        from app.models.user import Role, User
        from app.utils.constants import UserRole, UserStatus

        role = Role.query.filter_by(name=UserRole.SUPER_ADMIN.value).first()
        if not role:
            click.echo("❌ Roles not seeded. Run 'flask seed-db' first.")
            return

        if User.query.filter_by(email=email.lower()).first():
            click.echo(f"❌ User with email '{email}' already exists.")
            return

        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            status=UserStatus.ACTIVE.value,
            email_verified_at=__import__("datetime").datetime.utcnow(),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"✅ Super Admin created: {email}")

    @app.cli.command("drop-db")
    @click.confirmation_option(prompt="Are you sure you want to drop all tables?")
    def drop_db():
        """Drop all database tables (development only)."""
        from app.extensions import db

        db.drop_all()
        click.echo("⚠️  All tables dropped.")


def _seed_roles():
    """Create the 5 default roles if they don't exist."""
    from app.extensions import db
    from app.models.user import Role
    from app.utils.constants import UserRole

    roles = [
        {
            "name": UserRole.SUPER_ADMIN.value,
            "description": "Full platform access. System configuration, monitoring, and all operations.",
        },
        {
            "name": UserRole.ADMIN.value,
            "description": "Organization admin. User management, settings, reports, all tickets.",
        },
        {
            "name": UserRole.MANAGER.value,
            "description": "Team lead. Department tickets, assignments, escalations, performance.",
        },
        {
            "name": UserRole.AGENT.value,
            "description": "IT support staff. Ticket resolution, knowledge base, AI assistant.",
        },
        {
            "name": UserRole.EMPLOYEE.value,
            "description": "End user. Submit tickets, track status, search knowledge base.",
        },
    ]

    for role_data in roles:
        if not Role.query.filter_by(name=role_data["name"]).first():
            role = Role(**role_data)
            db.session.add(role)
            click.echo(f"  Created role: {role_data['name']}")

    db.session.commit()


def _seed_departments():
    """Create default IT departments."""
    from app.extensions import db
    from app.models.department import Department

    departments = [
        {"name": "IT Support", "description": "General IT helpdesk and user support."},
        {"name": "Infrastructure", "description": "Servers, networking, cloud, and DevOps."},
        {"name": "Security", "description": "Information security and compliance."},
        {"name": "Software Development", "description": "Application development and maintenance."},
        {"name": "Database Administration", "description": "Database management and optimization."},
    ]

    for dept_data in departments:
        if not Department.query.filter_by(name=dept_data["name"]).first():
            dept = Department(**dept_data)
            db.session.add(dept)
            click.echo(f"  Created department: {dept_data['name']}")

    db.session.commit()


def _seed_admin_user():
    """Create the default Super Admin user."""
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models.user import Role, User
    from app.utils.constants import UserRole, UserStatus

    email = "admin@intellidesk.ai"
    if User.query.filter_by(email=email).first():
        return

    role = Role.query.filter_by(name=UserRole.SUPER_ADMIN.value).first()
    user = User(
        email=email,
        first_name="System",
        last_name="Admin",
        role_id=role.id,
        status=UserStatus.ACTIVE.value,
        email_verified_at=datetime.now(timezone.utc),
    )
    user.set_password("Admin@123!")
    db.session.add(user)
    db.session.commit()
    click.echo(f"  Created Super Admin: {email} / Admin@123!")


def _seed_demo_users():
    """Create demo users for each role."""
    from datetime import datetime, timezone

    from app.extensions import db
    from app.models.department import Department
    from app.models.user import Role, User
    from app.utils.constants import UserStatus

    demo_users = [
        {
            "email": "manager@intellidesk.ai",
            "first_name": "Alice",
            "last_name": "Manager",
            "role": "manager",
            "password": "Manager@123!",
            "dept": "IT Support",
        },
        {
            "email": "agent@intellidesk.ai",
            "first_name": "Bob",
            "last_name": "Agent",
            "role": "agent",
            "password": "Agent@123!",
            "dept": "IT Support",
        },
        {
            "email": "employee@intellidesk.ai",
            "first_name": "Charlie",
            "last_name": "Employee",
            "role": "employee",
            "password": "Employee@123!",
            "dept": None,
        },
    ]

    for u_data in demo_users:
        if User.query.filter_by(email=u_data["email"]).first():
            continue
        role = Role.query.filter_by(name=u_data["role"]).first()
        dept_id = None
        if u_data["dept"]:
            dept = Department.query.filter_by(name=u_data["dept"]).first()
            dept_id = dept.id if dept else None

        user = User(
            email=u_data["email"],
            first_name=u_data["first_name"],
            last_name=u_data["last_name"],
            role_id=role.id,
            department_id=dept_id,
            status=UserStatus.ACTIVE.value,
            email_verified_at=datetime.now(timezone.utc),
        )
        user.set_password(u_data["password"])
        db.session.add(user)
        click.echo(f"  Created demo user: {u_data['email']} / {u_data['password']}")

    db.session.commit()


def _seed_settings():
    """Seed default system settings."""
    from app.extensions import db
    from app.models.department import Setting

    defaults = [
        ("org_name", "IntelliDesk AI Demo", "string", "Organization display name"),
        ("timezone", "UTC", "string", "Default platform timezone"),
        (
            "sla_critical_response_minutes",
            "15",
            "int",
            "SLA response time for Critical tickets (minutes)",
        ),
        (
            "sla_critical_resolution_hours",
            "4",
            "int",
            "SLA resolution time for Critical tickets (hours)",
        ),
        ("sla_high_response_hours", "1", "int", "SLA response time for High tickets (hours)"),
        ("sla_high_resolution_hours", "8", "int", "SLA resolution time for High tickets (hours)"),
        ("sla_medium_response_hours", "4", "int", "SLA response time for Medium tickets (hours)"),
        (
            "sla_medium_resolution_hours",
            "24",
            "int",
            "SLA resolution time for Medium tickets (hours)",
        ),
        ("sla_low_response_hours", "8", "int", "SLA response time for Low tickets (hours)"),
        ("sla_low_resolution_hours", "72", "int", "SLA resolution time for Low tickets (hours)"),
        ("ai_model", "llama-3.3-70b-versatile", "string", "Active Groq model name"),
        ("email_notifications_enabled", "true", "bool", "Enable email notifications"),
        ("max_upload_size_mb", "25", "int", "Maximum file upload size in MB"),
    ]

    for key, value, vtype, desc in defaults:
        if not Setting.query.filter_by(key=key).first():
            setting = Setting(key=key, value=value, value_type=vtype, description=desc)
            db.session.add(setting)

    db.session.commit()
    click.echo("  Settings seeded.")
