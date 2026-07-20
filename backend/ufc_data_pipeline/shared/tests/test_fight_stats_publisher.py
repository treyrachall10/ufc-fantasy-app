"""Tests for shared Fight Stats Pub/Sub publisher."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.shared import fight_stats_publisher as publisher


class PublishFightStatsJobTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.shared.fight_stats_publisher.publish_json",
        return_value="msg-1",
    )
    def test_publishes_normalized_payload(self, publish_json) -> None:
        message_id = publisher.publish_fight_stats_job(
            42,
            "http://ufcstats.com/fight-details/abc/",
        )

        assert message_id == "msg-1"
        publish_json.assert_called_once_with(
            publisher.FIGHT_STATS_TOPIC_ID,
            {
                "fight_id": 42,
                "fight_url": "http://ufcstats.com/fight-details/abc",
            },
            project_id=publisher.PROJECT_ID,
        )

    def test_rejects_empty_fight_url(self) -> None:
        with self.assertRaises(ValueError):
            publisher.publish_fight_stats_job(42, "")
