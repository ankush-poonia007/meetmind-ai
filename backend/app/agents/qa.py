"""
Q&A Agent for MeetMind AI.

Pattern: ReAct with Meeting-Scoped Hybrid RAG
Model: gemini-3.6-flash (via ProviderGateway with use_case="qa")

Responsibilities:
- Independent entry path for conversational questions.
- Strictly scoped to a single meeting (namespace 'meeting_{meeting_id}').
- Calls Gate 3 HybridRetriever (Pinecone Top 10 + BM25 Top 10 -> BGE Reranker Top 5).
- Synthesizes grounded, citation-attributed answers using gemini-3.6-flash.
- NO RRF, NO weighted fusion, NO cross-meeting retrieval.
- Returns answer, structured sources, and confidence level.
"""

import re
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.config import SUPERVISOR_MODEL
from app.core.constants import ConfidenceLevel
from app.core.logging import get_logger
from app.core.providers import get_provider_gateway
from app.graph.state import MeetMindState
from app.rag.retriever import RetrievedChunk, retrieve
from app.schemas.chat import ChatSource

logger = get_logger(__name__)

# Keywords triggering transcript fallback path when RAG retrieval is weak
TEMPORAL_DECISION_KEYWORDS: list[str] = [
    # Temporal / date queries
    "when",
    "which date",
    "what date",
    "what day",
    "which day",
    "what time",
    "which time",
    "timeline",
    "schedule",
    "deadline",
    "soft deadline",
    "due date",
    "due",
    # Identity / role / assignment queries
    "who",
    "whose",
    "role of",
    "what did",
    "assigned",
    "assignee",
    "responsible",
    "owner",
    # Decisions / agreements
    "decision",
    "decided",
    "decide",
    "agreed",
    "agreement",
    "conclusion",
    "action item",
    # Months and abbreviations
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
]


