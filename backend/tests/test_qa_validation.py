"""
MeetMind AI — Gate 7, Batch 5: Q&A Integration & Validation Test Suite.

Validates the complete meeting-specific Q&A workflow:
- Task 2: Meeting-scoped transcript retrieval & cross-meeting isolation.
- Task 3: Answer grounding & retrieval relevance (explicit, multi-section, speaker attribution, unanswerable).
- Task 4: Citation accuracy & structured format (speaker, timestamp, excerpt).
- Task 5: Chat history persistence (user & assistant messages, chronological order, cross-meeting isolation, rollback on failure).
- Task 6 & 7: Frontend/backend integration contracts and error handling (missing meeting, missing user, empty query).
"""

from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import uuid

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agents.qa import QAAgent
from app.core.constants import ChatRole as AppChatRole, ConfidenceLevel
from app.core.exceptions import MeetingNotFoundError, UserNotFoundError
from app.db.base import Base
from app.db.models.chat_message import ChatMessage, ChatRole as DBChatRole
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.transcript_chunk import TranscriptChunk, TranscriptChunkType
from app.db.models.user import User
from app.rag.retriever import HybridRetriever, RetrievedChunk, get_meeting_namespace
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.chat_service import ChatService


class BaseQATestCase(unittest.TestCase):
    """In-memory SQLite test fixture for isolated Q&A testing."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.db: Session = self.SessionLocal()

        # Create two distinct users
        self.user_a = User(id=uuid.uuid4(), name="Alice Architect", email="alice@meetmind.ai")
        self.user_b = User(id=uuid.uuid4(), name="Bob Backend", email="bob@meetmind.ai")

        # Create two distinct meetings with clearly different topics
        self.meeting_a = Meeting(
            id=uuid.uuid4(),
            user_id=self.user_a.id,
            title="Meeting A: Redis Cache Architecture",
            meeting_date=date.today(),
            raw_transcript="Redis cache outage occurred. Circuit breaker agreed.",
            input_format="txt",
        )
        self.meeting_b = Meeting(
            id=uuid.uuid4(),
            user_id=self.user_b.id,
            title="Meeting B: Database Sharding & Indexing",
            meeting_date=date.today(),
            raw_transcript="Database sharding strategy discussed. B-tree indexes planned.",
            input_format="txt",
        )

        self.db.add_all([self.user_a, self.user_b, self.meeting_a, self.meeting_b])
        self.db.commit()

        # Add Meeting A transcript chunks
        self.chunk_a1 = TranscriptChunk(
            id=uuid.uuid4(),
            meeting_id=self.meeting_a.id,
            chunk_index=0,
            speaker_name="Alice",
            speaker_role="Lead Architect",
            timestamp="09:05",
            content="We suffered a Redis cache failure on checkout leading to 500 errors.",
            chunk_type=TranscriptChunkType.dialogue,
            involves_user=True,
        )
        self.chunk_a2 = TranscriptChunk(
            id=uuid.uuid4(),
            meeting_id=self.meeting_a.id,
            chunk_index=1,
            speaker_name="Dave",
            speaker_role="DevOps",
            timestamp="09:12",
            content="I will implement an automated circuit breaker to prevent cascade failures by Friday.",
            chunk_type=TranscriptChunkType.dialogue,
            involves_user=False,
        )

        # Add Meeting B transcript chunks
        self.chunk_b1 = TranscriptChunk(
            id=uuid.uuid4(),
            meeting_id=self.meeting_b.id,
            chunk_index=0,
            speaker_name="Bob",
            speaker_role="DBA",
            timestamp="14:00",
            content="We need to partition the orders table into monthly shards.",
            chunk_type=TranscriptChunkType.dialogue,
            involves_user=True,
        )
        self.chunk_b2 = TranscriptChunk(
            id=uuid.uuid4(),
            meeting_id=self.meeting_b.id,
            chunk_index=1,
            speaker_name="Carol",
            speaker_role="Backend Eng",
            timestamp="14:15",
            content="We should create composite indexes on user_id and created_at.",
            chunk_type=TranscriptChunkType.dialogue,
            involves_user=False,
        )

        self.db.add_all([self.chunk_a1, self.chunk_a2, self.chunk_b1, self.chunk_b2])
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()
        self.db.close()


# ── Task 2: Meeting-Scoped Retrieval Tests ───────────────────────────────────

class TestMeetingScopedRetrieval(BaseQATestCase):
    """Verifies that retrieval is strictly restricted to the specified meeting."""

    def test_meeting_scoped_bm25_retrieval_isolation(self):
        """Verifies BM25 retrieval for Meeting A never returns Meeting B chunks, and vice versa."""
        retriever = HybridRetriever(embedder=MagicMock(), vector_store=MagicMock())

        # Query Meeting A for "circuit breaker"
        results_a = retriever.retrieve_bm25(
            meeting_id=self.meeting_a.id,
            query="circuit breaker failure",
            db_session=self.db,
        )
        self.assertTrue(len(results_a) > 0)
        found_circuit_breaker = False
        for r in results_a:
            self.assertEqual(r.meeting_id, str(self.meeting_a.id))
            if "circuit breaker" in r.content.lower():
                found_circuit_breaker = True
            self.assertNotIn("sharding", r.content.lower())
            self.assertNotIn("partition", r.content.lower())
        self.assertTrue(found_circuit_breaker)

        # Query Meeting B for "partition monthly shards"
        results_b = retriever.retrieve_bm25(
            meeting_id=self.meeting_b.id,
            query="partition monthly shards",
            db_session=self.db,
        )
        self.assertTrue(len(results_b) > 0)
        for r in results_b:
            self.assertEqual(r.meeting_id, str(self.meeting_b.id))
            self.assertIn("partition", r.content.lower())
            self.assertNotIn("redis", r.content.lower())

        # Cross-query: Asking about Redis in Meeting B returns empty
        cross_b = retriever.retrieve_bm25(
            meeting_id=self.meeting_b.id,
            query="redis cache outage",
            db_session=self.db,
        )
        self.assertEqual(len(cross_b), 0)

    def test_pinecone_namespace_scoping(self):
        """Verifies Pinecone namespace formatting enforces meeting_{meeting_id} scoping."""
        namespace_a = get_meeting_namespace(self.meeting_a.id)
        namespace_b = get_meeting_namespace(self.meeting_b.id)

        self.assertEqual(namespace_a, f"meeting_{self.meeting_a.id}")
        self.assertEqual(namespace_b, f"meeting_{self.meeting_b.id}")
        self.assertNotEqual(namespace_a, namespace_b)

    def test_retriever_validation_guards(self):
        """Verifies retrieval raises ValueError on empty or invalid meeting_id."""
        retriever = HybridRetriever(embedder=MagicMock(), vector_store=MagicMock())

        with self.assertRaises(ValueError):
            retriever.retrieve(meeting_id="", query="What happened?", db_session=self.db)

        # Empty query returns empty list without error
        res = retriever.retrieve(meeting_id=self.meeting_a.id, query="   ", db_session=self.db)
        self.assertEqual(res, [])


# ── Task 3: Answer Grounding & Relevance Tests ───────────────────────────────

class TestAnswerGroundingAndRelevance(BaseQATestCase):
    """Verifies that the Q&A Agent synthesizes grounded answers with proper attribution."""

    @patch("app.agents.qa.get_provider_gateway")
    @patch("app.agents.qa.retrieve")
    def test_qa_agent_grounded_answer_and_attribution(self, mock_retrieve, mock_gateway):
        """Verifies QAAgent incorporates retrieved context and speaker attribution into synthesis prompt."""
        # Setup mock chunks
        mock_chunks = [
            RetrievedChunk(
                chunk_id=str(self.chunk_a2.id),
                meeting_id=str(self.meeting_a.id),
                chunk_index=1,
                content=self.chunk_a2.content,
                speaker_name="Dave",
                speaker_role="DevOps",
                timestamp="09:12",
                chunk_type="dialogue",
                involves_user=False,
                rerank_score=0.88,
                retrieval_sources=["bm25"],
            )
        ]
        mock_retrieve.return_value = mock_chunks

        # Mock gateway execution
        mock_gw_instance = MagicMock()
        mock_gateway.return_value = mock_gw_instance
        mock_gw_instance.execute.return_value = (
            "Dave confirmed he will implement an automated circuit breaker by Friday to prevent cascade failures."
        )

        answer, sources, confidence = QAAgent.run_qa_agent(
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            question="Who is working on the circuit breaker and when is it due?",
            user_name="Alice",
            user_role="Lead Architect",
            db=self.db,
        )

        self.assertIn("Dave", answer)
        self.assertIn("circuit breaker", answer)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].speaker, "Dave")
        self.assertEqual(sources[0].timestamp, "09:12")
        self.assertIn("automated circuit breaker", sources[0].excerpt)

    @patch("app.agents.qa.retrieve", return_value=[])
    def test_qa_agent_unanswerable_question_handling(self, mock_retrieve):
        """Verifies unanswerable questions return a polite refusal with LOW confidence and no citations."""
        answer, sources, confidence = QAAgent.run_qa_agent(
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            question="What is the stock price of Apple?",
            user_name="Alice",
            db=self.db,
        )

        self.assertIn("could not find specific information", answer)
        self.assertEqual(len(sources), 0)
        self.assertEqual(confidence, ConfidenceLevel.LOW)

    def test_qa_agent_empty_query_guard(self):
        """Verifies empty question returns clear prompt request without triggering RAG."""
        answer, sources, confidence = QAAgent.run_qa_agent(
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            question="    ",
            user_name="Alice",
            db=self.db,
        )

        self.assertEqual(answer, "Please provide a question about the meeting.")
        self.assertEqual(sources, [])
        self.assertEqual(confidence, ConfidenceLevel.LOW)


# ── Task 4: Citation Validation Tests ────────────────────────────────────────

class TestCitationValidation(BaseQATestCase):
    """Verifies that citations strictly match retrieved meeting chunks."""

    @patch("app.agents.qa.retrieve")
    def test_citation_structure_and_limits(self, mock_retrieve):
        """Verifies ChatSource citations preserve speaker, timestamp, and truncate excerpt <= 250 chars."""
        long_content = "Word " * 100  # 500 chars
        chunk = RetrievedChunk(
            chunk_id=str(uuid.uuid4()),
            meeting_id=str(self.meeting_a.id),
            chunk_index=0,
            content=long_content,
            speaker_name="Sarah",
            speaker_role="Eng",
            timestamp="10:30",
            chunk_type="dialogue",
            involves_user=False,
            rerank_score=0.9,
            retrieval_sources=["semantic"],
        )
        mock_retrieve.return_value = [chunk]

        answer, sources, confidence = QAAgent.run_qa_agent(
            meeting_id=self.meeting_a.id,
            user_id=self.user_a.id,
            question="What did Sarah say?",
            user_name="Alice",
            db=self.db,
        )

        self.assertEqual(len(sources), 1)
        src = sources[0]
        self.assertEqual(src.speaker, "Sarah")
        self.assertEqual(src.timestamp, "10:30")
        self.assertTrue(len(src.excerpt) <= 250)


# ── Task 5: Chat History Persistence Tests ───────────────────────────────────

class TestChatHistoryPersistence(BaseQATestCase):
    """Verifies persistence of user and assistant messages, ordering, and cross-meeting isolation."""

    @patch("app.services.chat_service.ChatService._invoke_qa_pipeline")
    def test_chat_exchange_persistence_and_order(self, mock_invoke):
        """Verifies user and assistant messages are saved in chronological sequence."""
        mock_invoke.return_value = (
            "Dave is handling the circuit breaker.",
            [ChatSource(speaker="Dave", timestamp="09:12", excerpt="I will implement...")],
            ConfidenceLevel.HIGH,
        )

        chat_req = ChatRequest(
            question="Who handles the circuit breaker?",
            user_id=self.user_a.id,
        )

        res = ChatService.send_chat_message(self.db, self.meeting_a.id, chat_req)
        self.assertEqual(res.answer, "Dave is handling the circuit breaker.")

        # Check DB records
        history = ChatService.get_chat_history(self.db, self.meeting_a.id)
        self.assertEqual(len(history.messages), 2)

        # Message 1: user
        msg1 = history.messages[0]
        self.assertEqual(msg1.role, AppChatRole.USER)
        self.assertEqual(msg1.content, "Who handles the circuit breaker?")
        self.assertEqual(msg1.meeting_id, self.meeting_a.id)

        # Message 2: assistant
        msg2 = history.messages[1]
        self.assertEqual(msg2.role, AppChatRole.ASSISTANT)
        self.assertEqual(msg2.content, "Dave is handling the circuit breaker.")
        self.assertEqual(msg2.meeting_id, self.meeting_a.id)

        # Chronological ordering
        self.assertTrue(msg1.created_at <= msg2.created_at)

    @patch("app.services.chat_service.ChatService._invoke_qa_pipeline")
    def test_chat_history_cross_meeting_isolation(self, mock_invoke):
        """Verifies chat history in Meeting A is completely isolated from Meeting B."""
        mock_invoke.side_effect = [
            ("Answer for Meeting A", [], ConfidenceLevel.HIGH),
            ("Answer for Meeting B", [], ConfidenceLevel.HIGH),
        ]

        # Send message in Meeting A
        ChatService.send_chat_message(
            self.db,
            self.meeting_a.id,
            ChatRequest(question="Question for Meeting A", user_id=self.user_a.id),
        )

        # Send message in Meeting B
        ChatService.send_chat_message(
            self.db,
            self.meeting_b.id,
            ChatRequest(question="Question for Meeting B", user_id=self.user_b.id),
        )

        # Verify Meeting A history has ONLY Meeting A messages
        hist_a = ChatService.get_chat_history(self.db, self.meeting_a.id)
        self.assertEqual(len(hist_a.messages), 2)
        for m in hist_a.messages:
            self.assertEqual(m.meeting_id, self.meeting_a.id)
            self.assertIn("Meeting A", m.content)

        # Verify Meeting B history has ONLY Meeting B messages
        hist_b = ChatService.get_chat_history(self.db, self.meeting_b.id)
        self.assertEqual(len(hist_b.messages), 2)
        for m in hist_b.messages:
            self.assertEqual(m.meeting_id, self.meeting_b.id)
            self.assertIn("Meeting B", m.content)

    @patch("app.services.chat_service.ChatService._invoke_qa_pipeline")
    def test_clear_chat_history_scoped_to_meeting(self, mock_invoke):
        """Verifies clear_chat_history deletes only messages belonging to target meeting."""
        mock_invoke.side_effect = [
            ("Answer A", [], ConfidenceLevel.HIGH),
            ("Answer B", [], ConfidenceLevel.HIGH),
        ]

        ChatService.send_chat_message(
            self.db,
            self.meeting_a.id,
            ChatRequest(question="QA A", user_id=self.user_a.id),
        )
        ChatService.send_chat_message(
            self.db,
            self.meeting_b.id,
            ChatRequest(question="QA B", user_id=self.user_b.id),
        )

        # Clear Meeting A
        ChatService.clear_chat_history(self.db, self.meeting_a.id)

        # Meeting A should be empty
        hist_a = ChatService.get_chat_history(self.db, self.meeting_a.id)
        self.assertEqual(len(hist_a.messages), 0)

        # Meeting B must remain untouched
        hist_b = ChatService.get_chat_history(self.db, self.meeting_b.id)
        self.assertEqual(len(hist_b.messages), 2)

    @patch("app.services.chat_service.ChatService._invoke_qa_pipeline")
    def test_chat_pipeline_failure_rolls_back_user_message(self, mock_invoke):
        """Verifies that if Q&A pipeline throws an error, rollback prevents orphan user message."""
        mock_invoke.side_effect = RuntimeError("LLM synthesis crash")

        with self.assertRaises(RuntimeError):
            ChatService.send_chat_message(
                self.db,
                self.meeting_a.id,
                ChatRequest(question="Will fail", user_id=self.user_a.id),
            )

        # History should be empty because of rollback
        hist = ChatService.get_chat_history(self.db, self.meeting_a.id)
        self.assertEqual(len(hist.messages), 0)


# ── Task 6 & 7: Error Handling & Contract Tests ──────────────────────────────

class TestChatErrorHandling(BaseQATestCase):
    """Verifies error handling for non-existent meeting, user, and invalid payloads."""

    def test_send_chat_meeting_not_found(self):
        """Verifies HTTP 404 / MeetingNotFoundError on non-existent meeting ID."""
        non_existent_mid = uuid.uuid4()
        with self.assertRaises(MeetingNotFoundError):
            ChatService.send_chat_message(
                self.db,
                non_existent_mid,
                ChatRequest(question="Hello?", user_id=self.user_a.id),
            )

    def test_send_chat_user_not_found(self):
        """Verifies HTTP 404 / UserNotFoundError on non-existent user ID."""
        non_existent_uid = uuid.uuid4()
        with self.assertRaises(UserNotFoundError):
            ChatService.send_chat_message(
                self.db,
                self.meeting_a.id,
                ChatRequest(question="Hello?", user_id=non_existent_uid),
            )

    def test_get_history_meeting_not_found(self):
        """Verifies MeetingNotFoundError when requesting history for non-existent meeting."""
        with self.assertRaises(MeetingNotFoundError):
            ChatService.get_chat_history(self.db, uuid.uuid4())


if __name__ == "__main__":
    unittest.main()
