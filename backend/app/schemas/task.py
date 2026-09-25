"""
Pydantic contracts for Task domain.

Defines schemas for task creation, status updates, filtering,
and response serialization aligned with the locked Gate 1 database schema.
"""

from datetime import date, datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import TaskPriority, TaskStatus
from app.core.utils import normalize_deadline


# ── Base Schemas ─────────────────────────────────────────────────────────────

class TaskBase(BaseModel):
    """Shared attributes for task contracts."""
    title: str = Field(..., min_length=1, max_length=500, description="Task summary or action item")
    description: Optional[str] = Field(None, description="Detailed AI-generated explanation of the task")
    priority: Optional[TaskPriority] = Field(None, description="Priority classification: high, medium, or low")
    deadline: Optional[Union[datetime, date]] = Field(None, description="Target completion date or timestamp")

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline_field(cls, v: Any) -> Any:
        return normalize_deadline(v)


# ── Request Payloads ─────────────────────────────────────────────────────────

class TaskCreate(TaskBase):
    """Payload for creating a task in database."""
    meeting_id: UUID = Field(..., description="Parent meeting identifier")
    user_id: UUID = Field(..., description="Assigned user identifier")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Initial task status")


class TaskUpdate(BaseModel):
    """Payload for modifying an existing task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    deadline: Optional[Union[datetime, date]] = None
    status: Optional[TaskStatus] = None

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline_field(cls, v: Any) -> Any:
        return normalize_deadline(v)


class TaskStatusUpdate(BaseModel):
    """Payload for toggling task status (PUT /api/v1/tasks/{task_id}/status)."""
    status: TaskStatus = Field(..., description="Updated task status: pending or complete")


class TaskFilterParams(BaseModel):
    """Query parameter schema for task filtering (GET /api/v1/tasks/{user_id}/filter)."""
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    deadline_before: Optional[Union[date, datetime]] = None
    deadline_after: Optional[Union[date, datetime]] = None

    @field_validator("deadline_before", "deadline_after", mode="before")
    @classmethod
    def parse_filter_date_boundary(cls, v: Any) -> Any:
        if isinstance(v, str):
            val_str = v.strip()
            if not val_str:
                return None
            if "T" not in val_str and " " not in val_str:
                try:
                    return date.fromisoformat(val_str)
                except ValueError:
                    pass
        return v


# ── Response Models ──────────────────────────────────────────────────────────

class TaskResponse(TaskBase):
    """Standard API response representation of a task."""
    id: UUID = Field(..., description="Unique task identifier")
    meeting_id: UUID = Field(..., description="Parent meeting identifier")
    user_id: UUID = Field(..., description="Assigned user identifier")
    status: TaskStatus = Field(..., description="Task status")
    alert_sent: bool = Field(False, description="Deadline notification delivery flag")
    created_at: datetime = Field(..., description="Task creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# Convenience alias
TaskRead = TaskResponse
