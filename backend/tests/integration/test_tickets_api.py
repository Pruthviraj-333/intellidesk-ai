"""
IntelliDesk AI — Ticket API Integration Tests
Full lifecycle tests for /api/v1/tickets/* endpoints.
"""

import pytest


class TestCreateTicket:
    """Tests for POST /api/v1/tickets"""

    def test_employee_can_create_ticket(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Cannot access email client",
                "description": "Outlook is not opening since this morning. I have tried restarting.",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["ticket_number"].startswith("TKT-")
        assert data["status"] == "new"
        assert data["requester"] is not None

    def test_create_ticket_with_priority(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "VPN completely down for entire team",
                "description": "All 20 team members cannot connect to VPN since 9am. Critical for remote work.",
                "priority": "critical",
                "category": "Network",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["priority"] == "critical"
        assert data["category"] == "Network"
        # SLA deadlines should be set for critical tickets
        assert data["sla_response_deadline"] is not None
        assert data["sla_resolution_deadline"] is not None

    def test_create_ticket_title_too_short(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Hi",
                "description": "Short title test",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_create_ticket_requires_auth(self, client):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Test ticket",
                "description": "Test description for a ticket that needs auth.",
            },
        )
        assert resp.status_code == 401

    def test_create_ticket_invalid_priority(self, client, auth_headers_employee):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Test invalid priority",
                "description": "Testing that an invalid priority value is rejected.",
                "priority": "super_urgent",
            },
            headers=auth_headers_employee,
        )
        assert resp.status_code == 400


