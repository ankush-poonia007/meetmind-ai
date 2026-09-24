"""
Extraction API router for MeetMind AI.

Exposes endpoints to trigger multi-agent transcript extraction, retrieve extraction preview,
and process human-in-the-loop task confirmation decisions (YES, NO, PARTIAL).
Delegates entirely to ExtractionService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.extraction import (
    ExtractionConfirmRequest,
    ExtractionPreviewResponse,
    ExtractionResult,
    ExtractionRunRequest,
)
from app.services.extraction_service import ExtractionService

router = APIRouter()


@router.post(
    "/{meeting_id}/run",
    response_model=ExtractionPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Run extraction pipeline",
    description="Triggers multi-agent extraction pipeline on meeting transcript and returns preview items.",
)
def run_extraction(
    meeting_id: UUID,
    run_req: ExtractionRunRequest,
    db: Session = Depends(get_db),
) -> ExtractionPreviewResponse:
    """Runs extraction pipeline and returns preview."""
    return ExtractionService.run_extraction(db=db, meeting_id=meeting_id, user_id=run_req.user_id)


@router.get(
    "/{meeting_id}/preview",
    response_model=ExtractionPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get extraction preview",
    description="Retrieves extracted action items and highlights awaiting human-in-the-loop confirmation.",
)
def get_extraction_preview(
    meeting_id: UUID,
    user_id: UUID = Query(..., description="Requesting user UUID for ownership verification"),
    db: Session = Depends(get_db),
) -> ExtractionPreviewResponse:
    """Retrieves unconfirmed extraction preview for a meeting."""
    return ExtractionService.get_extraction_preview(db=db, meeting_id=meeting_id, user_id=user_id)


@router.post(
    "/{meeting_id}/confirm",
    response_model=ExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Confirm extracted tasks",
    description="Processes human-in-the-loop confirmation decision (YES, NO, or PARTIAL) and persists approved items.",
)
def confirm_extraction(
    meeting_id: UUID,
    confirm_req: ExtractionConfirmRequest,
    db: Session = Depends(get_db),
) -> ExtractionResult:
    """Submits task confirmation and commits approved items to database."""
    # Ensure meeting_id matches path
    if confirm_req.meeting_id != meeting_id:
        confirm_req = ExtractionConfirmRequest(
            meeting_id=meeting_id,
            user_id=confirm_req.user_id,
            user_confirmation=confirm_req.user_confirmation,
            confirmed_task_ids=confirm_req.confirmed_task_ids,
        )
    return ExtractionService.confirm_extraction(db=db, confirm_req=confirm_req)
