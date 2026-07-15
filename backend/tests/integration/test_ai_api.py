"""
IntelliDesk AI — AI Assistant Integration Tests
Tests for /api/v1/ai/* endpoints with mocked Groq and ChromaDB.
"""

from unittest.mock import MagicMock, patch

import pytest

# ─── Shared mock fixtures ─────────────────────────────────────────────────────

MOCK_LLM_RESPONSE = {
    "content": "Here are the steps to resolve your VPN issue:\n1. Check your credentials\n2. Restart the client\n3. Contact IT if issue persists.",
    "model": "llama-3.3-70b-versatile",
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "latency_ms": 420,
}

MOCK_RAG_RESULTS = [
    {
        "content": "To reset VPN, go to Settings > Network > VPN and click Reset.",
        "score": 0.92,
        "collection": "knowledge_articles",
        "metadata": {"article_id": "1", "title": "VPN Reset Guide"},
    }
]


class TestAIChat:
    """Tests for POST /api/v1/ai/chat"""

    def test_employee_can_chat_with_ai(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch(
                "app.services.ai_service.RAGService.semantic_search", return_value=MOCK_RAG_RESULTS
            ),
            patch(
                "app.services.ai_service.RAGService.build_context_for_query",
                return_value="VPN context text.",
            ),
        ):

            resp = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "How do I reset my VPN connection?",
                },
                headers=auth_headers_employee,
            )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "response" in data
        assert "session_uuid" in data
        assert "sources" in data
        assert "tokens_used" in data
        assert len(data["response"]) > 0

    def test_chat_creates_session_on_first_message(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch("app.services.ai_service.RAGService.semantic_search", return_value=[]),
            patch("app.services.ai_service.RAGService.build_context_for_query", return_value=""),
        ):

            resp = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "What is IntelliDesk AI?",
                },
                headers=auth_headers_employee,
            )

        assert resp.status_code == 200
        session_uuid = resp.get_json()["data"]["session_uuid"]
        assert session_uuid is not None

    def test_chat_continues_existing_session(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch("app.services.ai_service.RAGService.semantic_search", return_value=[]),
            patch("app.services.ai_service.RAGService.build_context_for_query", return_value=""),
        ):

            # First message creates session
            resp1 = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "How do I change my password?",
                },
                headers=auth_headers_employee,
            )
            session_uuid = resp1.get_json()["data"]["session_uuid"]

            # Second message continues same session
            resp2 = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "What if I forgot my old password?",
                    "session_uuid": session_uuid,
                },
                headers=auth_headers_employee,
            )

        assert resp2.status_code == 200
        assert resp2.get_json()["data"]["session_uuid"] == session_uuid

    def test_chat_requires_auth(self, client):
        resp = client.post("/api/v1/ai/chat", json={"query": "Help me with VPN"})
        assert resp.status_code == 401

    def test_chat_query_too_short(self, client, auth_headers_employee):
        resp = client.post("/api/v1/ai/chat", json={"query": "Hi"}, headers=auth_headers_employee)
        assert resp.status_code == 400

    def test_chat_response_includes_rag_sources(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch(
                "app.services.ai_service.RAGService.semantic_search", return_value=MOCK_RAG_RESULTS
            ),
            patch(
                "app.services.ai_service.RAGService.build_context_for_query", return_value="Context"
            ),
        ):

            resp = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "VPN configuration help needed",
                },
                headers=auth_headers_employee,
            )

        data = resp.get_json()["data"]
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0
        assert "content_preview" in data["sources"][0]
        assert "score" in data["sources"][0]


class TestAISessions:
    """Tests for AI session management endpoints."""

    def test_list_sessions(self, client, auth_headers_employee):
        resp = client.get("/api/v1/ai/sessions", headers=auth_headers_employee)
        assert resp.status_code == 200
        assert isinstance(resp.get_json()["data"], list)

    def test_get_session_history(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch("app.services.ai_service.RAGService.semantic_search", return_value=[]),
            patch("app.services.ai_service.RAGService.build_context_for_query", return_value=""),
        ):

            chat_resp = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "How do I submit a support ticket?",
                },
                headers=auth_headers_employee,
            )
            session_uuid = chat_resp.get_json()["data"]["session_uuid"]

        history_resp = client.get(
            f"/api/v1/ai/sessions/{session_uuid}", headers=auth_headers_employee
        )
        assert history_resp.status_code == 200
        messages = history_resp.get_json()["data"]
        assert len(messages) == 2  # user + assistant
        roles = {m["role"] for m in messages}
        assert "user" in roles
        assert "assistant" in roles

    def test_delete_session(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.ai_service.LLMService.chat_completion", return_value=MOCK_LLM_RESPONSE
            ),
            patch("app.services.ai_service.RAGService.semantic_search", return_value=[]),
            patch("app.services.ai_service.RAGService.build_context_for_query", return_value=""),
        ):

            chat_resp = client.post(
                "/api/v1/ai/chat",
                json={
                    "query": "Session to be deleted shortly.",
                },
                headers=auth_headers_employee,
            )
            session_uuid = chat_resp.get_json()["data"]["session_uuid"]

        del_resp = client.delete(
            f"/api/v1/ai/sessions/{session_uuid}", headers=auth_headers_employee
        )
        assert del_resp.status_code == 204


