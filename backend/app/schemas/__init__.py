"""
MeetMind AI schema contracts.

Clean re-exports of Pydantic models for API and application boundaries.
"""

from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageCreate,
    ChatMessageRead,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSource,
)
from app.schemas.extraction import (
    ExtractedHighlight,
    ExtractedTask,
    ExtractionConfirmRequest,
    ExtractionPreviewResponse,
    ExtractionResult,
    ExtractionRunRequest,
)
from app.schemas.highlight import (
    HighlightBase,
    HighlightCreate,
    HighlightListResponse,
    HighlightRead,
    HighlightResponse,
)
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingRead,
    MeetingResponse,
    ParticipantBase,
    ParticipantInfo,
    ParticipantResponse,
)
from app.schemas.notification import (
    NotificationResult,
    NotificationStatusResponse,
    NotificationTriggerRequest,
    PendingAlertResponse,
)
from app.schemas.task import (
    TaskBase,
    TaskCreate,
    TaskFilterParams,
    TaskRead,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.schemas.user import (
    UserCreate,
    UserRead,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserRead",
    # Meeting
    "ParticipantBase",
    "ParticipantInfo",
    "ParticipantResponse",
    "MeetingCreate",
    "MeetingResponse",
    "MeetingRead",
    "MeetingListItem",
    "MeetingDetail",
    # Task
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskStatusUpdate",
    "TaskFilterParams",
    "TaskResponse",
    "TaskRead",
    # Chat
    "ChatSource",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ChatMessageRead",
    "ChatRequest",
    "ChatResponse",
    "ChatHistoryResponse",
    # Highlight
    "HighlightBase",
    "HighlightCreate",
    "HighlightResponse",
    "HighlightRead",
    "HighlightListResponse",
    # Extraction
    "ExtractedTask",
    "ExtractedHighlight",
    "ExtractionRunRequest",
    "ExtractionPreviewResponse",
    "ExtractionConfirmRequest",
    "ExtractionResult",
    # Notification
    "NotificationTriggerRequest",
    "PendingAlertResponse",
    "NotificationStatusResponse",
    "NotificationResult",
]
