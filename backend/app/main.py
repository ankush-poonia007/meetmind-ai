"""
FastAPI application bootstrap.

Gate 1 scope: application object creation and health check only.
Business endpoints (meetings, tasks, chat, etc.) are implemented in later gates.
"""

from fastapi import FastAPI

from app.core.settings import settings

# ── Application ────────────────────────────────────────────────────────────
app = FastAPI(
    title="MeetMind AI",
    description=(
        "Agentic AI meeting assistant — PostgreSQL + LangGraph backend."
    ),
    version="1.0.0",
    debug=settings.debug,
)


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health() -> dict:
    """
    Lightweight liveness probe.

    Returns 200 OK when the application is running.
    Does NOT check database connectivity (use /health/db for that in a later gate).
    """
    return {"status": "ok", "app": "MeetMind AI", "env": settings.app_env}
