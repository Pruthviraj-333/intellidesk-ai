"""
IntelliDesk AI — Report Download Controller (Blueprint)
HTTP handlers for streaming PDF, CSV, and Excel reports.
Route prefix: /api/v1/reports
"""

from datetime import date, timedelta

from flask import Blueprint, send_file, request

from app.services.report_service import ReportService
from app.dtos.analytics_dto import ReportQuerySchema
from app.utils.decorators import validate_query, role_required
from app.utils.constants import UserRole
from app.utils.exceptions import ValidationError
from app.utils.response import success_response

report_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")


def _parse_report_params() -> tuple:
    """Parse and validate common report query parameters."""
    schema = ReportQuerySchema()
    errors = schema.validate(request.args)
    if errors:
        raise ValidationError(str(errors))
    params = schema.load(request.args)

    from_date = params["from_date"]
    to_date = params["to_date"]
    if from_date > to_date:
        raise ValidationError("from_date must be before to_date.")
    if (to_date - from_date).days > 366:
        raise ValidationError("Date range cannot exceed 1 year.")
    return from_date, to_date, params.get("department_id")


@report_bp.route("/tickets/pdf", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def download_ticket_report_pdf():
    """
    GET /api/v1/reports/tickets/pdf?from_date=2026-01-01&to_date=2026-06-30
    Download a styled PDF ticket performance report.
    """
    from_date, to_date, dept_id = _parse_report_params()
    buffer = ReportService.generate_ticket_report_pdf(from_date, to_date, dept_id)
    filename = f"intellidesk_tickets_{from_date}_{to_date}.pdf"
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@report_bp.route("/tickets/csv", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def download_ticket_report_csv():
    """
    GET /api/v1/reports/tickets/csv?from_date=2026-01-01&to_date=2026-06-30
    Download tickets as CSV (UTF-8 BOM, Excel-compatible).
    """
    from_date, to_date, dept_id = _parse_report_params()
    buffer = ReportService.export_tickets_csv(from_date, to_date, dept_id)
    filename = f"intellidesk_tickets_{from_date}_{to_date}.csv"
    return send_file(
        buffer,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@report_bp.route("/analytics/excel", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def download_analytics_excel():
    """
    GET /api/v1/reports/analytics/excel?from_date=2026-01-01&to_date=2026-06-30
    Download multi-sheet Excel analytics workbook:
    - Sheet 1: Daily Trends
    - Sheet 2: SLA Compliance
    - Sheet 3: Agent Performance
    """
    from_date, to_date, _ = _parse_report_params()
    buffer = ReportService.export_analytics_excel(from_date, to_date)
    filename = f"intellidesk_analytics_{from_date}_{to_date}.xlsx"
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@report_bp.route("/available", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def list_available_reports():
    """
    GET /api/v1/reports/available
    Returns metadata about all downloadable report types.
    """
    today = date.today()
    month_start = today.replace(day=1)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    return success_response([
        {
            "id": "ticket_performance_pdf",
            "name": "Ticket Performance Report",
            "format": "PDF",
            "description": "Summary of ticket KPIs, SLA compliance, and priority breakdown.",
            "endpoint": "/api/v1/reports/tickets/pdf",
            "suggested_period": {
                "from_date": str(last_month_start),
                "to_date": str(last_month_end),
            },
        },
        {
            "id": "ticket_export_csv",
            "name": "Ticket Data Export",
            "format": "CSV",
            "description": "Raw ticket data export with all fields, suitable for Excel analysis.",
            "endpoint": "/api/v1/reports/tickets/csv",
            "suggested_period": {
                "from_date": str(last_month_start),
                "to_date": str(last_month_end),
            },
        },
        {
            "id": "analytics_workbook_excel",
            "name": "Analytics Workbook",
            "format": "Excel (.xlsx)",
            "description": "Multi-sheet workbook with daily trends, SLA compliance, and agent performance.",
            "endpoint": "/api/v1/reports/analytics/excel",
            "suggested_period": {
                "from_date": str(last_month_start),
                "to_date": str(last_month_end),
            },
        },
    ])
