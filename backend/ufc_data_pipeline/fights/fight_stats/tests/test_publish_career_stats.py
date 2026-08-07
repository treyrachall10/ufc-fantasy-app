"""
Tests for fight-stats career-stats Pub/Sub publish helper.
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.fight_stats import service


class FightStatsCareerStatsPublishTests(SimpleTestCase):
    @patch("ufc_data_pipeline.fights.fight_stats.service.publish_json")
    def test_publish_career_stats_job_sends_fight_id_payload(
        self, publish_mock
    ) -> None:
        publish_mock.return_value = "msg-abc"

        message_id = service.publish_career_stats_job(9350)

        assert message_id == "msg-abc"
        publish_mock.assert_called_once_with(
            service.CAREER_STATS_TOPIC_ID,
            {"fight_id": 9350},
            project_id=service.PROJECT_ID,
        )
