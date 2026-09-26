"""
Tasks API router for MeetMind AI.

Exposes endpoints for user tasks, meeting tasks, task status updates, and task filtering.
Orders routes carefully to prevent route precedence conflicts.
Delegates entirely to TaskService.
"""

from datetime import date, datetime
from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.constants import TaskPriority, TaskStatus
from app.core.exceptions import InvalidOwnershipError
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.task import TaskFilterParams, TaskResponse, TaskStatusUpdate
from app.services.task_service import TaskService

router = APIRouter()


# ── 1. Static subpaths / Multi-segment routes first for route precedence ───────

@router.get(
    "/",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current user tasks",
    description="Retrieves all tasks assigned to the authenticated user, ordered by deadline ascending then priority.",
)
def list_my_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    """Retrieves all tasks for the current authenticated user."""
    return TaskService.get_user_tasks(db=db, user_id=current_user.id)


@router.get(
    "/{user_id}/filter",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Filter user tasks",
    description="Filters user tasks by priority, status, and deadline window. Ordered by deadline + priority.",
)
def filter_user_tasks(
    user_id: UUID,
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority: high, medium, low"),
    task_status: Optional[TaskStatus] = Query(None, alias="status", description="Filter by status: pending or complete"),
    deadline_before: Optional[Union[date, datetime]] = Query(None, description="Tasks due on or before date or timestamp"),
    deadline_after: Optional[Union[date, datetime]] = Query(None, description="Tasks due on or after date or timestamp"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    """Filters tasks for a user according to query parameters."""
    if user_id != current_user.id:
        raise InvalidOwnershipError(
            f"Access denied: cannot filter tasks for user '{user_id}'."
        )
    filter_params = TaskFilterParams(
        priority=priority,
        status=task_status,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
    )
    return TaskService.get_user_tasks(db=db, user_id=current_user.id, filter_params=filter_params)


@router.get(
    "/{user_id}/meeting/{meeting_id}",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get meeting tasks for user",
    description="Retrieves tasks belonging to a meeting and scoped to a specific user.",
)
def get_meeting_tasks(
    user_id: UUID,
    meeting_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    """Retrieves tasks for a specific meeting and user."""
    if user_id != current_user.id:
        raise InvalidOwnershipError(
            f"Access denied: cannot view tasks for user '{user_id}'."
        )
    return TaskService.get_meeting_tasks(db=db, meeting_id=meeting_id, user_id=current_user.id)


@router.put(
    "/{task_id}/status",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task status",
    description="Updates task lifecycle status (pending <-> complete).",
)
def update_task_status(
    task_id: UUID,
    status_in: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    """Updates status of a specific task."""
    return TaskService.update_task_status(
        db=db, task_id=task_id, status_update=status_in, user_id=current_user.id
    )


# ── 2. Single-segment generic route placed last ──────────────────────────────

@router.get(
    "/{user_id}",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all user tasks",
    description="Retrieves all tasks assigned to a user, ordered by deadline ascending then priority.",
)
def get_user_tasks(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    """Retrieves all tasks for a specific user."""
    if user_id != current_user.id:
        raise InvalidOwnershipError(
            f"Access denied: cannot view tasks for user '{user_id}'."
        )
    return TaskService.get_user_tasks(db=db, user_id=current_user.id)
