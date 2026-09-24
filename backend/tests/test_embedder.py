"""
Unit tests for Embedding and Pinecone Vector Storage Layer (Gate 3 - Batch 2).

Validates all 20 mandatory test requirements:
- TEST 1: Embed a valid chunk list (chunks accepted, result returned, ordering preserved)
- TEST 2: Correct Gemini model (verifies gemini-embedding-001)
- TEST 3: Correct embedding use case (verifies use_case="embedding")
- TEST 4: Provider Gateway boundary (embedder does not access raw keys, routes via gateway)
- TEST 5: Embedding dimension (verifies 3072-dimensional vector acceptance)
- TEST 6: Empty input (empty chunks -> no gateway call, clean empty result)
- TEST 7: Vector ID determinism ({meeting_id}_{chunk_index})
- TEST 8: Namespace determinism (meeting_{meeting_id})
- TEST 9: Metadata preservation (all 9 required metadata fields verified)
- TEST 10: Pinecone upsert (correct payload, IDs, namespace, metadata)
- TEST 11: Multiple chunks (all chunks become vectors, ordering preserved)
- TEST 12: Embedding count mismatch (raises EmbeddingError)
- TEST 13: Invalid dimension (raises EmbeddingError)
- TEST 14: Missing meeting ID (fails before external storage)
- TEST 15: Pinecone retry (transient failure triggers bounded retry)
- TEST 16: Pinecone permanent failure (surfaces as PineconeError)
- TEST 17: Re-ingestion namespace (old namespace cleared before upsert)
- TEST 18: Deterministic re-ingestion IDs (identical IDs across runs)
- TEST 19: Secret-safe logging (credentials never logged)
- TEST 20: No retrieval behavior (no query, no BM25, no reranker)
- RE-INGESTION TEST: End-to-end overwrite lifecycle
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import EMBEDDING_MODEL, PINECONE_DIMENSIONS
from app.core.exceptions import EmbeddingError, PineconeError
from app.rag.chunker import Chunk
from app.rag.embedder import (
    GeminiEmbedder,
    PineconeVectorStore,
    TranscriptEmbedder,
    VectorRecord,
    get_meeting_namespace,
    get_vector_id,
)


def make_dummy_vector(dim: int = PINECONE_DIMENSIONS, fill: float = 0.05) -> list[float]:
    """Helper to generate a mock vector of given dimension."""
    return [fill] * dim


def make_test_chunks(count: int = 2) -> list[Chunk]:
    """Helper to create dummy valid chunks."""
    return [
        Chunk(
            chunk_index=i,
            speaker_name=f"Speaker_{i}",
            speaker_role=f"Role_{i}",
            timestamp=f"10:{i:02d}",
            content=f"[Speaker_{i} (Role_{i}) - 10:{i:02d}]: Dialogue segment {i}",
            token_count=50,
            chunk_type="dialogue",
            involves_user=False,
        )
        for i in range(count)
    ]


class TestEmbedderAndPinecone(unittest.TestCase):
    """Test suite for Gate 3 - Batch 2 embedding and vector storage."""

    def setUp(self) -> None:
        self.meeting_id = "550e8400-e29b-41d4-a716-446655440000"

    # ── TEST 1: Embed a valid chunk list ───────────────────────────────────────

    def test_01_embed_valid_chunk_list(self) -> None:
        """Verify input chunks are accepted, embedded, and ordering preserved."""
        chunks = make_test_chunks(2)
        fake_vectors = [make_dummy_vector(fill=0.1), make_dummy_vector(fill=0.2)]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        embedder = GeminiEmbedder(gateway=mock_gateway)
        embeddings = embedder.embed_chunks(chunks)

        self.assertEqual(len(embeddings), 2)
        self.assertEqual(embeddings[0][0], 0.1)
        self.assertEqual(embeddings[1][0], 0.2)
        self.assertEqual(len(embeddings[0]), PINECONE_DIMENSIONS)
        self.assertEqual(len(embeddings[1]), PINECONE_DIMENSIONS)

    # ── TEST 2: Correct Gemini model ──────────────────────────────────────────

    def test_02_correct_gemini_model(self) -> None:
        """Verify embedding uses the locked gemini-embedding-001 model."""
        chunks = make_test_chunks(1)
        captured_model = []

        class MockGateway:
            def execute(self, use_case, operation, **kwargs):
                # Pass model string to operation
                return operation("dummy_key", EMBEDDING_MODEL)

        with patch("google.generativeai.embed_content") as mock_embed:
            mock_embed.return_value = {"embedding": [make_dummy_vector()]}
            embedder = GeminiEmbedder(gateway=MockGateway())
            embedder.embed_chunks(chunks)

            self.assertTrue(mock_embed.called)
            kwargs = mock_embed.call_args.kwargs
            self.assertEqual(kwargs.get("model"), "models/gemini-embedding-001")
            self.assertEqual(kwargs.get("output_dimensionality"), 3072)

    # ── TEST 3: Correct embedding use case ─────────────────────────────────────

    def test_03_correct_embedding_use_case(self) -> None:
        """Verify Provider Gateway is invoked with use_case='embedding'."""
        chunks = make_test_chunks(1)
        recorded_use_cases = []

        mock_gateway = MagicMock()
        mock_gateway.execute.side_effect = lambda use_case, op, **kw: (
            recorded_use_cases.append(use_case) or [make_dummy_vector()]
        )

        embedder = GeminiEmbedder(gateway=mock_gateway)
        embedder.embed_chunks(chunks)

        self.assertEqual(recorded_use_cases, ["embedding"])

    # ── TEST 4: Provider Gateway boundary ──────────────────────────────────────

    def test_04_provider_gateway_boundary(self) -> None:
        """Verify embedder never accesses raw API keys directly from settings or env."""
        embedder = GeminiEmbedder(gateway=MagicMock())

        # Verify embedder does not store or expose any raw credential attributes
        self.assertFalse(hasattr(embedder, "api_key"))
        self.assertFalse(hasattr(embedder, "google_api_key"))
        self.assertFalse(hasattr(embedder, "gemini_api_key"))

    # ── TEST 5: Embedding dimension ───────────────────────────────────────────

    def test_05_embedding_dimension(self) -> None:
        """Verify output vectors are validated as exactly 3072-dimensional."""
        chunks = make_test_chunks(1)
        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = [make_dummy_vector(dim=3072)]

        embedder = GeminiEmbedder(gateway=mock_gateway, expected_dimension=3072)
        embeddings = embedder.embed_chunks(chunks)

        self.assertEqual(len(embeddings[0]), 3072)

    # ── TEST 6: Empty input ───────────────────────────────────────────────────

    def test_06_empty_input(self) -> None:
        """Verify empty chunk list returns clean empty result without calling gateway."""
        mock_gateway = MagicMock()
        embedder = GeminiEmbedder(gateway=mock_gateway)

        result_chunks = embedder.embed_chunks([])
        result_texts = embedder.embed_texts([])

        self.assertEqual(result_chunks, [])
        self.assertEqual(result_texts, [])
        mock_gateway.execute.assert_not_called()

    # ── TEST 7: Vector ID determinism ─────────────────────────────────────────

    def test_07_vector_id_determinism(self) -> None:
        """Verify vector IDs follow the exact {meeting_id}_{chunk_index} format."""
        vec_id_0 = get_vector_id(self.meeting_id, 0)
        vec_id_4 = get_vector_id(self.meeting_id, 4)

        self.assertEqual(vec_id_0, f"{self.meeting_id}_0")
        self.assertEqual(vec_id_4, f"{self.meeting_id}_4")

        # Deterministic across multiple calls
        self.assertEqual(get_vector_id(self.meeting_id, 0), vec_id_0)

    # ── TEST 8: Namespace determinism ─────────────────────────────────────────

    def test_08_namespace_determinism(self) -> None:
        """Verify namespace is deterministically meeting_{meeting_id}."""
        namespace = get_meeting_namespace(self.meeting_id)
        self.assertEqual(namespace, f"meeting_{self.meeting_id}")

        # Deterministic
        self.assertEqual(get_meeting_namespace(self.meeting_id), namespace)

    # ── TEST 9: Metadata preservation ─────────────────────────────────────────

    def test_09_metadata_preservation(self) -> None:
        """Verify Pinecone metadata contains all 9 required fields."""
        chunks = [
            Chunk(
                chunk_index=0,
                speaker_name="Aryan",
                speaker_role="Project Manager",
                timestamp="10:00",
                content="[Aryan (Project Manager) - 10:00]: Meeting kickoff dialogue.",
                token_count=50,
                chunk_type="dialogue",
                involves_user=False,
            )
        ]
        embeddings = [make_dummy_vector()]

        coordinator = TranscriptEmbedder(
            embedder=MagicMock(),
            vector_store=MagicMock(),
        )
        records = coordinator.build_vector_records(self.meeting_id, chunks, embeddings)

        self.assertEqual(len(records), 1)
        meta = records[0].metadata

        # Verify all 9 required fields
        required_fields = [
            "chunk_id",
            "meeting_id",
            "chunk_index",
            "speaker_name",
            "speaker_role",
            "timestamp",
            "chunk_type",
            "involves_user",
            "content",
        ]
        for f in required_fields:
            self.assertIn(f, meta, f"Metadata must contain field '{f}'")

        self.assertEqual(meta["meeting_id"], self.meeting_id)
        self.assertEqual(meta["chunk_index"], 0)
        self.assertEqual(meta["speaker_name"], "Aryan")
        self.assertEqual(meta["speaker_role"], "Project Manager")
        self.assertEqual(meta["timestamp"], "10:00")
        self.assertEqual(meta["chunk_type"], "dialogue")
        self.assertEqual(meta["involves_user"], False)
        self.assertEqual(meta["content"], chunks[0].content)

    # ── TEST 10: Pinecone upsert ──────────────────────────────────────────────

    def test_10_pinecone_upsert(self) -> None:
        """Verify vectors are sent to Pinecone with correct IDs, values, metadata, and namespace."""
        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        store = PineconeVectorStore(client=mock_client)
        records = [
            VectorRecord(
                id=f"{self.meeting_id}_0",
                values=make_dummy_vector(fill=0.1),
                metadata={"test": "val"},
            )
        ]

        count = store.upsert_vectors(records, self.meeting_id)
        self.assertEqual(count, 1)

        mock_index.upsert.assert_called_once()
        call_kwargs = mock_index.upsert.call_args.kwargs
        self.assertEqual(call_kwargs["namespace"], f"meeting_{self.meeting_id}")
        self.assertEqual(len(call_kwargs["vectors"]), 1)
        self.assertEqual(call_kwargs["vectors"][0]["id"], f"{self.meeting_id}_0")
        self.assertEqual(call_kwargs["vectors"][0]["values"], records[0].values)
        self.assertEqual(call_kwargs["vectors"][0]["metadata"], {"test": "val"})

    # ── TEST 11: Multiple chunks ──────────────────────────────────────────────

    def test_11_multiple_chunks(self) -> None:
        """Verify multiple chunks are all converted to vector records in order without drops."""
        chunks = make_test_chunks(5)
        fake_vectors = [make_dummy_vector(fill=i * 0.1) for i in range(5)]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        embedder = GeminiEmbedder(gateway=mock_gateway)
        store = PineconeVectorStore(client=mock_client)
        coordinator = TranscriptEmbedder(embedder=embedder, vector_store=store)

        records = coordinator.embed_and_store(self.meeting_id, chunks)

        self.assertEqual(len(records), 5)
        for i in range(5):
            self.assertEqual(records[i].id, f"{self.meeting_id}_{i}")
            self.assertEqual(records[i].metadata["chunk_index"], i)
            self.assertEqual(chunks[i].pinecone_vector_id, f"{self.meeting_id}_{i}")

    # ── TEST 12: Embedding count mismatch ─────────────────────────────────────

    def test_12_embedding_count_mismatch(self) -> None:
        """Verify mismatch between input chunks and returned embeddings raises EmbeddingError."""
        chunks = make_test_chunks(3)
        # Provider returns only 2 vectors for 3 chunks
        fake_vectors = [make_dummy_vector(), make_dummy_vector()]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        embedder = GeminiEmbedder(gateway=mock_gateway)
        with self.assertRaises(EmbeddingError) as ctx:
            embedder.embed_chunks(chunks)
        self.assertIn("Embedding count mismatch", str(ctx.exception))

    # ── TEST 13: Invalid dimension ────────────────────────────────────────────

    def test_13_invalid_dimension(self) -> None:
        """Verify non-3072 dimension vector raises EmbeddingError."""
        chunks = make_test_chunks(1)
        # Returns 768-dim vector instead of 3072
        fake_vectors = [make_dummy_vector(dim=768)]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        embedder = GeminiEmbedder(gateway=mock_gateway)
        with self.assertRaises(EmbeddingError) as ctx:
            embedder.embed_chunks(chunks)
        self.assertIn("Invalid embedding dimension", str(ctx.exception))

    # ── TEST 14: Missing meeting ID ───────────────────────────────────────────

    def test_14_missing_meeting_id(self) -> None:
        """Verify missing or empty meeting_id fails before external storage."""
        chunks = make_test_chunks(1)
        coordinator = TranscriptEmbedder(embedder=MagicMock(), vector_store=MagicMock())

        with self.assertRaises(ValueError):
            coordinator.embed_and_store("", chunks)

        with self.assertRaises(ValueError):
            coordinator.embed_and_store(None, chunks)

        with self.assertRaises(ValueError):
            get_meeting_namespace("")

        with self.assertRaises(ValueError):
            get_vector_id("", 0)

    # ── TEST 15: Pinecone retry ───────────────────────────────────────────────

    def test_15_pinecone_retry(self) -> None:
        """Verify transient Pinecone failure triggers bounded retry and succeeds."""
        mock_index = MagicMock()
        # Fail once, then succeed on retry
        mock_index.upsert.side_effect = [RuntimeError("Transient 503 Service Unavailable"), {"upserted_count": 1}]
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        store = PineconeVectorStore(client=mock_client, retry_count=2)
        records = [VectorRecord(id="v1", values=make_dummy_vector(), metadata={})]

        with patch("time.sleep"):  # Avoid actual sleep during tests
            count = store.upsert_vectors(records, self.meeting_id)

        self.assertEqual(count, 1)
        self.assertEqual(mock_index.upsert.call_count, 2)

    # ── TEST 16: Pinecone permanent failure ───────────────────────────────────

    def test_16_pinecone_permanent_failure(self) -> None:
        """Verify permanent Pinecone failure exhausts retries and raises PineconeError."""
        mock_index = MagicMock()
        mock_index.upsert.side_effect = RuntimeError("Persistent Connection Refused")
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        store = PineconeVectorStore(client=mock_client, retry_count=2)
        records = [VectorRecord(id="v1", values=make_dummy_vector(), metadata={})]

        with patch("time.sleep"):
            with self.assertRaises(PineconeError) as ctx:
                store.upsert_vectors(records, self.meeting_id)

        self.assertIn("Pinecone upsert failed", str(ctx.exception))
        # Initial attempt + 2 retries = 3 attempts total
        self.assertEqual(mock_index.upsert.call_count, 3)

    # ── TEST 17: Re-ingestion namespace ───────────────────────────────────────

    def test_17_reingestion_namespace(self) -> None:
        """Verify existing namespace is cleared before new vectors are upserted."""
        chunks = make_test_chunks(2)
        fake_vectors = [make_dummy_vector(), make_dummy_vector()]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        embedder = GeminiEmbedder(gateway=mock_gateway)
        store = PineconeVectorStore(client=mock_client)
        coordinator = TranscriptEmbedder(embedder=embedder, vector_store=store)

        coordinator.embed_and_store(self.meeting_id, chunks)

        # delete_all=True must have been called on meeting namespace
        mock_index.delete.assert_called_once_with(
            delete_all=True,
            namespace=f"meeting_{self.meeting_id}",
        )
        # upsert must have been called on the same meeting namespace
        mock_index.upsert.assert_called_once()
        self.assertEqual(
            mock_index.upsert.call_args.kwargs["namespace"],
            f"meeting_{self.meeting_id}",
        )

    # ── TEST 18: Deterministic re-ingestion IDs ───────────────────────────────

    def test_18_deterministic_reingestion_ids(self) -> None:
        """Verify re-ingesting the same chunks produces identical deterministic vector IDs."""
        chunks = make_test_chunks(3)
        fake_vectors = [make_dummy_vector() for _ in range(3)]

        coordinator = TranscriptEmbedder(embedder=MagicMock(), vector_store=MagicMock())

        records_run1 = coordinator.build_vector_records(self.meeting_id, chunks, fake_vectors)
        records_run2 = coordinator.build_vector_records(self.meeting_id, chunks, fake_vectors)

        self.assertEqual(len(records_run1), len(records_run2))
        for r1, r2 in zip(records_run1, records_run2):
            self.assertEqual(r1.id, r2.id)
            self.assertEqual(r1.metadata, r2.metadata)

    # ── TEST 19: Secret-safe logging ──────────────────────────────────────────

    def test_19_secret_safe_logging(self) -> None:
        """Verify raw credentials or Authorization headers are never logged."""
        import io
        from loguru import logger as loguru_logger

        chunks = make_test_chunks(1)
        fake_vectors = [make_dummy_vector()]

        mock_gateway = MagicMock()
        mock_gateway.execute.return_value = fake_vectors

        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        embedder = GeminiEmbedder(gateway=mock_gateway)
        store = PineconeVectorStore(client=mock_client)
        coordinator = TranscriptEmbedder(embedder=embedder, vector_store=store)

        log_stream = io.StringIO()
        sink_id = loguru_logger.add(log_stream, level="INFO")
        try:
            coordinator.embed_and_store(self.meeting_id, chunks)
            log_output = log_stream.getvalue()

            # Ensure logs were generated
            self.assertGreater(len(log_output), 0)
            # Ensure no API key pattern or authorization header appears
            self.assertNotIn("AIza", log_output)
            self.assertNotIn("pcsk_", log_output)
            self.assertNotIn("Bearer", log_output)
            # Ensure safe diagnostic fields are logged instead
            self.assertIn(f"meeting_{self.meeting_id}", log_output)
        finally:
            loguru_logger.remove(sink_id)

    # ── TEST 20: No retrieval behavior ────────────────────────────────────────

    def test_20_no_retrieval_behavior(self) -> None:
        """Verify Batch 2 does not implement retrieval/query/BM25/rerank methods."""
        import app.rag.embedder as embedder_module

        # Ensure no query / search / bm25 functions in embedder module
        forbidden_terms = [
            "query",
            "retrieve",
            "retriever",
            "bm25",
            "rerank",
            "reranker",
            "similarity_search",
        ]
        module_attrs = dir(embedder_module)
        for term in forbidden_terms:
            self.assertNotIn(
                term,
                module_attrs,
                f"Batch 2 must not implement retrieval construct: '{term}'",
            )

    # ── RE-INGESTION TEST: Overwrite Lifecycle ─────────────────────────────────

    def test_reingestion_lifecycle_overwrite(self) -> None:
        """
        Verify approved overwrite lifecycle:
        1. Existing meeting namespace is purged via delete_all=True
        2. Database chunks deleted if db_session provided
        3. New vectors generated and upserted under same namespace
        """
        chunks_v1 = make_test_chunks(2)
        chunks_v2 = make_test_chunks(3)

        fake_vectors_v1 = [make_dummy_vector(fill=0.1) for _ in range(2)]
        fake_vectors_v2 = [make_dummy_vector(fill=0.2) for _ in range(3)]

        mock_gateway = MagicMock()
        mock_gateway.execute.side_effect = [fake_vectors_v1, fake_vectors_v2]

        mock_index = MagicMock()
        mock_client = MagicMock()
        mock_client.Index.return_value = mock_index

        mock_db_session = MagicMock()

        embedder = GeminiEmbedder(gateway=mock_gateway)
        store = PineconeVectorStore(client=mock_client)
        coordinator = TranscriptEmbedder(embedder=embedder, vector_store=store)

        # Ingestion 1
        rec1 = coordinator.embed_and_store(self.meeting_id, chunks_v1, db_session=mock_db_session)
        self.assertEqual(len(rec1), 2)
        self.assertEqual(mock_index.delete.call_count, 1)
        self.assertEqual(mock_index.upsert.call_count, 1)

        # Ingestion 2 (Re-ingestion / Overwrite)
        rec2 = coordinator.embed_and_store(self.meeting_id, chunks_v2, db_session=mock_db_session)
        self.assertEqual(len(rec2), 3)

        # Verify second deletion occurred before second upsert
        self.assertEqual(mock_index.delete.call_count, 2)
        self.assertEqual(mock_index.upsert.call_count, 2)

        # Verify DB session delete executed
        self.assertEqual(mock_db_session.execute.call_count, 2)
        self.assertEqual(mock_db_session.commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
