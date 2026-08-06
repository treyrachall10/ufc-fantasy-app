"""Tests for SERVICE_TYPE → ROOT_URLCONF selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from ufc_fantasy.service_routing import resolve_root_urlconf


def test_default_service_type_is_api() -> None:
    assert resolve_root_urlconf(None) == "ufc_fantasy.public_urls"
    assert resolve_root_urlconf("") == "ufc_fantasy.public_urls"
    assert resolve_root_urlconf("   ") == "ufc_fantasy.public_urls"


def test_api_service_type_resolves_public_urls() -> None:
    assert resolve_root_urlconf("api") == "ufc_fantasy.public_urls"


def test_unsupported_service_type_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unsupported SERVICE_TYPE"):
        resolve_root_urlconf("not-a-real-service")


def test_worker_service_types_not_registered_yet() -> None:
    """Issue 001 only registers api; worker roles arrive in later slices."""
    for worker in (
        "fights_in_event",
        "fighter_profile",
        "fight_stats",
        "career_stats",
        "score_fight",
        "pipeline",
    ):
        with pytest.raises(ValueError, match="Unsupported SERVICE_TYPE"):
            resolve_root_urlconf(worker)


def test_public_urlconf_module_is_api_only() -> None:
    """Assert public_urls mounts admin + api and no pipeline push routes."""
    source = (
        Path(__file__).resolve().parents[3] / "ufc_fantasy" / "public_urls.py"
    ).read_text(encoding="utf-8")

    assert "admin/" in source
    assert "api.urls" in source
    assert "pipeline" not in source
    assert "pubsub" not in source
