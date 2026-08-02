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

### Ticket Creation — Agentic Mode
You CAN help users raise IT support tickets by collecting the required details through natural conversation.

**How ticket creation works:**
1. When a user wants to report an issue or escalate, ask follow-up questions ONE AT A TIME to understand:
   - A clear issue title
   - A detailed description (device/system affected, when it started, scope/impact)
   - Urgency (how much it is impacting work)
2. Once you have enough detail (at minimum a clear title and description), say exactly:
   **"I have all the details I need — I'm raising a ticket for you now."**
3. The system backend WILL automatically create the real ticket at that moment.
4. If the user later asks "did you create the ticket?" or "what is the ticket number?", tell them:
   **"Yes, the ticket was raised successfully. You can view it and get the ticket number on the Tickets page from the left sidebar."**
5. Do NOT say you cannot confirm or that you have no access — the ticket IS created when you signal it.

### Critical Rules
- NEVER fabricate ticket numbers — the system generates them.
- NEVER say "I cannot confirm" after you have already said you're raising a ticket — it WAS created.
- If you cannot gather enough detail after 3 questions, ask the user to go to the Tickets page directly.

Always structure your answers with clean Markdown syntax:
- Use clear line breaks between paragraphs and steps.
- Put each step or list item on its own new line (e.g. 1. **Step name**: Description).
- Use bold text for key terms or step headings.
- Use section headers (e.g. ### Steps to Resolve) to group information logically.
- Use inline code (`code`) or code blocks for commands and technical settings.

When you are unsure about a technical solution, acknowledge it and suggest escalating to a human agent."""



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
    def extract_ticket_intent(
        conversation_history: list[dict],
        force: bool = False,
    ) -> Optional[dict]:
        """
        Analyse the conversation history to detect ticket creation intent and extract fields.

        Args:
            conversation_history: List of {role, content} message dicts.
            force: If True, skip the explicit-intent requirement — used when the AI has
                   already signalled it is raising a ticket. Just extract the fields.

        Returns:
            None — if not ready (intent absent or missing required fields)
            dict — {title, description, priority, category}
        """
        import json

        # Build a compact conversation summary for the classifier
        convo_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in conversation_history[-14:]  # last 14 messages for full context
        )

        if force:
            # The AI has already decided to raise a ticket — just extract the fields
            prompt = f"""An IT support assistant has decided to raise a ticket based on this conversation.
Extract the ticket fields from the conversation.

Conversation:
{convo_text}

Rules:
- Extract realistic values only from what was discussed — do not invent details.
- Combine all issue details into a comprehensive description.
- priority must be one of: critical, high, medium, low (infer from impact described)
- category must be one of: Hardware, Software, Network, Access/Permissions, Email, Database, Security, General

Respond ONLY with this JSON (no markdown, no explanation):
{{
  "ready": true,
  "title": "<short descriptive ticket title>",
  "description": "<detailed description summarising the issue from the conversation>",
  "priority": "<critical|high|medium|low>",
  "category": "<one of the allowed categories>"
}}"""
        else:
            # Standard mode — require explicit user intent
            prompt = f"""Review this IT support conversation and determine if a support ticket should be created.

Conversation:
{convo_text}

Rules:
- Only return ready=true if the user explicitly wants to create/raise/escalate a ticket AND you can extract a clear title and description.
- If the user is just asking for help (not requesting ticket creation), return ready=false.
- Extract realistic values only from what the user actually said — do not invent details.
- priority must be one of: critical, high, medium, low
- category must be one of: Hardware, Software, Network, Access/Permissions, Email, Database, Security, General

Respond ONLY with this JSON (no markdown, no explanation):
{{
  "ready": <true or false>,
  "title": "<short descriptive ticket title or null>",
  "description": "<detailed description from conversation or null>",
  "priority": "<critical|high|medium|low>",
  "category": "<one of the allowed categories>"
}}"""

        messages = [
            {
                "role": "system",
                "content": "You are a precise IT ticket intent classifier. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=300,
                use_fallback=True,
            )
            raw = result["content"].strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            parsed = json.loads(raw)
            if parsed.get("ready") and parsed.get("title") and parsed.get("description"):
                return {
                    "title": parsed["title"],
                    "description": parsed["description"],
                    "priority": parsed.get("priority", "medium"),
                    "category": parsed.get("category", "General"),
                }
            return None
        except Exception as e:
            logger.warning(f"extract_ticket_intent failed: {e}")
            return None


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

    @staticmethod
    def summarize_incident(
        incident_title: str,
        incident_description: str,
        severity: str,
        affected_services: str,
        timeline_events: list[dict],
    ) -> dict:
        """
        Generate an AI-powered executive summary for an incident.

        Returns:
            {executive_summary, timeline_summary, impact_analysis, action_items}
        """
        import json

        timeline_text = "\n".join(
            f"[{e.get('created_at', '')}] {e.get('event_type', '').upper()}: {e.get('description', '')}"
            for e in timeline_events
        ) or "No timeline events recorded."

        prompt = f"""Analyze this IT incident and generate a structured executive summary.

Incident: {incident_title}
Severity: {severity}
Affected Services: {affected_services or 'Not specified'}
Description: {incident_description}

Timeline:
{timeline_text}

Respond ONLY with valid JSON (no markdown):
{{
  "executive_summary": "<2-3 sentence executive summary>",
  "timeline_summary": "<brief chronological narrative of what happened>",
  "impact_analysis": "<what was affected and business impact>",
  "action_items": ["<action 1>", "<action 2>", "<action 3>"]
}}"""

        messages = [
            {"role": "system", "content": "You are a precise IT incident analyst. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(messages=messages, temperature=0.2, max_tokens=600)
            return json.loads(result["content"].strip())
        except Exception as e:
            logger.error(f"Incident summarization failed: {e}")
            return {
                "executive_summary": "AI summary unavailable.",
                "timeline_summary": "",
                "impact_analysis": "",
                "action_items": [],
            }

    @staticmethod
    def generate_ticket_email(
        email_type: str,
        ticket_title: str,
        ticket_number: str,
        requester_name: str,
        agent_name: str = "",
        resolution_notes: str = "",
    ) -> dict:
        """
        Generate a professional email draft for ticket events.

        Args:
            email_type: One of 'status_update', 'escalation', 'resolution', 'follow_up'
        Returns:
            {subject, body}
        """
        import json

        context_map = {
            "status_update": "A status update email informing the user of progress",
            "escalation": "An escalation notice explaining why this ticket has been escalated to senior support",
            "resolution": f"A resolution notification. Resolution notes: {resolution_notes}",
            "follow_up": "A friendly follow-up checking if the user's issue is fully resolved",
        }
        email_context = context_map.get(email_type, "A professional support email")

        prompt = f"""Write {email_context} for this IT support ticket.

Ticket: {ticket_number} — {ticket_title}
User: {requester_name}
Agent: {agent_name or 'Support Team'}

Return ONLY valid JSON:
{{
  "subject": "<professional email subject>",
  "body": "<complete professional email body in plain text, with greeting and sign-off>"
}}"""

        messages = [
            {"role": "system", "content": "You are a professional IT support email writer. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(messages=messages, temperature=0.5, max_tokens=400)
            return json.loads(result["content"].strip())
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return {
                "subject": f"Update on your ticket: {ticket_number}",
                "body": f"Dear {requester_name},\n\nWe are writing regarding your ticket '{ticket_title}'.\n\nBest regards,\nSupport Team",
            }

    @staticmethod
    def extract_action_items(
        ticket_title: str,
        comments: list[dict],
        context: str = "",
    ) -> list[dict]:
        """
        Extract structured action items from a ticket's comment thread.

        Returns:
            List of {action, suggested_assignee, priority, status}
        """
        import json

        thread_text = "\n".join(
            f"[{c.get('created_at', '')}] {c.get('author', '')} ({c.get('role', '')}): {c.get('body', '')}"
            for c in comments
        ) or "No comments."

        prompt = f"""Extract all action items and tasks from this IT support ticket thread.

Ticket: {ticket_title}

Thread:
{thread_text}

Return ONLY valid JSON array (no markdown):
[
  {{
    "action": "<clear action description>",
    "suggested_assignee": "<role or person name if mentioned, else 'Unassigned'>",
    "priority": "<high|medium|low>",
    "status": "pending"
  }}
]

If no action items found, return an empty array []."""

        messages = [
            {"role": "system", "content": "You are a precise IT operations analyst. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(messages=messages, temperature=0.2, max_tokens=500)
            parsed = json.loads(result["content"].strip())
            return parsed if isinstance(parsed, list) else []
        except Exception as e:
            logger.error(f"Action item extraction failed: {e}")
            return []

    @staticmethod
    def analyze_root_cause(
        problem_title: str,
        problem_description: str,
        linked_incidents: list[dict],
        kb_context: str = "",
    ) -> dict:
        """
        AI-powered root cause analysis for a Problem record.

        Returns:
            {root_cause_hypothesis, contributing_factors, remediation_steps, prevention_recommendations}
        """
        import json

        incidents_text = "\n".join(
            f"- [{i.get('incident_number', '')}] {i.get('title', '')} (Severity: {i.get('severity', '')})"
            for i in linked_incidents
        ) or "No linked incidents."

        kb_section = f"\n\nKnowledge Base Context:\n{kb_context}" if kb_context else ""

        prompt = f"""Perform a root cause analysis for this IT problem.

Problem: {problem_title}
Description: {problem_description}

Linked Incidents:
{incidents_text}{kb_section}

Respond ONLY with valid JSON:
{{
  "root_cause_hypothesis": "<most likely root cause in 2-3 sentences>",
  "contributing_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "remediation_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "prevention_recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}"""

        messages = [
            {"role": "system", "content": "You are an expert IT root cause analyst. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            result = LLMService.chat_completion(messages=messages, temperature=0.2, max_tokens=600)
            return json.loads(result["content"].strip())
        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            return {
                "root_cause_hypothesis": "AI analysis unavailable.",
                "contributing_factors": [],
                "remediation_steps": [],
                "prevention_recommendations": [],
            }
