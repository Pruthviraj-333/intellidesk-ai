"""
IntelliDesk AI — Analytics & Report API Integration Tests
Tests for /api/v1/analytics/* and /api/v1/reports/* endpoints.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

# ─── Mock analytics data ──────────────────────────────────────────────────────

MOCK_PLATFORM_SUMMARY = {
    "total_tickets": 482,
    "open_tickets": 64,
    "total_incidents": 18,
    "total_articles": 35,
    "total_agents": 12,
    "ai_sessions_total": 128,
    "overall_sla_compliance": 91.4,
}

MOCK_TRENDS = [
    {
        "date": "2026-07-01",
        "tickets_created": 12,
        "tickets_resolved": 10,
        "tickets_open": 42,
        "tickets_overdue": 3,
        "sla_compliance_rate": 83.3,
        "avg_resolution_hours": 4.2,
        "incidents_created": 1,
        "critical_incidents": 0,
        "ai_sessions": 8,
    },
    {
        "date": "2026-07-02",
        "tickets_created": 9,
        "tickets_resolved": 11,
        "tickets_open": 40,
        "tickets_overdue": 2,
        "sla_compliance_rate": 90.9,
        "avg_resolution_hours": 3.8,
        "incidents_created": 0,
        "critical_incidents": 0,
        "ai_sessions": 5,
    },
]

MOCK_LEADERBOARD = [
    {
        "agent_id": 3,
        "agent_name": "Alice Johnson",
        "avatar_url": None,
        "tickets_resolved": 47,
        "tickets_assigned": 52,
        "sla_breached": 3,
        "resolution_rate": 90.4,
        "avg_resolution_hours": 3.5,
    },
]

MOCK_HEATMAP = [
    {"day": 1, "hour": 9, "count": 23},
    {"day": 1, "hour": 10, "count": 31},
    {"day": 2, "hour": 14, "count": 18},
]


class TestAnalyticsSummary:
    """Tests for GET /api/v1/analytics/summary"""

    def test_admin_gets_platform_summary(self, client, auth_headers_admin):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_platform_summary",
            return_value=MOCK_PLATFORM_SUMMARY,
        ):
            resp = client.get("/api/v1/analytics/summary", headers=auth_headers_admin)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["total_tickets"] == 482
        assert data["overall_sla_compliance"] == 91.4
        assert "open_tickets" in data
        assert "total_agents" in data
        assert "ai_sessions_total" in data

    def test_manager_can_access_summary(self, client, auth_headers_manager):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_platform_summary",
            return_value=MOCK_PLATFORM_SUMMARY,
        ):
            resp = client.get("/api/v1/analytics/summary", headers=auth_headers_manager)
        assert resp.status_code == 200

    def test_employee_cannot_access_summary(self, client, auth_headers_employee):
        resp = client.get("/api/v1/analytics/summary", headers=auth_headers_employee)
        assert resp.status_code == 403

    def test_agent_cannot_access_summary(self, client, auth_headers_agent):
        resp = client.get("/api/v1/analytics/summary", headers=auth_headers_agent)
        assert resp.status_code == 403

    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/analytics/summary")
        assert resp.status_code == 401


class TestTrends:
    """Tests for GET /api/v1/analytics/trends"""

    def test_admin_gets_trend_data(self, client, auth_headers_admin):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_trend_data",
            return_value=MOCK_TRENDS,
        ):
            resp = client.get("/api/v1/analytics/trends?days=7", headers=auth_headers_admin)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["period_days"] == 7
        assert data["data_points"] == 2
        assert isinstance(data["trends"], list)
        for point in data["trends"]:
            assert "date" in point
            assert "tickets_created" in point
            assert "sla_compliance_rate" in point

    def test_invalid_days_rejected(self, client, auth_headers_admin):
        resp = client.get("/api/v1/analytics/trends?days=2", headers=auth_headers_admin)
        assert resp.status_code == 400  # min=7

    def test_trends_with_department_filter(self, client, auth_headers_manager):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_trend_data", return_value=[]
        ) as mock_trend:
            resp = client.get(
                "/api/v1/analytics/trends?days=30&department_id=1",
                headers=auth_headers_manager,
            )
        assert resp.status_code == 200
        mock_trend.assert_called_once_with(days=30, department_id=1)


class TestSLACompliance:
    """Tests for GET /api/v1/analytics/sla-compliance"""

    def test_sla_breakdown_returned(self, client, auth_headers_admin):
        mock_sla = {
            "critical": {"total": 10, "compliant": 9, "breached": 1, "compliance_rate": 90.0},
            "high": {"total": 45, "compliant": 40, "breached": 5, "compliance_rate": 88.9},
            "medium": {"total": 120, "compliant": 115, "breached": 5, "compliance_rate": 95.8},
            "low": {"total": 200, "compliant": 198, "breached": 2, "compliance_rate": 99.0},
        }
        with patch(
            "app.services.analytics_service.AnalyticsService.get_sla_compliance_by_priority",
            return_value=mock_sla,
        ):
            resp = client.get("/api/v1/analytics/sla-compliance", headers=auth_headers_admin)

        assert resp.status_code == 200
        data = resp.get_json()["data"]["sla_by_priority"]
        assert "critical" in data
        assert "high" in data
        assert "medium" in data
        assert "low" in data
        assert data["critical"]["compliance_rate"] == 90.0

    def test_employee_cannot_access(self, client, auth_headers_employee):
        resp = client.get("/api/v1/analytics/sla-compliance", headers=auth_headers_employee)
        assert resp.status_code == 403


class TestAgentLeaderboard:
    """Tests for GET /api/v1/analytics/agent-leaderboard"""

    def test_leaderboard_returns_ranked_agents(self, client, auth_headers_admin):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_agent_leaderboard",
            return_value=MOCK_LEADERBOARD,
        ):
            resp = client.get(
                "/api/v1/analytics/agent-leaderboard?days=30&limit=5",
                headers=auth_headers_admin,
            )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["period_days"] == 30
        agents = data["agents"]
        assert isinstance(agents, list)
        assert agents[0]["agent_name"] == "Alice Johnson"
        assert agents[0]["resolution_rate"] == 90.4

    def test_invalid_limit_rejected(self, client, auth_headers_admin):
        resp = client.get(
            "/api/v1/analytics/agent-leaderboard?limit=100",
            headers=auth_headers_admin,
        )
        assert resp.status_code == 400  # max=50


class TestHeatmap:
    """Tests for GET /api/v1/analytics/heatmap"""

    def test_heatmap_data_structure(self, client, auth_headers_admin):
        with patch(
            "app.services.analytics_service.AnalyticsService.get_heatmap_data",
            return_value=MOCK_HEATMAP,
        ):
            resp = client.get("/api/v1/analytics/heatmap?days=90", headers=auth_headers_admin)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["period_days"] == 90
        heatmap = data["heatmap"]
        assert isinstance(heatmap, list)
        for point in heatmap:
            assert "day" in point
            assert "hour" in point
            assert "count" in point
            assert 0 <= point["day"] <= 6
            assert 0 <= point["hour"] <= 23


class TestTicketVolume:
    """Tests for GET /api/v1/analytics/ticket-volume"""

    def test_volume_by_category(self, client, auth_headers_admin):
        mock_volume = [
            {"category": "Software", "count": 145},
            {"category": "Network", "count": 87},
            {"category": "Hardware", "count": 62},
        ]
        with patch(
            "app.services.analytics_service.AnalyticsService.get_ticket_volume_by_category",
            return_value=mock_volume,
        ):
            resp = client.get("/api/v1/analytics/ticket-volume", headers=auth_headers_admin)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        assert data[0]["category"] == "Software"
        assert data[0]["count"] == 145


class TestReportDownloads:
    """Tests for /api/v1/reports/* download endpoints."""

    VALID_PARAMS = "?from_date=2026-01-01&to_date=2026-06-30"

    def test_list_available_reports(self, client, auth_headers_admin):
        resp = client.get("/api/v1/reports/available", headers=auth_headers_admin)
        assert resp.status_code == 200
        reports = resp.get_json()["data"]
        assert isinstance(reports, list)
        assert len(reports) == 3
        formats = {r["format"] for r in reports}
        assert "PDF" in formats
        assert "CSV" in formats
        assert "Excel (.xlsx)" in formats

    def test_employee_cannot_access_reports(self, client, auth_headers_employee):
        resp = client.get(
            f"/api/v1/reports/tickets/pdf{self.VALID_PARAMS}", headers=auth_headers_employee
        )
        assert resp.status_code == 403

    def test_missing_date_params_rejected(self, client, auth_headers_admin):
        resp = client.get("/api/v1/reports/tickets/pdf", headers=auth_headers_admin)
        assert resp.status_code == 400

    def test_invalid_date_range_rejected(self, client, auth_headers_admin):
        resp = client.get(
            "/api/v1/reports/tickets/pdf?from_date=2026-06-30&to_date=2026-01-01",
            headers=auth_headers_admin,
        )
        assert resp.status_code == 400  # from > to

    def test_pdf_report_returns_pdf_content_type(self, client, auth_headers_admin):
        mock_buffer = MagicMock()
        mock_buffer.read.return_value = b"%PDF-1.4 fake-pdf-content"
        mock_buffer.seek.return_value = None

        import io

        real_buffer = io.BytesIO(b"%PDF-1.4 fake-pdf-content")

        with patch(
            "app.services.report_service.ReportService.generate_ticket_report_pdf",
            return_value=real_buffer,
        ):
            resp = client.get(
                f"/api/v1/reports/tickets/pdf{self.VALID_PARAMS}",
                headers=auth_headers_admin,
            )
        assert resp.status_code == 200
        assert "pdf" in resp.content_type.lower()

    def test_csv_report_returns_csv_content_type(self, client, auth_headers_admin):
        import io

        csv_content = "Ticket Number,Title\nTKT-20260101-0001,Test ticket\n"
        real_buffer = io.BytesIO(csv_content.encode("utf-8-sig"))

        with patch(
            "app.services.report_service.ReportService.export_tickets_csv", return_value=real_buffer
        ):
            resp = client.get(
                f"/api/v1/reports/tickets/csv{self.VALID_PARAMS}",
                headers=auth_headers_admin,
            )
        assert resp.status_code == 200
        assert "csv" in resp.content_type.lower() or "text" in resp.content_type.lower()

    def test_excel_report_returns_xlsx_content_type(self, client, auth_headers_admin):
        import io

        real_buffer = io.BytesIO(b"PK\x03\x04fake-xlsx-content")

        with patch(
            "app.services.report_service.ReportService.export_analytics_excel",
            return_value=real_buffer,
        ):
            resp = client.get(
                f"/api/v1/reports/analytics/excel{self.VALID_PARAMS}",
                headers=auth_headers_admin,
            )
        assert resp.status_code == 200
        assert "spreadsheet" in resp.content_type.lower() or "excel" in resp.content_type.lower()
