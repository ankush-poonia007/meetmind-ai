"""
FastAPI application bootstrap for MeetMind AI.

Configures application lifespan, provider gateway initialization, APScheduler,
CORS middleware, health probes, global exception handling, and /api/v1 router aggregation.
"""

from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.exceptions import (
    AllKeysCooldownError,
    DuplicateUserError,
    EntityNotFoundError,
    InvalidOwnershipError,
    InvalidStateError,
    MeetMindError,
    ProviderAuthError,
    ProviderExhaustedError,
    ProviderKeyFailoverExhaustedError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
)
from app.core.logging import get_logger
from app.core.providers import get_provider_gateway
from app.core.settings import settings
from app.db.session import get_db

logger = get_logger(__name__)


# ── Application Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.

    Startup:
    1. Initializes provider gateway (enforcing required Gemini configuration).
    2. Stores provider gateway on app.state.provider_gateway.
    3. Initializes and starts AsyncIOScheduler on app.state.scheduler.

    Shutdown:
    1. Shuts down AsyncIOScheduler cleanly.
    """
    logger.info("Application startup initiated.")

    # 1. Initialize provider gateway and store on app.state
    gateway = get_provider_gateway()
    app.state.provider_gateway = gateway
    logger.info("Provider gateway initialized and attached to app.state.")

    # 2. Initialize and start AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    app.state.scheduler = scheduler

    # Register thin scheduled deadline notification job (daily at 08:00 AM)
    def scheduled_deadline_notification_job() -> None:
        logger.info("APScheduler executing daily deadline notification job (08:00 AM).")
        try:
            from app.core.constants import NotificationTrigger
            from app.db.session import SessionLocal
            from app.services.notification_service import NotificationService

            db = SessionLocal()
            try:
                NotificationService.process_deadline_notifications(
                    db=db, trigger=NotificationTrigger.SCHEDULED
                )
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Error executing scheduled deadline notification job: {exc}")

    # Controlled registration: id + replace_existing prevents duplication across reloads
    scheduler.add_job(
        scheduled_deadline_notification_job,
        trigger="cron",
        hour=settings.notification_hour,
        minute=settings.notification_minute,
        id="daily_deadline_notification",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("APScheduler initialized, daily 08:00 notification job registered, and started.")

    logger.info("Application startup complete.")
    try:
        yield
    finally:
        # Shutdown
        logger.info("Application shutdown initiated.")
        if hasattr(app.state, "scheduler") and app.state.scheduler.running:
            app.state.scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped.")
        logger.info("Application shutdown complete.")


# ── Application Factory ──────────────────────────────────────────────────────

app = FastAPI(
    title="MeetMind AI",
    description="Agentic AI meeting assistant — PostgreSQL + LangGraph backend.",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)


# ── CORS Middleware ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ─────────────────────────────────────────────────

@app.exception_handler(MeetMindError)
async def meetmind_error_handler(request: Request, exc: MeetMindError) -> JSONResponse:
    """
    Translates MeetMindError hierarchy into structured, secret-safe HTTP responses.
    Prevents leakage of raw credentials, stack traces, and internal secrets.
    """
    if isinstance(exc, (EntityNotFoundError, InvalidOwnershipError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DuplicateUserError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidStateError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (ProviderRateLimitError, AllKeysCooldownError)):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, ProviderAuthError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(
        exc,
        (
            ProviderNotConfiguredError,
            ProviderExhaustedError,
            ProviderKeyFailoverExhaustedError,
        ),
    ):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.warning(
        f"Handled {exc.__class__.__name__} on {request.method} {request.url.path}: "
        f"{exc.message}"
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# ── Health Probes ────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health() -> dict[str, Any]:
    """Lightweight liveness probe confirming FastAPI process is active."""
    return {
        "status": "ok",
        "app": "MeetMind AI",
        "env": settings.app_env,
    }


@app.get("/health/db", tags=["health"])
def health_db(db: Session = Depends(get_db)) -> JSONResponse:
    """
    Database connectivity probe using Gate 1 session dependency.
    Executes SELECT 1 against PostgreSQL/Supabase.
    """
    try:
        db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "database": "connected"},
        )
    except Exception as exc:
        logger.error(f"Database health probe failed: {type(exc).__name__}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "database": "unavailable",
                "message": "Database connectivity check failed",
            },
        )


@app.get("/health/providers", tags=["health"])
def health_providers(request: Request) -> JSONResponse:
    """
    Operational health summary for configured AI and search providers.
    Consumes app.state.provider_gateway to retrieve safe diagnostics (zero secrets).
    """
    gateway = getattr(request.app.state, "provider_gateway", None)
    if gateway is None:
        gateway = get_provider_gateway()

    summary = gateway.get_health_summary()
    gemini_summary = summary.get("gemini")
    is_gemini_healthy = gemini_summary.is_available if gemini_summary else False

    status_code = (
        status.HTTP_200_OK if is_gemini_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    content = {
        "status": "ok" if is_gemini_healthy else "degraded",
        "providers": {k: v.model_dump() for k, v in summary.items()},
    }
    return JSONResponse(status_code=status_code, content=content)


# ── Router Registration ──────────────────────────────────────────────────────

app.include_router(api_router)
