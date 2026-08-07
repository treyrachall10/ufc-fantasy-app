"""
Shared helpers for pipeline enqueue management commands.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.core.management.base import CommandError


def require_positive_int(name: str, value: int) -> int:
    if value <= 0:
        raise CommandError(f"--{name} must be a positive integer")
    return value


def require_http_url(name: str, value: str) -> str:
    url = (value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise CommandError(f"--{name} must be a valid http(s) URL")
    return url
