"""
Application settings loaded from environment variables.

All configuration is sourced through pydantic-settings.
No secrets are hardcoded here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings class for MeetMind AI backend.

    Values are loaded from environment variables (or a .env file when
    running locally).  The variable names match the contract defined in
    backend/.env.example exactly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # tolerate variables not declared here
    )

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str

    # ── Google Gemini ──────────────────────────────────────────────────────
    google_api_key: str = ""

    # ── OpenRouter ─────────────────────────────────────────────────────────
    openrouter_api_key: str = ""

    # ── Pinecone ───────────────────────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index_name: str = "hackathon-index"

    # ── Resend Email ───────────────────────────────────────────────────────
    resend_api_key: str = ""
    resend_sender: str = "onboarding@resend.dev"

    # ── Notification Scheduler ─────────────────────────────────────────────
    notification_hour: int = 8
    notification_minute: int = 0

    # ── App ────────────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False


# Single module-level instance reused by the rest of the application.
# Later gates import this object directly.
settings = Settings()
