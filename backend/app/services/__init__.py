"""
MeetMind AI application service layer.

Provides clean business logic interfaces between FastAPI routers and:
- PostgreSQL persistence (Gate 1 synchronous Session)
- Provider infrastructure (Gate 2)
- Hybrid RAG pipeline (Gate 3)
- LangGraph multi-agent orchestration
"""

from app.services.chat_service import ChatService
from app.services.extraction_service import ExtractionService
from app.services.highlight_service import HighlightService
from app.services.meeting_service import MeetingService
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService
from app.services.user_service import UserService

__all__ = [
    "UserService",
    "MeetingService",
    "TaskService",
    "ChatService",
    "ExtractionService",
    "HighlightService",
    "NotificationService",
]
