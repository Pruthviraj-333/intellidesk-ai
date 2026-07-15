"""
IntelliDesk AI — LLM Service Unit Tests
Tests for ticket classification, response suggestion, and model fallback logic.
"""

import json
from unittest.mock import MagicMock, call, patch

import pytest


class TestTicketClassification:
    """Tests for LLMService.classify_ticket()"""

    def _mock_groq_response(self, content: dict, model="llama-3.3-70b-versatile"):
        """Build a mock LLM result dict."""
        return {
            "content": json.dumps(content),
            "model": model,
            "prompt_tokens": 100,
            "completion_tokens": 60,
            "latency_ms": 300,
        }

    def test_classify_returns_structured_result(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            mock_result = self._mock_groq_response(
                {
                    "category": "Hardware",
                    "priority": "high",
                    "department_name": "IT Support",
                    "confidence": 0.9,
                    "reasoning": "Screen blackout is a hardware issue.",
                }
            )
            with patch.object(LLMService, "chat_completion", return_value=mock_result):
                result = LLMService.classify_ticket(
                    "Screen goes black", "Laptop screen goes black on login"
                )
            assert result["category"] == "Hardware"
            assert result["priority"] == "high"
            assert result["confidence"] == 0.9

    def test_classify_falls_back_on_json_error(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            # LLM returns malformed JSON
            bad_result = {
                "content": "I think this is a hardware issue",
                "model": "llama-3.3-70b-versatile",
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "latency_ms": 200,
            }
            with patch.object(LLMService, "chat_completion", return_value=bad_result):
                result = LLMService.classify_ticket("Screen issue", "Laptop broken")
            # Should return safe defaults
            assert result["category"] == "General"
            assert result["priority"] == "medium"
            assert result["confidence"] == 0.0

    def test_classify_handles_groq_failure_gracefully(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            with patch.object(LLMService, "chat_completion", side_effect=RuntimeError("Groq down")):
                result = LLMService.classify_ticket("Issue", "Description of the issue")
            # Should return defaults, not raise
            assert result["category"] == "General"
            assert result["confidence"] == 0.0


class TestChatCompletion:
    """Tests for LLMService.chat_completion() with fallback logic."""

    def test_primary_model_used_on_success(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService, get_groq_client

            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Hello from LLM"
            mock_response.usage.prompt_tokens = 50
            mock_response.usage.completion_tokens = 30

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response

            with patch("app.services.llm_service.get_groq_client", return_value=mock_client):
                result = LLMService.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                    model="llama-3.3-70b-versatile",
                )
            assert result["content"] == "Hello from LLM"
            assert result["model"] == "llama-3.3-70b-versatile"
            assert result["prompt_tokens"] == 50

    def test_fallback_model_used_on_primary_failure(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Fallback response"
            mock_response.usage.prompt_tokens = 40
            mock_response.usage.completion_tokens = 20

            mock_client = MagicMock()
            # First call (primary) fails, second call (fallback) succeeds
            mock_client.chat.completions.create.side_effect = [
                Exception("Primary model unavailable"),
                mock_response,
            ]

            with patch("app.services.llm_service.get_groq_client", return_value=mock_client):
                result = LLMService.chat_completion(
                    messages=[{"role": "user", "content": "Test"}],
                    use_fallback=True,
                )
            assert result["content"] == "Fallback response"

    def test_raises_when_all_models_fail(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API error")

            with patch("app.services.llm_service.get_groq_client", return_value=mock_client):
                with pytest.raises(RuntimeError) as exc_info:
                    LLMService.chat_completion(
                        messages=[{"role": "user", "content": "Test"}],
                        use_fallback=True,
                    )
                assert "LLM service unavailable" in str(exc_info.value)


class TestResponseSuggestion:
    """Tests for LLMService.generate_ticket_response_suggestion()"""

    def test_suggestion_includes_context(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            mock_result = {
                "content": "Here is how to resolve your issue...",
                "model": "llama-3.3-70b-versatile",
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "latency_ms": 500,
            }

            captured_messages = []

            def capture_messages(messages, **kwargs):
                captured_messages.extend(messages)
                return mock_result

            with patch.object(LLMService, "chat_completion", side_effect=capture_messages):
                result = LLMService.generate_ticket_response_suggestion(
                    ticket_title="VPN not working",
                    ticket_description="Cannot connect to VPN",
                    context="To reset VPN go to Settings > Network.",
                )

            assert result == "Here is how to resolve your issue..."
            # Verify context was included in prompt
            full_prompt = " ".join(m["content"] for m in captured_messages)
            assert "Settings > Network" in full_prompt


class TestSummarizeThread:
    """Tests for LLMService.summarize_ticket_thread()"""

    def test_summarize_includes_thread_content(self, app):
        with app.app_context():
            from app.services.llm_service import LLMService

            mock_result = {
                "content": "• User reported VPN issue\n• Agent investigated config",
                "model": "llama-3.3-70b-versatile",
                "prompt_tokens": 180,
                "completion_tokens": 60,
                "latency_ms": 300,
            }

            captured = []

            def capture(messages, **kwargs):
                captured.extend(messages)
                return mock_result

            comments = [
                {
                    "author": "Alice",
                    "role": "Employee",
                    "body": "VPN not working",
                    "created_at": "2026-07-01 09:00",
                },
                {
                    "author": "Bob",
                    "role": "Agent",
                    "body": "Checking the config",
                    "created_at": "2026-07-01 09:15",
                },
            ]

            with patch.object(LLMService, "chat_completion", side_effect=capture):
                result = LLMService.summarize_ticket_thread("VPN Issue", comments)

            assert "VPN" in result
            full_prompt = " ".join(m["content"] for m in captured)
            assert "Alice" in full_prompt
            assert "Bob" in full_prompt
