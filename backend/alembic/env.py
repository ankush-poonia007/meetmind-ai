"""
Alembic environment configuration for MeetMind AI.

Key responsibilities:
1. Load DATABASE_URL from environment (never hardcoded).
2. Import Base.metadata — which requires all models to be imported first.
3. Configure synchronous (non-async) migrations using psycopg2-binary.
4. Support autogenerate so Alembic detects all seven tables.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Ensure the backend/ directory is on sys.path so app.* imports resolve ──
# This is necessary when running `alembic` from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import Base.metadata via models package ───────────────────────────────
# Importing app.db.models triggers all model imports, registering every
# table with Base.metadata before autogenerate runs.
from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: E402, F401  — side-effect: registers all 7 models

target_metadata = Base.metadata

# ── Alembic Config object ──────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Load DATABASE_URL from environment ────────────────────────────────────
# Priority: ALEMBIC_DATABASE_URL (CI override) → DATABASE_URL (application env)
database_url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Set it before running Alembic commands."
    )

# Override the sqlalchemy.url in alembic.ini with the env-sourced value.
config.set_main_option("sqlalchemy.url", database_url)


# ── Offline migrations ─────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for reviewing migration SQL or running against a DB
    that is not directly reachable from the migration host.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online migrations ──────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    Uses NullPool to avoid connection pooling issues in migration contexts.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,      # detect column type changes
            compare_server_default=True,  # detect default changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
