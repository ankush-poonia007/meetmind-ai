"""
SQLAlchemy declarative base.

All ORM models inherit from Base.
Alembic uses Base.metadata for autogeneration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for all MeetMind AI ORM models.

    Every model file must inherit from this class so that
    Base.metadata contains the complete schema for Alembic
    autogeneration and migration management.
    """
    pass
