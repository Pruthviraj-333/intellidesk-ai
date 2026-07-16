"""
IntelliDesk AI — Dashboard API Integration Tests
Tests for /api/v1/dashboard/* endpoints.
"""

import pytest


class TestDashboardSummary:
    """Tests for GET /api/v1/dashboard/summary"""

    def test_employee_gets_own_stats(self, client, auth_headers_employee):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers_employee)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "ticket_stats" in data
        assert "unread_notifications" in data

    def test_agent_gets_assigned_stats(self, client, auth_headers_agent):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers_agent)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "ticket_stats" in data
        assert "assigned_to_me" in data["ticket_stats"]

    def test_admin_gets_platform_stats(self, client, auth_headers_admin):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "ticket_stats" in data
        assert "incident_stats" in data
        assert "by_status" in data["ticket_stats"]
        assert "by_priority" in data["ticket_stats"]

    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401


class TestTicketTrends:
    """Tests for GET /api/v1/dashboard/ticket-trends"""

    def test_manager_can_get_trends(self, client, auth_headers_manager):
        resp = client.get("/api/v1/dashboard/ticket-trends", headers=auth_headers_manager)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "trends" in data
        assert "data_points" in data
        assert data["period_days"] == 30

    def test_employee_cannot_get_trends(self, client, auth_headers_employee):
        resp = client.get("/api/v1/dashboard/ticket-trends", headers=auth_headers_employee)
        assert resp.status_code == 403


class TestSLACompliance:
    """Tests for GET /api/v1/dashboard/sla-compliance"""

    def test_admin_gets_sla_data(self, client, auth_headers_admin):
        resp = client.get("/api/v1/dashboard/sla-compliance", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.get_json()["data"]["sla_compliance"]
        # Should have data for all 4 priorities
        assert "critical" in data
        assert "high" in data
        assert "medium" in data
        assert "low" in data
        for priority, stats in data.items():
            assert "compliance_rate" in stats
            assert 0 <= stats["compliance_rate"] <= 100

    def test_employee_cannot_access_sla(self, client, auth_headers_employee):
        resp = client.get("/api/v1/dashboard/sla-compliance", headers=auth_headers_employee)
        assert resp.status_code == 403


class TestAgentPerformance:
    """Tests for GET /api/v1/dashboard/agent-performance"""

    def test_admin_gets_performance_data(self, client, auth_headers_admin):
        resp = client.get("/api/v1/dashboard/agent-performance", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert isinstance(data, list)
        for agent in data:
            assert "agent_name" in agent
            assert "total_assigned" in agent
            assert "resolution_rate" in agent
            assert 0 <= agent["resolution_rate"] <= 100

    def test_agent_cannot_access_performance_report(self, client, auth_headers_agent):
        resp = client.get("/api/v1/dashboard/agent-performance", headers=auth_headers_agent)
        assert resp.status_code == 403
