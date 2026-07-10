"""
Tests for fight-stats subscriber idle shutdown behavior.
"""

from __future__ import annotations

import os
from concurrent.futures import TimeoutError
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.fight_stats import consumer


class FightStatsIdleShutdownTests(SimpleTestCase):
    def _mock_subscriber(self, subscriber_cls: MagicMock, future: MagicMock) -> None:
        subscriber = subscriber_cls.return_value
        subscriber.__enter__.return_value = subscriber
        subscriber.__exit__.return_value = False
        subscriber.subscription_path.return_value = (
            "projects/local-project/subscriptions/sub"
        )
        subscriber.subscribe.return_value = future

    @patch.dict(
        os.environ,
        {
            "GOOGLE_CLOUD_PROJECT": "local-project",
            "PUBSUB_FIGHT_STATS_SUBSCRIPTION": "fight-stats-jobs-sub",
            "WORKER_IDLE_SHUTDOWN_ENABLED": "true",
            "WORKER_IDLE_TIMEOUT_SECONDS": "1",
            "WORKER_IDLE_CHECK_INTERVAL_SECONDS": "1",
        },
    )
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.pubsub_v1.SubscriberClient")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.ensure_django")
    def test_run_subscriber_shuts_down_when_idle_enabled(
        self, _ensure_django: MagicMock, subscriber_cls: MagicMock
    ) -> None:
        future = MagicMock()
        future.result.side_effect = [TimeoutError(), None]
        self._mock_subscriber(subscriber_cls, future)

        with patch(
            "ufc_data_pipeline.fights.fight_stats.consumer.monotonic",
            return_value=10.0,
        ):
            consumer._LAST_MESSAGE_AT = 0.0
            consumer.run_subscriber()

        future.cancel.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "GOOGLE_CLOUD_PROJECT": "local-project",
            "PUBSUB_FIGHT_STATS_SUBSCRIPTION": "fight-stats-jobs-sub",
            "WORKER_IDLE_SHUTDOWN_ENABLED": "false",
            "WORKER_IDLE_CHECK_INTERVAL_SECONDS": "1",
        },
    )
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.pubsub_v1.SubscriberClient")
    @patch("ufc_data_pipeline.fights.fight_stats.consumer.ensure_django")
    def test_run_subscriber_keeps_listening_when_idle_disabled(
        self, _ensure_django: MagicMock, subscriber_cls: MagicMock
    ) -> None:
        future = MagicMock()
        future.result.side_effect = [TimeoutError(), None]
        self._mock_subscriber(subscriber_cls, future)

        with patch(
            "ufc_data_pipeline.fights.fight_stats.consumer.monotonic",
            return_value=999.0,
        ):
            consumer._LAST_MESSAGE_AT = 0.0
            consumer.run_subscriber()

        future.cancel.assert_not_called()
