"""
Application settings loaded from environment variables.

All configuration is sourced through pydantic-settings.
Supports multi-key provider rotation: 20 Gemini keys, 5 OpenRouter keys, 5 Tavily keys,
plus backward-compatible legacy single-key fallbacks.
Credentials are masked in string representations.
"""

from typing import Any, Optional, Union
from urllib.parse import urlparse
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings class for MeetMind AI backend.

    Values are loaded from environment variables (or a .env file when
    running locally). Supports 30 numbered provider keys plus legacy fallbacks.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # tolerate variables not declared here
    )

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = ""

    # ── Google Gemini Legacy ───────────────────────────────────────────────
    google_api_key: str = ""

    # ── Google Gemini (20 Key Slots) ───────────────────────────────────────
    # Accepts GEMINI_API_KEY_N or GOOGLE_API_KEY_N via AliasChoices
    gemini_api_key_1: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_1", "google_api_key_1"))
    gemini_api_key_2: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_2", "google_api_key_2"))
    gemini_api_key_3: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_3", "google_api_key_3"))
    gemini_api_key_4: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_4", "google_api_key_4"))
    gemini_api_key_5: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_5", "google_api_key_5"))
    gemini_api_key_6: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_6", "google_api_key_6"))
    gemini_api_key_7: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_7", "google_api_key_7"))
    gemini_api_key_8: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_8", "google_api_key_8"))
    gemini_api_key_9: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_9", "google_api_key_9"))
    gemini_api_key_10: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_10", "google_api_key_10"))
    gemini_api_key_11: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_11", "google_api_key_11"))
    gemini_api_key_12: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_12", "google_api_key_12"))
    gemini_api_key_13: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_13", "google_api_key_13"))
    gemini_api_key_14: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_14", "google_api_key_14"))
    gemini_api_key_15: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_15", "google_api_key_15"))
    gemini_api_key_16: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_16", "google_api_key_16"))
    gemini_api_key_17: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_17", "google_api_key_17"))
    gemini_api_key_18: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_18", "google_api_key_18"))
    gemini_api_key_19: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_19", "google_api_key_19"))
    gemini_api_key_20: str = Field(default="", validation_alias=AliasChoices("gemini_api_key_20", "google_api_key_20"))

    # ── OpenRouter Legacy ──────────────────────────────────────────────────
    openrouter_api_key: str = ""

    # ── OpenRouter (5 Key Slots) ───────────────────────────────────────────
    openrouter_api_key_1: str = ""
    openrouter_api_key_2: str = ""
    openrouter_api_key_3: str = ""
    openrouter_api_key_4: str = ""
    openrouter_api_key_5: str = ""

    # ── Tavily (5 Key Slots + Optional Legacy) ─────────────────────────────
    tavily_api_key: str = ""
    tavily_api_key_1: str = ""
    tavily_api_key_2: str = ""
    tavily_api_key_3: str = ""
    tavily_api_key_4: str = ""
    tavily_api_key_5: str = ""

    # ── Pinecone ───────────────────────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index_name: str = "hackathon-index"

    # ── Resend Email ───────────────────────────────────────────────────────
    resend_api_key: str = ""
    resend_sender: str = "MeetMind <onboarding@resend.dev>"

    # ── Notification Scheduler ─────────────────────────────────────────────
    notification_hour: int = 8
    notification_minute: int = 0

    # ── JWT Authentication Configuration (Batch 4.4 Foundation) ────────────
    jwt_secret_key: str = Field(
        default="meetmind-dev-jwt-secret-key-at-least-32-chars-long!",
        description="Secret key for signing and verifying JWT tokens",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT cryptographic signing algorithm",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=1440,
        description="JWT access token lifetime in minutes (default 24h)",
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False

    # ── CORS Configuration ─────────────────────────────────────────────────
    cors_origins: Union[list[str], str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ],
        description="Allowed frontend origins for CORS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """
        Parses and sanitizes CORS allowed origins from environment variables.
        Supports comma-separated strings, JSON lists, or iterables.
        Ensures exact origins (scheme + host[:port]) without trailing slashes or subpaths.
        Prevents accidental character-by-character string splitting.
        """
        default_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ]

        def _clean_single_origin(origin: str) -> str:
            origin = origin.strip()
            if not origin:
                return ""
            if origin == "*":
                return "*"
            if "://" in origin:
                parsed = urlparse(origin)
                if parsed.scheme and parsed.netloc:
                    return f"{parsed.scheme}://{parsed.netloc}"
            return origin.rstrip("/")

        if v is None:
            return default_origins

        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return default_origins
            # Handle JSON array representation e.g. ["http://localhost:5173"]
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    import json
                    parsed_list = json.loads(v_str)
                    if isinstance(parsed_list, list):
                        cleaned = [_clean_single_origin(str(item)) for item in parsed_list]
                        return [c for c in cleaned if c]
                except Exception:
                    pass
            # Comma-separated string representation e.g. "http://localhost:5173,http://localhost:3000"
            raw_items = v_str.split(",")
            cleaned = [_clean_single_origin(item) for item in raw_items]
            return [c for c in cleaned if c]

        if isinstance(v, (list, tuple, set)):
            cleaned = [_clean_single_origin(str(item)) for item in v]
            return [c for c in cleaned if c]

        return default_origins

    def validate_security_configuration(self) -> None:
        """Fails safely if security configuration is missing or invalid in production."""
        if self.app_env == "production":
            if (
                not self.jwt_secret_key
                or "dev-jwt-secret" in self.jwt_secret_key
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "Production configuration error: JWT_SECRET_KEY must be explicitly configured "
                    "with a secure key of at least 32 characters."
                )

    # ── Provider Credential Extraction ─────────────────────────────────────


    def get_gemini_keys(self) -> list[str]:
        """
        Returns list of non-empty Gemini keys from numbered slots 1..20.
        Falls back to legacy google_api_key if no numbered slots are configured.
        """
        slots = [
            getattr(self, f"gemini_api_key_{i}", "") for i in range(1, 21)
        ]
        active = [k.strip() for k in slots if k and k.strip()]
        if not active and self.google_api_key and self.google_api_key.strip():
            return [self.google_api_key.strip()]
        return active

    def get_openrouter_keys(self) -> list[str]:
        """
        Returns list of non-empty OpenRouter keys from numbered slots 1..5.
        Falls back to legacy openrouter_api_key if no numbered slots are configured.
        """
        slots = [
            getattr(self, f"openrouter_api_key_{i}", "") for i in range(1, 6)
        ]
        active = [k.strip() for k in slots if k and k.strip()]
        if not active and self.openrouter_api_key and self.openrouter_api_key.strip():
            return [self.openrouter_api_key.strip()]
        return active

    def get_tavily_keys(self) -> list[str]:
        """
        Returns list of non-empty Tavily keys from numbered slots 1..5.
        Falls back to tavily_api_key if no numbered slots are configured.
        """
        slots = [
            getattr(self, f"tavily_api_key_{i}", "") for i in range(1, 6)
        ]
        active = [k.strip() for k in slots if k and k.strip()]
        if not active and self.tavily_api_key and self.tavily_api_key.strip():
            return [self.tavily_api_key.strip()]
        return active

    # ── Secret-Safe Representations ────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<Settings app_env={self.app_env!r} debug={self.debug} "
            f"cors_origins={self.cors_origins!r} "
            f"gemini_keys_configured={len(self.get_gemini_keys())} "
            f"openrouter_keys_configured={len(self.get_openrouter_keys())} "
            f"tavily_keys_configured={len(self.get_tavily_keys())}>"
        )

    def __str__(self) -> str:
        return self.__repr__()


# Single module-level instance reused by the rest of the application.
settings = Settings()
