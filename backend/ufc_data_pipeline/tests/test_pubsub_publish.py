"""
Tests for shared Pub/Sub JSON publish helper.
"""

from __future__ import annotations

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from ufc_data_pipeline.pubsub_publish import publish_json


class PublishJsonTests(TestCase):
    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "local-project"})
    @patch("ufc_data_pipeline.pubsub_publish.pubsub_v1.PublisherClient")
    def test_publish_json_encodes_payload_and_returns_message_id(
        self, publisher_cls: MagicMock
    ) -> None:
        publisher = publisher_cls.return_value
        publisher.topic_path.return_value = "projects/local-project/topics/fight-stats-jobs"
        future = MagicMock()
        future.result.return_value = "msg-42"
        publisher.publish.return_value = future

        message_id = publish_json(
            "fight-stats-jobs",
            {"fight_id": 1, "fight_url": "http://example.com/fight"},
        )

        assert message_id == "msg-42"
        publisher.topic_path.assert_called_once_with("local-project", "fight-stats-jobs")
        published_bytes = publisher.publish.call_args[0][1]
        assert b'"fight_id": 1' in published_bytes
        assert b"http://example.com/fight" in published_bytes

    def test_publish_json_requires_project(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                publish_json("fight-stats-jobs", {"fight_id": 1})
