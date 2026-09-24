"""
Notifications API router for MeetMind AI.

Exposes endpoints to manually trigger deadline notifications and inspect pending alerts
due within the next 24 hours. Does NOT register APScheduler jobs (deferred to Batch 3).
Delegates entirely to NotificationService.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.constants import NotificationTrigger
from app.db.session import get_db
from app.schemas.notification import (
    NotificationStatusResponse,
    NotificationTriggerRequest,
    PendingAlertResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post(
    "/trigger",
    response_model=NotificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger deadline notifications",
    description="Manually triggers the deadline notification run across qualifying pending tasks.",
)
def trigger_notifications(
    trigger_req: Optional[NotificationTriggerRequest] = None,
    db: Session = Depends(get_db),
) -> NotificationStatusResponse:
    """Triggers deadline notification run."""
    trigger = trigger_req.trigger if trigger_req else NotificationTrigger.MANUAL
    return NotificationService.process_deadline_notifications(db=db, trigger=trigger)


@router.get(
    "/{user_id}/pending",
    response_model=list[PendingAlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Get pending notifications",
    description="Retrieves pending tasks due within the next 24 hours where alert_sent is false.",
)
def get_pending_notifications(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> list[PendingAlertResponse]:
    """Retrieves pending alerts due within 24h for a user."""
    return NotificationService.get_pending_alerts_for_user(db=db, user_id=user_id)
