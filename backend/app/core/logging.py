"""
Centralized structured logging for MeetMind AI using Loguru.

Provides get_logger() for module-scoped logger instances with
consistent formatting, environment-driven level configuration,
and no secret exposure.
"""

import sys
from loguru import logger


# ── Configuration Flag ───────────────────────────────────────────────────────
_LOGGING_INITIALIZED = False


def _configure_logging() -> None:
    """Configures the default Loguru sink with standardized formatting."""
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    logger.remove()

    debug = False
    try:
        from app.core.settings import settings
        debug = bool(getattr(settings, "debug", False))
    except Exception:
        # Fallback when settings cannot be loaded (e.g. unit tests or differing CWD)
        debug = False

    log_level = "DEBUG" if debug else "INFO"

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        level=log_level,
        format=log_format,
        colorize=True,
        backtrace=debug,
        diagnose=False,  # Prevent leaking local variables containing secrets
    )

    _LOGGING_INITIALIZED = True


def get_logger(name: str = "meetmind") -> "logger.__class__":
    """
    Returns a logger instance bound with the caller's module name.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Application event")
    """
    if not _LOGGING_INITIALIZED:
        _configure_logging()

    return logger.bind(name=name)