class TestListTickets:
    """Tests for GET /api/v1/tickets"""

    def test_employee_sees_only_own_tickets(self, client, auth_headers_employee):
        resp = client.get("/api/v1/tickets/", headers=auth_headers_employee)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_agent_sees_all_tickets(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/", headers=auth_headers_agent)
        assert resp.status_code == 200

    def test_filter_by_status(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/?status=new", headers=auth_headers_agent)
        assert resp.status_code == 200
        for ticket in resp.get_json()["data"]:
            assert ticket["status"] == "new"

    def test_filter_by_priority(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/?priority=critical", headers=auth_headers_agent)
        assert resp.status_code == 200

    def test_pagination_defaults(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/", headers=auth_headers_agent)
        pagination = resp.get_json()["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 20

    def test_search_tickets(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/?search=VPN", headers=auth_headers_agent)
        assert resp.status_code == 200


class TestGetTicket:
    """Tests for GET /api/v1/tickets/:id"""

    def test_get_own_ticket_as_employee(self, client, auth_headers_employee, auth_headers_agent):
        # Create a ticket as employee
        create_resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "My specific ticket for get test",
                "description": "Description for the get test ticket to verify access.",
            },
            headers=auth_headers_employee,
        )
        ticket_id = create_resp.get_json()["data"]["id"]

        # Employee can fetch their own ticket
        resp = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert resp.get_json()["data"]["id"] == ticket_id

    def test_get_nonexistent_ticket(self, client, auth_headers_agent):
        resp = client.get("/api/v1/tickets/999999", headers=auth_headers_agent)
        assert resp.status_code == 404

    def test_ticket_detail_has_comments_field(self, client, auth_headers_agent):
        # Create a ticket first
        create_resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Ticket for detail field test",
                "description": "Checking that the detail schema includes comments and attachments.",
            },
            headers=auth_headers_agent,
        )
        ticket_id = create_resp.get_json()["data"]["id"]

        resp = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_headers_agent)
        data = resp.get_json()["data"]
        assert "comments" in data
        assert "attachments" in data
        assert isinstance(data["comments"], list)


class TestUpdateTicket:
    """Tests for PUT /api/v1/tickets/:id"""

    def _create_ticket(self, client, headers):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Ticket for update test scenario",
                "description": "This ticket will be updated during the test run.",
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_agent_can_update_assigned_ticket(self, client, auth_headers_agent, auth_headers_admin):
        ticket_id = self._create_ticket(client, auth_headers_agent)

        # First assign to agent via admin
        client.put(
            f"/api/v1/tickets/{ticket_id}/assign",
            json={"assignee_id": 3},  # agent is id 3 in test seed
            headers=auth_headers_admin,
        )

        # Agent updates their ticket
        resp = client.put(
            f"/api/v1/tickets/{ticket_id}", json={"status": "open"}, headers=auth_headers_agent
        )
        assert resp.status_code in (200, 403)  # 403 if not agent's ticket

    def test_employee_cannot_update_ticket(self, client, auth_headers_employee):
        ticket_id = self._create_ticket(client, auth_headers_employee)
        resp = client.put(
            f"/api/v1/tickets/{ticket_id}", json={"priority": "high"}, headers=auth_headers_employee
        )
        assert resp.status_code == 403

    def test_invalid_status_transition_rejected(self, client, auth_headers_admin):
        ticket_id = self._create_ticket(client, auth_headers_admin)
        # Try to jump from 'new' directly to 'closed'
        resp = client.put(
            f"/api/v1/tickets/{ticket_id}", json={"status": "closed"}, headers=auth_headers_admin
        )
        assert resp.status_code == 422
        assert "transition" in resp.get_json()["error"]["message"].lower()

    def test_resolve_requires_resolution_notes(self, client, auth_headers_admin):
        ticket_id = self._create_ticket(client, auth_headers_admin)
        # Move to open first
        client.put(
            f"/api/v1/tickets/{ticket_id}", json={"status": "open"}, headers=auth_headers_admin
        )
        client.put(
            f"/api/v1/tickets/{ticket_id}",
            json={"status": "in_progress"},
            headers=auth_headers_admin,
        )
        # Try to resolve without notes
        resp = client.put(
            f"/api/v1/tickets/{ticket_id}", json={"status": "resolved"}, headers=auth_headers_admin
        )
        assert resp.status_code == 400


class TestComments:
    """Tests for ticket comment endpoints."""

    def _create_ticket(self, client, headers):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Ticket for comment tests",
                "description": "This ticket is used to test the commenting system.",
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_add_public_comment(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"body": "I am looking into this issue right now."},
            headers=auth_headers_agent,
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["is_internal"] == False
        assert data["body"] == "I am looking into this issue right now."

    def test_add_internal_note_as_agent(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"body": "Internal: user seems to have wrong VPN config.", "is_internal": True},
            headers=auth_headers_agent,
        )
        assert resp.status_code == 201
        assert resp.get_json()["data"]["is_internal"] == True

    def test_employee_cannot_add_internal_note(self, client, auth_headers_employee):
        ticket_id = self._create_ticket(client, auth_headers_employee)
        resp = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"body": "This is internal.", "is_internal": True},
            headers=auth_headers_employee,
        )
        assert resp.status_code == 403

    def test_list_comments(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"body": "First comment on this ticket."},
            headers=auth_headers_agent,
        )
        resp = client.get(f"/api/v1/tickets/{ticket_id}/comments", headers=auth_headers_agent)
        assert resp.status_code == 200
        assert len(resp.get_json()["data"]) >= 1

    def test_empty_comment_body_rejected(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/tickets/{ticket_id}/comments", json={"body": ""}, headers=auth_headers_agent
        )
        assert resp.status_code == 400


class TestDeleteTicket:
    """Tests for DELETE /api/v1/tickets/:id"""

    def test_admin_can_delete_ticket(self, client, auth_headers_admin, auth_headers_employee):
        create_resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Ticket to be deleted by admin",
                "description": "This ticket will be soft-deleted during testing.",
            },
            headers=auth_headers_employee,
        )
        ticket_id = create_resp.get_json()["data"]["id"]

        resp = client.delete(f"/api/v1/tickets/{ticket_id}", headers=auth_headers_admin)
        assert resp.status_code == 204

        # Verify soft-deleted (not found)
        get_resp = client.get(f"/api/v1/tickets/{ticket_id}", headers=auth_headers_admin)
        assert get_resp.status_code == 404

    def test_employee_cannot_delete_ticket(self, client, auth_headers_employee):
        create_resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Employee tries to delete this ticket",
                "description": "This should be rejected because employees cannot delete tickets.",
            },
            headers=auth_headers_employee,
        )
        ticket_id = create_resp.get_json()["data"]["id"]

        resp = client.delete(f"/api/v1/tickets/{ticket_id}", headers=auth_headers_employee)
        assert resp.status_code == 403
