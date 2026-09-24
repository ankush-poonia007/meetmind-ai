"""
Meetings API router for MeetMind AI.

Exposes endpoints for creating meetings, listing user meetings, retrieving meeting
detail with detected participants, and deleting meetings with database cascade.
Delegates entirely to MeetingService.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingResponse,
)
from app.services.meeting_service import MeetingService

router = APIRouter()


@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting",
    description="Submits form-first meeting metadata and transcript. Generates placeholder title if not provided.",
)
def create_meeting(
    meeting_in: MeetingCreate,
    submitter_name: Optional[str] = Query(None, description="Submitter participant display name"),
    submitter_role: Optional[str] = Query(None, description="Submitter participant meeting role"),
    db: Session = Depends(get_db),
) -> MeetingResponse:
    """Creates a new meeting record with deterministic placeholder title."""
    return MeetingService.create_meeting(
        db=db,
        meeting_in=meeting_in,
        submitter_name=submitter_name,
        submitter_role=submitter_role,
    )


@router.get(
    "/{meeting_id}/detail",
    response_model=MeetingDetail,
    status_code=status.HTTP_200_OK,
    summary="Get meeting detail",
    description="Retrieves comprehensive meeting details including detected participants.",
)
def get_meeting_detail(
    meeting_id: UUID,
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Retrieves meeting detail with participants."""
    return MeetingService.get_meeting_detail(db=db, meeting_id=meeting_id)


@router.get(
    "/{user_id}",
    response_model=list[MeetingListItem],
    status_code=status.HTTP_200_OK,
    summary="List user meetings",
    description="Returns lightweight meeting summaries belonging to a specific user, ordered chronologically.",
)
def get_user_meetings(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> list[MeetingListItem]:
    """Retrieves all meetings belonging to user."""
    return MeetingService.get_meetings_for_user(db=db, user_id=user_id)


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a meeting",
    description="Deletes a meeting and triggers database cascade for participants, tasks, highlights, and chat.",
)
def delete_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    """Deletes meeting and cascading dependencies."""
    MeetingService.delete_meeting(db=db, meeting_id=meeting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
