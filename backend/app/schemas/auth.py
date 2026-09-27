"""
Authentication Pydantic schemas for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.5 — Backend Authentication APIs

Defines contracts for registration, login, token issuance, and logout.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_password_complexity
from app.schemas.user import EMAIL_REGEX, UserResponse



class AuthRegisterRequest(BaseModel):
    """
    Request payload for user registration with credentials.
    POST /api/v1/auth/register
    """
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's first name",
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's last name",
    )
    mobile_number: Optional[str] = Field(
        None,
        max_length=25,
        description="Optional mobile contact number (non-unique)",
    )
    email: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=EMAIL_REGEX,
        description="Unique email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=14,
        description="Password meeting complexity requirements (8-14 chars, upper, lower, digit, special)",
    )
    confirm_password: Optional[str] = Field(
        None,
        description="Optional password confirmation field for client-side alignment",
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional full name override; defaults to 'first_name last_name'",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        is_valid, err_msg = validate_password_complexity(v)
        if not is_valid:
            raise ValueError(err_msg)
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None:
            password = info.data.get("password")
            if password is not None and v != password:
                raise ValueError("Passwords do not match.")
        return v



class AuthLoginRequest(BaseModel):
    """
    Request payload for user login.
    POST /api/v1/auth/login
    """
    email: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=EMAIL_REGEX,
        description="Account email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Plaintext password to verify",
    )


class AuthTokenResponse(BaseModel):
    """
    Response returned upon successful registration or login.
    Provides standard JWT access token and sanitized user profile.
    """
    access_token: str = Field(
        ...,
        description="JWT bearer access token",
    )
    token_type: str = Field(
        default="bearer",
        description="Authentication token type",
    )
    expires_in: int = Field(
        ...,
        description="Token lifetime in seconds (e.g., 86400 for 24h)",
    )
    user: UserResponse = Field(
        ...,
        description="Sanitized authenticated user profile (zero credentials exposed)",
    )


class LogoutResponse(BaseModel):
    """
    Response payload for stateless logout.
    POST /api/v1/auth/logout
    """
    status: str = Field(
        default="ok",
        description="Status acknowledgment",
    )
    message: str = Field(
        default="Successfully logged out. Please discard your access token.",
        description="Confirmation instruction for client",
    )
