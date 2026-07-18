"""
Tests for Event Watcher fights-in-event publisher.
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.events.event_watcher.publisher import publish_fights_in_event


class PublishFightsInEventTests(SimpleTestCase):
    @patch("ufc_data_pipeline.events.event_watcher.publisher.publish_json")
    def test_publishes_existing_fights_in_event_payload(self, publish_mock) -> None:
        publish_mock.return_value = "msg-9"

        message_id = publish_fights_in_event(
            12,
            "http://ufcstats.com/event-details/abc",
        )

        assert message_id == "msg-9"
        publish_mock.assert_called_once_with(
            "fights-in-event",
            {
                "url": "http://ufcstats.com/event-details/abc",
                "event_id": 12,
            },
            project_id="local-project",
        )
