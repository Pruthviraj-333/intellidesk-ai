"""
IntelliDesk AI — Application Factory
Creates and configures the Flask application instance.
"""

import os
import logging

from flask import Flask

from app.config.settings import config
from app.extensions import db, migrate, jwt, ma, cors, socketio, limiter, mail


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory. Creates a configured Flask app instance.

    Args:
        config_name: Configuration profile ('development', 'production', 'testing').
                     Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # ─── Initialize Extensions ───────────────────────────────────────────────────
    _init_extensions(app)

    # ─── Register Blueprints ─────────────────────────────────────────────────────
    _register_blueprints(app)

    # ─── Register Error Handlers ─────────────────────────────────────────────────
    _register_error_handlers(app)

    # ─── Configure Logging ───────────────────────────────────────────────────────
    _configure_logging(app)

    # ─── Register CLI Commands ───────────────────────────────────────────────────
    _register_cli_commands(app)

    # ─── Configure JWT Callbacks ─────────────────────────────────────────────────
    _configure_jwt(app)

    return app


def _init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions with the app instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    cors.init_app(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    socketio.init_app(
        app,
        cors_allowed_origins=app.config["CORS_ORIGINS"],
        async_mode="eventlet",
        logger=False,
        engineio_logger=False,
    )
    limiter.init_app(app)
    mail.init_app(app)


def _register_blueprints(app: Flask) -> None:
    """Register all Flask Blueprint controllers."""
    from app.controllers import health_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.user_controller import user_bp
    from app.controllers.department_controller import department_bp
    from app.controllers.ticket_controller import ticket_bp
    from app.controllers.incident_controller import incident_bp, problem_bp, notification_bp
    from app.controllers.dashboard_controller import dashboard_bp
    from app.controllers.knowledge_controller import knowledge_bp
    from app.controllers.document_controller import document_bp
    from app.controllers.ai_controller import ai_bp
    from app.controllers.analytics_controller import analytics_bp
    from app.controllers.report_controller import report_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(incident_bp)
    app.register_blueprint(problem_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(report_bp)

    # All routes registered.


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from app.utils.exceptions import (
        NotFoundError,
        ValidationError,
        AuthorizationError,
        AuthenticationError,
        ConflictError,
        BusinessLogicError,
    )
    from app.utils.response import error_response

    @app.errorhandler(NotFoundError)
    def handle_not_found(e):
        return error_response("NOT_FOUND", str(e), 404)

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return error_response("VALIDATION_ERROR", str(e), 400, details=e.details)

    @app.errorhandler(AuthorizationError)
    def handle_authorization_error(e):
        return error_response("FORBIDDEN", str(e), 403)

    @app.errorhandler(AuthenticationError)
    def handle_authentication_error(e):
        return error_response("UNAUTHORIZED", str(e), 401)

    @app.errorhandler(ConflictError)
    def handle_conflict_error(e):
        return error_response("CONFLICT", str(e), 409)

    @app.errorhandler(BusinessLogicError)
    def handle_business_logic_error(e):
        return error_response("BUSINESS_LOGIC_ERROR", str(e), 422)

    @app.errorhandler(404)
    def handle_404(e):
        return error_response("NOT_FOUND", "The requested resource was not found.", 404)

    @app.errorhandler(405)
    def handle_405(e):
        return error_response("METHOD_NOT_ALLOWED", "Method not allowed.", 405)

    @app.errorhandler(429)
    def handle_429(e):
        return error_response(
            "RATE_LIMIT_EXCEEDED",
            "Too many requests. Please slow down.",
            429,
        )

    @app.errorhandler(500)
    def handle_500(e):
        app.logger.exception("Internal server error")
        return error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
            500,
        )


def _configure_logging(app: Flask) -> None:
    """Configure structured JSON logging."""
    from app.utils.logger import configure_logger

    configure_logger(app)


def _register_cli_commands(app: Flask) -> None:
    """Register Flask CLI commands."""
    from app.cli import register_commands

    register_commands(app)


def _configure_jwt(app: Flask) -> None:
    """Configure JWT callbacks for token validation and user loading."""
    import redis
    from flask_jwt_extended import decode_token

    redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check Redis blocklist for revoked tokens."""
        jti = jwt_payload["jti"]
        token_in_redis = redis_client.get(f"blocklist:{jti}")
        return token_in_redis is not None

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        from app.utils.response import error_response

        return error_response("TOKEN_EXPIRED", "Your session has expired. Please log in again.", 401)

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        from app.utils.response import error_response

        return error_response("INVALID_TOKEN", "Invalid authentication token.", 401)

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        from app.utils.response import error_response

        return error_response(
            "UNAUTHORIZED", "Authentication is required to access this resource.", 401
        )

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        from app.utils.response import error_response

        return error_response(
            "TOKEN_REVOKED", "This token has been revoked. Please log in again.", 401
        )
