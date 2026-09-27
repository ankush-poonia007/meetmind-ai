"""
Pydantic contracts for Extraction and Confirmation workflows.

Defines schemas for extracted tasks, highlights, pipeline invocation,
preview inspection, and user confirmation decisions.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.constants import TaskPriority, UserConfirmation


# ── Extracted Artifact Schemas ───────────────────────────────────────────────

class ExtractedTask(BaseModel):
    """An unconfirmed action item extracted by the Extraction Agent."""
    id: Optional[str] = Field(None, description="Task identifier or index")
    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: Optional[str] = Field(None, description="AI-generated description")
    priority: Optional[TaskPriority] = Field(TaskPriority.MEDIUM, description="Inferred task priority")
    deadline: Optional[date] = Field(None, description="Extracted completion deadline")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence score")


class ExtractedHighlight(BaseModel):
    """A meeting highlight or announcement extracted by the Extraction Agent."""
    content: str = Field(..., min_length=1, description="Highlight text")
    relevance_reason: Optional[str] = Field(None, description="Why this highlight is relevant to user")


# ── Confirmation Edit Schemas ────────────────────────────────────────────────

class ModifiedTaskConfirm(BaseModel):
    """Edited task details submitted during confirmation."""
    id: Optional[str] = Field(None, description="Task identifier or original index")
    title: Optional[str] = Field(None, max_length=500, description="Task title")
    description: Optional[str] = Field(None, description="User-edited task description")
    deadline: Optional[date] = Field(None, description="User-edited deadline")
    priority: Optional[TaskPriority] = Field(None, description="Task priority")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")


# ── API Interaction Schemas ──────────────────────────────────────────────────

class ExtractionRunRequest(BaseModel):
    """Payload to trigger the extraction pipeline (POST /api/v1/extraction/{meeting_id}/run)."""
    meeting_id: UUID = Field(..., description="Target meeting identifier")
    user_id: UUID = Field(..., description="Target user identifier")
    person_name: Optional[str] = Field(
        None,
        description="Explicit participant name to extract tasks for",
    )

    @field_validator("person_name")
    @classmethod
    def validate_person_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("person_name cannot be empty or whitespace")
            return v.strip()
        return v


class ExtractionPreviewResponse(BaseModel):
    """Preview of extracted items awaiting user confirmation (GET /api/v1/extraction/{meeting_id}/preview)."""
    meeting_id: UUID = Field(..., description="Meeting identifier")
    tasks: list[ExtractedTask] = Field(default_factory=list, description="Extracted tasks awaiting confirmation")
    highlights: list[ExtractedHighlight] = Field(default_factory=list, description="Extracted highlights")
    task_count: int = Field(0, description="Number of extracted tasks")
    highlight_count: int = Field(0, description="Number of extracted highlights")
    extraction_complete: bool = Field(False, description="Whether extraction agent has completed")


class ExtractionConfirmRequest(BaseModel):
    """Payload for user confirmation response (POST /api/v1/extraction/{meeting_id}/confirm)."""
    meeting_id: UUID = Field(..., description="Target meeting identifier")
    user_id: UUID = Field(..., description="Target user identifier")
    user_confirmation: UserConfirmation = Field(..., description="Confirmation decision: yes, no, or partial")
    confirmed_task_ids: list[str] = Field(
        default_factory=list,
        description="List of selected task identifiers or indices if user_confirmation is partial",
    )
    modified_tasks: Optional[list[ModifiedTaskConfirm]] = Field(
        default_factory=list,
        description="List of user-edited task objects with updated descriptions, deadlines, etc.",
    )

    @field_validator("confirmed_task_ids")
    @classmethod
    def validate_no_duplicate_task_ids(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate task IDs submitted in confirmation request")
        return v


class ExtractionResult(BaseModel):
    """Outcome of task and highlight persistence after confirmation."""
    meeting_id: UUID = Field(..., description="Target meeting identifier")
    saved_tasks: int = Field(0, description="Number of tasks saved to database")
    discarded_tasks: int = Field(0, description="Number of tasks discarded")
    saved_highlights: int = Field(0, description="Number of highlights saved to database")
    confirmation_complete: bool = Field(False, description="Whether confirmation step has concluded")
    dashboard_ready: bool = Field(False, description="Whether dashboard is ready to display persisted items")
