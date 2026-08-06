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


def test_worker_service_types_resolve_to_dedicated_urlconfs() -> None:
    assert resolve_root_urlconf("fights_in_event") == "ufc_fantasy.fights_in_event_urls"
    assert resolve_root_urlconf("fighter_profile") == "ufc_fantasy.fighter_profile_urls"
    assert resolve_root_urlconf("fight_stats") == "ufc_fantasy.fight_stats_urls"
    assert resolve_root_urlconf("career_stats") == "ufc_fantasy.career_stats_urls"
    assert resolve_root_urlconf("score_fight") == "ufc_fantasy.score_fight_urls"


def test_unknown_service_type_still_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unsupported SERVICE_TYPE"):
        resolve_root_urlconf("pipeline")


def test_public_urlconf_module_is_api_only() -> None:
    """Assert public_urls mounts admin + api and no pipeline push routes."""
    source = (
        Path(__file__).resolve().parents[3] / "ufc_fantasy" / "public_urls.py"
    ).read_text(encoding="utf-8")

    assert "admin/" in source
    assert "api.urls" in source
    assert "pipeline" not in source
    assert "pubsub" not in source
