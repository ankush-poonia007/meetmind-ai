"""
Pydantic contracts for Highlight domain.

Defines schemas for meeting highlights (decisions, announcements, important context)
aligned with the locked Gate 1 database schema.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HighlightBase(BaseModel):
    """Base highlight attributes."""
    content: str = Field(..., min_length=1, description="Highlight content text")


class HighlightCreate(HighlightBase):
    """Payload for saving an individual highlight."""
    meeting_id: UUID = Field(..., description="Parent meeting identifier")
    user_id: UUID = Field(..., description="Target user identifier")


class HighlightResponse(HighlightBase):
    """API response model for a meeting highlight."""
    id: UUID = Field(..., description="Unique highlight identifier")
    meeting_id: UUID = Field(..., description="Parent meeting identifier")
    user_id: UUID = Field(..., description="Target user identifier")
    created_at: datetime = Field(..., description="Highlight creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class HighlightListResponse(BaseModel):
    """List response for meeting or user highlights."""
    meeting_id: Optional[UUID] = None
    user_id: UUID
    highlights: list[HighlightResponse] = Field(default_factory=list, description="Extracted highlights")


# Convenience alias
HighlightRead = HighlightResponse
