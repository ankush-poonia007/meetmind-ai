"""
Highlights API router for MeetMind AI.

Exposes endpoints for retrieving meeting-scoped and user-scoped highlights.
Delegates entirely to HighlightService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import InvalidOwnershipError
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.highlight import HighlightListResponse
from app.services.highlight_service import HighlightService

router = APIRouter()


@router.get(
    "/",
    response_model=HighlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user highlights",
    description="Retrieves all highlights relevant to the authenticated user across all meetings.",
)
def list_my_highlights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HighlightListResponse:
    """Retrieves all highlights for the current authenticated user across all meetings."""
    return HighlightService.get_user_highlights(db=db, user_id=current_user.id)


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HighlightListResponse:
    """Retrieves highlights for a specific meeting and user."""
    if user_id != current_user.id:
        raise InvalidOwnershipError(
            f"Access denied: cannot view highlights for user '{user_id}'."
        )
    return HighlightService.get_meeting_highlights(db=db, meeting_id=meeting_id, user_id=current_user.id)


@router.get(
    "/{user_id}",
    response_model=HighlightListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all user highlights",
    description="Retrieves all highlights relevant to a user across all meetings.",
)
def get_user_highlights(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HighlightListResponse:
    """Retrieves all highlights for a user across all meetings."""
    if user_id != current_user.id:
        raise InvalidOwnershipError(
            f"Access denied: cannot view highlights for user '{user_id}'."
        )
    return HighlightService.get_user_highlights(db=db, user_id=current_user.id)
