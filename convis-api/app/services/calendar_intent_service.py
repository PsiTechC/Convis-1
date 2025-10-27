"""
Service that infers calendar booking details from ongoing conversations.
Used by realtime call handlers to detect when a meeting should be scheduled.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class CalendarIntentService:
    """Extract structured appointment details from a conversation transcript."""

    def __init__(self) -> None:
        self._default_model = "gpt-4o-mini"

    async def extract_from_conversation(
        self,
        messages: List[Dict[str, str]],
        openai_api_key: str,
        timezone: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze the recent conversation to determine if a calendar event should be created.

        Args:
            messages: Ordered list of {"role": str, "text": str} entries.
            openai_api_key: API key to call OpenAI with.
            timezone: Preferred timezone hint (IANA string). Optional.

        Returns:
            Parsed dict with keys:
                should_schedule (bool)
                reason (str)
                appointment (dict with title, start_iso, end_iso, timezone, notes)
                confirmation_text (str)
        """
        if not messages:
            return None

        api_key = openai_api_key or settings.openai_api_key
        if not api_key:
            logger.warning("No OpenAI API key available for calendar intent extraction")
            return None

        # Keep only the most recent exchanges to limit prompt size.
        window = messages[-12:]
        conversation_lines = [
            f"{entry['role'].upper()}: {entry['text'].strip()}"
            for entry in window
            if entry.get("text")
        ]
        conversation_snippet = "\n".join(conversation_lines)

        prompt = f"""You are assisting an AI voice agent that schedules calendar events.
Review the recent call transcript and determine whether the caller has confirmed a meeting or appointment.

Provide a JSON object with the following structure:
{{
  "should_schedule": true | false,
  "reason": "Short explanation",
  "appointment": {{
    "title": "Concise meeting title",
    "start_iso": "YYYY-MM-DDTHH:MM:SS",
    "end_iso": "YYYY-MM-DDTHH:MM:SS",
    "timezone": "IANA timezone string",
    "duration_minutes": 30,
    "attendees": ["email@example.com"],
    "notes": "Optional notes or summary"
  }},
  "confirmation_text": "One sentence the assistant can say to confirm scheduling."
}}

Rules:
- Return "should_schedule": false if any essential detail (date, time) is missing or ambiguous.
- Infer duration only if stated; otherwise default to 30 minutes.
- For timezone, prefer the provided hint "{timezone}" if details are unclear. Otherwise infer from dialogue.
- Never fabricate impossible dates (e.g., February 30).
- start_iso and end_iso must be ISO 8601 (no timezone offset, separate timezone field).
- When should_schedule is false, set appointment to null.

CONVERSATION:
{conversation_snippet}

Respond with ONLY the JSON object."""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._default_model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert assistant that extracts structured appointment data "
                        "from live call transcripts. Always obey the output schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed: Dict[str, Any] = json.loads(raw_content)

                # Basic validation to guard against malformed outputs.
                if not isinstance(parsed, dict):
                    raise ValueError("Parsed result is not a dict")

                if parsed.get("should_schedule") and not parsed.get("appointment"):
                    logger.debug("Model indicated scheduling but omitted appointment payload; ignoring.")
                    return None

                return parsed
        except Exception as exc:
            logger.error(f"Error extracting calendar intent: {exc}")
            return None

