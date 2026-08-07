"""Canonical URL handling for UFCStats resources."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

UFCSTATS_BASE_URL = "http://ufcstats.com"


def normalize_ufcstats_url(url: str | None) -> str:
    """Return one canonical absolute UFCStats URL, or an empty string."""
    raw = (url or "").strip()
    if not raw:
        return ""

    absolute = urljoin(f"{UFCSTATS_BASE_URL}/", raw)
    parts = urlsplit(absolute)
    path = parts.path
    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            "",  # Query parameters are not part of UFCStats resource identity.
            "",  # Fragments are client-side only.
        )
    )
