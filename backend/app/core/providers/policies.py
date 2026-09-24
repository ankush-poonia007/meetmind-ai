"""
Use-case-aware provider and model resolution policies.

Maps agent capabilities and pipeline use cases to the correct provider
key pool and model configuration.
"""

from typing import Optional

from app.core.config import (
    BACKUP_MODEL,
    EMBEDDING_MODEL,
    FALLBACK_MODEL,
    SUB_AGENT_MODEL,
    SUPERVISOR_MODEL,
)
from app.core.constants import ProviderName


class ProviderPolicy:
    """
    Policy engine that routes an operation use case to its designated
    provider and model string.
    """

    # Static policy mapping: use_case -> (ProviderName, Optional[model_string])
    _POLICY_MAP: dict[str, tuple[ProviderName, Optional[str]]] = {
        # Gemini-backed use cases
        "supervisor": (ProviderName.GEMINI, SUPERVISOR_MODEL),
        "sub_agent": (ProviderName.GEMINI, SUB_AGENT_MODEL),
        "qa": (ProviderName.GEMINI, SUPERVISOR_MODEL),
        "embedding": (ProviderName.GEMINI, EMBEDDING_MODEL),
        # OpenRouter-backed use cases
        "fallback": (ProviderName.OPENROUTER, FALLBACK_MODEL),
        "backup": (ProviderName.OPENROUTER, BACKUP_MODEL),
        # Tavily-backed use cases (no model string)
        "web_search": (ProviderName.TAVILY, None),
    }

    @classmethod
    def get_provider(cls, use_case: str) -> ProviderName:
        """Returns the ProviderName responsible for the given use case."""
        if use_case not in cls._POLICY_MAP:
            raise ValueError(
                f"Unknown use case '{use_case}'. Approved use cases are: "
                f"{list(cls._POLICY_MAP.keys())}"
            )
        return cls._POLICY_MAP[use_case][0]

    @classmethod
    def get_model(cls, use_case: str) -> Optional[str]:
        """Returns the configured model string for the given use case, if applicable."""
        if use_case not in cls._POLICY_MAP:
            raise ValueError(
                f"Unknown use case '{use_case}'. Approved use cases are: "
                f"{list(cls._POLICY_MAP.keys())}"
            )
        return cls._POLICY_MAP[use_case][1]

    @classmethod
    def is_valid_use_case(cls, use_case: str) -> bool:
        """Returns True if the use case is recognized by the policy."""
        return use_case in cls._POLICY_MAP
