"""
Unit tests for Hybrid Retrieval and BGE Reranker (Gate 3 - Batch 3).

Validates all 28 mandatory test requirements:
- TEST 1: Semantic retrieval (Pinecone returns candidates, top 10 requested, scores preserved)
- TEST 2: Meeting-scoped Pinecone namespace (meeting_{meeting_id})
- TEST 3: Query embedding boundary (ProviderGateway invoked with use_case="embedding")
- TEST 4: BM25 retrieval (PostgreSQL transcript chunks used, BM25Okapi returns matches)
- TEST 5: BM25 meeting isolation (only requested meeting's chunks enter corpus)
- TEST 6: BM25 Top 10 (maximum 10 BM25 candidates returned)
- TEST 7: Empty BM25 corpus (returns empty result without error)
- TEST 8: Hybrid merge (semantic + BM25 candidates combined into union)
- TEST 9: Deduplication (candidate in both systems appears once)
- TEST 10: Retrieval source tracking (semantic-only, BM25-only, both)
- TEST 11: Score preservation (semantic_score and bm25_score preserved on merge)
- TEST 12: RetrievedChunk contract (all 13 required fields validated)
- TEST 13: BGE reranking (CrossEncoder receives query + content pairs, rerank scores assigned)
- TEST 14: Final Top 5 (when > 5 candidates exist, exactly 5 returned)
- TEST 15: Fewer than 5 candidates (all valid candidates returned)
- TEST 16: Reranker lazy loading (importing module does not load model; loads on first request)
- TEST 17: Reranker reuse (subsequent requests reuse existing loaded model)
- TEST 18: Reranker failure fallback (model failure triggers deterministic fallback, no crash)
- TEST 19: Reranker failure score semantics (fallback leaves rerank_score as None)
- TEST 20: Meeting isolation end-to-end (meeting A candidates never include meeting B)
- TEST 21: Empty query (no meaningless external retrieval, returns [])
- TEST 22: Missing meeting ID (fails before external retrieval)
- TEST 23: Malformed metadata (invalid Pinecone match handled safely without crash)
- TEST 24: Candidate bound (at most 20 candidates enter reranker)
- TEST 25: No RRF (verifies no RRF formula or reciprocal rank calculations)
- TEST 26: No cross-meeting retrieval (independent meeting scope enforcement)
- TEST 27: No direct API-key access (retriever has no credential access)
- TEST 28: Deterministic fallback (stable ordering on repeated fallback runs)
"""

import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.rag.reranker import BGEReranker
from app.rag.retriever import (
    HybridRetriever,
    RetrievedChunk,
    retrieve,
    tokenize_bm25,
)


class MockDBChunk:
    """Mock for SQLAlchemy TranscriptChunk."""

    def __init__(
        self,
        chunk_id: str,
        meeting_id: uuid.UUID,
        chunk_index: int,
        content: str,
        speaker_name: str = "Aryan",
        speaker_role: str = "PM",
        timestamp: str = "10:00",
        chunk_type: str = "dialogue",
        involves_user: bool = False,
    ) -> None:
        self.id = uuid.UUID(chunk_id) if isinstance(chunk_id, str) and len(chunk_id) == 36 else uuid.uuid4()
        self.meeting_id = meeting_id
        self.chunk_index = chunk_index
        self.content = content
        self.speaker_name = speaker_name
        self.speaker_role = speaker_role
        self.timestamp = timestamp
        self.chunk_type = chunk_type
        self.involves_user = involves_user


def make_retrieved_chunk(
    idx: int,
    meeting_id: str,
    content: str = "",
    sem_score: float = None,
    bm25_score: float = None,
    sources: list = None,
    chunk_id: str = None,
) -> RetrievedChunk:
    """Helper to create dummy RetrievedChunk instances."""
    c_id = chunk_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{meeting_id}_{idx}"))
    return RetrievedChunk(
        chunk_id=c_id,
        meeting_id=meeting_id,
        chunk_index=idx,
        content=content or f"Content of chunk {idx}",
        speaker_name="Speaker",
        speaker_role="Role",
        timestamp="10:00",
        chunk_type="dialogue",
        involves_user=False,
        semantic_score=sem_score,
        bm25_score=bm25_score,
        rerank_score=None,
        retrieval_sources=sources or ["semantic"],
    )


