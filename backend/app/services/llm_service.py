"""
IntelliDesk AI — Groq LLM Service
Provider-abstracted LLM client using Groq API.
Implements: chat, ticket classification, smart summarization, and suggestions.
"""

import time
from typing import Optional

from flask import current_app

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Groq client singleton
_groq_client = None


def get_groq_client():
    """Lazy-initialize and return the Groq API client."""
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        api_key = current_app.config.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


class LLMService:
    """
    Abstraction layer for Groq LLM API calls.
    All prompts are structured to return JSON where needed for reliability.
    """

    SYSTEM_PROMPT = """You are IntelliDesk AI, an intelligent IT service desk assistant.
Your role is to help IT staff and employees resolve technical issues efficiently.
You have access to the company's knowledge base and can provide step-by-step guidance.
Always be professional, concise, and solution-focused.
When you are unsure, acknowledge it and suggest escalating to a human agent."""

    @staticmethod
    def chat_completion(
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_fallback: bool = True,
    ) -> dict:
        """
        Send messages to Groq and return the response with token metadata.

        Args:
            messages: List of {role, content} dicts (OpenAI-compatible format).
            model: Override the default model.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens in completion.
            use_fallback: Fall back to smaller model if primary fails.

        Returns:
            {content, model, prompt_tokens, completion_tokens, latency_ms}
        """
        client = get_groq_client()
        primary_model = model or current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        fallback_model = current_app.config.get("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")

        models_to_try = [primary_model]
        if use_fallback and primary_model != fallback_model:
            models_to_try.append(fallback_model)

        last_error = None
        for attempt_model in models_to_try:
            try:
                t0 = time.monotonic()
                response = client.chat.completions.create(
                    model=attempt_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)

                return {
                    "content": response.choices[0].message.content,
                    "model": attempt_model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "latency_ms": latency_ms,
                }
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed with model '{attempt_model}': {e}")
                continue

        logger.error(f"All LLM models failed. Last error: {last_error}")
        raise RuntimeError(f"LLM service unavailable: {last_error}")

    @staticmethod
    def classify_ticket(ticket_title: str, ticket_description: str) -> dict:
        """
        Use LLM to classify a ticket: category, priority, and department suggestion.

        Returns:
            {category, priority, department_name, confidence, reasoning}
        """
        import json

        prompt = f"""Analyze this IT support ticket and classify it.
Return your response ONLY as valid JSON with these exact keys.

Ticket Title: {ticket_title}
Ticket Description: {ticket_description}

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "category": "<one of: Hardware, Software, Network, Access/Permissions, Email, Database, Security, General>",
  "priority": "<one of: critical, high, medium, low>",
  "department_name": "<suggested department name>",
  "confidence": <0.0-1.0 float>,
  "reasoning": "<one sentence explaining the classification>"
}}"""

        messages = [
            {
                "role": "system",
                "content": "You are a precise IT ticket classifier. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(
                messages=messages,
                temperature=0.1,  # Low temp for deterministic classification
                max_tokens=256,
            )
            parsed = json.loads(result["content"].strip())
            parsed["model"] = result["model"]
            parsed["prompt_tokens"] = result["prompt_tokens"]
            parsed["completion_tokens"] = result["completion_tokens"]
            parsed["latency_ms"] = result["latency_ms"]
            return parsed
        except Exception as e:
            logger.error(f"Ticket classification failed: {e}")
            return {
                "category": "General",
                "priority": "medium",
                "department_name": None,
                "confidence": 0.0,
                "reasoning": "Classification failed — defaulting to General/Medium.",
                "model": None,
            }

    @staticmethod
    def generate_ticket_response_suggestion(
        ticket_title: str,
        ticket_description: str,
        context: str = "",
    ) -> str:
        """
        Generate a suggested agent reply for a ticket using RAG context.

        Args:
            ticket_title: Ticket title.
            ticket_description: Full ticket description.
            context: Relevant knowledge base context from RAG search.

        Returns:
            Suggested response text.
        """
        context_section = f"\n\nRelevant knowledge base context:\n{context}" if context else ""

        prompt = f"""A user submitted the following IT support ticket:

Title: {ticket_title}
Description: {ticket_description}{context_section}

Write a professional, helpful reply to this ticket. Be concise and solution-focused.
If the issue requires further investigation, say so. Do not make up technical details."""

        messages = [
            {"role": "system", "content": LLMService.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = LLMService.chat_completion(
            messages=messages,
            temperature=0.5,
            max_tokens=512,
        )
        return result["content"]

    @staticmethod
    def summarize_ticket_thread(ticket_title: str, comments: list[dict]) -> str:
        """
        Generate a concise summary of a ticket's comment thread for quick agent context.

        Args:
            ticket_title: Ticket title.
            comments: List of {author, role, body, created_at} dicts.

        Returns:
            Summarized thread as text.
        """
        thread_text = "\n".join(
            f"[{c['created_at']}] {c['author']} ({c['role']}): {c['body']}" for c in comments
        )

        prompt = f"""Summarize this IT support ticket thread in 3-5 bullet points.
Focus on: the problem, steps taken, current status, and open action items.

Ticket: {ticket_title}

Thread:
{thread_text}"""

        messages = [
            {"role": "system", "content": "You are a precise IT support analyst."},
            {"role": "user", "content": prompt},
        ]

        result = LLMService.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=400,
        )
        return result["content"]

    @staticmethod
    def get_resolution_steps(issue_description: str, context: str = "") -> str:
        """
        Generate step-by-step resolution guide for a known issue.
        Used by the AI assistant when a user describes a problem.
        """
        context_section = f"\n\nRelevant knowledge:\n{context}" if context else ""

        prompt = f"""An IT user has the following problem:

{issue_description}{context_section}

Provide a numbered, step-by-step troubleshooting guide to resolve this issue.
Keep steps clear and actionable. Include a final step to escalate if self-help fails."""

        messages = [
            {"role": "system", "content": LLMService.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = LLMService.chat_completion(
            messages=messages,
            temperature=0.4,
            max_tokens=600,
        )
        return result["content"]
