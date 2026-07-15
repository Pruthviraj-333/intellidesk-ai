"""
IntelliDesk AI — Structured JSON Logger
Configures application-wide structured logging with correlation IDs.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from flask import Flask, g, request


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured, machine-parseable logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach request context if available
        try:
            log_entry["request_id"] = getattr(g, "request_id", None)
            log_entry["method"] = request.method
            log_entry["path"] = request.path
            log_entry["ip"] = request.remote_addr
        except RuntimeError:
            # Outside of request context
            pass

        # Attach exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Attach any extra fields
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def configure_logger(app: Flask) -> None:
    """
    Configure structured JSON logging for the Flask application.
    Sets up request ID injection via before_request hook.
    """
    # Clear existing handlers
    app.logger.handlers.clear()

    # Set log level based on environment
    log_level = logging.DEBUG if app.debug else logging.INFO
    app.logger.setLevel(log_level)

    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(JSONFormatter())
    app.logger.addHandler(handler)

    # Also configure the root logger for libraries
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    # Inject request ID into each request context
    @app.before_request
    def inject_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Log incoming requests
    @app.before_request
    def log_request():
        if not request.path.startswith("/api/v1/health"):
            app.logger.info(
                "Request received",
                extra={
                    "extra": {
                        "method": request.method,
                        "path": request.path,
                        "content_type": request.content_type,
                    }
                },
            )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for use in service/repository modules."""
    return logging.getLogger(name)