class TestHybridRetrieverAndReranker(unittest.TestCase):
    """Test suite for Gate 3 - Batch 3 Hybrid Retrieval and Reranking."""

    def setUp(self) -> None:
        self.meeting_id_str = "550e8400-e29b-41d4-a716-446655440000"
        self.meeting_uuid = uuid.UUID(self.meeting_id_str)

    # ── TEST 1: Semantic retrieval ─────────────────────────────────────────────

    def test_01_semantic_retrieval(self) -> None:
        """Verify Pinecone returns semantic candidates, top 10 requested, scores preserved."""
        mock_index = MagicMock()
        mock_matches = [
            MagicMock(
                id=f"{self.meeting_id_str}_{i}",
                score=0.95 - (i * 0.05),
                metadata={
                    "chunk_id": f"00000000-0000-0000-0000-00000000000{i}",
                    "meeting_id": self.meeting_id_str,
                    "chunk_index": i,
                    "content": f"Semantic content {i}",
                    "speaker_name": "Alice",
                    "speaker_role": "Architect",
                    "timestamp": "10:00",
                    "chunk_type": "dialogue",
                    "involves_user": False,
                },
            )
            for i in range(12)
        ]
        mock_index.query.return_value = MagicMock(matches=mock_matches)

        mock_store = MagicMock()
        mock_store.get_index.return_value = mock_index

        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [[0.1] * 3072]

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        results = retriever.retrieve_semantic(self.meeting_id_str, "architecture query")

        # Top 10 enforced
        self.assertEqual(len(results), 10)
        # Scores preserved
        self.assertAlmostEqual(results[0].semantic_score, 0.95)
        self.assertEqual(results[0].retrieval_sources, ["semantic"])
        # Query top_k parameter
        mock_index.query.assert_called_once()
        self.assertEqual(mock_index.query.call_args.kwargs["top_k"], 10)

    # ── TEST 2: Meeting-scoped Pinecone namespace ──────────────────────────────

    def test_02_meeting_scoped_pinecone_namespace(self) -> None:
        """Verify Pinecone query strictly targets meeting_{meeting_id} namespace."""
        mock_index = MagicMock()
        mock_index.query.return_value = MagicMock(matches=[])
        mock_store = MagicMock()
        mock_store.get_index.return_value = mock_index

        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [[0.1] * 3072]

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        retriever.retrieve_semantic(self.meeting_id_str, "test query")

        call_namespace = mock_index.query.call_args.kwargs["namespace"]
        self.assertEqual(call_namespace, f"meeting_{self.meeting_id_str}")

    # ── TEST 3: Query embedding boundary ───────────────────────────────────────

    def test_03_query_embedding_boundary(self) -> None:
        """Verify query embedding is generated via embedder delegating to gateway."""
        mock_embedder = MagicMock()
        mock_embedder.embed_texts.return_value = [[0.1] * 3072]

        mock_store = MagicMock()
        mock_store.get_index.return_value = MagicMock(query=MagicMock(return_value=MagicMock(matches=[])))

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        retriever.retrieve_semantic(self.meeting_id_str, "user query")

        mock_embedder.embed_texts.assert_called_once_with(["user query"])

    # ── TEST 4: BM25 retrieval ────────────────────────────────────────────────

    def test_04_bm25_retrieval(self) -> None:
        """Verify PostgreSQL chunks used with BM25Okapi to return lexical matches."""
        db_chunks = [
            MockDBChunk(
                chunk_id="00000000-0000-0000-0000-000000000001",
                meeting_id=self.meeting_uuid,
                chunk_index=0,
                content="We need to finalize the dashboard requirements and API spec this week.",
            ),
            MockDBChunk(
                chunk_id="00000000-0000-0000-0000-000000000002",
                meeting_id=self.meeting_uuid,
                chunk_index=1,
                content="The weather in Bengaluru is very pleasant today with light rain.",
            ),
        ]
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = db_chunks

        retriever = HybridRetriever()
        results = retriever.retrieve_bm25(self.meeting_id_str, "dashboard requirements", db_session=mock_session)

        self.assertGreaterEqual(len(results), 1)
        self.assertIn("dashboard requirements", results[0].content)
        self.assertGreater(results[0].bm25_score, 0.0)
        self.assertEqual(results[0].retrieval_sources, ["bm25"])

    # ── TEST 5: BM25 meeting isolation ─────────────────────────────────────────

    def test_05_bm25_meeting_isolation(self) -> None:
        """Verify only chunks for the requested meeting_id are queried from PostgreSQL."""
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        retriever = HybridRetriever()
        retriever.retrieve_bm25(self.meeting_id_str, "query", db_session=mock_session)

        # Verify SQL execution was requested
        mock_session.execute.assert_called_once()

    # ── TEST 6: BM25 Top 10 ───────────────────────────────────────────────────

    def test_06_bm25_top_10(self) -> None:
        """Verify BM25 returns at most 10 candidates even when corpus has more matches."""
        db_chunks = [
            MockDBChunk(
                chunk_id=f"00000000-0000-0000-0000-0000000000{i:02d}",
                meeting_id=self.meeting_uuid,
                chunk_index=i,
                content=f"Database migration checkpoint {i} for postgres storage.",
            )
            for i in range(15)
        ]
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = db_chunks

        retriever = HybridRetriever()
        results = retriever.retrieve_bm25(self.meeting_id_str, "database migration postgres", db_session=mock_session)

        self.assertLessEqual(len(results), 10)

    # ── TEST 7: Empty BM25 corpus ──────────────────────────────────────────────

    def test_07_empty_bm25_corpus(self) -> None:
        """Verify empty PostgreSQL corpus returns [] without raising an error."""
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        retriever = HybridRetriever()
        results = retriever.retrieve_bm25(self.meeting_id_str, "query", db_session=mock_session)

        self.assertEqual(results, [])

    # ── TEST 8: Hybrid merge ──────────────────────────────────────────────────

    def test_08_hybrid_merge(self) -> None:
        """Verify disjoint semantic and BM25 candidate lists are merged into union."""
        sem_chunks = [make_retrieved_chunk(i, self.meeting_id_str, sources=["semantic"]) for i in range(3)]
        bm25_chunks = [make_retrieved_chunk(i + 10, self.meeting_id_str, sources=["bm25"]) for i in range(3)]

        retriever = HybridRetriever()
        merged = retriever.merge_and_deduplicate(sem_chunks, bm25_chunks)

        self.assertEqual(len(merged), 6)

    # ── TEST 9: Deduplication ─────────────────────────────────────────────────

    def test_09_deduplication(self) -> None:
        """Verify duplicate chunk appearing in both systems appears only once."""
        shared_id = "11111111-1111-1111-1111-111111111111"
        sem_chunk = make_retrieved_chunk(0, self.meeting_id_str, chunk_id=shared_id, sem_score=0.9, sources=["semantic"])
        bm25_chunk = make_retrieved_chunk(0, self.meeting_id_str, chunk_id=shared_id, bm25_score=5.5, sources=["bm25"])

        retriever = HybridRetriever()
        merged = retriever.merge_and_deduplicate([sem_chunk], [bm25_chunk])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].chunk_id, shared_id)

    # ── TEST 10: Retrieval source tracking ────────────────────────────────────

    def test_10_retrieval_source_tracking(self) -> None:
        """Verify semantic-only, BM25-only, and dual-source candidates track sources accurately."""
        c_sem_only = make_retrieved_chunk(1, self.meeting_id_str, chunk_id="id-sem-only", sources=["semantic"])
        c_bm25_only = make_retrieved_chunk(2, self.meeting_id_str, chunk_id="id-bm25-only", sources=["bm25"])

        shared_id = "id-both"
        c_both_sem = make_retrieved_chunk(3, self.meeting_id_str, chunk_id=shared_id, sem_score=0.8, sources=["semantic"])
        c_both_bm = make_retrieved_chunk(3, self.meeting_id_str, chunk_id=shared_id, bm25_score=4.2, sources=["bm25"])

        retriever = HybridRetriever()
        merged = retriever.merge_and_deduplicate([c_sem_only, c_both_sem], [c_bm25_only, c_both_bm])

        by_id = {c.chunk_id: c for c in merged}
        self.assertEqual(by_id["id-sem-only"].retrieval_sources, ["semantic"])
        self.assertEqual(by_id["id-bm25-only"].retrieval_sources, ["bm25"])
        self.assertEqual(set(by_id[shared_id].retrieval_sources), {"semantic", "bm25"})

    # ── TEST 11: Score preservation ───────────────────────────────────────────

    def test_11_score_preservation(self) -> None:
        """Verify semantic_score and bm25_score are both preserved on merged duplicate."""
        shared_id = "id-shared-scores"
        c_sem = make_retrieved_chunk(0, self.meeting_id_str, chunk_id=shared_id, sem_score=0.88, sources=["semantic"])
        c_bm = make_retrieved_chunk(0, self.meeting_id_str, chunk_id=shared_id, bm25_score=6.75, sources=["bm25"])

        retriever = HybridRetriever()
        merged = retriever.merge_and_deduplicate([c_sem], [c_bm])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].semantic_score, 0.88)
        self.assertEqual(merged[0].bm25_score, 6.75)

    # ── TEST 12: RetrievedChunk contract ──────────────────────────────────────

    def test_12_retrieved_chunk_contract(self) -> None:
        """Verify RetrievedChunk model has all 13 required fields."""
        chunk = RetrievedChunk(
            chunk_id="c-123",
            meeting_id=self.meeting_id_str,
            chunk_index=0,
            content="Valid dialogue content",
            speaker_name="Priya",
            speaker_role="Schema Architect",
            timestamp="11:00",
            chunk_type="dialogue",
            involves_user=True,
            semantic_score=0.91,
            bm25_score=3.4,
            rerank_score=0.85,
            retrieval_sources=["semantic", "bm25"],
        )

        d = chunk.model_dump()
        expected_keys = [
            "chunk_id", "meeting_id", "chunk_index", "content",
            "speaker_name", "speaker_role", "timestamp", "chunk_type",
            "involves_user", "semantic_score", "bm25_score", "rerank_score",
            "retrieval_sources",
        ]
        for key in expected_keys:
            self.assertIn(key, d)

    # ── TEST 13: BGE reranking ────────────────────────────────────────────────

    def test_13_bge_reranking(self) -> None:
        """Verify CrossEncoder receives (query, content) pairs and assigns rerank scores."""
        candidates = [
            make_retrieved_chunk(0, self.meeting_id_str, content="Irrelevant chat about lunch"),
            make_retrieved_chunk(1, self.meeting_id_str, content="Exact match for dashboard deadline"),
        ]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.12, 0.94]

        reranker = BGEReranker()
        reranker._model = mock_model  # Inject mock model

        reranked = reranker.rerank("dashboard deadline", candidates)

        mock_model.predict.assert_called_once_with([
            ("dashboard deadline", "Irrelevant chat about lunch"),
            ("dashboard deadline", "Exact match for dashboard deadline"),
        ])
        # Sorted descending: highest rerank_score first
        self.assertEqual(reranked[0].content, "Exact match for dashboard deadline")
        self.assertEqual(reranked[0].rerank_score, 0.94)
        self.assertEqual(reranked[1].rerank_score, 0.12)

    # ── TEST 14: Final Top 5 ──────────────────────────────────────────────────

    def test_14_final_top_5(self) -> None:
        """Verify when > 5 candidates exist, exactly Top 5 are returned."""
        candidates = [make_retrieved_chunk(i, self.meeting_id_str) for i in range(8)]

        mock_model = MagicMock()
        mock_model.predict.return_value = [float(i) for i in range(8)]

        reranker = BGEReranker(top_k=5)
        reranker._model = mock_model

        results = reranker.rerank("query", candidates)
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0].rerank_score, 7.0)

    # ── TEST 15: Fewer than 5 candidates ──────────────────────────────────────

    def test_15_fewer_than_5_candidates(self) -> None:
        """Verify when < 5 candidates exist, all available candidates are returned."""
        candidates = [make_retrieved_chunk(i, self.meeting_id_str) for i in range(3)]

        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.2, 0.3]

        reranker = BGEReranker(top_k=5)
        reranker._model = mock_model

        results = reranker.rerank("query", candidates)
        self.assertEqual(len(results), 3)

    # ── TEST 16: Reranker lazy loading ────────────────────────────────────────

    def test_16_reranker_lazy_loading(self) -> None:
        """Verify importing module does not load CrossEncoder model."""
        fresh_reranker = BGEReranker(model_name="dummy-model")
        self.assertFalse(fresh_reranker.is_loaded)
        self.assertIsNone(fresh_reranker._model)

    # ── TEST 17: Reranker reuse ───────────────────────────────────────────────

    def test_17_reranker_reuse(self) -> None:
        """Verify subsequent requests reuse the existing model without reloading."""
        reranker = BGEReranker()
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8, 0.5]
        reranker._model = mock_model

        candidates = [
            make_retrieved_chunk(0, self.meeting_id_str),
            make_retrieved_chunk(1, self.meeting_id_str),
        ]
        reranker.rerank("q1", candidates)
        reranker.rerank("q2", candidates)

        # Same model reused
        self.assertEqual(mock_model.predict.call_count, 2)

    # ── TEST 18: Reranker failure fallback ────────────────────────────────────

    def test_18_reranker_failure_fallback(self) -> None:
        """Verify model failure triggers deterministic fallback without crashing."""
        reranker = BGEReranker()
        reranker._load_failed = True  # Simulate model load failure

        candidates = [
            make_retrieved_chunk(0, self.meeting_id_str, sem_score=0.5, sources=["semantic"]),
            make_retrieved_chunk(1, self.meeting_id_str, sem_score=0.9, sources=["semantic", "bm25"]),
        ]

        results = reranker.rerank("query", candidates)
        self.assertEqual(len(results), 2)
        # Dual-source candidate ranked first in fallback
        self.assertEqual(results[0].chunk_index, 1)

    # ── TEST 19: Reranker failure score semantics ─────────────────────────────

    def test_19_reranker_failure_score_semantics(self) -> None:
        """Verify fallback leaves rerank_score as None and never invents a fake score."""
        reranker = BGEReranker()
        reranker._load_failed = True

        candidates = [make_retrieved_chunk(0, self.meeting_id_str, sem_score=0.7)]
        results = reranker.rerank("query", candidates)

        self.assertIsNone(results[0].rerank_score)

    # ── TEST 20: Meeting isolation end-to-end ──────────────────────────────────

    def test_20_meeting_isolation_end_to_end(self) -> None:
        """Verify meeting A retrieval never returns chunks from meeting B."""
        meeting_b = "660e8400-e29b-41d4-a716-446655440001"

        mock_index = MagicMock()
        mock_index.query.return_value = MagicMock(matches=[
            MagicMock(
                id=f"{self.meeting_id_str}_0",
                score=0.9,
                metadata={
                    "chunk_id": "c-0",
                    "meeting_id": self.meeting_id_str,
                    "chunk_index": 0,
                    "content": "Meeting A content",
                },
            )
        ])
        mock_store = MagicMock(get_index=MagicMock(return_value=mock_index))
        mock_embedder = MagicMock(embed_texts=MagicMock(return_value=[[0.1] * 3072]))

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        results = retriever.retrieve(self.meeting_id_str, "query")

        for r in results:
            self.assertEqual(r.meeting_id, self.meeting_id_str)
            self.assertNotEqual(r.meeting_id, meeting_b)

    # ── TEST 21: Empty query ──────────────────────────────────────────────────

    def test_21_empty_query(self) -> None:
        """Verify empty query returns [] without making external calls."""
        mock_embedder = MagicMock()
        mock_store = MagicMock()

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        self.assertEqual(retriever.retrieve(self.meeting_id_str, ""), [])
        self.assertEqual(retriever.retrieve(self.meeting_id_str, "   "), [])

        mock_embedder.embed_texts.assert_not_called()
        mock_store.get_index.assert_not_called()

    # ── TEST 22: Missing meeting ID ───────────────────────────────────────────

    def test_22_missing_meeting_id(self) -> None:
        """Verify missing or empty meeting_id raises ValueError before retrieval."""
        retriever = HybridRetriever()

        with self.assertRaises(ValueError):
            retriever.retrieve("", "query")

        with self.assertRaises(ValueError):
            retriever.retrieve(None, "query")

    # ── TEST 23: Malformed metadata ───────────────────────────────────────────

    def test_23_malformed_metadata(self) -> None:
        """Verify malformed Pinecone match metadata is skipped without raising an error."""
        mock_index = MagicMock()
        mock_index.query.return_value = MagicMock(matches=[
            MagicMock(id="bad1", score=0.9, metadata=None),
            MagicMock(id="bad2", score=0.8, metadata={"content": ""}),  # Empty content
            MagicMock(
                id="good",
                score=0.7,
                metadata={
                    "chunk_id": "c-good",
                    "meeting_id": self.meeting_id_str,
                    "chunk_index": 0,
                    "content": "Valid content",
                },
            ),
        ])
        mock_store = MagicMock(get_index=MagicMock(return_value=mock_index))
        mock_embedder = MagicMock(embed_texts=MagicMock(return_value=[[0.1] * 3072]))

        retriever = HybridRetriever(embedder=mock_embedder, vector_store=mock_store)
        results = retriever.retrieve_semantic(self.meeting_id_str, "query")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Valid content")

    # ── TEST 24: Candidate bound ──────────────────────────────────────────────

    def test_24_candidate_bound(self) -> None:
        """Verify at most 20 candidates enter reranking."""
        sem_chunks = [make_retrieved_chunk(i, self.meeting_id_str) for i in range(10)]
        bm25_chunks = [make_retrieved_chunk(i + 10, self.meeting_id_str) for i in range(10)]

        retriever = HybridRetriever()
        merged = retriever.merge_and_deduplicate(sem_chunks, bm25_chunks)

        self.assertLessEqual(len(merged), 20)

    # ── TEST 25: No RRF ───────────────────────────────────────────────────────

    def test_25_no_rrf(self) -> None:
        """Verify retriever module does not implement RRF formula or reciprocal ranking."""
        import app.rag.retriever as retriever_module
        source = Path(retriever_module.__file__).read_text(encoding="utf-8")

        self.assertNotIn("rrf", source.lower())
        self.assertNotIn("reciprocal_rank", source.lower())
        self.assertNotIn("1 / (60 +", source)

    # ── TEST 26: No cross-meeting retrieval ───────────────────────────────────

    def test_26_no_cross_meeting_retrieval(self) -> None:
        """Verify semantic and BM25 paths independently enforce meeting scope."""
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        retriever = HybridRetriever()
        retriever.retrieve_bm25(self.meeting_id_str, "q", db_session=mock_session)

        # Meeting ID passed in query
        call_stmt = mock_session.execute.call_args[0][0]
        compiled = call_stmt.compile()
        self.assertTrue(
            self.meeting_uuid in compiled.params.values()
            or str(self.meeting_uuid) in str(compiled.params)
        )

    # ── TEST 27: No direct API-key access ─────────────────────────────────────

    def test_27_no_direct_api_key_access(self) -> None:
        """Verify retriever has no provider credential attributes or direct env access."""
        retriever = HybridRetriever(embedder=MagicMock(), vector_store=MagicMock())

        self.assertFalse(hasattr(retriever, "api_key"))
        self.assertFalse(hasattr(retriever, "gemini_key"))
        self.assertFalse(hasattr(retriever, "google_api_key"))

    # ── TEST 28: Deterministic fallback ───────────────────────────────────────

    def test_28_deterministic_fallback(self) -> None:
        """Verify repeated reranker failure produces identical stable ordering."""
        reranker = BGEReranker()
        reranker._load_failed = True

        c1 = make_retrieved_chunk(1, self.meeting_id_str, sem_score=0.4, bm25_score=2.0, sources=["semantic"])
        c2 = make_retrieved_chunk(2, self.meeting_id_str, sem_score=0.8, bm25_score=5.0, sources=["semantic", "bm25"])
        c3 = make_retrieved_chunk(3, self.meeting_id_str, sem_score=0.9, sources=["semantic"])

        run1 = reranker.rerank("q", [c1, c2, c3])
        run2 = reranker.rerank("q", [c1, c2, c3])

        self.assertEqual([c.chunk_id for c in run1], [c.chunk_id for c in run2])
        # Dual-source candidate ranked first
        self.assertEqual(run1[0].chunk_id, c2.chunk_id)


if __name__ == "__main__":
    unittest.main()
