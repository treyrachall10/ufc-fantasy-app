"""
Tests for pipeline enqueue management commands.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class EnqueueCommandTests(SimpleTestCase):
    @patch("fantasy.management.commands.enqueue_fight_stats.publish_json")
    def test_enqueue_fight_stats_publishes_payload(self, publish_mock) -> None:
        publish_mock.return_value = "msg-1"
        out = StringIO()

        call_command(
            "enqueue_fight_stats",
            "--fight-id",
            "7",
            "--fight-url",
            "http://ufcstats.com/fight-details/abc",
            stdout=out,
        )

        publish_mock.assert_called_once_with(
            "fight-stats-jobs",
            {
                "fight_id": 7,
                "fight_url": "http://ufcstats.com/fight-details/abc",
            },
        )
        assert "msg-1" in out.getvalue()

    def test_enqueue_fight_stats_rejects_invalid_url(self) -> None:
        with self.assertRaises(CommandError):
            call_command(
                "enqueue_fight_stats",
                "--fight-id",
                "7",
                "--fight-url",
                "not-a-url",
            )

    @patch("fantasy.management.commands.enqueue_fight_import.publish_json")
    def test_enqueue_fight_import_publishes_payload(self, publish_mock) -> None:
        publish_mock.return_value = "msg-2"

        call_command(
            "enqueue_fight_import",
            "--event-id",
            "3",
            "--url",
            "http://ufcstats.com/event-details/xyz",
        )

        publish_mock.assert_called_once_with(
            "fights-in-event",
            {
                "url": "http://ufcstats.com/event-details/xyz",
                "event_id": 3,
            },
        )

    @patch("fantasy.management.commands.enqueue_fighter_profile.publish_json")
    def test_enqueue_fighter_profile_publishes_payload(self, publish_mock) -> None:
        publish_mock.return_value = "msg-3"

        call_command(
            "enqueue_fighter_profile",
            "--fighter-id",
            "9",
            "--fighter-url",
            "http://ufcstats.com/fighter-details/abc",
        )

        publish_mock.assert_called_once_with(
            "fighter-profile-jobs",
            {
                "fighter_id": 9,
                "fighter_url": "http://ufcstats.com/fighter-details/abc",
            },
        )

    @patch("fantasy.management.commands.enqueue_score_fight.publish_json")
    def test_enqueue_score_fight_publishes_payload(self, publish_mock) -> None:
        publish_mock.return_value = "msg-4"
        out = StringIO()

        call_command("enqueue_score_fight", "--fight-id", "12", stdout=out)

        publish_mock.assert_called_once_with(
            "score-fight-jobs",
            {"fight_id": 12},
        )
        assert "msg-4" in out.getvalue()

    def test_enqueue_score_fight_rejects_non_positive_fight_id(self) -> None:
        with self.assertRaises(CommandError):
            call_command("enqueue_score_fight", "--fight-id", "0")
