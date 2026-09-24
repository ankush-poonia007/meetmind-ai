"""
Pydantic contracts for Meeting domain.

Defines schemas for meeting submission, list views, detail responses,
and participant representation aligned with the locked Gate 1 database schema.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import InputFormat


# ── Participant Schemas ──────────────────────────────────────────────────────

class ParticipantBase(BaseModel):
    """Base participant schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Participant name")
    role: Optional[str] = Field(None, max_length=255, description="Role in meeting or organization")
    is_current_user: bool = Field(False, description="Flag indicating if this participant is the submitting user")


class ParticipantInfo(ParticipantBase):
    """Participant detail schema including persistent identifiers."""
    id: Optional[UUID] = Field(None, description="Participant identifier")
    meeting_id: Optional[UUID] = Field(None, description="Parent meeting identifier")

    model_config = ConfigDict(from_attributes=True)


# ── Meeting Schemas ──────────────────────────────────────────────────────────

class MeetingBase(BaseModel):
    """Shared meeting metadata."""
    title: Optional[str] = Field(None, max_length=500, description="Meeting title (may be extracted by Ingestion Agent)")
    organization: Optional[str] = Field(None, max_length=255, description="Organization or team name")
    meeting_date: date = Field(..., description="Date of the meeting")
    meeting_time: Optional[str] = Field(None, max_length=10, description="Time of the meeting (e.g. '14:00')")
    input_format: InputFormat = Field(InputFormat.TEXT, description="Transcript format: pdf, txt, or text")


class MeetingCreate(MeetingBase):
    """Payload for submitting a new meeting (POST /api/v1/meetings/)."""
    user_id: UUID = Field(..., description="Owner user identifier")
    raw_transcript: str = Field(..., min_length=1, description="Full raw transcript text or parsed content")


class MeetingResponse(MeetingBase):
    """Standard API response for a meeting entity."""
    id: UUID = Field(..., description="Unique meeting identifier")
    user_id: UUID = Field(..., description="Owner user identifier")
    title: str = Field(..., description="Meeting title")
    raw_transcript: str = Field(..., description="Original meeting transcript")
    pinecone_namespace: Optional[str] = Field(None, description="Pinecone vector namespace")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class MeetingListItem(BaseModel):
    """Lightweight summary for meeting lists (GET /api/v1/meetings/{user_id})."""
    id: UUID
    user_id: UUID
    title: str
    organization: Optional[str] = None
    meeting_date: date
    meeting_time: Optional[str] = None
    input_format: InputFormat
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingDetail(MeetingResponse):
    """Detailed view including detected participants (GET /api/v1/meetings/{meeting_id}/detail)."""
    participants: list[ParticipantInfo] = Field(default_factory=list, description="Meeting participants")

    model_config = ConfigDict(from_attributes=True)


# Convenience aliases
MeetingRead = MeetingResponse
ParticipantResponse = ParticipantInfo
