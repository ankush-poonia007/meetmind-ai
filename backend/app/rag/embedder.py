"""
Embedding and Pinecone Vector Storage Layer for MeetMind AI RAG Pipeline (Gate 3 - Batch 2).

Converts structured Chunk objects from Batch 1 into 3072-dimensional embeddings
using Gemini (gemini-embedding-001) via ProviderGateway, and stores them in Pinecone
under meeting-scoped namespaces (meeting_{meeting_id}) with deterministic vector IDs
({meeting_id}_{chunk_index}).

Architecture constraints:
- Provider Gateway mediation: Embedder never accesses raw API keys directly.
- Use case: 'embedding' (resolves to ProviderName.GEMINI, EMBEDDING_MODEL).
- Vector dimension: 3072 (validated strictly).
- Namespace: meeting_{meeting_id} (hard isolation boundary).
- Vector ID: {meeting_id}_{chunk_index} (deterministic idempotency).
- Approved re-ingestion: Clears existing vectors for namespace before upserting.
- Secret safety: Credentials never logged.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.core.config import (
    EMBEDDING_MODEL,
    PINECONE_DIMENSIONS,
    PINECONE_NAMESPACE_PREFIX,
    PINECONE_RETRY_COUNT,
)
from app.core.exceptions import EmbeddingError, PineconeError, ProviderError
from app.core.logging import get_logger
from app.core.providers.gateway import ProviderGateway, get_provider_gateway
from app.core.settings import settings as app_settings
from app.rag.chunker import Chunk

logger = get_logger("rag.embedder")


# ── Identifiers and Namespaces ───────────────────────────────────────────────

def get_meeting_namespace(meeting_id: Union[str, uuid.UUID]) -> str:
    """
    Return deterministic Pinecone namespace for a meeting: meeting_{meeting_id}.
    This namespace acts as a hard multi-tenant isolation boundary.
    """
    if not meeting_id or not str(meeting_id).strip():
        raise ValueError("meeting_id cannot be empty")
    return f"{PINECONE_NAMESPACE_PREFIX}{meeting_id}"


def get_vector_id(meeting_id: Union[str, uuid.UUID], chunk_index: int) -> str:
    """
    Return deterministic vector ID: {meeting_id}_{chunk_index}.
    Enables safe idempotent overwrite and prevents duplicate vector creation.
    """
    if not meeting_id or not str(meeting_id).strip():
        raise ValueError("meeting_id cannot be empty")
    if chunk_index < 0:
        raise ValueError("chunk_index cannot be negative")
    return f"{meeting_id}_{chunk_index}"


# ── Vector Record Contract ───────────────────────────────────────────────────

class VectorRecord(BaseModel):
    """
    Normalized vector record payload ready for Pinecone upsert.
    """

    id: str = Field(..., description="Deterministic vector ID ({meeting_id}_{chunk_index})")
    values: List[float] = Field(..., description="Embedding vector (3072 floats)")
    metadata: Dict[str, Any] = Field(..., description="Chunk metadata dictionary")


# ── Gemini Embedder ──────────────────────────────────────────────────────────

class GeminiEmbedder:
    """
    Generates 3072-dimensional vector embeddings using Gemini via ProviderGateway.

    Enforces Provider Gateway boundary: never reads raw API keys directly from
    environment or settings. All provider calls are routed through
    ProviderGateway.execute("embedding", ...).
    """

    def __init__(
        self,
        gateway: Optional[ProviderGateway] = None,
        batch_size: int = 32,
        expected_dimension: int = PINECONE_DIMENSIONS,
        model_name: str = EMBEDDING_MODEL,
    ) -> None:
        self.gateway = gateway or get_provider_gateway()
        self.batch_size = batch_size
        self.expected_dimension = expected_dimension
        self.model_name = model_name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of text strings into 3072-dimensional vectors.

        Splits texts into batches (default 32) and routes each batch
        through ProviderGateway with use_case='embedding'.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            def _call_gemini_embed(api_key: str, model_str: Optional[str]) -> List[List[float]]:
                target_model = model_str or self.model_name
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=api_key)

                    response = genai.embed_content(
                        model=target_model,
                        content=batch,
                        task_type="retrieval_document",
                        output_dimensionality=self.expected_dimension,
                    )
                    raw_emb = response.get("embedding", [])
                    # Handle single embedding vs list of embeddings
                    if raw_emb and isinstance(raw_emb[0], (int, float)):
                        return [raw_emb]
                    return raw_emb
                except Exception as exc:
                    logger.warning("Gemini embedding API call failed: %s", exc)
                    raise

            try:
                batch_embeddings = self.gateway.execute("embedding", _call_gemini_embed)
            except ProviderError as pe:
                raise EmbeddingError(f"Embedding failed via provider gateway: {pe.message}") from pe
            except Exception as exc:
                raise EmbeddingError(f"Embedding failed: {exc}") from exc

            if not isinstance(batch_embeddings, list):
                raise EmbeddingError(
                    f"Expected list of embeddings from provider, got {type(batch_embeddings).__name__}"
                )

            all_embeddings.extend(batch_embeddings)

        # Validate count
        if len(all_embeddings) != len(texts):
            raise EmbeddingError(
                f"Embedding count mismatch: expected {len(texts)} embeddings, got {len(all_embeddings)}"
            )

        # Validate dimensions
        for idx, vec in enumerate(all_embeddings):
            if not isinstance(vec, list) or len(vec) != self.expected_dimension:
                actual_dim = len(vec) if isinstance(vec, list) else 0
                raise EmbeddingError(
                    f"Invalid embedding dimension at index {idx}: expected {self.expected_dimension}, got {actual_dim}"
                )

        return all_embeddings

    def embed_chunks(self, chunks: List[Chunk]) -> List[List[float]]:
        """Extract content from chunks and generate embeddings."""
        if not chunks:
            return []
        texts = [chunk.content for chunk in chunks]
        return self.embed_texts(texts)


# ── Pinecone Vector Store ────────────────────────────────────────────────────

class PineconeVectorStore:
    """
    Manages vector storage in Pinecone with meeting-scoped namespace isolation.

    Handles deterministic vector upserts, bounded transient retries,
    and namespace clearing for re-ingestion.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        client: Optional[Any] = None,
        retry_count: int = PINECONE_RETRY_COUNT,
    ) -> None:
        self.index_name = index_name or app_settings.pinecone_index_name
        self._api_key = api_key or app_settings.pinecone_api_key
        self.retry_count = retry_count
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise PineconeError("Pinecone API key is not configured in settings.")
            try:
                from pinecone import Pinecone
                self._client = Pinecone(api_key=self._api_key)
            except Exception as exc:
                raise PineconeError(f"Failed to initialize Pinecone client: {exc}") from exc
        return self._client

    def get_index(self) -> Any:
        """Returns the Pinecone Index handle."""
        client = self._get_client()
        try:
            return client.Index(name=self.index_name)
        except Exception as exc:
            raise PineconeError(f"Failed to connect to Pinecone index '{self.index_name}': {exc}") from exc

    def upsert_vectors(
        self,
        vectors: List[VectorRecord],
        meeting_id: Union[str, uuid.UUID],
    ) -> int:
        """
        Upsert vector records into the meeting namespace with bounded retry.
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required for Pinecone upsert")
        if not vectors:
            return 0

        namespace = get_meeting_namespace(meeting_id)
        index = self.get_index()

        payload = [
            {"id": v.id, "values": v.values, "metadata": v.metadata}
            for v in vectors
        ]

        attempt = 0
        last_error = None
        while attempt <= self.retry_count:
            try:
                index.upsert(vectors=payload, namespace=namespace)
                logger.info(
                    f"Upserted {len(vectors)} vectors to Pinecone namespace '{namespace}'"
                )
                return len(vectors)
            except Exception as exc:
                last_error = exc
                attempt += 1
                if attempt <= self.retry_count:
                    logger.warning(
                        f"Pinecone upsert transient error (attempt {attempt}/{self.retry_count}): {exc}"
                    )
                    time.sleep(0.5 * attempt)
                else:
                    break

        raise PineconeError(
            f"Pinecone upsert failed after {self.retry_count + 1} attempts: {last_error}"
        ) from last_error

    def delete_meeting_vectors(self, meeting_id: Union[str, uuid.UUID]) -> None:
        """
        Delete all vectors in the meeting namespace (meeting_{meeting_id}).
        Used for safe re-ingestion / overwrite.
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required to delete vectors")

        namespace = get_meeting_namespace(meeting_id)
        index = self.get_index()

        attempt = 0
        last_error = None
        while attempt <= self.retry_count:
            try:
                index.delete(delete_all=True, namespace=namespace)
                logger.info(f"Cleared Pinecone vectors for namespace '{namespace}'")
                return
            except Exception as exc:
                err_str = str(exc).lower()
                # If namespace doesn't exist or is empty, consider cleared
                if "not found" in err_str or "namespace not found" in err_str or "404" in err_str:
                    logger.info(f"Namespace '{namespace}' did not exist in Pinecone; nothing to delete.")
                    return
                last_error = exc
                attempt += 1
                if attempt <= self.retry_count:
                    logger.warning(
                        f"Pinecone delete transient error (attempt {attempt}/{self.retry_count}): {exc}"
                    )
                    time.sleep(0.5 * attempt)
                else:
                    break

        raise PineconeError(
            f"Pinecone delete failed for namespace '{namespace}' after {self.retry_count + 1} attempts: {last_error}"
        ) from last_error