class QAAgent:
    """
    Q&A Agent managing grounded, meeting-isolated question answering.
    Supports Path A (hybrid RAG chunks) and Path B (transcript fallback).
    """

    model_name: str = SUPERVISOR_MODEL

    @classmethod
    def run_qa_agent(
        cls,
        meeting_id: UUID,
        user_id: UUID,
        question: str,
        user_name: str,
        user_role: Optional[str] = None,
        db: Optional[Session] = None,
        raw_transcript: Optional[str] = None,
        chat_history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[str, list[ChatSource], ConfidenceLevel]:
        """
        Executes hybrid RAG and answer generation for a user question:
        1. Queries Gate 3 HybridRetriever strictly for meeting_{meeting_id}.
        2. Reranks chunks via BGE cross-encoder.
        3. Evaluates two-path approach:
           - Path A (RAG only): top rerank score >= 0.3 and no keyword match.
           - Path B (Transcript fallback): top score < 0.3 OR question has temporal/decision/identity keywords.
        4. Synthesizes grounded answer via gemini-3.6-flash with 25s timeout.
        5. Attributes citations and assesses confidence.
        """
        clean_query = question.strip()
        logger.info(f"QAAgent processing query for meeting {meeting_id}: '{clean_query[:60]}'")

        if not clean_query:
            return "Please provide a question about the meeting.", [], ConfidenceLevel.LOW

        # 1. Hybrid RAG retrieval
        retrieved_chunks: list[RetrievedChunk] = []
        try:
            retrieved_chunks = retrieve(meeting_id=meeting_id, query=clean_query, db_session=db)
            logger.info(f"QAAgent retrieved {len(retrieved_chunks)} reranked chunks")
        except Exception as exc:
            logger.warning(f"RAG retrieval encounter during Q&A: {exc}")

        # 2. Build structured ChatSource citations from retrieved chunks
        sources: list[ChatSource] = []
        for idx, chunk in enumerate(retrieved_chunks):
            sources.append(
                ChatSource(
                    speaker=chunk.speaker_name or "Speaker",
                    timestamp=chunk.timestamp,
                    excerpt=chunk.content[:250],
                )
            )

        # 3. Two-path evaluation: Check keyword match and top rerank score
        question_lower = clean_query.lower()
        has_keyword = any(
            re.search(rf"\b{re.escape(kw)}\b", question_lower)
            for kw in TEMPORAL_DECISION_KEYWORDS
        )
        top_score = retrieved_chunks[0].rerank_score if retrieved_chunks else None
        score_below_threshold = (top_score is None) or (top_score < 0.3)
        trigger_fallback = has_keyword or score_below_threshold

        # Resolve raw_transcript if needed
        active_raw_transcript: Optional[str] = raw_transcript
        if trigger_fallback and not active_raw_transcript and db is not None:
            try:
                from app.db.models.meeting import Meeting
                m_rec = db.query(Meeting).filter(Meeting.id == meeting_id).first()
                if m_rec and m_rec.raw_transcript:
                    active_raw_transcript = m_rec.raw_transcript
            except Exception as exc:
                logger.warning(f"Could not load raw transcript from database: {exc}")

        # Resolve chat_history if not provided
        active_chat_history: Optional[list[dict[str, str]]] = chat_history
        if active_chat_history is None and db is not None:
            try:
                from app.db.models.chat_message import ChatMessage
                recent_records = (
                    db.query(ChatMessage)
                    .filter(
                        ChatMessage.meeting_id == meeting_id,
                        ChatMessage.user_id == user_id,
                    )
                    .order_by(ChatMessage.created_at.desc())
                    .limit(5)
                    .all()
                )
                active_chat_history = [
                    {
                        "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                        "content": m.content,
                    }
                    for m in reversed(recent_records)
                ]
            except Exception as exc:
                logger.warning(f"Could not load recent chat history: {exc}")
                active_chat_history = []

        # 4. Handle cases where no content is available or query has no RAG matches and no fallback keywords
        if not retrieved_chunks and (not active_raw_transcript or not has_keyword):
            answer = (
                f"I could not find specific information regarding '{clean_query}' "
                f"in the transcript for this meeting."
            )
            return answer, [], ConfidenceLevel.LOW

        # 5. Synthesize answer with appropriate prompt context
        fallback_context = active_raw_transcript if trigger_fallback else None

        answer = cls._synthesize_answer(
            question=clean_query,
            chunks=retrieved_chunks,
            user_name=user_name,
            user_role=user_role,
            raw_transcript=fallback_context,
            chat_history=active_chat_history,
        )

        # Attribute citation if sources was empty but raw transcript was used
        if not sources and fallback_context:
            sources.append(
                ChatSource(
                    speaker="Meeting Transcript",
                    timestamp=None,
                    excerpt=fallback_context[:250].strip(),
                )
            )

        # 6. Confidence assessment
        confidence = ConfidenceLevel.HIGH
        if len(retrieved_chunks) < 2 and not fallback_context:
            confidence = ConfidenceLevel.MEDIUM
        if top_score is not None and top_score < 0.2 and not fallback_context:
            confidence = ConfidenceLevel.LOW
        elif top_score is not None and top_score < 0.3:
            confidence = ConfidenceLevel.MEDIUM

        return answer, sources, confidence

    @classmethod
    def _synthesize_answer(
        cls,
        question: str,
        chunks: list[RetrievedChunk],
        user_name: str,
        user_role: Optional[str] = None,
        raw_transcript: Optional[str] = None,
        chat_history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """
        Synthesizes an answer using ProviderGateway with use_case="qa".
        Uses two prompt templates:
        - Path A: RAG-only template (primarily based on excerpts).
        - Path B: RAG + Transcript fallback template (excerpts + full transcript).
        Includes recent conversation history if present.
        Enforces a 25s timeout on the Gemini API call.
        """
        history_lines: list[str] = []
        if chat_history:
            for msg in chat_history:
                role = str(msg.get("role", "")).lower()
                role_label = "User" if "user" in role else "Assistant"
                content = msg.get("content", "").strip()
                if content:
                    history_lines.append(f"{role_label}: {content}")
        history_block = (
            "Recent conversation:\n" + "\n".join(history_lines) + "\n\n"
            if history_lines
            else ""
        )

        context_blocks: list[str] = []
        for i, c in enumerate(chunks):
            speaker_tag = f"[{c.speaker_name or 'Speaker'}]"
            context_blocks.append(f"Excerpt {i + 1} {speaker_tag}: {c.content}")
        context_str = "\n\n".join(context_blocks) if context_blocks else "None available."

        if raw_transcript:
            # Path B: RAG + Full Transcript Fallback prompt
            prompt = f"""You are MeetMind AI, an intelligent meeting assistant.
Answer the user's question using the provided meeting excerpts and the full meeting transcript.
Synthesize a direct, accurate, and helpful response based on the discussion, decisions, dates, and speaker commitments recorded.
If the answer cannot be found in either the excerpts or the transcript, state clearly that it is not discussed.
Do not fabricate information.

{history_block}User: {user_name} (Role: {user_role or 'Participant'})
Question: {question}

Meeting Excerpts:
{context_str}

Full Meeting Transcript:
{raw_transcript}

Grounded Answer:"""
        else:
            # Path A: RAG-only prompt
            prompt = f"""You are MeetMind AI, an intelligent meeting assistant.
Answer the user's question based primarily on the provided meeting excerpts.
Synthesize a direct, accurate, and helpful response based on the discussion recorded.
If the answer is not contained in the excerpts, state clearly that it is not discussed.
Do not fabricate information.

{history_block}User: {user_name} (Role: {user_role or 'Participant'})
Question: {question}

Meeting Excerpts:
{context_str}

Grounded Answer:"""

        try:
            gateway = get_provider_gateway()

            def _call_gemini_qa(api_key: str, model_str: Optional[str]) -> str:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_str or cls.model_name)
                resp = model.generate_content(
                    prompt,
                    request_options={"timeout": 25},
                )
                return resp.text.strip()

            return gateway.execute("qa", _call_gemini_qa)
        except Exception as exc:
            logger.info(f"LLM synthesis skipped or unavailable ({exc}); using extractive fallback")
            # Deterministic synthesis for test suites and offline mode
            if chunks:
                top_content = chunks[0].content
                return (
                    f"Based on the meeting transcript ({chunks[0].speaker_name or 'Speaker'}): "
                    f"{top_content}"
                )
            if raw_transcript:
                return f"Based on the meeting transcript: {raw_transcript[:300].strip()}"
            return f"I could not find specific information regarding '{question}' in the transcript for this meeting."

    @classmethod
    def run(cls, state: MeetMindState, db: Optional[Session] = None) -> dict[str, Any]:
        """
        LangGraph node entry point for Q&A pipeline.
        """
        import uuid
        meeting_id_str = state.get("meeting_id", "")
        user_id_str = state.get("user_id", "")
        question = state.get("user_question", "")
        user_name = state.get("user_name", "User")
        user_role = state.get("user_role")
        raw_transcript = state.get("raw_transcript")

        meeting_uuid = uuid.UUID(meeting_id_str)
        user_uuid = uuid.UUID(user_id_str)

        answer, sources, confidence = cls.run_qa_agent(
            meeting_id=meeting_uuid,
            user_id=user_uuid,
            question=question,
            user_name=user_name,
            user_role=user_role,
            db=db,
            raw_transcript=raw_transcript,
        )

        return {
            "qa_answer": answer,
            "qa_sources": [s.model_dump() for s in sources],
            "qa_confidence": confidence.value if hasattr(confidence, "value") else str(confidence),
            "final_response": answer,
            "current_stage": "qa",
            "session_action": "complete",
        }


# Module level convenience export
run_qa_agent = QAAgent.run_qa_agent
