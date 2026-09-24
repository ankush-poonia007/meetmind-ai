"""
Hybrid Retrieval Engine for MeetMind AI RAG Pipeline (Gate 3 - Batch 3).

Coordinates hybrid retrieval for a single meeting:
1. Pinecone Semantic Retrieval (Top 10, namespace=meeting_{meeting_id})
2. PostgreSQL BM25 Lexical Retrieval (Top 10, filtered by meeting_id)
3. Union Merge + Deduplication by chunk identity (retaining scores and sources)
4. Local BGE CrossEncoder Reranking (BAAI/bge-reranker-v2-m3)
5. Final Top 5 Selection as normalized RetrievedChunk objects

Strict architecture boundaries:
- NO reciprocal rank fusion or weighted score formulas.
- NO cross-meeting retrieval (meeting_id is a hard boundary for both paths).
- NO direct API-key access (query embeddings routed via ProviderGateway with use_case="embedding").
- NO LLM text generation or Q&A synthesis (retrieves context only).
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

from app.core.config import (
    BM25_TOP_K,
    PINECONE_TOP_K,
    RERANKER_TOP_K,
)
from app.core.logging import get_logger
from app.rag.embedder import (
    GeminiEmbedder,
    PineconeVectorStore,
    get_meeting_namespace,
)
from app.rag.reranker import BGEReranker, get_reranker

logger = get_logger("rag.retriever")


# ── Normalized Retrieval Contract ────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    """
    Normalized retrieval candidate representing a merged and reranked transcript chunk.
    Consumed downstream by the Q&A Agent.
    """

    chunk_id: str = Field(..., description="Unique chunk UUID string")
    meeting_id: str = Field(..., description="Meeting ID string")
    chunk_index: int = Field(..., description="0-based sequence index in transcript")
    content: str = Field(..., description="Text content of the chunk")
    speaker_name: Optional[str] = Field(default="Unknown Speaker", description="Attributed speaker name")
    speaker_role: Optional[str] = Field(default=None, description="Speaker role if known")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of the turn/chunk if known")
    chunk_type: Optional[str] = Field(default="dialogue", description="Chunk classification (dialogue, decision, task_mention)")
    involves_user: bool = Field(default=False, description="Flag indicating if chunk involves current user")
    semantic_score: Optional[float] = Field(default=None, description="Cosine similarity score from Pinecone (0.0 - 1.0)")
    bm25_score: Optional[float] = Field(default=None, description="Lexical relevance score from BM25Okapi")
    rerank_score: Optional[float] = Field(default=None, description="CrossEncoder relevance score from BGE reranker")
    retrieval_sources: List[str] = Field(default_factory=list, description="List of retrieval sources, e.g. ['semantic', 'bm25']")


# ── BM25 Tokenizer ───────────────────────────────────────────────────────────

def tokenize_bm25(text: str) -> List[str]:
    """
    Deterministic lightweight lowercase word tokenizer for BM25.
    Extracts alphanumeric tokens consistently for both corpus documents and queries.
    """
    if not text:
        return []
    return re.findall(r"\b\w+\b", text.lower())


# ── Hybrid Retriever ─────────────────────────────────────────────────────────

class HybridRetriever:
    """
    Retrieval engine implementing the frozen Gate 3 hybrid RAG pipeline:
    Semantic Top 10 + BM25 Top 10 -> Merge/Dedup -> BGE Rerank -> Top 5.
    """

    def __init__(
        self,
        embedder: Optional[GeminiEmbedder] = None,
        vector_store: Optional[PineconeVectorStore] = None,
        reranker: Optional[BGEReranker] = None,
        semantic_top_k: int = PINECONE_TOP_K,
        bm25_top_k: int = BM25_TOP_K,
        final_top_k: int = RERANKER_TOP_K,
    ) -> None:
        self.embedder = embedder or GeminiEmbedder()
        self.vector_store = vector_store or PineconeVectorStore()
        self.reranker = reranker or get_reranker()
        self.semantic_top_k = semantic_top_k
        self.bm25_top_k = bm25_top_k
        self.final_top_k = final_top_k

    # ── Semantic Retrieval ───────────────────────────────────────────────────

    def retrieve_semantic(
        self,
        meeting_id: Union[str, uuid.UUID],
        query: str,
    ) -> List[RetrievedChunk]:
        """
        Query Pinecone under meeting_{meeting_id} using Gemini query embedding.
        Returns Top 10 semantic candidates.
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required for semantic retrieval")
        if not query or not query.strip():
            return []

        # Step 1: Generate query embedding using Provider Gateway (use_case="embedding")
        query_embeddings = self.embedder.embed_texts([query.strip()])
        if not query_embeddings:
            return []
        query_vector = query_embeddings[0]

        # Step 2: Query meeting namespace in Pinecone
        namespace = get_meeting_namespace(meeting_id)
        index = self.vector_store.get_index()

        try:
            results = index.query(
                vector=query_vector,
                top_k=self.semantic_top_k,
                namespace=namespace,
                include_metadata=True,
            )
        except Exception as exc:
            logger.warning(f"Pinecone query failed for namespace '{namespace}': {exc}")
            return []

        if isinstance(results, dict):
            matches = results.get("matches", [])
        else:
            matches = getattr(results, "matches", [])

        candidates: List[RetrievedChunk] = []
        for m in matches:
            meta = getattr(m, "metadata", None) or (m.get("metadata") if isinstance(m, dict) else {})
            if not isinstance(meta, dict) or not meta.get("content"):
                # Skip invalid or malformed metadata without crashing
                logger.warning(f"Skipping match with invalid or empty metadata: {m}")
                continue

            score_val = getattr(m, "score", None) or (m.get("score") if isinstance(m, dict) else 0.0)

            chunk_id = str(meta.get("chunk_id") or getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else uuid.uuid4()))
            chunk = RetrievedChunk(
                chunk_id=chunk_id,
                meeting_id=str(meeting_id),
                chunk_index=int(meta.get("chunk_index", 0)),
                content=str(meta.get("content", "")),
                speaker_name=meta.get("speaker_name") or "Unknown Speaker",
                speaker_role=meta.get("speaker_role") or None,
                timestamp=meta.get("timestamp") or None,
                chunk_type=meta.get("chunk_type") or "dialogue",
                involves_user=bool(meta.get("involves_user", False)),
                semantic_score=float(score_val) if score_val is not None else None,
                bm25_score=None,
                rerank_score=None,
                retrieval_sources=["semantic"],
            )
            candidates.append(chunk)

        logger.info(f"Retrieved {len(candidates)} semantic candidates from namespace '{namespace}'")
        return candidates[:self.semantic_top_k]

    # ── BM25 Retrieval ───────────────────────────────────────────────────────

    def retrieve_bm25(
        self,
        meeting_id: Union[str, uuid.UUID],
        query: str,
        db_session: Optional[Any] = None,
    ) -> List[RetrievedChunk]:
        """
        Query PostgreSQL transcript_chunks for meeting_id using in-memory BM25Okapi.
        Returns Top 10 lexical candidates.
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required for BM25 retrieval")
        if not query or not query.strip() or db_session is None:
            return []

        tokenized_query = tokenize_bm25(query)
        if not tokenized_query:
            return []

        # Step 1: Fetch meeting-scoped chunks from PostgreSQL
        try:
            from sqlalchemy import select
            from app.db.models.transcript_chunk import TranscriptChunk

            meeting_uuid = uuid.UUID(str(meeting_id))
            stmt = (
                select(TranscriptChunk)
                .where(TranscriptChunk.meeting_id == meeting_uuid)
                .order_by(TranscriptChunk.chunk_index)
            )
            chunks = db_session.execute(stmt).scalars().all()
        except Exception as exc:
            logger.warning(f"Failed to fetch PostgreSQL chunks for BM25 (meeting={meeting_id}): {exc}")
            return []

        if not chunks:
            logger.info(f"No PostgreSQL chunks found for meeting {meeting_id}; BM25 returning empty.")
            return []

        # Step 2: Build in-memory BM25Okapi corpus
        corpus = [tokenize_bm25(c.content) for c in chunks]
        bm25 = BM25Okapi(corpus)

        # Step 3: Score documents
        scores = bm25.get_scores(tokenized_query)

        # Step 4: Rank candidates
        scored_pairs = []
        for idx, (chunk_obj, score) in enumerate(zip(chunks, scores)):
            # Guard against rank_bm25 zero-IDF behavior on small corpora (N <= 2)
            term_overlap = len(set(tokenized_query) & set(corpus[idx]))
            if score > 0.0 or term_overlap > 0:
                effective_score = float(score) if score > 0.0 else float(term_overlap) * 0.1
                scored_pairs.append((chunk_obj, effective_score))

        # Sort descending by BM25 score
        scored_pairs.sort(key=lambda pair: pair[1], reverse=True)
        top_pairs = scored_pairs[:self.bm25_top_k]

        candidates: List[RetrievedChunk] = []
        for chunk_obj, score in top_pairs:
            chunk_type_val = (
                chunk_obj.chunk_type.value
                if hasattr(chunk_obj.chunk_type, "value")
                else (str(chunk_obj.chunk_type) if chunk_obj.chunk_type else "dialogue")
            )
            retrieved = RetrievedChunk(
                chunk_id=str(chunk_obj.id),
                meeting_id=str(meeting_id),
                chunk_index=chunk_obj.chunk_index,
                content=chunk_obj.content,
                speaker_name=chunk_obj.speaker_name or "Unknown Speaker",
                speaker_role=chunk_obj.speaker_role or None,
                timestamp=chunk_obj.timestamp or None,
                chunk_type=chunk_type_val,
                involves_user=bool(chunk_obj.involves_user),
                semantic_score=None,
                bm25_score=score,
                rerank_score=None,
                retrieval_sources=["bm25"],
            )
            candidates.append(retrieved)

        logger.info(f"Retrieved {len(candidates)} BM25 candidates for meeting {meeting_id}")
        return candidates

    # ── Merge and Deduplication ──────────────────────────────────────────────

    def merge_and_deduplicate(
        self,
        semantic_candidates: List[RetrievedChunk],
        bm25_candidates: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Merge candidate sets from semantic and BM25 retrieval into a unified candidate pool.

        Deduplicates based on chunk identity (chunk_id or meeting_id_chunk_index).
        Preserves both semantic_score and bm25_score when a chunk appears in both.
        Records retrieval_sources accurately (['semantic'], ['bm25'], or ['semantic', 'bm25']).
        """
        merged_dict: Dict[str, RetrievedChunk] = {}

        # Helper to get deduplication key
        def get_key(c: RetrievedChunk) -> str:
            if c.chunk_id and str(c.chunk_id).strip():
                return str(c.chunk_id).strip()
            return f"{c.meeting_id}_{c.chunk_index}"

        # 1. Ingest semantic candidates
        for c in semantic_candidates:
            key = get_key(c)
            merged_dict[key] = c

        # 2. Ingest / merge BM25 candidates
        for c in bm25_candidates:
            key = get_key(c)
            if key in merged_dict:
                existing = merged_dict[key]
                existing.bm25_score = c.bm25_score
                if "bm25" not in existing.retrieval_sources:
                    existing.retrieval_sources.append("bm25")
            else:
                merged_dict[key] = c

        candidates = list(merged_dict.values())
        logger.info(
            f"Merged {len(semantic_candidates)} semantic + {len(bm25_candidates)} BM25 candidates "
            f"into {len(candidates)} deduplicated candidates."
        )
        return candidates

    # ── End-to-End Retrieval ─────────────────────────────────────────────────

    def retrieve(
        self,
        meeting_id: Union[str, uuid.UUID],
        query: str,
        db_session: Optional[Any] = None,
    ) -> List[RetrievedChunk]:
        """
        End-to-end meeting-scoped hybrid retrieval:
        1. Validate meeting_id and query
        2. Semantic retrieval (Top 10)
        3. BM25 retrieval (Top 10)
        4. Merge + deduplication
        5. Local BGE CrossEncoder reranking
        6. Return Top 5 candidates as normalized RetrievedChunk objects
        """
        if not meeting_id or not str(meeting_id).strip():
            raise ValueError("meeting_id is required for retrieval")
        if not query or not query.strip():
            logger.info("Empty query provided; returning empty retrieval result.")
            return []

        clean_query = query.strip()

        # Step 1: Semantic retrieval (Top 10)
        semantic_candidates = self.retrieve_semantic(meeting_id, clean_query)

        # Step 2: BM25 retrieval (Top 10)
        bm25_candidates = self.retrieve_bm25(meeting_id, clean_query, db_session=db_session)

        # Step 3: Merge and deduplicate (bounded candidate set <= 20)
        candidates = self.merge_and_deduplicate(semantic_candidates, bm25_candidates)

        if not candidates:
            logger.info(f"No candidates retrieved for meeting {meeting_id}; returning empty.")
            return []

        # Step 4: BGE Reranking (or graceful deterministic fallback)
        reranked = self.reranker.rerank(clean_query, candidates, top_k=self.final_top_k)

        logger.info(
            f"Completed hybrid retrieval for meeting {meeting_id}: "
            f"returning {len(reranked)} final chunks (top_k={self.final_top_k})."
        )
        return reranked


# ── Global Function ──────────────────────────────────────────────────────────

def retrieve(
    meeting_id: Union[str, uuid.UUID],
    query: str,
    db_session: Optional[Any] = None,
) -> List[RetrievedChunk]:
    """Convenience functional wrapper for meeting-scoped hybrid retrieval."""
    retriever = HybridRetriever()
    return retriever.retrieve(meeting_id=meeting_id, query=query, db_session=db_session)
