"""
IntelliDesk AI — Config Layer
Environment-based configuration with BaseConfig, Development, Production, Testing.
"""

import os
from datetime import timedelta


class BaseConfig:
    """Base configuration — shared across all environments."""

    # ─── Core ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # ─── SQLAlchemy ─────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "postgresql://intellidesk:password@localhost:5432/intellidesk"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # ─── JWT ────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=7)
    JWT_ALGORITHM: str = "HS256"
    JWT_BLACKLIST_ENABLED: bool = True
    JWT_BLACKLIST_TOKEN_CHECKS: list = ["access", "refresh"]

    # ─── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # ─── Celery ─────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"

    # ─── Flask-Mail (Gmail SMTP) ─────────────────────────────────────────────────
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: str = os.environ.get("GMAIL_USER", "")
    MAIL_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD", "")
    MAIL_DEFAULT_SENDER: str = os.environ.get("GMAIL_USER", "noreply@intellidesk.ai")
    MAIL_FROM_NAME: str = os.environ.get("EMAIL_FROM_NAME", "IntelliDesk AI")

    # ─── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # ─── ChromaDB ───────────────────────────────────────────────────────────────
    CHROMA_HOST: str = os.environ.get("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.environ.get("CHROMA_PORT", "8000"))

    # ─── AI (Groq) ──────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "groq")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_FALLBACK_MODEL: str = os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
    EMBEDDING_MODEL: str = os.environ.get(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # ─── Cloudinary ─────────────────────────────────────────────────────────────
    CLOUDINARY_URL: str = os.environ.get("CLOUDINARY_URL", "")

    # ─── Rate Limiting ──────────────────────────────────────────────────────────
    RATELIMIT_STORAGE_URI: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    RATELIMIT_DEFAULT: str = "200/hour"
    RATELIMIT_STRATEGY: str = "fixed-window"

    # ─── File Upload ────────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
    MAX_CONTENT_LENGTH: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS: set = {"pdf", "docx", "txt", "md", "png", "jpg", "jpeg"}

    # ─── App Settings ───────────────────────────────────────────────────────────
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    API_VERSION: str = "v1"
    DEFAULT_PAGINATION_SIZE: int = 20
    MAX_PAGINATION_SIZE: int = 100
    TOKEN_EXPIRY_HOURS: int = 24  # Email verification / password reset tokens


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set True to see all SQL queries
    # Disable rate limiting in development — all Docker traffic
    # appears to come from the same IP (Nginx proxy), so limits
    # are exhausted almost instantly during normal usage.
    RATELIMIT_ENABLED = False


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }


class TestingConfig(BaseConfig):
    """Testing environment configuration — uses SQLite in-memory."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=10)
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    MAIL_SUPPRESS_SEND = True


# Config registry
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