# ── High-Level Coordinator ───────────────────────────────────────────────────

class TranscriptEmbedder:
    """
    Coordinates embedding generation and Pinecone vector storage for meeting chunks.

    Implements the approved re-ingestion strategy:
    1. Clear existing vectors for meeting namespace (and optional DB chunks)
    2. Generate embeddings via GeminiEmbedder (mediated by ProviderGateway)
    3. Construct deterministic VectorRecords with required metadata
    4. Upsert vectors to Pinecone namespace meeting_{meeting_id}
    5. Update chunk.pinecone_vector_id on chunks
    """

    def __init__(
        self,
        embedder: Optional[GeminiEmbedder] = None,
        vector_store: Optional[PineconeVectorStore] = None,
    ) -> None:
        self.embedder = embedder or GeminiEmbedder()
        self.vector_store = vector_store or PineconeVectorStore()

    def build_vector_records(
        self,
        meeting_id: Union[str, uuid.UUID],
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> List[VectorRecord]:
        """Construct deterministic VectorRecord objects from chunks and embeddings."""
        if len(chunks) != len(embeddings):
            raise EmbeddingError(
                f"Chunk and embedding counts mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        records: List[VectorRecord] = []
        for chunk, emb in zip(chunks, embeddings):
            vec_id = get_vector_id(meeting_id, chunk.chunk_index)
            chunk.pinecone_vector_id = vec_id

            # Determine chunk_id: use chunk.id if present, else deterministic UUID
            raw_id = getattr(chunk, "id", None)
            chunk_id_str = str(raw_id) if raw_id else str(uuid.uuid5(uuid.NAMESPACE_DNS, vec_id))

            metadata = {
                "chunk_id": chunk_id_str,
                "meeting_id": str(meeting_id),
                "chunk_index": chunk.chunk_index,
                "speaker_name": chunk.speaker_name or "Unknown Speaker",
                "speaker_role": chunk.speaker_role or "",
                "timestamp": chunk.timestamp or "",
                "chunk_type": chunk.chunk_type,
                "involves_user": chunk.involves_user,
                "content": chunk.content,
            }

            records.append(VectorRecord(id=vec_id, values=emb, metadata=metadata))

        return records

    def embed_and_store(
        self,
        meeting_id: Union[str, uuid.UUID],
        chunks: List[Chunk],
        db_session: Optional[Any] = None,
    ) -> List[VectorRecord]:
        """
        Embeds chunks and stores them in Pinecone with deterministic IDs.
        Implements the approved overwrite / re-ingestion lifecycle.
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required")

        if not chunks:
            logger.info("Empty chunk list provided for meeting %s; skipping embedding.", meeting_id)
            return []

        # Validate chunk objects
        for idx, chunk in enumerate(chunks):
            if not isinstance(chunk, Chunk):
                raise ValueError(
                    f"Invalid chunk object at index {idx}: expected Chunk, got {type(chunk).__name__}"
                )
            if not chunk.content or not chunk.content.strip():
                raise ValueError(f"Chunk at index {idx} has empty content")

        # Step 1: Safe re-ingestion cleanup
        # a) If database session provided, clean stale PostgreSQL chunks
        if db_session is not None:
            try:
                from sqlalchemy import delete
                from app.db.models.transcript_chunk import TranscriptChunk
                meeting_uuid = uuid.UUID(str(meeting_id))
                db_session.execute(delete(TranscriptChunk).where(TranscriptChunk.meeting_id == meeting_uuid))
                db_session.commit()
                logger.info(f"Cleaned stale PostgreSQL chunks for meeting {meeting_id}")
            except Exception as exc:
                logger.warning("Failed to delete stale PostgreSQL chunks: %s", exc)
                if hasattr(db_session, "rollback"):
                    db_session.rollback()

        # b) Clear existing Pinecone vectors for this meeting namespace
        self.vector_store.delete_meeting_vectors(meeting_id)

        # Step 2: Generate Gemini embeddings via ProviderGateway
        embeddings = self.embedder.embed_chunks(chunks)

        # Step 3: Build deterministic VectorRecords
        records = self.build_vector_records(meeting_id, chunks, embeddings)

        # Step 4: Upsert to Pinecone namespace
        self.vector_store.upsert_vectors(records, meeting_id)

        return records
