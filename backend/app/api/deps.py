"""
FastAPI dependency injection for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.5 — Backend Authentication APIs

Provides:
- get_current_user: Resolves the canonical authenticated User identity from a Bearer JWT.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidTokenError
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

# HTTPBearer security scheme (auto_error=False allows structured exception handling)
oauth2_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates a Bearer JWT,
    resolving the canonical User entity from the database.

    Args:
        auth_header: Extracted Authorization Bearer token header.
        db: Active database session.

    Returns:
        User: Canonical authenticated SQLAlchemy User model.

    Raises:
        InvalidTokenError: If Authorization header is missing, token is malformed,
                           or subject claim does not resolve to an active user.
        TokenExpiredError: If token expiration has elapsed.
    """
    if auth_header is None or not auth_header.credentials:
        raise InvalidTokenError("Missing authentication token.")

    token = auth_header.credentials.strip()
    payload = decode_access_token(token)

    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("Token subject (sub) claim is missing.")

    try:
        user_id = UUID(str(sub))
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError("Token subject claim is not a valid UUID.") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise InvalidTokenError("User not found or account deactivated.")

    return user
