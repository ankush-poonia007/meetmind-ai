"""
Models package initialiser.

Importing all models here ensures they are registered with Base.metadata
when this package is imported.  Alembic's env.py imports this module so
that autogenerate can discover all seven tables.
"""

from app.db.models.chat_message import ChatMessage, ChatRole
from app.db.models.highlight import Highlight
from app.db.models.meeting import Meeting
from app.db.models.meeting_participant import MeetingParticipant
from app.db.models.task import Task, TaskPriority, TaskStatus
from app.db.models.transcript_chunk import TranscriptChunk, TranscriptChunkType
from app.db.models.user import User

__all__ = [
    "User",
    "Meeting",
    "MeetingParticipant",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "Highlight",
    "ChatMessage",
    "ChatRole",
    "TranscriptChunk",
    "TranscriptChunkType",
]
