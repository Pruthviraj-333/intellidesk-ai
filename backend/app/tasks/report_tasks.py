"""Report generation Celery tasks — implemented in Milestone 5."""

from app.tasks import celery_app


@celery_app.task(bind=True, queue="reports", max_retries=2)
def generate_report_task(self, report_id: str, report_type: str, params: dict):
    """Generate PDF/CSV report asynchronously."""
    # TODO: Implement in M5
    pass
