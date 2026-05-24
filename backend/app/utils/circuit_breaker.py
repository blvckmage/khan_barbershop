"""Simple async circuit breaker for guarding external API calls.

Pattern:
    Closed (normal) → too many failures → Open (block calls)
                                            ↓ after recovery_timeout
                                       Half-Open (probe with 1 call)
                                            ↓                ↓
                                         success           failure
                                            ↓                ↓
                                        Closed            Open

Usage:
    breaker = CircuitBreaker(name="openai", failure_threshold=5, recovery_timeout=60)

    try:
        result = await breaker.call(openai_client.chat.completions.create, **kwargs)
    except CircuitOpenError:
        return "Сервис временно недоступен"
"""
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"        # normal operation
    OPEN = "open"            # failing, reject calls
    HALF_OPEN = "half_open"  # probing after recovery_timeout


class CircuitOpenError(Exception):
    """Raised when the circuit is OPEN and the call is rejected without execution."""
    def __init__(self, breaker_name: str, time_until_retry: float):
        self.breaker_name = breaker_name
        self.time_until_retry = time_until_retry
        super().__init__(
            f"Circuit '{breaker_name}' is OPEN — retry in {time_until_retry:.0f}s"
        )


class CircuitBreaker:
    """Async circuit breaker.

    Args:
        name: identifier for logging/metrics
        failure_threshold: consecutive failures before opening
        recovery_timeout: seconds to stay OPEN before allowing a HALF_OPEN probe
        expected_exceptions: tuple of exception classes that count as failures
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: tuple = (Exception,),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._failures = 0
        self._opened_at: float | None = None
        self._state: CircuitState = CircuitState.CLOSED
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute `func(*args, **kwargs)` through the breaker.

        Raises CircuitOpenError if the circuit is OPEN and not yet ready to probe.
        Any exception from `func` matching expected_exceptions is counted.
        """
        async with self._lock:
            await self._check_state()
            if self._state == CircuitState.OPEN:
                remaining = self.recovery_timeout - (time.monotonic() - (self._opened_at or 0))
                raise CircuitOpenError(self.name, max(0.0, remaining))

        try:
            result = await func(*args, **kwargs)
        except self.expected_exceptions as e:
            await self._on_failure(e)
            raise
        else:
            await self._on_success()
            return result

    async def _check_state(self):
        """Transition OPEN → HALF_OPEN if recovery_timeout elapsed."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                logger.info(f"🔁 Circuit '{self.name}' → HALF_OPEN (probing)")
                self._state = CircuitState.HALF_OPEN

    async def _on_success(self):
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(f"✅ Circuit '{self.name}' → CLOSED (recovered)")
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None

    async def _on_failure(self, exc: Exception):
        async with self._lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN:
                # Probe failed → back to OPEN
                logger.warning(f"⚠️ Circuit '{self.name}' probe failed → OPEN again")
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
            elif self._failures >= self.failure_threshold:
                logger.error(
                    f"🚨 Circuit '{self.name}' → OPEN "
                    f"({self._failures} consecutive failures, last: {type(exc).__name__}: {exc})"
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def snapshot(self) -> dict:
        """Read-only state for diagnostics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failures": self._failures,
            "opened_at": self._opened_at,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# ─── Shared singletons ────────────────────────────────────────────────────────
# Tuned conservatively: open after 5 errors, retry after 60s.

import httpx

alteegio_breaker = CircuitBreaker(
    name="alteegio",
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exceptions=(httpx.HTTPError, httpx.TimeoutException, OSError),
)

openai_breaker = CircuitBreaker(
    name="openai",
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exceptions=(Exception,),  # OpenAI lib raises many different types
)
