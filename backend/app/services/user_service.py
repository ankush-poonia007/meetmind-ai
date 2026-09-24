"""
User service for MeetMind AI.

Handles user creation/registration, retrieval, and profile updates.
Enforces email uniqueness and raises typed exceptions.
Does NOT implement authentication, passwords, or JWTs.
"""

from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import DuplicateUserError, UserNotFoundError
from app.core.logging import get_logger
from app.db.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

logger = get_logger(__name__)


class UserService:
    """Service layer managing User domain entities."""

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> UserResponse:
        """
        Creates and persists a new user record.

        Args:
            db: Active synchronous database session.
            user_in: Validated user creation payload.

        Returns:
            UserResponse schema with database-generated id and created_at.

        Raises:
            DuplicateUserError: If a user with the specified email already exists.
        """
        logger.info(f"Attempting to create user with email: {user_in.email}")

        # Check existing user by email
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            logger.warning(f"Registration rejected: email {user_in.email} already exists")
            raise DuplicateUserError(
                f"User with email '{user_in.email}' already exists.",
                details={"email": user_in.email},
            )

        user = User(
            name=user_in.name,
            email=user_in.email,
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            logger.error(f"Database integrity error creating user {user_in.email}: {exc}")
            raise DuplicateUserError(
                f"User with email '{user_in.email}' already exists.",
                details={"email": user_in.email},
            ) from exc
        except Exception as exc:
            db.rollback()
            logger.error(f"Unexpected error creating user {user_in.email}: {exc}")
            raise

        logger.info(f"Successfully created user {user.id} ({user.email})")
        return UserResponse.model_validate(user)

    @staticmethod
    def get_user_by_id(db: Session, user_id: UUID) -> UserResponse:
        """
        Retrieves a user by their unique primary key.

        Args:
            db: Active synchronous database session.
            user_id: Unique UUID of the user.

        Returns:
            UserResponse schema.

        Raises:
            UserNotFoundError: If no user with the given ID exists.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User not found with id: {user_id}")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )
        return UserResponse.model_validate(user)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> UserResponse:
        """
        Retrieves a user by their email address.

        Args:
            db: Active synchronous database session.
            email: Email address of the user.

        Returns:
            UserResponse schema.

        Raises:
            UserNotFoundError: If no user with the given email exists.
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.warning(f"User not found with email: {email}")
            raise UserNotFoundError(
                f"User with email '{email}' not found.",
                details={"email": email},
            )
        return UserResponse.model_validate(user)

    @staticmethod
    def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> UserResponse:
        """
        Updates an existing user's name or email.

        Args:
            db: Active synchronous database session.
            user_id: Unique UUID of the user to update.
            user_update: Fields to modify.

        Returns:
            Updated UserResponse schema.

        Raises:
            UserNotFoundError: If no user with the given ID exists.
            DuplicateUserError: If updating to an email that is already registered to another user.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"Update failed: user not found with id {user_id}")
            raise UserNotFoundError(
                f"User with id '{user_id}' not found.",
                details={"user_id": str(user_id)},
            )

        if user_update.email and user_update.email != user.email:
            existing = db.query(User).filter(User.email == user_update.email).first()
            if existing and existing.id != user_id:
                logger.warning(f"Update rejected: email {user_update.email} in use by another user")
                raise DuplicateUserError(
                    f"User with email '{user_update.email}' already exists.",
                    details={"email": user_update.email},
                )
            user.email = user_update.email

        if user_update.name is not None:
            user.name = user_update.name

        try:
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            logger.error(f"Integrity error updating user {user_id}: {exc}")
            raise DuplicateUserError(
                f"User with email '{user_update.email}' already exists.",
                details={"email": user_update.email},
            ) from exc
        except Exception as exc:
            db.rollback()
            logger.error(f"Unexpected error updating user {user_id}: {exc}")
            raise

        logger.info(f"Updated user {user.id}")
        return UserResponse.model_validate(user)
