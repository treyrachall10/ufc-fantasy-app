"""Tests for score-fight service orchestration."""

from unittest import TestCase
from unittest.mock import patch

from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoreFightAPIError,
    ScoringSourceIncompleteError,
)
from ufc_data_pipeline.fantasy.score_fight.scoring import (
    ScoringInputError,
    calculate_fight_scoring,
)
from ufc_data_pipeline.fantasy.score_fight.service import process_score_fight


def _source_payload() -> dict:
    return {
        "fight": {
            "fight_id": 123,
            "fight_status": "COMPLETED",
            "method": "KO/TKO",
            "round": 1,
            "time": 120,
            "winner_id": 1,
        },
        "fighters": [
            {
                "fighter_id": 1,
                "rounds": [
                    {
                        "round_number": 1,
                        "kd": 1,
                        "sig_str_landed": 15,
                        "td_landed": 2,
                        "sub_att": 1,
                        "ctrl_time": 40,
                        "reversals": 1,
                    }
                ],
            },
            {
                "fighter_id": 2,
                "rounds": [
                    {
                        "round_number": 1,
                        "kd": 0,
                        "sig_str_landed": 8,
                        "td_landed": 0,
                        "sub_att": 0,
                        "ctrl_time": 10,
                        "reversals": 0,
                    }
                ],
            },
        ],
    }


class ScoreFightServiceTests(TestCase):
    @patch("ufc_data_pipeline.fantasy.score_fight.service.api_client")
    def test_fetches_scores_and_persists_once(self, mock_api_client) -> None:
        source = _source_payload()
        mock_api_client.fetch_scoring_source.return_value = source

        process_score_fight(123)

        mock_api_client.fetch_scoring_source.assert_called_once_with(123)
        mock_api_client.set_fight_scoring.assert_called_once_with(
            123,
            calculate_fight_scoring(source),
        )

    @patch("ufc_data_pipeline.fantasy.score_fight.service.api_client")
    def test_source_failure_does_not_persist(self, mock_api_client) -> None:
        mock_api_client.fetch_scoring_source.side_effect = (
            ScoringSourceIncompleteError("source incomplete")
        )

        with self.assertRaises(ScoringSourceIncompleteError):
            process_score_fight(123)

        mock_api_client.set_fight_scoring.assert_not_called()

    @patch("ufc_data_pipeline.fantasy.score_fight.service.api_client")
    def test_scoring_failure_does_not_persist(self, mock_api_client) -> None:
        source = _source_payload()
        source["fighters"].pop()
        mock_api_client.fetch_scoring_source.return_value = source

        with self.assertRaises(ScoringInputError):
            process_score_fight(123)

        mock_api_client.set_fight_scoring.assert_not_called()

    @patch("ufc_data_pipeline.fantasy.score_fight.service.api_client")
    def test_write_failure_propagates_after_single_attempt(
        self,
        mock_api_client,
    ) -> None:
        mock_api_client.fetch_scoring_source.return_value = _source_payload()
        mock_api_client.set_fight_scoring.side_effect = ScoreFightAPIError(
            "write failed"
        )

        with self.assertRaisesRegex(ScoreFightAPIError, "write failed"):
            process_score_fight(123)

        mock_api_client.fetch_scoring_source.assert_called_once_with(123)
        mock_api_client.set_fight_scoring.assert_called_once()
