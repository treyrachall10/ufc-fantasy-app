"""
Tests for career-stats score-fight Pub/Sub publish helper.
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fighters.career_stats import service


class CareerStatsScoreFightPublishTests(SimpleTestCase):
    @patch("ufc_data_pipeline.fighters.career_stats.service.publish_json")
    def test_publish_score_fight_job_sends_fight_id_payload(
        self, publish_mock
    ) -> None:
        publish_mock.return_value = "msg-abc"

        message_id = service.publish_score_fight_job(9350)

        assert message_id == "msg-abc"
        publish_mock.assert_called_once_with(
            service.SCORE_FIGHT_TOPIC_ID,
            {"fight_id": 9350},
            project_id=service.PROJECT_ID,
        )
