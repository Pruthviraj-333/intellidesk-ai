"""
IntelliDesk AI — Incident API Integration Tests
Tests for /api/v1/incidents/* and /api/v1/problems/* endpoints.
"""

import pytest


class TestCreateIncident:
    """Tests for POST /api/v1/incidents"""

    def test_agent_can_create_incident(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": "Production database unreachable",
                "description": "The main PostgreSQL cluster is not responding. All services are affected.",
                "severity": "critical",
                "impact": "high",
                "affected_services": "API, Dashboard, Auth Service",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["incident_number"].startswith("INC-")
        assert data["severity"] == "critical"
        assert data["status"] == "open"
        # Timeline should have creation entry
        assert len(data["timeline"]) >= 1
        assert data["timeline"][0]["event_type"] == "created"

    def test_employee_cannot_create_incident(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": "My computer is broken",
                "description": "Employee trying to create an incident, which is not allowed.",
                "severity": "low",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 403

    def test_invalid_severity_rejected(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": "Test incident with bad severity",
                "description": "This should fail because the severity value is not valid.",
                "severity": "catastrophic",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 400

    def test_create_incident_requires_auth(self, client):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": "Unauthorized incident",
                "description": "Test without auth token.",
                "severity": "high",
            },
        )
        assert resp.status_code == 401


class TestListIncidents:
    """Tests for GET /api/v1/incidents"""

    def test_agent_can_list_incidents(self, client, auth_headers_agent):
        resp = client.get("/api/v1/incidents/", headers=auth_headers_agent)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)
        assert "pagination" in resp.get_json()

    def test_filter_by_severity(self, client, auth_headers_manager):
        resp = client.get("/api/v1/incidents/?severity=critical", headers=auth_headers_manager)
        assert resp.status_code == 200
        for incident in resp.get_json()["data"]:
            assert incident["severity"] == "critical"

    def test_employee_cannot_list_incidents(self, client, auth_headers_employee):
        resp = client.get("/api/v1/incidents/", headers=auth_headers_employee)
        assert resp.status_code == 403


class TestUpdateIncident:
    """Tests for PUT /api/v1/incidents/:id"""

    def _create_incident(self, client, headers, severity="high"):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": f"Incident for update tests {severity}",
                "description": "This incident will be updated in a test scenario.",
                "severity": severity,
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_update_incident_status(self, client, auth_headers_manager):
        incident_id = self._create_incident(client, auth_headers_manager)
        resp = client.put(
            f"/api/v1/incidents/{incident_id}",
            json={"status": "in_progress", "assignee_id": 3},
            headers=auth_headers_manager,
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "in_progress"

    def test_update_creates_timeline_entry(self, client, auth_headers_manager):
        incident_id = self._create_incident(client, auth_headers_manager)
        resp = client.put(
            f"/api/v1/incidents/{incident_id}",
            json={"status": "in_progress"},
            headers=auth_headers_manager,
        )
        assert resp.status_code == 200
        timeline = resp.get_json()["data"]["timeline"]
        # Should have: created + status_change = at least 2 entries
        assert len(timeline) >= 2

    def test_add_timeline_entry(self, client, auth_headers_agent):
        incident_id = self._create_incident(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={
                "event_type": "update",
                "description": "Identified root cause: misconfigured firewall rule blocking database port.",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["event_type"] == "update"

    def test_invalid_event_type_rejected(self, client, auth_headers_agent):
        incident_id = self._create_incident(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/incidents/{incident_id}/timeline",
            json={
                "event_type": "magic_fix",
                "description": "This event type does not exist.",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 400


class TestProblems:
    """Tests for /api/v1/problems endpoints."""

    def _create_incident_id(self, client, headers):
        resp = client.post(
            "/api/v1/incidents/",
            json={
                "title": "Recurring outage for problem linkage",
                "description": "This incident will be linked to a problem record.",
                "severity": "high",
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_manager_can_create_problem(self, client, auth_headers_manager):
        incident_id = self._create_incident_id(client, auth_headers_manager)
        resp = client.post(
            "/api/v1/problems/",
            json={
                "title": "Recurring network timeouts during peak hours",
                "description": "Investigation into root cause of repeated network timeout incidents.",
                "linked_incident_ids": [incident_id],
            },
            headers=auth_headers_manager,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["problem_number"].startswith("PRB-")
        assert data["status"] == "open"
        assert len(data["linked_incidents"]) >= 1

    def test_agent_cannot_create_problem(self, client, auth_headers_agent):
        resp = client.post(
            "/api/v1/problems/",
            json={
                "title": "Agent tries to create problem",
                "description": "This should be rejected due to insufficient role.",
            },
            headers=auth_headers_agent,
        )
        assert resp.status_code == 403

    def test_update_problem_root_cause(self, client, auth_headers_manager):
        # Create problem first
        create_resp = client.post(
            "/api/v1/problems/",
            json={
                "title": "Problem to get root cause",
                "description": "Root cause will be updated in subsequent test step.",
            },
            headers=auth_headers_manager,
        )
        problem_id = create_resp.get_json()["data"]["id"]

        resp = client.put(
            f"/api/v1/problems/{problem_id}",
            json={
                "root_cause": "Memory leak in connection pool causing cascading failures under load.",
                "workaround": "Restart service every 6 hours until patch is deployed.",
            },
            headers=auth_headers_manager,
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "Memory leak" in data["root_cause"]

    def test_list_problems(self, client, auth_headers_admin):
        resp = client.get("/api/v1/problems/", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)


class TestNotifications:
    """Tests for /api/v1/notifications endpoints."""

    def test_list_notifications(self, client, auth_headers_employee):
        resp = client.get("/api/v1/notifications/", headers=auth_headers_employee)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["data"], list)
        assert "unread_count" in data.get("meta", {}) or "pagination" in data

    def test_mark_all_read(self, client, auth_headers_employee):
        resp = client.put("/api/v1/notifications/read-all", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert "marked_read" in resp.get_json()["data"]

    def test_notifications_require_auth(self, client):
        resp = client.get("/api/v1/notifications/")
        assert resp.status_code == 401