class TestTicketClassification:
    """Tests for AI ticket classification endpoints."""

    def _create_ticket(self, client, headers):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Laptop screen is completely black after login",
                "description": "My laptop screen goes completely black right after I log in. The backlight seems off.",
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_agent_can_classify_ticket(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)

        mock_classification = {
            "category": "Hardware",
            "priority": "high",
            "department_name": "IT Support",
            "confidence": 0.87,
            "reasoning": "Screen blackout is a hardware display issue.",
            "model": "llama-3.3-70b-versatile",
            "prompt_tokens": 120,
            "completion_tokens": 60,
            "latency_ms": 350,
        }

        with patch(
            "app.services.llm_service.LLMService.classify_ticket", return_value=mock_classification
        ):
            resp = client.post(
                f"/api/v1/ai/tickets/{ticket_id}/classify",
                headers=auth_headers_agent,
            )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["predicted_category"] == "Hardware"
        assert data["predicted_priority"] == "high"
        assert data["confidence_score"] == pytest.approx(0.87, abs=0.01)

    def test_employee_cannot_classify_ticket(
        self, client, auth_headers_employee, auth_headers_agent
    ):
        ticket_id = self._create_ticket(client, auth_headers_agent)
        resp = client.post(
            f"/api/v1/ai/tickets/{ticket_id}/classify",
            headers=auth_headers_employee,
        )
        assert resp.status_code == 403

    def test_submit_classification_feedback(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)

        with patch(
            "app.services.llm_service.LLMService.classify_ticket",
            return_value={
                "category": "Software",
                "priority": "medium",
                "department_name": "IT",
                "confidence": 0.75,
                "reasoning": "Application crash is a software issue.",
                "model": "llama-3.3-70b-versatile",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "latency_ms": 300,
            },
        ):
            client.post(f"/api/v1/ai/tickets/{ticket_id}/classify", headers=auth_headers_agent)

        resp = client.post(
            f"/api/v1/ai/tickets/{ticket_id}/classification/feedback",
            json={"was_accepted": True},
            headers=auth_headers_agent,
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["was_accepted"] is True


class TestTicketSuggestions:
    """Tests for AI ticket response suggestions."""

    def _create_ticket(self, client, headers):
        resp = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Cannot access company SharePoint portal",
                "description": "Getting 403 Forbidden when trying to access SharePoint. Worked yesterday.",
            },
            headers=headers,
        )
        return resp.get_json()["data"]["id"]

    def test_suggest_response_for_ticket(self, client, auth_headers_agent):
        ticket_id = self._create_ticket(client, auth_headers_agent)

        with (
            patch(
                "app.services.llm_service.LLMService.chat_completion",
                return_value=MOCK_LLM_RESPONSE,
            ),
            patch("app.services.rag_service.RAGService.build_context_for_query", return_value=""),
        ):

            resp = client.post(
                f"/api/v1/ai/tickets/{ticket_id}/suggest-response",
                headers=auth_headers_agent,
            )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "suggestion" in data
        assert "ticket_number" in data
        assert len(data["suggestion"]) > 0


class TestResolutionGuide:
    """Tests for AI resolution guide endpoint."""

    def test_get_resolution_guide(self, client, auth_headers_employee):
        with (
            patch(
                "app.services.llm_service.LLMService.chat_completion",
                return_value=MOCK_LLM_RESPONSE,
            ),
            patch("app.services.rag_service.RAGService.build_context_for_query", return_value=""),
        ):

            resp = client.post(
                "/api/v1/ai/resolution-guide",
                json={
                    "issue_description": "My Outlook keeps crashing every time I open an email with attachments.",
                    "include_rag": False,
                },
                headers=auth_headers_employee,
            )

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "resolution_guide" in data
        assert "issue_description" in data

    def test_resolution_guide_requires_auth(self, client):
        resp = client.post(
            "/api/v1/ai/resolution-guide",
            json={
                "issue_description": "My VPN is not connecting properly.",
            },
        )
        assert resp.status_code == 401
