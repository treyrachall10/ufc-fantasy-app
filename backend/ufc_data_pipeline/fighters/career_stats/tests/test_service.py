"""
Tests for career-stats service orchestration (mocked api_client).
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fighters.career_stats.counters import calculate_career_stats
from ufc_data_pipeline.fighters.career_stats.service import process_career_stats


FIGHTER_A = 100
FIGHTER_B = 200


def _source_payload() -> dict:
    return {
        "fighters": [
            {
                "fighter_id": FIGHTER_A,
                "fights": [
                    {
                        "fight_id": 1,
                        "result": "W",
                        "method": "KO/TKO",
                        "winner_id": FIGHTER_A,
                        "round": 2,
                        "time": 90,
                        "sig_str_landed": 10,
                        "sig_str_attempted": 20,
                        "total_str_landed": 12,
                        "total_str_attempted": 22,
                        "td_landed": 1,
                        "td_attempted": 2,
                        "sub_att": 0,
                        "ctrl_time": 30,
                        "reversals": 0,
                        "head_str_landed": 5,
                        "head_str_attempted": 10,
                        "body_str_landed": 3,
                        "body_str_attempted": 5,
                        "leg_str_landed": 2,
                        "leg_str_attempted": 5,
                        "distance_str_landed": 8,
                        "distance_str_attempted": 15,
                        "clinch_str_landed": 1,
                        "clinch_str_attempted": 3,
                        "ground_str_landed": 1,
                        "ground_str_attempted": 2,
                        "sig_str_landed_opp": 4,
                        "sig_str_attempted_opp": 9,
                        "td_landed_opp": 0,
                        "td_attempted_opp": 1,
                        "ctrl_time_opp": 10,
                    }
                ],
            },
            {
                "fighter_id": FIGHTER_B,
                "fights": [
                    {
                        "fight_id": 1,
                        "result": "L",
                        "method": "KO/TKO",
                        "winner_id": FIGHTER_A,
                        "round": 2,
                        "time": 90,
                        "sig_str_landed": 4,
                        "sig_str_attempted": 9,
                        "total_str_landed": 5,
                        "total_str_attempted": 10,
                        "td_landed": 0,
                        "td_attempted": 1,
                        "sub_att": 0,
                        "ctrl_time": 10,
                        "reversals": 0,
                        "head_str_landed": 2,
                        "head_str_attempted": 4,
                        "body_str_landed": 1,
                        "body_str_attempted": 2,
                        "leg_str_landed": 1,
                        "leg_str_attempted": 3,
                        "distance_str_landed": 3,
                        "distance_str_attempted": 7,
                        "clinch_str_landed": 1,
                        "clinch_str_attempted": 1,
                        "ground_str_landed": 0,
                        "ground_str_attempted": 1,
                        "sig_str_landed_opp": 10,
                        "sig_str_attempted_opp": 20,
                        "td_landed_opp": 1,
                        "td_attempted_opp": 2,
                        "ctrl_time_opp": 30,
                    }
                ],
            },
        ]
    }


class CareerStatsServiceTests(SimpleTestCase):
    @patch("ufc_data_pipeline.fighters.career_stats.service.api_client")
    def test_process_loads_source_recalculates_and_upserts_both(
        self,
        mock_api_client,
    ) -> None:
        source = _source_payload()
        mock_api_client.fetch_career_stats_source.return_value = source

        process_career_stats(1)

        mock_api_client.fetch_career_stats_source.assert_called_once_with(1)
        assert mock_api_client.upsert_fighter_career_stats.call_count == 2

        expected_a = calculate_career_stats(
            FIGHTER_A,
            source["fighters"][0]["fights"],
        )
        expected_b = calculate_career_stats(
            FIGHTER_B,
            source["fighters"][1]["fights"],
        )
        mock_api_client.upsert_fighter_career_stats.assert_any_call(
            FIGHTER_A,
            expected_a,
        )
        mock_api_client.upsert_fighter_career_stats.assert_any_call(
            FIGHTER_B,
            expected_b,
        )

    @patch("ufc_data_pipeline.fighters.career_stats.service.api_client")
    def test_repeated_run_upserts_same_full_replace_payload(
        self,
        mock_api_client,
    ) -> None:
        source = _source_payload()
        mock_api_client.fetch_career_stats_source.return_value = source

        process_career_stats(1)
        first_calls = [
            call.args for call in mock_api_client.upsert_fighter_career_stats.call_args_list
        ]

        mock_api_client.upsert_fighter_career_stats.reset_mock()
        process_career_stats(1)
        second_calls = [
            call.args for call in mock_api_client.upsert_fighter_career_stats.call_args_list
        ]

        assert first_calls == second_calls
        assert first_calls[0][1]["wins"] == 1
        assert first_calls[0][1]["sig_str_landed"] == 10

    @patch("ufc_data_pipeline.fighters.career_stats.service.api_client")
    def test_empty_fighters_raises_for_consumer_retry(
        self,
        mock_api_client,
    ) -> None:
        mock_api_client.fetch_career_stats_source.return_value = {"fighters": []}

        with self.assertRaises(RuntimeError):
            process_career_stats(1)

        mock_api_client.upsert_fighter_career_stats.assert_not_called()

    @patch("ufc_data_pipeline.fighters.career_stats.service.api_client")
    def test_api_failure_propagates(self, mock_api_client) -> None:
        mock_api_client.fetch_career_stats_source.side_effect = RuntimeError(
            "API GET failed"
        )

        with self.assertRaises(RuntimeError):
            process_career_stats(1)
