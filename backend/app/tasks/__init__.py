"""
IntelliDesk AI — Celery Application
Celery instance setup and task autodiscovery.
"""

from celery import Celery


def make_celery(app=None) -> Celery:
    """
    Create and configure a Celery instance.
    If a Flask app is provided, integrates with its config.
    If not, reads from environment variables directly.
    """
    import os

    broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    result_backend = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    celery = Celery(
        "intellidesk",
        broker=broker_url,
        backend=result_backend,
        include=[
            "app.tasks.email_tasks",
            "app.tasks.document_tasks",
            "app.tasks.ai_tasks",
            "app.tasks.report_tasks",
            "app.tasks.sla_tasks",
            "app.tasks.maintenance_tasks",
        ],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        # Named queues for task routing
        task_queues={
            "default": {"exchange": "default", "routing_key": "default"},
            "email": {"exchange": "email", "routing_key": "email"},
            "documents": {"exchange": "documents", "routing_key": "documents"},
            "ai": {"exchange": "ai", "routing_key": "ai"},
            "reports": {"exchange": "reports", "routing_key": "reports"},
        },
        task_default_queue="default",
        task_routes={
            "app.tasks.email_tasks.*": {"queue": "email"},
            "app.tasks.document_tasks.*": {"queue": "documents"},
            "app.tasks.ai_tasks.*": {"queue": "ai"},
            "app.tasks.report_tasks.*": {"queue": "reports"},
        },
        # ── Celery Beat Schedule ──────────────────────────────────────────────
        beat_schedule={
            # Daily metric snapshot — every night at 00:05 UTC
            "daily-metrics-snapshot": {
                "task": "app.tasks.maintenance_tasks.compute_daily_metrics_snapshot",
                "schedule": 86400,  # every 24 hours
                "options": {"queue": "default"},
            },
            # SLA breach check — every 15 minutes
            "sla-breach-monitor": {
                "task": "app.tasks.maintenance_tasks.check_sla_breaches",
                "schedule": 900,  # every 15 minutes
                "options": {"queue": "default"},
            },
            # Token cleanup — every night at 02:00 UTC
            "cleanup-expired-tokens": {
                "task": "app.tasks.maintenance_tasks.cleanup_expired_tokens",
                "schedule": 86400,
                "options": {"queue": "default"},
            },
        },
    )

    if app is None:
        try:
            from app import create_app

            app = create_app()
        except Exception:
            pass

    if app is not None:
        filtered_config = {k: v for k, v in app.config.items() if not k.startswith("CELERY_")}
        celery.conf.update(filtered_config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Module-level Celery instance used by the worker process
celery_app = make_celery()
