"""
Identity Agent for MeetMind AI.

Pattern: Form-First Identity Matching
Model: gemini-3.5-flash-lite (via ProviderGateway with use_case="sub_agent")

Responsibilities:
- Reads user name and role from state or PostgreSQL meeting_participants / user.
- Searches transcript chunks for mentions of the user.
- Contextualizes user mentions (what was assigned to, asked of, or discussed by the user).
- Updates meeting_participants.is_current_user = True for the matching participant.
- Updates state with user_mentions and marks identity_confirmed = True.
- Sets session_action = "extract".
- Strictly follows form-first identity; NEVER prompts conversationally for identity.
"""

import uuid
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.config import SUB_AGENT_MODEL
from app.core.logging import get_logger
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.transcript_chunk import TranscriptChunk
from app.db.models.user import User
from app.graph.state import MeetMindState

logger = get_logger(__name__)


class IdentityAgent:
    """
    Identity Agent establishing user identity context and extracting mentions.
    """

    model_name: str = SUB_AGENT_MODEL

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        Executes identity resolution:
        1. Identifies user name & role from state or database.
        2. Scans transcript chunks for mentions of the user name.
        3. Marks is_current_user = True in meeting_participants.
        4. Updates state with user_mentions and identity_confirmed = True.
        """
        meeting_id_str = state.get("meeting_id", "")
        user_id_str = state.get("user_id", "")

        logger.info(f"IdentityAgent resolving identity for meeting {meeting_id_str}, user {user_id_str}")

        user_name = state.get("user_name", "")
        user_role = state.get("user_role", "")

        # 1. Fetch user details from DB if missing
        if db and user_id_str:
            try:
                user_uuid = uuid.UUID(user_id_str)
                user = db.query(User).filter(User.id == user_uuid).first()
                if user:
                    if not user_name:
                        user_name = user.name
                    role_val = getattr(user, "role", None)
                    if not user_role and role_val:
                        user_role = role_val
            except Exception as exc:
                logger.warning(f"Error querying User for identity: {exc}")

        # 2. Check MeetingParticipant table for participant identity
        if db and meeting_id_str:
            try:
                meeting_uuid = uuid.UUID(meeting_id_str)
                participant = (
                    db.query(MeetingParticipant)
                    .filter(
                        MeetingParticipant.meeting_id == meeting_uuid,
                        MeetingParticipant.is_current_user.is_(True),
                    )
                    .first()
                )
                if participant:
                    user_name = participant.name
                    user_role = participant.role or user_role
                elif user_name:
                    # Match by name and update is_current_user = True
                    matched_p = (
                        db.query(MeetingParticipant)
                        .filter(
                            MeetingParticipant.meeting_id == meeting_uuid,
                            MeetingParticipant.name.ilike(user_name),
                        )
                        .first()
                    )
                    if matched_p:
                        matched_p.is_current_user = True
                        db.commit()
                        user_role = matched_p.role or user_role
            except Exception as exc:
                if db:
                    db.rollback()
                logger.warning(f"Error resolving participant identity: {exc}")

        # Fallback default name if still empty
        if not user_name:
            user_name = "User"

        # 3. Search transcript chunks for user mentions
        user_mentions: list[str] = []
        name_lower = user_name.lower().strip()

        if db and meeting_id_str:
            try:
                meeting_uuid = uuid.UUID(meeting_id_str)
                chunks = (
                    db.query(TranscriptChunk)
                    .filter(TranscriptChunk.meeting_id == meeting_uuid)
                    .order_by(TranscriptChunk.chunk_index.asc())
                    .all()
                )
                for chunk in chunks:
                    chunk_text = chunk.content or ""
                    # Check if speaker is the user or user is mentioned in text
                    speaker_is_user = chunk.speaker_name and (
                        name_lower in chunk.speaker_name.lower()
                    )
                    content_mentions_user = name_lower in chunk_text.lower()

                    if speaker_is_user or content_mentions_user:
                        chunk.involves_user = True
                        # Extract sentences or lines containing the name
                        for line in chunk_text.splitlines():
                            if name_lower in line.lower() or speaker_is_user:
                                clean_line = line.strip()
                                if clean_line and clean_line not in user_mentions:
                                    user_mentions.append(clean_line)
                db.commit()
            except Exception as exc:
                if db:
                    db.rollback()
                logger.warning(f"Error scanning transcript chunks for mentions: {exc}")

        # If no DB chunks were available, scan raw_transcript from state
        if not user_mentions and state.get("raw_transcript"):
            raw = state.get("raw_transcript", "")
            for line in raw.splitlines():
                if name_lower in line.lower():
                    clean_line = line.strip()
                    if clean_line and clean_line not in user_mentions:
                        user_mentions.append(clean_line)

        logger.info(
            f"IdentityAgent identified {len(user_mentions)} mentions for user '{user_name}' ({user_role})"
        )

        return {
            "user_name": user_name,
            "user_role": user_role,
            "user_mentions": user_mentions,
            "identity_confirmed": True,
            "current_stage": "identity",
            "session_action": "extract",
        }
