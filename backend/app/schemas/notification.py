"""
Pydantic contracts for Notification domain.

Defines schemas for manual notification triggers, pending alert queries,
and notification execution summaries.
"""

from datetime import date, datetime
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.constants import NotificationTrigger


class NotificationTriggerRequest(BaseModel):
    """Payload for manually triggering deadline alerts (POST /api/v1/notifications/trigger)."""
    trigger: NotificationTrigger = Field(
        NotificationTrigger.MANUAL,
        description="Trigger source: scheduled or manual",
    )


class PendingAlertResponse(BaseModel):
    """Information regarding a pending task nearing its deadline (GET /api/v1/notifications/{user_id}/pending)."""
    task_id: UUID = Field(..., description="Unique task identifier")
    meeting_id: UUID = Field(..., description="Associated meeting identifier")
    user_id: UUID = Field(..., description="Assigned user identifier")
    title: str = Field(..., description="Task title")
    deadline: Optional[Union[datetime, date]] = Field(None, description="Task deadline")
    days_until_due: Optional[int] = Field(None, description="Days remaining until deadline")


class NotificationStatusResponse(BaseModel):
    """Summary result returned after executing a notification check."""
    tasks_checked: int = Field(0, description="Total qualifying tasks inspected")
    alerts_sent: int = Field(0, description="Total email alerts successfully sent")
    failed_alerts: list[str] = Field(default_factory=list, description="Identifiers of tasks that failed notification")
    completion_time: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of execution completion")


# Convenience alias
NotificationResult = NotificationStatusResponse
