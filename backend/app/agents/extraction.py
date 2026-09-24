"""
Extraction Agent for MeetMind AI.

Pattern: ReAct
Model: gemini-3.5-flash-lite (via ProviderGateway with use_case="sub_agent")

Responsibilities:
- Reads user mentions, user identity context, and transcript.
- Analyzes context to extract tasks assigned to or relevant to the user.
- Extracts priority (high/medium/low) based on urgency language.
- Extracts deadlines where present.
- Extracts key highlights (decisions, milestones, announcements).
- Caches unconfirmed extraction preview for HITL confirmation.
- Updates state with extracted_tasks and extracted_highlights.
- Sets session_action = "confirm".
"""

import json
import re
from datetime import date, timedelta
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.config import SUB_AGENT_MODEL
from app.core.constants import TaskPriority
from app.core.logging import get_logger
from app.core.providers import get_provider_gateway
from app.db.models.meeting import Meeting
from app.db.models.transcript_chunk import TranscriptChunk
from app.graph.state import MeetMindState

logger = get_logger(__name__)


class ExtractionAgent:
    """
    Extraction Agent responsible for identifying actionable tasks and meeting highlights.
    """

    model_name: str = SUB_AGENT_MODEL

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        Executes extraction reasoning:
        1. Gathers transcript context and user mentions.
        2. Performs task and highlight extraction.
        3. Assigns priorities and deadlines.
        4. Updates state and caches unconfirmed preview for HITL confirmation.
        """
        meeting_id_str = state.get("meeting_id", "")
        user_name = state.get("user_name", "User")
        user_role = state.get("user_role", "")
        user_mentions = state.get("user_mentions", [])
        raw_transcript = state.get("raw_transcript", "")

        logger.info(f"ExtractionAgent running for meeting {meeting_id_str}, user '{user_name}'")

        # 1. Fetch transcript context from DB if not in state
        if db and meeting_id_str and not raw_transcript:
            try:
                import uuid
                meeting_uuid = uuid.UUID(meeting_id_str)
                meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
                if meeting and meeting.raw_transcript:
                    raw_transcript = meeting.raw_transcript
            except Exception as exc:
                logger.warning(f"Error loading transcript for extraction: {exc}")

        # 2. Extract tasks and highlights
        extracted_tasks, extracted_highlights = cls._extract_with_fallback(
            meeting_id=meeting_id_str,
            user_name=user_name,
            user_role=user_role,
            mentions=user_mentions,
            transcript=raw_transcript,
        )

        logger.info(
            f"Extraction complete: {len(extracted_tasks)} tasks, "
            f"{len(extracted_highlights)} highlights extracted."
        )

        # 3. Cache unconfirmed preview in ExtractionService state store
        from app.services.extraction_service import ExtractionService
        import uuid
        try:
            m_uuid = uuid.UUID(meeting_id_str)
            ExtractionService.set_extraction_preview(
                meeting_id=m_uuid,
                tasks=extracted_tasks,
                highlights=extracted_highlights,
            )
        except Exception as exc:
            logger.warning(f"Failed to cache extraction preview in service: {exc}")

        return {
            "extracted_tasks": extracted_tasks,
            "extracted_highlights": extracted_highlights,
            "extraction_complete": True,
            "current_stage": "extraction",
            "session_action": "confirm",
        }

    @classmethod
    def _extract_with_fallback(
        cls,
        meeting_id: str,
        user_name: str,
        user_role: str,
        mentions: list[str],
        transcript: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Attempts AI extraction via ProviderGateway; falls back to deterministic
        heuristic extraction if provider is unavailable or in offline test mode.
        """
        try:
            gateway = get_provider_gateway()
            tasks, highlights = cls._extract_with_llm(
                gateway=gateway,
                user_name=user_name,
                user_role=user_role,
                mentions=mentions,
                transcript=transcript,
            )
            if tasks or highlights:
                return tasks, highlights
        except Exception as exc:
            logger.info(f"LLM extraction skipped or unavailable ({exc}); using heuristic extraction")

        return cls._extract_heuristically(
            user_name=user_name,
            mentions=mentions,
            transcript=transcript,
        )

    @classmethod
    def _extract_with_llm(
        cls,
        gateway: Any,
        user_name: str,
        user_role: str,
        mentions: list[str],
        transcript: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Executes LLM extraction via ProviderGateway using SUB_AGENT_MODEL."""
        context_text = "\n".join(mentions[:10]) if mentions else transcript[:2000]

        prompt = f"""You are an executive assistant extracting action items from a meeting transcript.
Target User: {user_name} (Role: {user_role})

User Mentions & Dialogue Context:
{context_text}

Extract any action items specifically assigned to or relevant to {user_name}.
Also extract 1-2 key meeting decisions or highlights relevant to the team.

Output strictly valid JSON with this format:
{{
  "tasks": [
    {{
      "title": "Short title",
      "description": "Clear 1-2 sentence description",
      "priority": "high" | "medium" | "low",
      "deadline": "YYYY-MM-DD" or null
    }}
  ],
  "highlights": [
    {{
      "content": "Key decision or announcement",
      "relevance_reason": "Why this matters"
    }}
  ]
}}
"""

        def _call_gemini(api_key: str, model_str: Optional[str]) -> str:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_str or cls.model_name)
            resp = model.generate_content(prompt)
            return resp.text

        response_text = gateway.execute("sub_agent", _call_gemini)
        # Parse JSON from response
        clean_text = response_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_text)
        tasks = data.get("tasks", [])
        for idx, t in enumerate(tasks):
            t["id"] = str(idx)
            t["confidence_score"] = 0.95

        highlights = data.get("highlights", [])
        return tasks, highlights

    @classmethod
    def _extract_heuristically(
        cls,
        user_name: str,
        mentions: list[str],
        transcript: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Deterministic rule-based extraction for offline testing or when provider is unavailable.
        """
        tasks: list[dict[str, Any]] = []
        highlights: list[dict[str, Any]] = []

        combined_lines = mentions if mentions else [line.strip() for line in transcript.splitlines() if line.strip()]

        task_patterns = [
            (r"(?:action item|todo|will take care of|needs to|please|assigned to|follow up on)\s*[:\-]?\s*(.*)", TaskPriority.HIGH),
            (r"(?:prepare|review|submit|complete|send|finalize|update)\s+(.*)", TaskPriority.MEDIUM),
            (r"(?:look into|check|consider|investigate)\s+(.*)", TaskPriority.LOW),
        ]

        today = date.today()

        for idx, line in enumerate(combined_lines):
            line_clean = line.strip()
            # Task extraction
            for pattern, prio in task_patterns:
                match = re.search(pattern, line_clean, re.IGNORECASE)
                if match:
                    action_text = match.group(1).strip()
                    if len(action_text) > 5 and len(tasks) < 5:
                        # Extract deadline if urgency words found
                        deadline_val: Optional[str] = None
                        if any(w in line_clean.lower() for w in ("tomorrow", "urgent", "24h", "asap")):
                            deadline_val = (today + timedelta(days=1)).isoformat()
                        elif "by end of week" in line_clean.lower() or "friday" in line_clean.lower():
                            deadline_val = (today + timedelta(days=5)).isoformat()

                        # Priority tuning
                        if any(w in line_clean.lower() for w in ("urgent", "asap", "critical")):
                            prio = TaskPriority.HIGH

                        tasks.append({
                            "id": str(len(tasks)),
                            "title": action_text[:80].capitalize(),
                            "description": f"Action assigned in context: '{line_clean}'",
                            "priority": prio.value,
                            "deadline": deadline_val,
                            "confidence_score": 0.85,
                        })
                    break

            # Highlight extraction
            if any(w in line_clean.lower() for w in ("decided", "agreed", "launched", "milestone", "announced", "status")):
                if len(highlights) < 3:
                    highlights.append({
                        "content": line_clean,
                        "relevance_reason": "Team decision or announcement identified during meeting",
                    })

        # Ensure at least one fallback item if nothing matched
        if not tasks and mentions:
            tasks.append({
                "id": "0",
                "title": f"Follow up on discussion for {user_name}",
                "description": f"Review points raised in: {mentions[0]}",
                "priority": TaskPriority.MEDIUM.value,
                "deadline": (today + timedelta(days=3)).isoformat(),
                "confidence_score": 0.75,
            })

        if not highlights:
            highlights.append({
                "content": f"Meeting conducted with {user_name} participant engagement.",
                "relevance_reason": "General meeting context",
            })

        return tasks, highlights
