"""
ProviderGateway: central execution boundary for multi-provider, multi-key rotation.

Encapsulates credentials, enforces bounded key failover, protects against raw secret
leakage, and differentiates provider/API failures from application/programming errors.
"""

from typing import Any, Callable, Optional, TypeVar

from app.core.config import MAX_KEY_FAILOVER_ATTEMPTS
from app.core.constants import FailureClass, ProviderName
from app.core.exceptions import (
    AllKeysCooldownError,
    ProviderAuthError,
    ProviderError,
    ProviderExhaustedError,
    ProviderKeyFailoverExhaustedError,
    ProviderNotConfiguredError,
    ProviderRateLimitError,
)
from app.core.logging import get_logger
from app.core.providers.key_pool import KeyPool
from app.core.providers.models import ProviderHealthSummary
from app.core.providers.policies import ProviderPolicy
from app.core.settings import Settings, settings as app_settings

logger = get_logger(__name__)

T = TypeVar("T")


class ProviderGateway:
    """
    Gateway mediating all interactions with external AI and search providers.

    Features:
    - Automatic use-case to provider/model resolution
    - Thread-safe key selection with round-robin rotation
    - Cooldown management on rate limits and transient errors
    - Permanent disabling on authentication failures
    - Bounded key failover (maximum 3 attempts)
    - Strict secret protection: credentials never escape the gateway
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        custom_pools: Optional[dict[ProviderName, KeyPool]] = None,
    ) -> None:
        self.policy: type[ProviderPolicy] = ProviderPolicy
        self.pools: dict[ProviderName, KeyPool] = {}

        if custom_pools is not None:
            # Allows injecting mock or synthetic pools during testing
            self.pools = custom_pools
            # Validate required provider
            if ProviderName.GEMINI not in self.pools or len(self.pools[ProviderName.GEMINI].keys) == 0:
                raise ProviderNotConfiguredError(
                    "Gemini provider is required but no keys were configured."
                )
        else:
            cfg = settings or app_settings
            self._initialize_pools(cfg)

    def _initialize_pools(self, cfg: Settings) -> None:
        """Initializes pools for Gemini, OpenRouter, and Tavily from settings."""
        # 1. Gemini (Required)
        gemini_keys = cfg.get_gemini_keys()
        if not gemini_keys:
            raise ProviderNotConfiguredError(
                "Gemini provider is required but no Gemini keys are configured in environment."
            )
        self.pools[ProviderName.GEMINI] = KeyPool(ProviderName.GEMINI, gemini_keys)
        logger.info(
            f"Initialized Gemini pool with {len(self.pools[ProviderName.GEMINI].keys)} keys."
        )

        # 2. OpenRouter (Optional)
        openrouter_keys = cfg.get_openrouter_keys()
        if openrouter_keys:
            self.pools[ProviderName.OPENROUTER] = KeyPool(
                ProviderName.OPENROUTER, openrouter_keys
            )
            logger.info(
                f"Initialized OpenRouter pool with {len(self.pools[ProviderName.OPENROUTER].keys)} keys."
            )

        # 3. Tavily (Optional)
        tavily_keys = cfg.get_tavily_keys()
        if tavily_keys:
            self.pools[ProviderName.TAVILY] = KeyPool(ProviderName.TAVILY, tavily_keys)
            logger.info(
                f"Initialized Tavily pool with {len(self.pools[ProviderName.TAVILY].keys)} keys."
            )

    def execute(
        self,
        use_case: str,
        operation: Callable[[str, Optional[str]], T],
        max_failover_attempts: int = MAX_KEY_FAILOVER_ATTEMPTS,
    ) -> T:
        """
        Executes a provider operation with bounded key failover and health tracking.

        The credential is passed directly to the `operation` callable inside this
        gateway boundary and is NEVER returned, logged, or exposed to the caller.

        Args:
            use_case: Capability key (e.g. 'supervisor', 'sub_agent', 'qa', 'fallback')
            operation: Callable receiving (raw_credential, model_string) and returning result
            max_failover_attempts: Maximum keys to attempt before raising failover exhaustion

        Raises:
            ProviderNotConfiguredError: If the provider has no keys configured.
            ProviderExhaustedError: If all keys are permanently disabled.
            AllKeysCooldownError: If all available keys are in cooldown.
            ProviderKeyFailoverExhaustedError: If failover attempts exceed limit.
            Exception: Any application/programming error is immediately re-raised.
        """
        provider = self.policy.get_provider(use_case)
        model = self.policy.get_model(use_case)

        pool = self.pools.get(provider)
        if not pool or not pool.keys:
            raise ProviderNotConfiguredError(
                f"Provider '{provider.value}' for use case '{use_case}' is not configured."
            )

        attempts = 0
        last_failure_reason: Optional[str] = None

        while attempts < max_failover_attempts:
            key_entry = pool.select_key()

            try:
                # Execute inside provider boundary — passing credential only internally
                result = operation(key_entry._get_credential(), model)
                pool.record_success(key_entry.safe_id)
                return result

            except Exception as exc:
                # ── Correction 2: Provider Failure vs Application Failure ────────
                if not self.is_provider_error(exc):
                    # Application/programming bugs must NOT poison the key or failover!
                    logger.error(
                        f"Non-provider application error during {use_case} on {key_entry.safe_id}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    raise

                # Actual provider/API/network failure attributable to key/provider
                failure_class = self.classify_error(exc)
                pool.record_failure(key_entry.safe_id, failure_class)
                attempts += 1
                last_failure_reason = f"{failure_class.value} on {key_entry.safe_id}"

                logger.warning(
                    f"Provider failure during {use_case} attempt {attempts}/{max_failover_attempts} "
                    f"({last_failure_reason})"
                )

                if attempts >= max_failover_attempts:
                    raise ProviderKeyFailoverExhaustedError(
                        f"Exhausted {max_failover_attempts} key failover attempts for use case "
                        f"'{use_case}' on provider '{provider.value}'. Last error: {last_failure_reason}"
                    ) from exc

        raise ProviderKeyFailoverExhaustedError(
            f"Exhausted failover attempts for use case '{use_case}'."
        )

    def is_provider_error(self, error: Exception) -> bool:
        """
        Distinguishes provider/API/network failures from internal application/programming errors.

        Returns True for HTTP errors (4xx/5xx from external APIs), timeouts, and network drops.
        Returns False for TypeError, KeyError, AttributeError, ValueError, and application bugs.
        """
        # Explicit provider exceptions from our domain hierarchy
        if isinstance(
            error,
            (
                ProviderAuthError,
                ProviderRateLimitError,
                ProviderError,
                TimeoutError,
                ConnectionError,
            ),
        ):
            return True

        # Check for HTTP status codes on the exception (e.g. requests, httpx, google SDKs)
        status_code = getattr(error, "status_code", None)
        if status_code is None and hasattr(error, "response"):
            status_code = getattr(error.response, "status_code", None)

        if status_code is not None and isinstance(status_code, int):
            return status_code in (401, 403, 429) or (500 <= status_code < 600)

        # Check error message strings for provider failure markers
        err_msg = str(error).lower()
        provider_markers = [
            "rate limit",
            "quota exceeded",
            "resource exhausted",
            "429",
            "unauthorized",
            "invalid api key",
            "authentication",
            "401",
            "forbidden",
            "permission denied",
            "403",
            "bad gateway",
            "502",
            "service unavailable",
            "503",
            "gateway timeout",
            "504",
            "internal server error",
            "500",
            "timeout",
            "connection error",
            "connection refused",
            "connection reset",
        ]

        if any(marker in err_msg for marker in provider_markers):
            return True

        # Standard application/programming errors are NOT provider errors
        if isinstance(
            error,
            (
                TypeError,
                KeyError,
                AttributeError,
                IndexError,
                ValueError,
                ImportError,
                ZeroDivisionError,
            ),
        ):
            return False

        return False

    def classify_error(self, error: Exception) -> FailureClass:
        """Normalizes external provider exceptions into FailureClass taxonomy."""
        status_code = getattr(error, "status_code", None)
        if status_code is None and hasattr(error, "response"):
            status_code = getattr(error.response, "status_code", None)

        if status_code == 401:
            return FailureClass.UNAUTHORIZED
        if status_code == 403:
            return FailureClass.FORBIDDEN
        if status_code == 429:
            return FailureClass.RATE_LIMITED
        if status_code and 500 <= status_code < 600:
            return FailureClass.PROVIDER_ERROR

        if isinstance(error, TimeoutError):
            return FailureClass.TIMEOUT
        if isinstance(error, ConnectionError):
            return FailureClass.CONNECTION_FAILED

        err_msg = str(error).lower()
        if "401" in err_msg or "unauthorized" in err_msg or "invalid api key" in err_msg:
            return FailureClass.UNAUTHORIZED
        if "403" in err_msg or "forbidden" in err_msg or "permission denied" in err_msg:
            return FailureClass.FORBIDDEN
        if "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg or "exhausted" in err_msg:
            return FailureClass.RATE_LIMITED
        if any(code in err_msg for code in ("500", "502", "503", "504")) or "server error" in err_msg:
            return FailureClass.PROVIDER_ERROR
        if "timeout" in err_msg or "timed out" in err_msg:
            return FailureClass.TIMEOUT
        if "connection" in err_msg or "network" in err_msg:
            return FailureClass.CONNECTION_FAILED

        return FailureClass.UNKNOWN

    def get_health_summary(self) -> dict[str, ProviderHealthSummary]:
        """
        Returns safe operational diagnostics across all configured provider pools.
        Strictly zero raw secrets in output; safe IDs only.
        """
        return {
            provider.value: pool.get_health_summary()
            for provider, pool in self.pools.items()
        }


# ── Module Singleton Pattern ─────────────────────────────────────────────────
_PROVIDER_GATEWAY: Optional[ProviderGateway] = None


def get_provider_gateway(
    settings_override: Optional[Settings] = None,
    custom_pools: Optional[dict[ProviderName, KeyPool]] = None,
) -> ProviderGateway:
    """Returns or initializes the global ProviderGateway singleton."""
    global _PROVIDER_GATEWAY
    if _PROVIDER_GATEWAY is None or settings_override is not None or custom_pools is not None:
        _PROVIDER_GATEWAY = ProviderGateway(
            settings=settings_override, custom_pools=custom_pools
        )
    return _PROVIDER_GATEWAY
