"""
IntelliDesk AI — Email Celery Tasks
Async email sending tasks routed to the 'email' queue.
"""

from app.tasks import celery_app


@celery_app.task(bind=True, queue="email", max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_email: str, user_name: str, token: str):
    """Send email verification link asynchronously."""
    try:
        from app.services.email_service import EmailService

        EmailService.send_verification_email(user_email, user_name, token)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="email", max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_email: str, user_name: str, token: str):
    """Send password reset link asynchronously."""
    try:
        from app.services.email_service import EmailService

        EmailService.send_password_reset_email(user_email, user_name, token)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, queue="email", max_retries=3, default_retry_delay=60)
def send_ticket_notification_email_task(self, recipient_email: str, subject: str, html_body: str):
    """Send a generic ticket notification email."""
    try:
        from app.services.email_service import EmailService

        EmailService._send(to=recipient_email, subject=subject, html_body=html_body)
    except Exception as exc:
        raise self.retry(exc=exc)
