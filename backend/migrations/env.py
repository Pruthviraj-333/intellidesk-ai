"""
Alembic Migration Environment
Configured to use IntelliDesk AI's SQLAlchemy models for autogenerate support.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import the Flask app to access database config
import sys
import os

# Allow importing from the backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db

# Import all models so Alembic can detect them for autogenerate
from app.models import (
    User, Role, UserToken,
    Department, Setting, AuditLog,
    Ticket, Comment, Attachment,
    Incident, IncidentTimeline, Problem, Project,
    Notification,
    KnowledgeArticle, ArticleCategory, ArticleTag, ArticleVote,
    Document, DocumentChunk,
    AISession, AIMessage, AIClassification,
    DailyMetricSnapshot, AgentDailyMetric,
)  # noqa: F401

flask_app = create_app(os.environ.get("FLASK_ENV", "development"))

# Alembic Config object
config = context.config

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from SQLAlchemy models
target_metadata = db.metadata

# Override sqlalchemy.url with our Flask app's DATABASE_URL
config.set_main_option(
    "sqlalchemy.url",
    flask_app.config.get("SQLALCHEMY_DATABASE_URI"),
)


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode (connects to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
