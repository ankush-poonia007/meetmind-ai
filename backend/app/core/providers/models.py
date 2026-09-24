"""
Internal data models for provider key entries and operational health tracking.

Strictly encapsulates raw API credentials so callers outside core/providers/
never receive or access them. All public and diagnostic interfaces expose
only safe non-secret identifiers (e.g. gemini#1).
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import FailureClass, KeyHealth, ProviderName


class KeyEntry:
    """
    In-memory representation of an individual provider API key slot.

    Maintains lifecycle health, usage counters, and cooldown timestamps.
    The credential itself is stored in private attribute `_raw_key` and is
    never exposed via public properties, string representations, or diagnostics.
    """

    def __init__(
        self,
        safe_id: str,
        raw_key: str,
        provider: ProviderName,
        slot_number: int,
        health: KeyHealth = KeyHealth.ACTIVE,
    ) -> None:
        self.safe_id: str = safe_id
        self._raw_key: str = raw_key
        self.provider: ProviderName = provider
        self.slot_number: int = slot_number
        self.health: KeyHealth = health

        self.usage_count: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.consecutive_failures: int = 0

        self.last_used: Optional[datetime] = None
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.cooldown_until: Optional[datetime] = None
        self.last_error_class: Optional[FailureClass] = None

    def _get_credential(self) -> str:
        """
        Internal credential accessor used strictly within provider infrastructure
        (e.g., passing to adapter execution callables).
        Callers outside core/providers/ must NEVER call or receive this.
        """
        return self._raw_key

    def __repr__(self) -> str:
        return (
            f"<KeyEntry safe_id={self.safe_id!r} provider={self.provider.value!r} "
            f"health={self.health.value!r} usage={self.usage_count} "
            f"failures={self.failure_count}>"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def to_diagnostic_dict(self) -> dict[str, Any]:
        """Returns safe operational metadata with zero credential exposure."""
        return {
            "safe_id": self.safe_id,
            "provider": self.provider.value,
            "slot_number": self.slot_number,
            "health": self.health.value,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consecutive_failures": self.consecutive_failures,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "last_error_class": self.last_error_class.value if self.last_error_class else None,
        }


class ProviderHealthSummary(BaseModel):
    """
    Safe operational diagnostic summary of a provider's key pool.
    Exposes only non-secret aggregated numbers and safe IDs.
    """
    provider: str = Field(..., description="Provider name")
    configured_key_count: int = Field(0, description="Total keys configured in pool")
    active_key_count: int = Field(0, description="Number of currently active keys")
    cooldown_key_count: int = Field(0, description="Number of keys currently in cooldown")
    disabled_key_count: int = Field(0, description="Number of permanently disabled keys")
    total_usage: int = Field(0, description="Cumulative requests dispatched through pool")
    is_available: bool = Field(False, description="True if at least one key is active or in temporary cooldown")
    keys_status: list[dict[str, Any]] = Field(default_factory=list, description="Per-key safe diagnostic metadata")

    model_config = ConfigDict(from_attributes=True)
