"""
MeetMind AI RAG Engine.

Exposes the complete frozen Gate 3 RAG pipeline interfaces:
- Batch 1: TranscriptChunker, Chunk
- Batch 2: GeminiEmbedder, PineconeVectorStore, TranscriptEmbedder, VectorRecord,
           get_meeting_namespace, get_vector_id
- Batch 3: HybridRetriever, RetrievedChunk, retrieve, tokenize_bm25,
           BGEReranker, get_reranker
"""

from app.rag.chunker import Chunk, TranscriptChunker
from app.rag.embedder import (
    GeminiEmbedder,
    PineconeVectorStore,
    TranscriptEmbedder,
    VectorRecord,
    get_meeting_namespace,
    get_vector_id,
)
from app.rag.reranker import BGEReranker, get_reranker
from app.rag.retriever import (
    HybridRetriever,
    RetrievedChunk,
    retrieve,
    tokenize_bm25,
)

__all__ = [
    # Batch 1 Chunker
    "Chunk",
    "TranscriptChunker",
    # Batch 2 Embedder & Vector Store
    "GeminiEmbedder",
    "PineconeVectorStore",
    "TranscriptEmbedder",
    "VectorRecord",
    "get_meeting_namespace",
    "get_vector_id",
    # Batch 3 Hybrid Retrieval & Reranker
    "HybridRetriever",
    "RetrievedChunk",
    "retrieve",
    "tokenize_bm25",
    "BGEReranker",
    "get_reranker",
]
