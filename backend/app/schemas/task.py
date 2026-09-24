"""
Pydantic contracts for Task domain.

Defines schemas for task creation, status updates, filtering,
and response serialization aligned with the locked Gate 1 database schema.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import TaskPriority, TaskStatus


# ── Base Schemas ─────────────────────────────────────────────────────────────

class TaskBase(BaseModel):
    """Shared attributes for task contracts."""
    title: str = Field(..., min_length=1, max_length=500, description="Task summary or action item")
    description: Optional[str] = Field(None, description="Detailed AI-generated explanation of the task")
    priority: Optional[TaskPriority] = Field(None, description="Priority classification: high, medium, or low")
    deadline: Optional[date] = Field(None, description="Target completion date")


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
    deadline: Optional[date] = None
    status: Optional[TaskStatus] = None


class TaskStatusUpdate(BaseModel):
    """Payload for toggling task status (PUT /api/v1/tasks/{task_id}/status)."""
    status: TaskStatus = Field(..., description="Updated task status: pending or complete")


class TaskFilterParams(BaseModel):
    """Query parameter schema for task filtering (GET /api/v1/tasks/{user_id}/filter)."""
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    deadline_before: Optional[date] = None
    deadline_after: Optional[date] = None


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
