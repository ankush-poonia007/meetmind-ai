"""
Concurrency-safe in-memory key pool with health-aware round-robin selection.

Manages active, cooldown, and disabled states for provider credentials.
Performs lazy cooldown expiry and thread-safe state transitions via threading.Lock.
"""

import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import (
    COOLDOWN_RATE_LIMIT_ESCALATED_SECONDS,
    COOLDOWN_RATE_LIMIT_INITIAL_SECONDS,
    COOLDOWN_TRANSIENT_ERROR_SECONDS,
)
from app.core.constants import FailureClass, KeyHealth, ProviderName
from app.core.exceptions import (
    AllKeysCooldownError,
    ProviderExhaustedError,
    ProviderNotConfiguredError,
)
from app.core.logging import get_logger
from app.core.providers.models import KeyEntry, ProviderHealthSummary

logger = get_logger(__name__)


class KeyPool:
    """
    Thread-safe key pool for an individual provider (Gemini, OpenRouter, or Tavily).

    Maintains independent round-robin rotation, health states, and usage tracking.
    """

    def __init__(self, provider: ProviderName, keys: list[str]) -> None:
        self.provider: ProviderName = provider
        self._lock: threading.Lock = threading.Lock()
        self._pointer: int = 0

        # Construct KeyEntry list with safe identifiers
        self.keys: list[KeyEntry] = []
        for i, raw_key in enumerate(keys, start=1):
            if raw_key and raw_key.strip():
                safe_id = f"{provider.value}#{i}"
                self.keys.append(
                    KeyEntry(
                        safe_id=safe_id,
                        raw_key=raw_key.strip(),
                        provider=provider,
                        slot_number=i,
                        health=KeyHealth.ACTIVE,
                    )
                )

    def select_key(self, now: Optional[datetime] = None) -> KeyEntry:
        """
        Atomically selects the next eligible ACTIVE key using round-robin.

        Performs lazy cooldown evaluation before selection.
        Raises:
            ProviderNotConfiguredError: If the pool has 0 configured keys.
            ProviderExhaustedError: If all keys are permanently DISABLED.
            AllKeysCooldownError: If all non-disabled keys are currently in COOLDOWN.
        """
        current_time = now or datetime.now(timezone.utc)

        with self._lock:
            if not self.keys:
                raise ProviderNotConfiguredError(
                    f"No keys configured for provider '{self.provider.value}'."
                )

            # 1. Lazy cooldown recovery
            for key in self.keys:
                if key.health == KeyHealth.COOLDOWN and key.cooldown_until:
                    if key.cooldown_until <= current_time:
                        key.health = KeyHealth.ACTIVE
                        key.cooldown_until = None
                        logger.info(f"Key {key.safe_id} exited cooldown; returned to ACTIVE")

            # 2. Check pool-level health conditions
            disabled_count = sum(1 for k in self.keys if k.health == KeyHealth.DISABLED)
            cooldown_count = sum(1 for k in self.keys if k.health == KeyHealth.COOLDOWN)
            total_keys = len(self.keys)

            if disabled_count == total_keys:
                raise ProviderExhaustedError(
                    f"All {total_keys} keys for provider '{self.provider.value}' are permanently disabled."
                )

            if disabled_count + cooldown_count == total_keys:
                raise AllKeysCooldownError(
                    f"All available keys for provider '{self.provider.value}' are currently in cooldown."
                )

            # 3. Round-robin walk for an ACTIVE key
            n = len(self.keys)
            for step in range(n):
                candidate_index = (self._pointer + step) % n
                candidate = self.keys[candidate_index]

                if candidate.health == KeyHealth.ACTIVE:
                    candidate.usage_count += 1
                    candidate.last_used = current_time
                    self._pointer = (candidate_index + 1) % n
                    return candidate

            # Fallback if no active key found
            raise AllKeysCooldownError(
                f"No active key available for provider '{self.provider.value}'."
            )

    def record_success(self, safe_id: str, now: Optional[datetime] = None) -> None:
        """Records a successful operation on the key; resets consecutive failures."""
        current_time = now or datetime.now(timezone.utc)

        with self._lock:
            key = self._find_key(safe_id)
            if key:
                key.success_count += 1
                key.consecutive_failures = 0
                key.last_success = current_time

    def record_failure(
        self,
        safe_id: str,
        failure_class: FailureClass,
        now: Optional[datetime] = None,
        custom_cooldown_seconds: Optional[int] = None,
    ) -> None:
        """
        Records a provider failure and updates key health and cooldown.

        - UNAUTHORIZED / FORBIDDEN: Permanently disabled.
        - RATE_LIMITED: 60s cooldown; escalates to 300s if repeated.
        - Transient: 30s cooldown.
        """
        current_time = now or datetime.now(timezone.utc)

        with self._lock:
            key = self._find_key(safe_id)
            if not key:
                return

            key.failure_count += 1
            key.consecutive_failures += 1
            key.last_failure = current_time
            key.last_error_class = failure_class

            if failure_class in (FailureClass.UNAUTHORIZED, FailureClass.FORBIDDEN):
                key.health = KeyHealth.DISABLED
                key.cooldown_until = None
                logger.warning(f"Key {key.safe_id} permanently disabled due to {failure_class.value}")

            elif failure_class == FailureClass.RATE_LIMITED:
                key.health = KeyHealth.COOLDOWN
                if key.consecutive_failures > 1:
                    duration = custom_cooldown_seconds or COOLDOWN_RATE_LIMIT_ESCALATED_SECONDS
                else:
                    duration = custom_cooldown_seconds or COOLDOWN_RATE_LIMIT_INITIAL_SECONDS

                key.cooldown_until = current_time + timedelta(seconds=duration)
                logger.warning(
                    f"Key {key.safe_id} rate-limited; cooldown for {duration}s "
                    f"(consecutive_failures={key.consecutive_failures})"
                )

            else:
                # Transient error (PROVIDER_ERROR, TIMEOUT, CONNECTION_FAILED, UNKNOWN)
                key.health = KeyHealth.COOLDOWN
                duration = custom_cooldown_seconds or COOLDOWN_TRANSIENT_ERROR_SECONDS
                key.cooldown_until = current_time + timedelta(seconds=duration)
                logger.warning(
                    f"Key {key.safe_id} encountered {failure_class.value}; "
                    f"transient cooldown for {duration}s"
                )

    def get_health_summary(self, now: Optional[datetime] = None) -> ProviderHealthSummary:
        """Generates safe operational health statistics for this pool."""
        current_time = now or datetime.now(timezone.utc)

        with self._lock:
            # Lazy update before snapshot
            for key in self.keys:
                if key.health == KeyHealth.COOLDOWN and key.cooldown_until:
                    if key.cooldown_until <= current_time:
                        key.health = KeyHealth.ACTIVE
                        key.cooldown_until = None

            active_cnt = sum(1 for k in self.keys if k.health == KeyHealth.ACTIVE)
            cooldown_cnt = sum(1 for k in self.keys if k.health == KeyHealth.COOLDOWN)
            disabled_cnt = sum(1 for k in self.keys if k.health == KeyHealth.DISABLED)
            total_usage = sum(k.usage_count for k in self.keys)
            is_avail = (active_cnt > 0 or cooldown_cnt > 0)

            return ProviderHealthSummary(
                provider=self.provider.value,
                configured_key_count=len(self.keys),
                active_key_count=active_cnt,
                cooldown_key_count=cooldown_cnt,
                disabled_key_count=disabled_cnt,
                total_usage=total_usage,
                is_available=is_avail,
                keys_status=[k.to_diagnostic_dict() for k in self.keys],
            )

    def _find_key(self, safe_id: str) -> Optional[KeyEntry]:
        """Internal helper to look up a key by safe_id."""
        for k in self.keys:
            if k.safe_id == safe_id:
                return k
        return None
