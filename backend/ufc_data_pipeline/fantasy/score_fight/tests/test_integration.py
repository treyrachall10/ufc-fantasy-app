"""Integration coverage for the complete score-fight processing path."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import (
    FightScore,
    FightStats,
    Fighters,
    Fights,
    RoundScore,
    RoundStats,
)
from ufc_data_pipeline.fantasy.score_fight import consumer
from ufc_data_pipeline.models import ScoreFightJob


class ScoreFightIntegrationTests(TestCase):
    """Exercise enqueue contract, consumer, HTTP contracts, scoring, and writes."""

    def setUp(self) -> None:
        self.api_client = APIClient()
        _api_key, self.api_key = APIKey.objects.create_key(
            name="ufc_data_pipeline_service"
        )
        self.fighter_a = Fighters.objects.create(full_name="A One")
        self.fighter_b = Fighters.objects.create(full_name="B Two")

    def _create_fight(self, *, unscoreable: bool = False) -> Fights:
        fight = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            method="Could Not Continue" if unscoreable else "KO/TKO",
            round=1,
            time=120,
            winner=None if unscoreable else self.fighter_a,
        )
        stats_a = FightStats.objects.create(
            fight=fight,
            fighter=self.fighter_a,
            result="NC" if unscoreable else "W",
        )
        stats_b = FightStats.objects.create(
            fight=fight,
            fighter=self.fighter_b,
            result="NC" if unscoreable else "L",
        )
        RoundStats.objects.create(
            fight_stats=stats_a,
            round_number=1,
            kd=1,
            sig_str_landed=15,
            td_landed=2,
            sub_att=1,
            ctrl_time=40,
            reversals=1,
        )
        RoundStats.objects.create(
            fight_stats=stats_b,
            round_number=1,
            kd=0,
            sig_str_landed=8,
            td_landed=0,
            sub_att=0,
            ctrl_time=10,
            reversals=0,
        )
        return fight

    def _route_worker_request(self, method, url, **kwargs):
        """Route worker HTTP calls through DRF without mocking either endpoint."""
        path = urlsplit(url).path
        authorization = kwargs["headers"]["Authorization"]
        request_kwargs = {"HTTP_AUTHORIZATION": authorization}
        if method == "GET":
            response = self.api_client.get(path, **request_kwargs)
        elif method == "PATCH":
            response = self.api_client.patch(
                path,
                kwargs.get("json"),
                format="json",
                **request_kwargs,
            )
        else:
            raise AssertionError(f"Unexpected worker HTTP method: {method}")

        # DRF responses expose the requests.Response fields used by api_client
        # except ``ok``; add it so only the network boundary is substituted.
        response.ok = 200 <= response.status_code < 400
        return response

    def _enqueue_and_deliver(self, fight_id: int) -> MagicMock:
        """Capture the enqueue payload, then deliver it as Pub/Sub would."""
        published_payloads: list[dict] = []

        def capture_publish(topic_id: str, payload: dict) -> str:
            self.assertEqual(topic_id, "score-fight-jobs")
            published_payloads.append(payload)
            return "integration-message"

        with patch(
            "fantasy.management.commands.enqueue_score_fight.publish_json",
            side_effect=capture_publish,
        ):
            call_command(
                "enqueue_score_fight",
                "--fight-id",
                str(fight_id),
                stdout=StringIO(),
            )

        self.assertEqual(published_payloads, [{"fight_id": fight_id}])
        message = MagicMock()
        message.data = json.dumps(published_payloads[0]).encode("utf-8")
        consumer.callback(message)
        return message

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api_client.PIPELINE_API_BASE_URL",
        "http://testserver",
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api_client.requests.request"
    )
    def test_enqueue_to_completed_job_persists_both_fighters(
        self,
        request_mock,
    ) -> None:
        fight = self._create_fight()
        request_mock.side_effect = self._route_worker_request

        with patch(
            "ufc_data_pipeline.fantasy.score_fight.api_client."
            "PIPELINE_SERVICE_API_KEY",
            self.api_key,
        ):
            message = self._enqueue_and_deliver(fight.fight_id)

        job = ScoreFightJob.objects.get(fight_id=fight.fight_id)
        self.assertEqual(job.status, ScoreFightJob.Status.COMPLETED)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(
            set(
                FightScore.objects.filter(fight=fight).values_list(
                    "fighter_id",
                    flat=True,
                )
            ),
            {self.fighter_a.fighter_id, self.fighter_b.fighter_id},
        )
        self.assertEqual(
            set(
                RoundScore.objects.filter(
                    round_stats__fight_stats__fight=fight
                ).values_list(
                    "round_stats__fight_stats__fighter_id",
                    flat=True,
                )
            ),
            {self.fighter_a.fighter_id, self.fighter_b.fighter_id},
        )
        self.assertEqual(request_mock.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in request_mock.call_args_list],
            ["GET", "PATCH"],
        )
        message.ack.assert_called_once()
        message.nack.assert_not_called()

    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api_client.PIPELINE_API_BASE_URL",
        "http://testserver",
    )
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.api_client.requests.request"
    )
    def test_unscoreable_fight_fails_without_writing_scores(
        self,
        request_mock,
    ) -> None:
        fight = self._create_fight(unscoreable=True)
        request_mock.side_effect = self._route_worker_request

        with patch(
            "ufc_data_pipeline.fantasy.score_fight.api_client."
            "PIPELINE_SERVICE_API_KEY",
            self.api_key,
        ):
            message = self._enqueue_and_deliver(fight.fight_id)

        job = ScoreFightJob.objects.get(fight_id=fight.fight_id)
        self.assertEqual(job.status, ScoreFightJob.Status.FAILED)
        self.assertIn("unscoreable", job.error_msg)
        self.assertFalse(FightScore.objects.filter(fight=fight).exists())
        self.assertFalse(
            RoundScore.objects.filter(
                round_stats__fight_stats__fight=fight
            ).exists()
        )
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[0], "GET")
        message.ack.assert_called_once()
        message.nack.assert_not_called()
