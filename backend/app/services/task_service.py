"""
Task service for MeetMind AI.

Handles task querying, filtering by status/priority/deadline, ordering by deadline+priority,
and status updates. Enforces user/meeting ownership boundaries and respects lowercase
database TaskStatus enum.
"""

from typing import Optional, Union
from uuid import UUID
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidOwnershipError,
    MeetingNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.db.models.meeting import Meeting
from app.db.models.task import Task, TaskPriority as DBTaskPriority, TaskStatus as DBTaskStatus
from app.db.models.user import User
from app.schemas.task import TaskFilterParams, TaskResponse, TaskStatusUpdate

logger = get_logger(__name__)


def _priority_sort_order():
    """Generates a SQL CASE expression mapping priority high->1, medium->2, low->3."""
    return case(
        (Task.priority == DBTaskPriority.high, 1),
        (Task.priority == DBTaskPriority.medium, 2),
        (Task.priority == DBTaskPriority.low, 3),
        else_=4,
    )


class TaskService:
    """Service layer managing Task domain entities and filtering."""

    @staticmethod
    def get_user_tasks(
        db: Session,
        user_id: UUID,
        filter_params: Optional[TaskFilterParams] = None,
    ) -> list[TaskResponse]:
        """
        Retrieves all tasks assigned to a user, with optional filtering
        by priority, status, and deadline window.
        Ordered by deadline ascending (nulls last) then priority (high -> low).

        Args:
            db: Active synchronous database session.
            user_id: Target user UUID.
            filter_params: Optional filter criteria.

        Returns:
            List of TaskResponse schemas.

        Raises:
            UserNotFoundError: If the specified user does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Get user tasks failed: user {user_id} not found")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        query = db.query(Task).filter(Task.user_id == user_id)

        if filter_params:
            if filter_params.status is not None:
                status_val = (
                    filter_params.status.value
                    if hasattr(filter_params.status, "value")
                    else str(filter_params.status).lower()
                )
                query = query.filter(Task.status == status_val)

            if filter_params.priority is not None:
                prio_val = (
                    filter_params.priority.value
                    if hasattr(filter_params.priority, "value")
                    else str(filter_params.priority).lower()
                )
                query = query.filter(Task.priority == prio_val)

            if filter_params.deadline_before is not None:
                query = query.filter(Task.deadline <= filter_params.deadline_before)

            if filter_params.deadline_after is not None:
                query = query.filter(Task.deadline >= filter_params.deadline_after)

        # Default ordering: deadline + priority
        tasks = query.order_by(
            Task.deadline.asc().nullslast(),
            _priority_sort_order().asc(),
            Task.created_at.desc(),
        ).all()

        return [TaskResponse.model_validate(t) for t in tasks]

    @staticmethod
    def get_meeting_tasks(
        db: Session,
        meeting_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> list[TaskResponse]:
        """
        Retrieves tasks associated with a specific meeting, ordered by deadline + priority.

        Args:
            db: Active synchronous database session.
            meeting_id: Target meeting UUID.
            user_id: Optional user UUID to filter tasks to a specific user.

        Returns:
            List of TaskResponse schemas.

        Raises:
            MeetingNotFoundError: If the meeting does not exist.
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.warning(f"Get meeting tasks failed: meeting {meeting_id} not found")
            raise MeetingNotFoundError(
                f"Meeting with id '{meeting_id}' not found.",
                details={"meeting_id": str(meeting_id)},
            )

        query = db.query(Task).filter(Task.meeting_id == meeting_id)
        if user_id is not None:
            query = query.filter(Task.user_id == user_id)

        tasks = query.order_by(
            Task.deadline.asc().nullslast(),
            _priority_sort_order().asc(),
            Task.created_at.desc(),
        ).all()

        return [TaskResponse.model_validate(t) for t in tasks]

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: UUID,
        status_update: Union[TaskStatusUpdate, str],
        user_id: Optional[UUID] = None,
    ) -> TaskResponse:
        """
        Updates the status of an existing task (e.g. pending <-> complete).
        Enforces lowercase database enum value.

        Args:
            db: Active synchronous database session.
            task_id: Unique UUID of the task.
            status_update: New status (pending or complete).
            user_id: Optional UUID of the user attempting modification for ownership check.

        Returns:
            Updated TaskResponse schema.

        Raises:
            TaskNotFoundError: If the task does not exist.
            InvalidOwnershipError: If user_id is provided and does not match task assignee.
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"Update task status failed: task {task_id} not found")
            raise TaskNotFoundError(
                f"Task with id '{task_id}' not found.",
                details={"task_id": str(task_id)},
            )

        if user_id is not None and task.user_id != user_id:
            logger.warning(
                f"Task ownership violation: user {user_id} attempted to modify task {task_id} owned by {task.user_id}"
            )
            raise InvalidOwnershipError(
                f"Task with id '{task_id}' does not belong to user '{user_id}'.",
                details={"task_id": str(task_id), "user_id": str(user_id)},
            )

        # Normalize status to lowercase string matching DBTaskStatus enum
        if isinstance(status_update, TaskStatusUpdate):
            raw_val = (
                status_update.status.value
                if hasattr(status_update.status, "value")
                else str(status_update.status)
            )
        else:
            raw_val = (
                status_update.value
                if hasattr(status_update, "value")
                else str(status_update)
            )

        normalized_status = raw_val.strip().lower()
        if normalized_status not in ("pending", "complete"):
            raise ValueError(f"Invalid task status: '{normalized_status}'. Must be 'pending' or 'complete'.")

        task.status = DBTaskStatus(normalized_status)

        try:
            db.commit()
            db.refresh(task)
            logger.info(f"Updated task {task.id} status to '{task.status.value}'")
        except Exception as exc:
            db.rollback()
            logger.error(f"Error updating task {task_id}: {exc}")
            raise

        return TaskResponse.model_validate(task)
