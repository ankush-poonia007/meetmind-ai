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


class QAAgent:
    """
    Q&A Agent managing grounded, meeting-isolated question answering.
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
    ) -> tuple[str, list[ChatSource], ConfidenceLevel]:
        """
        Executes hybrid RAG and answer generation for a user question:
        1. Queries Gate 3 HybridRetriever strictly for meeting_{meeting_id}.
        2. Reranks chunks via BGE cross-encoder.
        3. Generates grounded answer via gemini-3.6-flash (mediated by ProviderGateway).
        4. Attributes citations and assesses confidence.
        """
        clean_query = question.strip()
        logger.info(f"QAAgent processing query for meeting {meeting_id}: '{clean_query[:60]}'")

        if not clean_query:
            return "Please provide a question about the meeting.", [], ConfidenceLevel.LOW

        # 1. Hybrid RAG retrieval (Top 5 reranked chunks from Gate 3)
        retrieved_chunks: list[RetrievedChunk] = []
        try:
            retrieved_chunks = retrieve(meeting_id=meeting_id, query=clean_query, db_session=db)
            logger.info(f"QAAgent retrieved {len(retrieved_chunks)} reranked chunks")
        except Exception as exc:
            logger.warning(f"RAG retrieval encounter during Q&A: {exc}")

        # 2. Build structured ChatSource citations
        sources: list[ChatSource] = []
        for idx, chunk in enumerate(retrieved_chunks):
            sources.append(
                ChatSource(
                    speaker=chunk.speaker_name or "Speaker",
                    timestamp=chunk.timestamp,
                    excerpt=chunk.content[:250],
                )
            )

        # 3. Grounded Answer Synthesis
        if not retrieved_chunks:
            answer = (
                f"I could not find specific information regarding '{clean_query}' "
                f"in the transcript for this meeting."
            )
            return answer, [], ConfidenceLevel.LOW

        answer = cls._synthesize_answer(
            question=clean_query,
            chunks=retrieved_chunks,
            user_name=user_name,
            user_role=user_role,
        )

        # 4. Confidence assessment
        confidence = ConfidenceLevel.HIGH
        if len(retrieved_chunks) < 2:
            confidence = ConfidenceLevel.MEDIUM
        top_score = retrieved_chunks[0].rerank_score
        if top_score is not None and top_score < 0.2:
            confidence = ConfidenceLevel.LOW

        return answer, sources, confidence

    @classmethod
    def _synthesize_answer(
        cls,
        question: str,
        chunks: list[RetrievedChunk],
        user_name: str,
        user_role: Optional[str] = None,
    ) -> str:
        """
        Synthesizes an answer using ProviderGateway with use_case="qa".
        Provides deterministic synthesis fallback if provider is unconfigured or in tests.
        """
        context_blocks: list[str] = []
        for i, c in enumerate(chunks):
            speaker_tag = f"[{c.speaker_name or 'Speaker'}]"
            context_blocks.append(f"Excerpt {i + 1} {speaker_tag}: {c.content}")
        context_str = "\n\n".join(context_blocks)

        prompt = f"""You are MeetMind AI, an intelligent meeting assistant.
Answer the user's question based ONLY on the provided meeting excerpts.
Do not fabricate information. If the answer is not contained in the excerpts, state clearly that it is not discussed.

User: {user_name} (Role: {user_role or 'Participant'})
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
                resp = model.generate_content(prompt)
                return resp.text.strip()

            return gateway.execute("qa", _call_gemini_qa)
        except Exception as exc:
            logger.info(f"LLM synthesis skipped or unavailable ({exc}); using extractive fallback")
            # Deterministic synthesis for test suites and offline mode
            top_content = chunks[0].content
            return (
                f"Based on the meeting transcript ({chunks[0].speaker_name or 'Speaker'}): "
                f"{top_content}"
            )

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

        meeting_uuid = uuid.UUID(meeting_id_str)
        user_uuid = uuid.UUID(user_id_str)

        answer, sources, confidence = cls.run_qa_agent(
            meeting_id=meeting_uuid,
            user_id=user_uuid,
            question=question,
            user_name=user_name,
            user_role=user_role,
            db=db,
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
