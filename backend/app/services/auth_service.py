"""
Authentication service for MeetMind AI.

Phase: 4 — Authentication, User Isolation & Dashboard Integration
Batch: 4.5 — Backend Authentication APIs

Provides:
- Atomic user registration with credentials.
- Constant-time email and password authentication with generic error secrecy.
- Safe handling of legacy uncredentialed accounts.
- JWT access token generation adhering to frozen Batch 4.4 settings.
"""

from typing import Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateUserError,
    InvalidCredentialsError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    hash_password,
    validate_password_complexity,
    verify_password,
)
from app.core.settings import settings
from app.db.models.user import User
from app.db.models.user_credentials import UserCredentials
from app.schemas.auth import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
)
from app.schemas.user import UserResponse

logger = get_logger(__name__)

# Static dummy hash for constant-time comparison when email does not exist
# Prevents side-channel timing attacks that enumerate registered emails
_DUMMY_ARGON2_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$c29tZXJhbmRvbXNhbHQ1NQ$"
    "eG93eWprM253cWRqY2tqZGtzY2prZHNjc2tkc2Nrc2Q"
)


class AuthService:
    """Service layer managing user authentication, registration, and tokens."""

    @staticmethod
    def register(
        db: Session,
        reg_in: AuthRegisterRequest,
    ) -> AuthTokenResponse:
        """
        Atomically registers a new user with credentials.

        Args:
            db: Active database session.
            reg_in: Validated registration payload.

        Returns:
            AuthTokenResponse: Access token and sanitized user profile.

        Raises:
            ValueError: If password fails complexity rules.
            DuplicateUserError: If email is already registered.
        """
        # 1. Enforce strict backend password complexity rules
        is_valid, err_msg = validate_password_complexity(reg_in.password)
        if not is_valid:
            logger.warning(f"Registration rejected for {reg_in.email}: {err_msg}")
            raise ValueError(err_msg)

        # 2. Check for existing account with this email
        existing = db.query(User).filter(User.email == reg_in.email).first()
        if existing:
            logger.warning(
                f"Registration rejected: email {reg_in.email} already exists"
            )
            raise DuplicateUserError(
                f"User with email '{reg_in.email}' already exists.",
                details={"email": reg_in.email},
            )

        # 3. Hash password using Argon2id with RFC 9106 parameters
        pw_hash = hash_password(reg_in.password)

        # 4. Synthesize full name if not explicitly provided
        full_name = reg_in.name or f"{reg_in.first_name} {reg_in.last_name}".strip()

        # 5. Instantiate models within single atomic unit of work
        user = User(
            name=full_name,
            first_name=reg_in.first_name,
            last_name=reg_in.last_name,
            mobile_number=reg_in.mobile_number,
            email=reg_in.email,
        )

        creds = UserCredentials(
            user=user,
            password_hash=pw_hash,
        )

        db.add_all([user, creds])

        # 6. Atomically commit transaction with rollback on failure
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            logger.error(f"Database integrity error during registration of {reg_in.email}: {exc}")
            raise DuplicateUserError(
                f"User with email '{reg_in.email}' already exists.",
                details={"email": reg_in.email},
            ) from exc
        except Exception as exc:
            db.rollback()
            logger.error(f"Unexpected error during registration of {reg_in.email}: {exc}")
            raise

        logger.info(f"Successfully registered user {user.id} ({user.email})")

        # 7. Issue JWT access token
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
        )
        expires_in = settings.jwt_access_token_expire_minutes * 60

        return AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def authenticate(
        db: Session,
        login_in: AuthLoginRequest,
    ) -> AuthTokenResponse:
        """
        Authenticates a user via email and password in constant time.
        Avoids account enumeration by returning a generic error on any failure.

        Args:
            db: Active database session.
            login_in: Login credentials.

        Returns:
            AuthTokenResponse: Generated access token and sanitized user profile.

        Raises:
            InvalidCredentialsError: On incorrect email, incorrect password,
                                     or uncredentialed legacy account.
        """
        user = db.query(User).filter(User.email == login_in.email).first()

        # Account not found -> run dummy verification to equalize timing
        if not user:
            verify_password(login_in.password, _DUMMY_ARGON2_HASH)
            logger.warning(f"Login failed: email {login_in.email} not found")
            raise InvalidCredentialsError("Invalid email or password.")

        # Account found but lacks credentials (e.g. legacy account) -> fail safely
        if not user.credentials or not user.credentials.password_hash:
            verify_password(login_in.password, _DUMMY_ARGON2_HASH)
            logger.warning(
                f"Login failed: user {user.id} ({login_in.email}) has no credentials record"
            )
            raise InvalidCredentialsError("Invalid email or password.")

        # Verify password in constant time
        is_correct = verify_password(login_in.password, user.credentials.password_hash)
        if not is_correct:
            logger.warning(f"Login failed: incorrect password for user {user.id}")
            raise InvalidCredentialsError("Invalid email or password.")

        logger.info(f"User {user.id} successfully authenticated")

        # Issue JWT access token
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
        )
        expires_in = settings.jwt_access_token_expire_minutes * 60

        return AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        )
