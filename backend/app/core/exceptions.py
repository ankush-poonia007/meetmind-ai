"""
Domain and application exception hierarchy for MeetMind AI.

Organized cleanly by domain and lifecycle stage.
Avoids exposing environment secrets or provider keys in error messages.
"""

from typing import Any, Optional


# ── Base Application Error ───────────────────────────────────────────────────

class MeetMindError(Exception):
    """
    Base exception for all MeetMind AI domain and infrastructure errors.
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ── Entity & Resource Errors ─────────────────────────────────────────────────

class EntityNotFoundError(MeetMindError):
    """Base error when a requested domain entity does not exist."""


class UserNotFoundError(EntityNotFoundError):
    """Raised when a specified user ID or email is not found."""


class MeetingNotFoundError(EntityNotFoundError):
    """Raised when a specified meeting ID is not found."""


class TaskNotFoundError(EntityNotFoundError):
    """Raised when a specified task ID is not found."""


class HighlightNotFoundError(EntityNotFoundError):
    """Raised when a specified highlight ID is not found."""


class DuplicateUserError(MeetMindError):
    """Raised when registering a user with an email that is already registered."""


class InvalidOwnershipError(MeetMindError):
    """Raised when a user attempts to access a resource belonging to another user or meeting."""


class InvalidStateError(MeetMindError):
    """Raised when an operation is invalid for the current resource or pipeline state."""


# ── Pipeline & Agent Errors ──────────────────────────────────────────────────

class PipelineError(MeetMindError):
    """Base error for failures during multi-agent LangGraph execution."""


class IngestionError(PipelineError):
    """Raised when transcript ingestion, parsing, or chunking fails."""


class IdentityError(PipelineError):
    """Raised when user identification inside the transcript fails."""


class ExtractionError(PipelineError):
    """Raised when task or highlight extraction fails."""


class ConfirmationError(PipelineError):
    """Raised when human-in-the-loop task confirmation encounters an error."""


class QAError(MeetMindError):
    """Raised when meeting-scoped Q&A retrieval or answer generation fails."""


class NotificationError(MeetMindError):
    """Raised during the deadline notification process."""


# ── External Service Integration Errors ──────────────────────────────────────

class EmbeddingError(MeetMindError):
    """Raised when vector embedding generation fails."""


class PineconeError(MeetMindError):
    """Raised when Pinecone index operations or upserts fail."""


class EmailDeliveryError(MeetMindError):
    """Raised when sending an alert email via Resend fails."""


# ── Provider Contract Exceptions (Batch 2 Foundation) ────────────────────────

class ProviderError(MeetMindError):
    """Base exception for AI/search provider errors."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a requested provider has no configured keys."""


class ProviderExhaustedError(ProviderError):
    """Raised when all keys for a provider are permanently disabled."""


class AllKeysCooldownError(ProviderError):
    """Raised when all active keys for a provider are currently in cooldown."""


class ProviderKeyFailoverExhaustedError(ProviderError):
    """Raised when bounded key failover attempts have all been exhausted."""


class ProviderAuthError(ProviderError):
    """Raised when a provider rejects an API key (HTTP 401/403)."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider returns a rate limit response (HTTP 429)."""
