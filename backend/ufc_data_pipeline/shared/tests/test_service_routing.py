"""Tests for SERVICE_TYPE → ROOT_URLCONF selection."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import pytest

from ufc_fantasy.service_routing import resolve_root_urlconf

BACKEND_DIR = Path(__file__).resolve().parents[3]


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
    source = (BACKEND_DIR / "ufc_fantasy" / "public_urls.py").read_text(
        encoding="utf-8"
    )

    assert "admin/" in source
    assert "api.urls" in source
    assert "pipeline" not in source
    assert "pubsub" not in source


class NoServiceRoutingTests(unittest.TestCase):
    def test_no_service_resolves_to_noop_urlconf(self) -> None:
        self.assertEqual(
            resolve_root_urlconf("no_service"),
            "ufc_fantasy.no_service_urls",
        )
        self.assertEqual(
            resolve_root_urlconf("  no_service  "),
            "ufc_fantasy.no_service_urls",
        )

    def test_no_service_urlconf_does_not_import_api_or_supabase(self) -> None:
        """Boot Django as a no_service process and assert HTTP/API modules stay unloaded."""
        script = r"""
import os
import sys

os.environ["SERVICE_TYPE"] = "no_service"
os.environ["DJANGO_SETTINGS_MODULE"] = "ufc_fantasy.test_settings"

import django

django.setup()

from django.conf import settings
from django.urls import get_resolver

assert settings.ROOT_URLCONF == "ufc_fantasy.no_service_urls"
assert list(get_resolver().url_patterns) == []

forbidden = ("api.urls", "api.views", "services.supabase")
loaded = [name for name in forbidden if name in sys.modules]
if loaded:
    raise SystemExit("unexpected imports: " + ", ".join(loaded))
"""
        env = os.environ.copy()
        env["SERVICE_TYPE"] = "no_service"
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(BACKEND_DIR)
            if not pythonpath
            else str(BACKEND_DIR) + os.pathsep + pythonpath
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
