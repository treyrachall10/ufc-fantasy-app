"""
Tests for shared worker idle-shutdown environment settings.
"""

from __future__ import annotations

import os
from unittest import TestCase
from unittest.mock import patch

from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    idle_shutdown_enabled,
    idle_timeout_seconds,
    max_messages,
    should_shutdown_for_idle,
)


class WorkerSettingsTests(TestCase):
    def test_idle_shutdown_defaults_to_enabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert idle_shutdown_enabled() is True
            assert idle_timeout_seconds() == 60
            assert idle_check_interval_seconds() == 5
            assert max_messages() == 3

    def test_max_messages_reads_env(self) -> None:
        with patch.dict(os.environ, {"WORKER_MAX_MESSAGES": "5"}):
            assert max_messages() == 5

    def test_max_messages_rejects_non_positive(self) -> None:
        with patch.dict(os.environ, {"WORKER_MAX_MESSAGES": "0"}):
            with self.assertRaises(ValueError):
                max_messages()

    def test_idle_shutdown_enabled_parses_truthy_and_falsy(self) -> None:
        with patch.dict(os.environ, {"WORKER_IDLE_SHUTDOWN_ENABLED": "false"}):
            assert idle_shutdown_enabled() is False
        with patch.dict(os.environ, {"WORKER_IDLE_SHUTDOWN_ENABLED": "1"}):
            assert idle_shutdown_enabled() is True
        with patch.dict(os.environ, {"WORKER_IDLE_SHUTDOWN_ENABLED": "off"}):
            assert idle_shutdown_enabled() is False

    def test_idle_shutdown_enabled_rejects_invalid_value(self) -> None:
        with patch.dict(os.environ, {"WORKER_IDLE_SHUTDOWN_ENABLED": "maybe"}):
            with self.assertRaises(ValueError):
                idle_shutdown_enabled()

    def test_idle_timeout_rejects_non_positive(self) -> None:
        with patch.dict(os.environ, {"WORKER_IDLE_TIMEOUT_SECONDS": "0"}):
            with self.assertRaises(ValueError):
                idle_timeout_seconds()
        with patch.dict(os.environ, {"WORKER_IDLE_TIMEOUT_SECONDS": "abc"}):
            with self.assertRaises(ValueError):
                idle_timeout_seconds()

    def test_should_shutdown_for_idle_respects_enabled_flag(self) -> None:
        with patch.dict(
            os.environ,
            {
                "WORKER_IDLE_SHUTDOWN_ENABLED": "false",
                "WORKER_IDLE_TIMEOUT_SECONDS": "60",
            },
        ):
            assert should_shutdown_for_idle(120.0) is False

        with patch.dict(
            os.environ,
            {
                "WORKER_IDLE_SHUTDOWN_ENABLED": "true",
                "WORKER_IDLE_TIMEOUT_SECONDS": "60",
            },
        ):
            assert should_shutdown_for_idle(59.0) is False
            assert should_shutdown_for_idle(60.1) is True
