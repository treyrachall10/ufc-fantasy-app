"""
Shared worker idle-shutdown settings from environment.

Workers should depend only on these values — not on environment names like
``development`` / ``production``.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off", ""}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUTHY:
        return True
    if normalized in _FALSY:
        return False
    raise ValueError(f"{name} must be a boolean-like value, got {raw!r}")


def _env_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return value


def idle_shutdown_enabled() -> bool:
    """Return whether workers should exit after an idle period. Default: True."""
    return _env_bool("WORKER_IDLE_SHUTDOWN_ENABLED", True)


def idle_timeout_seconds() -> int:
    """Seconds without messages before idle shutdown. Default: 60."""
    return _env_positive_int("WORKER_IDLE_TIMEOUT_SECONDS", 60)


def idle_check_interval_seconds() -> int:
    """How often to poll the pull future for idle checks. Default: 5."""
    return _env_positive_int("WORKER_IDLE_CHECK_INTERVAL_SECONDS", 5)


def should_shutdown_for_idle(idle_for_s: float) -> bool:
    """
    Return True when the worker should exit due to idle time.

    When idle shutdown is disabled, always returns False.
    """
    if not idle_shutdown_enabled():
        return False
    return idle_for_s > idle_timeout_seconds()
