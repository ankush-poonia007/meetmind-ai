"""
Authentication API router for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.5 — Backend Authentication APIs

Exposes endpoints for user registration, email/password login,
stateless logout, and authenticated user profile retrieval (/auth/me).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    LogoutResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Registers a new user with email and password. "
        "Atomically persists credentials using Argon2id. "
        "Issues a signed 24h JWT access token upon successful registration."
    ),
)
def register(
    reg_in: AuthRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    """Registers a new user account with credentials and returns a JWT access token."""
    return AuthService.register(db=db, reg_in=reg_in)


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain access token",
    description=(
        "Authenticates a user with email and password using Argon2id. "
        "Issues a signed 24h JWT access token on success. "
        "Returns a generic error on failure to prevent account enumeration."
    ),
)
def login(
    login_in: AuthLoginRequest,
    db: Session = Depends(get_db),
) -> AuthTokenResponse:
    """Authenticates credentials and returns a JWT access token."""
    return AuthService.authenticate(db=db, login_in=login_in)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Stateless user logout",
    description=(
        "Performs stateless logout. In a stateless JWT architecture, the server "
        "acknowledges the request, and the client must discard its stored token."
    ),
)
def logout() -> LogoutResponse:
    """Confirms stateless logout. The client must discard its stored access token."""
    return LogoutResponse(
        status="ok",
        message="Successfully logged out. Please discard your access token.",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
    description=(
        "Retrieves the sanitized profile of the authenticated user identified "
        "by the Bearer JWT in the Authorization header. Never exposes password hashes "
        "or credentials."
    ),
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieves profile of the current authenticated user."""
    return UserResponse.model_validate(current_user)
