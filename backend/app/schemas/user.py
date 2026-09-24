"""
Pydantic contracts for User domain.

Defines schemas for user registration, profile updates, and API responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UserBase(BaseModel):
    """Shared user attributes."""
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=EMAIL_REGEX,
        description="Unique email address",
    )


class UserCreate(UserBase):
    """Payload for user registration (POST /api/v1/users/register)."""
    pass


class UserUpdate(BaseModel):
    """Payload for updating user profile (PUT /api/v1/users/{user_id})."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated name")
    email: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        pattern=EMAIL_REGEX,
        description="Updated email address",
    )


class UserResponse(UserBase):
    """API response model for user entity."""
    id: UUID = Field(..., description="Unique user identifier")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)


# Convenience alias for read operations
UserRead = UserResponse
