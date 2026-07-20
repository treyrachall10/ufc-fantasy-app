"""Tests for shared Fights In Event Pub/Sub publisher."""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.shared import fights_in_event_publisher as publisher


class PublishFightsInEventTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.shared.fights_in_event_publisher.publish_json",
        return_value="msg-9",
    )
    def test_publishes_existing_fights_in_event_payload(self, publish_json) -> None:
        message_id = publisher.publish_fights_in_event(
            12,
            "http://ufcstats.com/event-details/abc",
        )

        assert message_id == "msg-9"
        publish_json.assert_called_once_with(
            publisher.FIGHTS_IN_EVENT_TOPIC_ID,
            {
                "url": "http://ufcstats.com/event-details/abc",
                "event_id": 12,
            },
            project_id=publisher.PROJECT_ID,
        )

    @patch(
        "ufc_data_pipeline.shared.fights_in_event_publisher.publish_json",
        return_value="msg-10",
    )
    def test_optional_metadata_is_backward_compatible(self, publish_json) -> None:
        message_id = publisher.publish_fights_in_event(
            12,
            "http://ufcstats.com/event-details/abc",
            reason="MISSING_FIGHT",
            fingerprint="abc123",
        )
        assert message_id == "msg-10"
        publish_json.assert_called_once_with(
            publisher.FIGHTS_IN_EVENT_TOPIC_ID,
            {
                "url": "http://ufcstats.com/event-details/abc",
                "event_id": 12,
                "reason": "MISSING_FIGHT",
                "fingerprint": "abc123",
            },
            project_id=publisher.PROJECT_ID,
        )

    def test_rejects_empty_event_url(self) -> None:
        with self.assertRaises(ValueError):
            publisher.publish_fights_in_event(12, "")
