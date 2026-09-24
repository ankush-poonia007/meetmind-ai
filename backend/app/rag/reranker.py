"""
Local BGE CrossEncoder Reranker for MeetMind AI RAG Pipeline (Gate 3 - Batch 3).

Reranks candidate transcript chunks using BAAI/bge-reranker-v2-m3.
Enforces:
- Lazy loading: Model is NOT loaded on module import or application startup.
- Thread-safe caching: Initialized on first request and reused across subsequent calls.
- Graceful fallback: If CrossEncoder cannot load (e.g. PyTorch DLL restrictions under
  Windows WDAC or out-of-memory), falls back to deterministic candidate ordering
  leaving rerank_score as None without crashing the pipeline.
- Top-5 truncation: Returns at most 5 reranked candidates.
"""

from __future__ import annotations

import threading
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.core.config import RERANKER_MODEL, RERANKER_TOP_K
from app.core.logging import get_logger

logger = get_logger("rag.reranker")


class BGEReranker:
    """
    Lazy-loaded, thread-safe CrossEncoder reranker.

    Reranks candidates based on deep query-document cross-attention using
    BAAI/bge-reranker-v2-m3.
    """

    def __init__(
        self,
        model_name: str = RERANKER_MODEL,
        top_k: int = RERANKER_TOP_K,
    ) -> None:
        self.model_name = model_name
        self.top_k = top_k
        self._model: Optional[Any] = None
        self._model_lock = threading.Lock()
        self._load_failed = False
        self._load_error_message: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        """Returns True if the underlying model has already been loaded into memory."""
        return self._model is not None

    def _get_model(self) -> Optional[Any]:
        """
        Lazily initialize the CrossEncoder model in a thread-safe manner.
        Returns the cached model instance or None if loading failed.
        """
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model
            if self._load_failed:
                return None

            try:
                logger.info(f"Lazily loading CrossEncoder reranker model '{self.model_name}'...")
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                logger.info(f"Successfully loaded CrossEncoder reranker '{self.model_name}'.")
                return self._model
            except Exception as exc:
                self._load_failed = True
                self._load_error_message = str(exc)
                logger.warning(
                    f"CrossEncoder model '{self.model_name}' failed to load (operating in graceful fallback mode): {exc}"
                )
                return None

    def rerank(
        self,
        query: str,
        candidates: List[Any],
        top_k: Optional[int] = None,
    ) -> List[Any]:
        """
        Rerank a list of candidate chunks with respect to the user query.

        Normal path:
        - Pairs: (query, candidate.content)
        - Computes cross-encoder logits
        - Assigns rerank_score to each candidate
        - Sorts descending and returns Top-K (default 5)

        Fallback path (when model is unavailable or inference fails):
        - Retains candidate rerank_score as None (never invents a fake score)
        - Applies deterministic sorting (dual-source agreement, scores, chunk index)
        - Returns Top-K (default 5)
        """
        limit = top_k or self.top_k
        if not candidates:
            return []
        if len(candidates) <= 1:
            return candidates[:limit]

        model = self._get_model()

        if model is not None:
            try:
                # Build (query, content) pairs for CrossEncoder scoring
                pairs = [(query, getattr(c, "content", "")) for c in candidates]
                scores = model.predict(pairs)

                # Assign rerank_score
                for idx, candidate in enumerate(candidates):
                    score_val = float(scores[idx])
                    candidate.rerank_score = score_val

                # Sort descending by rerank_score
                sorted_candidates = sorted(
                    candidates,
                    key=lambda c: (
                        c.rerank_score if c.rerank_score is not None else float("-inf")
                    ),
                    reverse=True,
                )
                return sorted_candidates[:limit]
            except Exception as exc:
                logger.warning(
                    f"Reranking inference failed; falling back to deterministic candidate ordering: {exc}"
                )
                # Fall through to fallback ordering

        # Fallback path: model loading or inference failed
        return self._deterministic_fallback_sort(candidates, limit)

    def _deterministic_fallback_sort(
        self,
        candidates: List[Any],
        limit: int,
    ) -> List[Any]:
        """
        Deterministic fallback ordering when BGE reranker is unavailable.

        Priority order:
        1. Candidates agreed upon by both sources (retrieval_sources length: 2 vs 1)
        2. Semantic score (if present, descending)
        3. BM25 score (if present, descending)
        4. Chronological chunk index (ascending)

        Guarantees rerank_score remains None (never fabricates a score).
        """
        for c in candidates:
            c.rerank_score = None

        def fallback_sort_key(c: Any) -> tuple:
            sources_len = len(getattr(c, "retrieval_sources", []))
            sem_score = getattr(c, "semantic_score", None)
            bm25_score = getattr(c, "bm25_score", None)
            idx = getattr(c, "chunk_index", 0)

            return (
                -sources_len,
                -(sem_score if sem_score is not None else -999.0),
                -(bm25_score if bm25_score is not None else -999.0),
                idx,
            )

        sorted_candidates = sorted(candidates, key=fallback_sort_key)
        return sorted_candidates[:limit]


# ── Global Singleton Pattern ─────────────────────────────────────────────────

_GLOBAL_RERANKER: Optional[BGEReranker] = None
_RERANKER_LOCK = threading.Lock()


def get_reranker(
    model_name: str = RERANKER_MODEL,
    top_k: int = RERANKER_TOP_K,
) -> BGEReranker:
    """Returns or initializes the thread-safe BGEReranker singleton."""
    global _GLOBAL_RERANKER
    if _GLOBAL_RERANKER is None:
        with _RERANKER_LOCK:
            if _GLOBAL_RERANKER is None:
                _GLOBAL_RERANKER = BGEReranker(model_name=model_name, top_k=top_k)
    return _GLOBAL_RERANKER
