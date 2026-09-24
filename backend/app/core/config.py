"""
Static application configuration parameters for MeetMind AI.

Contains model identifiers, RAG retrieval limits, chunking parameters,
and static retry/rotation thresholds.
Non-secret values only.
"""

# ── Model Identifiers ────────────────────────────────────────────────────────
# Supervisor and Q&A Agent orchestrators
SUPERVISOR_MODEL = "gemini-3.6-flash"

# Sub-agents (Ingestion, Identity, Extraction, Confirmation, Notification)
SUB_AGENT_MODEL = "gemini-3.5-flash-lite"

# Embedding model for vector representation
EMBEDDING_MODEL = "models/gemini-embedding-001"

# Local cross-encoder reranker
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# OpenRouter fallback for exhausted Gemini quota
FALLBACK_MODEL = "thinkingmachines/inkling:free"

# OpenRouter backup orchestrator
BACKUP_MODEL = "openai/gpt-oss-120b"


# ── Transcript Chunking & Vector Parameters ──────────────────────────────────
# Speaker-aware chunking boundaries
CHUNK_SIZE_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 50
CHUNK_SIZE_MIN_TOKENS = 200

# Pinecone vector configuration
PINECONE_DIMENSIONS = 3072
PINECONE_NAMESPACE_PREFIX = "meeting_"


# ── Retrieval Limits ─────────────────────────────────────────────────────────
# Number of candidates fetched from semantic vector search
PINECONE_TOP_K = 10

# Number of candidates fetched from PostgreSQL BM25 keyword search
BM25_TOP_K = 10

# Top reranked candidates fed to the synthesis prompt
RERANKER_TOP_K = 5


# ── Operation Retry Limits ───────────────────────────────────────────────────
# Number of retries for external service calls
EMBEDDING_RETRY_COUNT = 3
PINECONE_RETRY_COUNT = 2
DB_WRITE_RETRY_COUNT = 2
RESEND_RETRY_COUNT = 1


# ── Conversational & Notification Context ────────────────────────────────────
# Number of previous chat messages loaded for conversational memory
CHAT_HISTORY_LIMIT = 5

# Number of top transcript chunks retrieved for notification email context
NOTIFICATION_CONTEXT_CHUNKS = 3


# ── Provider Key Rotation Tuning (Static Defaults for Batch 2) ───────────────
# Default cooldown durations in seconds
COOLDOWN_RATE_LIMIT_INITIAL_SECONDS = 60
COOLDOWN_RATE_LIMIT_ESCALATED_SECONDS = 300
COOLDOWN_TRANSIENT_ERROR_SECONDS = 30

# Maximum consecutive transient errors before a key is placed in cooldown
MAX_CONSECUTIVE_FAILURES_BEFORE_COOLDOWN = 3

# Maximum key failover attempts within a single request
MAX_KEY_FAILOVER_ATTEMPTS = 3
