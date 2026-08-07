"""Tests for score-fight subscriber idle and flow-control behavior."""

from concurrent.futures import TimeoutError
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fantasy.score_fight import consumer


class ScoreFightIdleShutdownTests(SimpleTestCase):
    def _subscriber(self, subscriber_cls: MagicMock, future: MagicMock) -> None:
        subscriber = subscriber_cls.return_value
        subscriber.__enter__.return_value = subscriber
        subscriber.__exit__.return_value = False
        subscriber.subscription_path.return_value = (
            "projects/local-project/subscriptions/score-fight-jobs-sub"
        )
        subscriber.subscribe.return_value = future

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.MAX_MESSAGES",
        4,
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.pubsub_v1.SubscriberClient"
    )
    @patch("ufc_data_pipeline.fantasy.score_fight.consumer.ensure_django")
    def test_idle_enabled_cancels_with_configured_flow_control(
        self,
        _ensure_django,
        subscriber_cls,
    ) -> None:
        future = MagicMock()
        future.result.side_effect = [TimeoutError(), None]
        self._subscriber(subscriber_cls, future)

        with (
            patch(
                "ufc_data_pipeline.fantasy.score_fight.consumer.monotonic",
                return_value=10.0,
            ),
            patch(
                "ufc_data_pipeline.fantasy.score_fight.consumer."
                "idle_check_interval_seconds",
                return_value=1,
            ),
            patch(
                "ufc_data_pipeline.fantasy.score_fight.consumer."
                "should_shutdown_for_idle",
                return_value=True,
            ),
        ):
            consumer._LAST_MESSAGE_AT = 0.0
            consumer.run_subscriber()

        future.cancel.assert_called_once()
        subscribe_kwargs = subscriber_cls.return_value.subscribe.call_args.kwargs
        self.assertEqual(subscribe_kwargs["flow_control"].max_messages, 4)

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.consumer.pubsub_v1.SubscriberClient"
    )
    @patch("ufc_data_pipeline.fantasy.score_fight.consumer.ensure_django")
    def test_idle_disabled_keeps_listening(
        self,
        _ensure_django,
        subscriber_cls,
    ) -> None:
        future = MagicMock()
        future.result.side_effect = [TimeoutError(), None]
        self._subscriber(subscriber_cls, future)

        with (
            patch(
                "ufc_data_pipeline.fantasy.score_fight.consumer."
                "idle_check_interval_seconds",
                return_value=1,
            ),
            patch(
                "ufc_data_pipeline.fantasy.score_fight.consumer."
                "should_shutdown_for_idle",
                return_value=False,
            ),
        ):
            consumer.run_subscriber()

        future.cancel.assert_not_called()
