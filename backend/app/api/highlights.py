"""
Highlights API router for MeetMind AI.

Exposes endpoints for retrieving meeting-scoped and user-scoped highlights.
Delegates entirely to HighlightService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.highlight import HighlightListResponse
from app.services.highlight_service import HighlightService

router = APIRouter()


@router.get(
    "/{user_id}/meeting/{meeting_id}",
    response_model=HighlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get meeting highlights",
    description="Retrieves highlights for a specific meeting, scoped to the specified user.",
)
def get_meeting_highlights(
    user_id: UUID,
    meeting_id: UUID,
    db: Session = Depends(get_db),
) -> HighlightListResponse:
    """Retrieves highlights for a specific meeting and user."""
    return HighlightService.get_meeting_highlights(db=db, meeting_id=meeting_id, user_id=user_id)


@router.get(
    "/{user_id}",
    response_model=HighlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all user highlights",
    description="Retrieves all highlights relevant to a user across all meetings.",
)
def get_user_highlights(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> HighlightListResponse:
    """Retrieves all highlights for a user across all meetings."""
    return HighlightService.get_user_highlights(db=db, user_id=user_id)
