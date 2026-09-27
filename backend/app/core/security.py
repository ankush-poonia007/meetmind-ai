"""
Security and password hashing foundation for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.4 — Authentication & Database Foundation

Provides:
- Argon2id password hashing and verification using RFC 9106 recommended parameters.
- Password complexity validation rules (8-14 chars, upper, lower, number, special char).
- Cryptographic salt generation via OS entropy.
- Secret-safe execution: Passwords and hashes are never logged.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Final

from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


# ── Explicit Argon2id Parameters (RFC 9106 & OWASP Recommendations) ────────
# Type: Argon2id (hybrid mode resistant to both side-channel and GPU attacks)
# time_cost: 3 iterations
# memory_cost: 65536 KiB (64 MiB)
# parallelism: 4 threads/lanes
# hash_len: 32 bytes (256-bit output hash)
# salt_len: 16 bytes (128-bit cryptographically secure random salt)
ARGON2_TIME_COST: Final[int] = 3
ARGON2_MEMORY_COST: Final[int] = 65536
ARGON2_PARALLELISM: Final[int] = 4
ARGON2_HASH_LEN: Final[int] = 32
ARGON2_SALT_LEN: Final[int] = 16

# Centralized PasswordHasher instance with explicit parameters
_password_hasher: Final[PasswordHasher] = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
    salt_len=ARGON2_SALT_LEN,
    type=Type.ID,
)

# ── Password Complexity Validation Rules ─────────────────────────────────────
# Minimum length: 8 characters
# Maximum length: 14 characters
# At least one uppercase letter [A-Z]
# At least one lowercase letter [a-z]
# At least one numerical digit [0-9]
# At least one special character
PASSWORD_MIN_LENGTH: Final[int] = 8
PASSWORD_MAX_LENGTH: Final[int] = 14
SPECIAL_CHARS_PATTERN: Final[re.Pattern] = re.compile(
    r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]"
)


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """
    Validates a password against the strict Batch 4.4 complexity rules.

    Requirements:
    - Minimum length: 8 characters
    - Maximum length: 14 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character

    Args:
        password: Raw candidate password string.

    Returns:
        tuple[bool, str]: (is_valid, error_message). If valid, error_message is empty.
    """
    if not isinstance(password, str):
        return False, "Password must be a string."

    if len(password) < PASSWORD_MIN_LENGTH:
        return (
            False,
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
        )

    if len(password) > PASSWORD_MAX_LENGTH:
        return (
            False,
            f"Password must be at most {PASSWORD_MAX_LENGTH} characters long.",
        )

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."

    if not SPECIAL_CHARS_PATTERN.search(password):
        return False, "Password must contain at least one special character."

    return True, ""


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using Argon2id with explicit RFC 9106 parameters.

    Automatically uses a cryptographically secure 16-byte random salt generated
    from operating system entropy. Never logs the password or resulting hash.

    Args:
        password: Raw candidate plaintext password.

    Returns:
        str: Encoded Argon2id hash string (e.g. '$argon2id$v=19$m=65536,t=3,p=4$...').

    Raises:
        ValueError: If password is empty or fails complexity rules.
        RuntimeError: If hashing fails internally.
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    is_valid, error_msg = validate_password_complexity(password)
    if not is_valid:
        raise ValueError(error_msg)

    try:
        return _password_hasher.hash(password)
    except HashingError as exc:
        logger.error("Argon2id hashing operation encountered an unexpected error.")
        raise RuntimeError("Failed to compute password hash.") from exc


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a candidate plaintext password against an Argon2id hash.

    Employs constant-time verification to prevent timing attacks.
    Never logs passwords or hashes.

    Args:
        password: Plaintext password to verify.
        hashed_password: Argon2 hash stored in database.

    Returns:
        bool: True if password matches the hash, False otherwise.
    """
    if not password or not hashed_password:
        return False

    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.warning("Unexpected exception during password verification.")
        return False


# ── JWT Access Token Operations (Batch 4.5) ──────────────────────────────────

def create_access_token(
    subject: str | uuid.UUID,
    email: str | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Creates a signed JWT access token for an authenticated user.

    Args:
        subject: Canonical user identifier (users.id).
        email: User email address.
        expires_delta: Optional custom token expiration duration.
        extra_claims: Optional dictionary of additional claims.

    Returns:
        str: Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if email:
        to_encode["email"] = email

    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT access token.

    Validates cryptographic signature, token algorithm, and expiration.
    Ensures 'sub' claim is present and well-formed.

    Args:
        token: Raw JWT bearer string.

    Returns:
        dict[str, Any]: Verified token claims payload.

    Raises:
        TokenExpiredError: If the token expiration time has elapsed.
        InvalidTokenError: If signature verification fails, algorithm mismatches,
                           or subject claim is missing.
    """
    if not token or not isinstance(token, str):
        raise InvalidTokenError("Missing or malformed access token.")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired.") from exc
    except JWTError as exc:
        raise InvalidTokenError("Invalid token signature or malformed token.") from exc
    except Exception as exc:
        logger.warning(f"Unexpected error decoding JWT: {exc}")
        raise InvalidTokenError("Could not validate token.") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token subject (sub) claim is missing.")

    return payload

