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

import re
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

        # If explicit participant name provided, use strict participant resolution
        explicit_person = state.get("person_name")
        if explicit_person:
            return cls._resolve_explicit_participant(
                explicit_name=explicit_person,
                meeting_id_str=meeting_id_str,
                state=state,
                db=db,
            )

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
            "identity_complete": True,
            "current_stage": "identity",
            "session_action": "extract",
        }

    @classmethod
    def _resolve_explicit_participant(
        cls,
        explicit_name: str,
        meeting_id_str: str,
        state: MeetMindState,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        """
        Resolves identity for an explicitly entered participant name:
        - Inspects meeting participants and transcript chunks/speakers.
        - Handles exact matches, known aliases/prefixes, and speaker labels.
        - Identifies ambiguous matches (multiple candidates) or missing identity.
        - Avoids substituting the logged-in user's profile.
        - Avoids returning tasks assigned to unrelated participants.
        """
        target = explicit_name.strip()
        target_lower = target.lower()
        meeting_uuid = uuid.UUID(meeting_id_str) if meeting_id_str else None

        participants: list[MeetingParticipant] = []
        chunks: list[TranscriptChunk] = []

        if db and meeting_uuid:
            try:
                participants = (
                    db.query(MeetingParticipant)
                    .filter(MeetingParticipant.meeting_id == meeting_uuid)
                    .all()
                )
                chunks = (
                    db.query(TranscriptChunk)
                    .filter(TranscriptChunk.meeting_id == meeting_uuid)
                    .order_by(TranscriptChunk.chunk_index.asc())
                    .all()
                )
            except Exception as exc:
                logger.warning(f"Error querying DB for explicit participant resolution: {exc}")

        # Gather all candidate names from participants, chunk speakers, and raw transcript
        candidate_names: set[str] = {p.name.strip() for p in participants if p.name}
        for chunk in chunks:
            if chunk.speaker_name and chunk.speaker_name.strip():
                for sp in chunk.speaker_name.split(","):
                    clean_sp = sp.strip().strip("[]")
                    if clean_sp:
                        candidate_names.add(clean_sp)

        raw_transcript = state.get("raw_transcript", "")
        if raw_transcript:
            for line in raw_transcript.splitlines():
                line_str = line.strip()
                speaker_match = re.match(r"^\[?([A-Za-z0-9_\s\.\-]{1,40})\]?:", line_str)
                if speaker_match:
                    candidate_names.add(speaker_match.group(1).strip())

        # 1. Exact match (case-insensitive)
        exact_matches = [c for c in candidate_names if c.lower() == target_lower]
        if not exact_matches:
            exact_matches = [c for c in candidate_names if c.lower().strip(":,.-") == target_lower]

        resolved_name: Optional[str] = None
        user_role: str = ""

        if len(exact_matches) == 1:
            resolved_name = exact_matches[0]
        elif len(exact_matches) > 1:
            resolved_name = exact_matches[0]
        else:
            # 2. Known alias / First name / Substring matching
            partial_matches: set[str] = set()
            for cand in candidate_names:
                cand_lower = cand.lower()
                cand_words = [w.strip("(),.:-") for w in cand_lower.split()]
                if target_lower in cand_words or cand_lower.startswith(target_lower + " "):
                    partial_matches.add(cand)

            if len(partial_matches) == 1:
                resolved_name = list(partial_matches)[0]
            elif len(partial_matches) > 1:
                # Ambiguous identity!
                logger.info(
                    f"Ambiguous identity for '{target}': multiple candidates {partial_matches}"
                )
                return {
                    "person_name": target,
                    "user_name": target,
                    "user_role": "",
                    "user_mentions": [],
                    "identity_confirmed": False,
                    "identity_complete": True,
                    "identity_status": "ambiguous",
                    "identity_message": f"Ambiguous participant identity for '{target}'. Multiple matching participants found: {', '.join(sorted(partial_matches))}.",
                    "current_stage": "identity",
                    "session_action": "extract",
                }
            else:
                # 3. Check if target_name is mentioned in transcript text as a word
                found_in_text = False
                word_pattern = re.compile(rf"\b{re.escape(target_lower)}\b", re.IGNORECASE)
                for chunk in chunks:
                    if word_pattern.search(chunk.content or ""):
                        found_in_text = True
                        break
                if not found_in_text and raw_transcript:
                    if word_pattern.search(raw_transcript):
                        found_in_text = True

                if found_in_text:
                    resolved_name = target
                else:
                    # Missing identity
                    logger.info(f"Participant '{target}' not found in meeting transcript or roster")
                    return {
                        "person_name": target,
                        "user_name": target,
                        "user_role": "",
                        "user_mentions": [],
                        "identity_confirmed": False,
                        "identity_complete": True,
                        "identity_status": "not_found",
                        "identity_message": f"Participant '{target}' was not found in meeting transcript or participant roster.",
                        "current_stage": "identity",
                        "session_action": "extract",
                    }

        # Resolve role if available from participant record
        for p in participants:
            if p.name.strip().lower() == resolved_name.lower():
                user_role = p.role or ""
                break

        # Collect user mentions specifically involving resolved_name or target
        user_mentions: list[str] = []
        name_keys = {target_lower, resolved_name.lower()}

        source_lines: list[str] = []
        if chunks:
            for chunk in chunks:
                for line in (chunk.content or "").splitlines():
                    source_lines.append(line.strip())
        elif raw_transcript:
            source_lines = [line.strip() for line in raw_transcript.splitlines()]

        for line_str in source_lines:
            if not line_str or line_str in user_mentions:
                continue

            spk_match = re.match(r"^\[?([A-Za-z0-9_\s\.\-]{1,40})\]?:\s*(.*)", line_str)
            if spk_match:
                spk = spk_match.group(1).strip().lower()
                body = spk_match.group(2)
                # Spoken by resolved user: include
                if any(k in spk for k in name_keys):
                    user_mentions.append(line_str)
                # Or body explicitly addresses/mentions resolved user: include
                elif any(re.search(rf"\b{re.escape(k)}\b", body, re.IGNORECASE) for k in name_keys):
                    user_mentions.append(line_str)
            else:
                if any(re.search(rf"\b{re.escape(k)}\b", line_str, re.IGNORECASE) for k in name_keys):
                    user_mentions.append(line_str)

        logger.info(
            f"IdentityAgent resolved explicit participant '{target}' -> '{resolved_name}' ({len(user_mentions)} mentions)"
        )

        return {
            "person_name": target,
            "user_name": resolved_name,
            "user_role": user_role,
            "user_mentions": user_mentions,
            "identity_confirmed": True,
            "identity_complete": True,
            "identity_status": "resolved",
            "identity_message": f"Participant '{resolved_name}' resolved.",
            "current_stage": "identity",
            "session_action": "extract",
        }
