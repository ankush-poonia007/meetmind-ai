"""
Ingestion Agent for MeetMind AI.

Pattern: ReAct
Model: gemini-3.5-flash-lite (via ProviderGateway with use_case="sub_agent")

Responsibilities:
- Reads raw meeting transcript from database/state.
- Chunks transcript using Gate 3 SpeakerAwareChunker.
- Embeds and stores chunks in Pinecone namespace 'meeting_{meeting_id}' and PostgreSQL transcript_chunks.
- Extracts participant metadata.
- Updates state with chunk counts and completion status.
- Sets session_action = "identify".
"""

import uuid
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.config import SUB_AGENT_MODEL
from app.core.logging import get_logger
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.transcript_chunk import TranscriptChunk, TranscriptChunkType
from app.graph.state import MeetMindState
from app.rag.chunker import TranscriptChunker
from app.rag.embedder import TranscriptEmbedder

logger = get_logger(__name__)


class IngestionAgent:
    """
    Ingestion Agent coordinating transcript parsing, chunking, and embedding.
    """

    model_name: str = SUB_AGENT_MODEL

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        Executes ingestion stage:
        1. Retrieves raw transcript.
        2. Chunks transcript using SpeakerAwareChunker.
        3. Embeds and stores vectors into Pinecone and chunks into PostgreSQL.
        4. Identifies and records participants.
        5. Updates state.
        """
        meeting_id_str = state.get("meeting_id", "")
        logger.info(f"IngestionAgent processing meeting {meeting_id_str}")

        if not meeting_id_str:
            return {
                "error": "Missing meeting_id for ingestion",
                "current_stage": "ingestion",
                "session_action": "complete",
            }

        meeting_uuid = uuid.UUID(meeting_id_str)
        raw_transcript = state.get("raw_transcript", "")

        # If db provided and raw_transcript empty in state, fetch from db
        if not raw_transcript and db:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_uuid).first()
            if meeting and meeting.raw_transcript:
                raw_transcript = meeting.raw_transcript

        if not raw_transcript or not raw_transcript.strip():
            logger.warning(f"Empty transcript for meeting {meeting_id_str}; skipping chunking")
            return {
                "chunks_stored": 0,
                "pinecone_namespace": f"meeting_{meeting_id_str}",
                "ingestion_complete": True,
                "current_stage": "ingestion",
                "session_action": "identify",
            }

        # 1. Chunk transcript
        chunker = TranscriptChunker()
        chunks = chunker.chunk(raw_transcript)
        logger.info(f"IngestionAgent created {len(chunks)} chunks for meeting {meeting_id_str}")

        # 2. Embed and store to Pinecone + DB
        chunks_stored = len(chunks)
        try:
            embedder = TranscriptEmbedder()
            embedder.embed_and_store(meeting_id=meeting_uuid, chunks=chunks, db_session=db)
        except Exception as exc:
            logger.warning(f"Vector embedding skipped or failed during ingestion (fallback): {exc}")

        # 3. Persist chunks in PostgreSQL if db available and not already persisted
        if db:
            try:
                # Check if chunks are already in DB
                existing_count = (
                    db.query(TranscriptChunk)
                    .filter(TranscriptChunk.meeting_id == meeting_uuid)
                    .count()
                )
                if existing_count == 0:
                    for c in chunks:
                        chunk_type_enum = TranscriptChunkType.dialogue
                        if c.chunk_type in TranscriptChunkType._value2member_map_:
                            chunk_type_enum = TranscriptChunkType(c.chunk_type)

                        db_chunk = TranscriptChunk(
                            meeting_id=meeting_uuid,
                            chunk_index=c.chunk_index,
                            speaker_name=c.speaker_name,
                            speaker_role=c.speaker_role,
                            content=c.content,
                            timestamp=c.timestamp,
                            chunk_type=chunk_type_enum,
                            involves_user=c.involves_user,
                            pinecone_vector_id=c.pinecone_vector_id,
                        )
                        db.add(db_chunk)
                    db.commit()
                    logger.info(f"Persisted {len(chunks)} TranscriptChunk rows to PostgreSQL")
            except Exception as exc:
                db.rollback()
                logger.error(f"Failed to persist transcript chunks to DB: {exc}")

        # 4. Extract participants
        participants_list: list[dict[str, Any]] = state.get("participants", [])
        if not participants_list and db:
            db_participants = (
                db.query(MeetingParticipant)
                .filter(MeetingParticipant.meeting_id == meeting_uuid)
                .all()
            )
            participants_list = [
                {"name": p.name, "role": p.role, "is_current_user": p.is_current_user}
                for p in db_participants
            ]

        pinecone_ns = f"meeting_{meeting_id_str}"
        return {
            "chunks_stored": chunks_stored,
            "pinecone_namespace": pinecone_ns,
            "participants": participants_list,
            "ingestion_complete": True,
            "current_stage": "ingestion",
            "session_action": "identify",
        }
