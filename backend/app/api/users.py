"""
Users API router for MeetMind AI.

Exposes endpoints for user registration, user retrieval by ID, and profile updates.
Delegates entirely to UserService.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user profile with unique email. No authentication or passwords.",
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Registers a new user record."""
    return UserService.create_user(db=db, user_in=user_in)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Retrieves a user profile by unique user identifier.",
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Retrieves user profile by UUID."""
    return UserService.get_user_by_id(db=db, user_id=user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Updates user name or email address.",
)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Updates user profile attributes."""
    return UserService.update_user(db=db, user_id=user_id, user_update=user_update)
