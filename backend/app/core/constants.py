"""
Core application constants and enums for MeetMind AI.

Contains domain, routing, session, and provider contract enums.
No provider runtime logic or external API clients are implemented here.
"""

from enum import Enum


# ── Session & Routing Enums ──────────────────────────────────────────────────

class SessionAction(str, Enum):
    """
    Session action routing targets for LangGraph supervisor.
    """
    INGEST = "ingest"
    IDENTIFY = "identify"
    EXTRACT = "extract"
    CONFIRM = "confirm"
    QA = "qa"
    NOTIFY = "notify"
    COMPLETE = "complete"


class AgentName(str, Enum):
    """
    Identifies the specialized agents in the MeetMind system.
    """
    SUPERVISOR = "supervisor"
    INGESTION = "ingestion"
    IDENTITY = "identity"
    EXTRACTION = "extraction"
    CONFIRMATION = "confirmation"
    QA = "qa"
    NOTIFICATION = "notification"


# ── Transcript & Ingestion Enums ─────────────────────────────────────────────

class InputFormat(str, Enum):
    """
    Accepted input transcript formats.
    """
    PDF = "pdf"
    TXT = "txt"
    TEXT = "text"


class TranscriptChunkType(str, Enum):
    """
    Semantic classification of transcript chunks for retrieval.
    """
    DIALOGUE = "dialogue"
    DECISION = "decision"
    TASK_MENTION = "task_mention"


# ── Human-in-the-Loop & Domain Enums ─────────────────────────────────────────

class UserConfirmation(str, Enum):
    """
    User response states during task confirmation step.
    """
    YES = "yes"
    NO = "no"
    PARTIAL = "partial"


class ConfidenceLevel(str, Enum):
    """
    Extraction and Q&A confidence scoring.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskPriority(str, Enum):
    """
    Task priority classifications aligned with database schema.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """
    Lifecycle status of a confirmed user task.
    """
    PENDING = "pending"
    COMPLETE = "complete"


class ChatRole(str, Enum):
    """
    Meeting-scoped Q&A chat message sender roles.
    """
    USER = "user"
    ASSISTANT = "assistant"


class NotificationTrigger(str, Enum):
    """
    Invocation source for the notification pipeline.
    """
    SCHEDULED = "scheduled"
    MANUAL = "manual"


# ── Provider Contract Enums (Batch 2 Foundation) ─────────────────────────────

class ProviderName(str, Enum):
    """
    Supported LLM and search providers.
    """
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    TAVILY = "tavily"


class KeyHealth(str, Enum):
    """
    Health state of an individual provider key.
    Follows approved 3-state rotation design (no EXHAUSTED state).
    """
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    DISABLED = "disabled"


class FailureClass(str, Enum):
    """
    Normalized failure categories for provider request classification.
    """
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    CONNECTION_FAILED = "connection_failed"
    UNKNOWN = "unknown"
