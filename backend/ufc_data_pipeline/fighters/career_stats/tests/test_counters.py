"""
Unit tests for pure career-stats counters.
"""

from django.test import SimpleTestCase

from ufc_data_pipeline.fighters.career_stats.counters import calculate_career_stats


FIGHTER_ID = 100
OPPONENT_ID = 200

EXPECTED_KEYS = {
    "total_fights",
    "wins",
    "losses",
    "draws",
    "ko_tko_wins",
    "tko_doctor_stoppage_wins",
    "submission_wins",
    "unanimous_decision_wins",
    "split_decision_wins",
    "majority_decision_wins",
    "dq_wins",
    "ko_tko_losses",
    "tko_doctor_stoppage_losses",
    "submission_losses",
    "unanimous_decision_losses",
    "split_decision_losses",
    "majority_decision_losses",
    "dq_losses",
    "sig_str_landed",
    "sig_str_attempted",
    "total_str_landed",
    "total_str_attempted",
    "td_landed",
    "td_attempted",
    "sub_att",
    "ctrl_time",
    "reversals",
    "total_fight_time",
    "head_str_landed",
    "head_str_attempted",
    "body_str_landed",
    "body_str_attempted",
    "leg_str_landed",
    "leg_str_attempted",
    "distance_str_landed",
    "distance_str_attempted",
    "clinch_str_landed",
    "clinch_str_attempted",
    "ground_str_landed",
    "ground_str_attempted",
    "sig_str_landed_opp",
    "sig_str_attempted_opp",
    "td_landed_opp",
    "td_attempted_opp",
    "ctrl_time_opp",
}


def _row(**overrides) -> dict:
    base = {
        "fight_id": 1,
        "result": "W",
        "method": "KO/TKO",
        "winner_id": FIGHTER_ID,
        "round": 1,
        "time": 60,
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
    base.update(overrides)
    return base


class CareerStatsCountersTests(SimpleTestCase):
    def test_empty_history_returns_complete_zero_dict(self) -> None:
        values = calculate_career_stats(FIGHTER_ID, [])
        assert set(values.keys()) == EXPECTED_KEYS
        assert all(v == 0 for v in values.values())

    def test_sums_additive_fields_and_null_coalescing(self) -> None:
        values = calculate_career_stats(
            FIGHTER_ID,
            [
                _row(fight_id=1, sig_str_landed=10, sig_str_landed_opp=4),
                _row(
                    fight_id=2,
                    sig_str_landed=None,
                    sig_str_landed_opp=None,
                    ctrl_time=None,
                    winner_id=OPPONENT_ID,
                    result="L",
                    method="Submission",
                ),
            ],
        )
        assert values["sig_str_landed"] == 10
        assert values["sig_str_landed_opp"] == 4
        assert values["ctrl_time"] == 30
        assert values["total_fights"] == 2
        assert values["wins"] == 1
        assert values["losses"] == 1

    def test_win_loss_draw_rules(self) -> None:
        values = calculate_career_stats(
            FIGHTER_ID,
            [
                _row(fight_id=1, winner_id=FIGHTER_ID, result="W", method="KO/TKO"),
                _row(
                    fight_id=2,
                    winner_id=OPPONENT_ID,
                    result="L",
                    method="Submission",
                ),
                _row(
                    fight_id=3,
                    winner_id=None,
                    result="D",
                    method="Decision - Majority",
                ),
            ],
        )
        assert values["wins"] == 1
        assert values["losses"] == 1
        assert values["draws"] == 1
        assert values["total_fights"] == 3

    def test_each_supported_method_bucket_long_and_short(self) -> None:
        rows = [
            _row(fight_id=1, method="KO/TKO", winner_id=FIGHTER_ID, result="W"),
            _row(fight_id=2, method="TKO", winner_id=OPPONENT_ID, result="L"),
            _row(
                fight_id=3,
                method="TKO - Doctor's Stoppage",
                winner_id=FIGHTER_ID,
                result="W",
            ),
            _row(fight_id=4, method="SUB", winner_id=OPPONENT_ID, result="L"),
            _row(
                fight_id=5,
                method="Decision - Unanimous",
                winner_id=FIGHTER_ID,
                result="W",
            ),
            _row(fight_id=6, method="S-DEC", winner_id=OPPONENT_ID, result="L"),
            _row(
                fight_id=7,
                method="Decision - Majority",
                winner_id=FIGHTER_ID,
                result="W",
            ),
            _row(fight_id=8, method="DQ", winner_id=OPPONENT_ID, result="L"),
            _row(fight_id=9, method="U-DEC", winner_id=FIGHTER_ID, result="W"),
            _row(fight_id=10, method="Submission", winner_id=OPPONENT_ID, result="L"),
        ]
        values = calculate_career_stats(FIGHTER_ID, rows)

        assert values["ko_tko_wins"] == 1
        assert values["ko_tko_losses"] == 1
        assert values["tko_doctor_stoppage_wins"] == 1
        assert values["submission_losses"] == 2  # SUB + Submission
        assert values["unanimous_decision_wins"] == 2  # long + U-DEC
        assert values["split_decision_losses"] == 1
        assert values["majority_decision_wins"] == 1
        assert values["dq_losses"] == 1
        assert values["wins"] == 5
        assert values["losses"] == 5

    def test_nc_with_null_result_is_excluded(self) -> None:
        values = calculate_career_stats(
            FIGHTER_ID,
            [
                _row(
                    fight_id=1,
                    method="Could Not Continue",
                    result=None,
                    winner_id=None,
                    sig_str_landed=99,
                    round=3,
                    time=100,
                ),
                _row(
                    fight_id=2,
                    method="Overturned",
                    result=None,
                    winner_id=None,
                    sig_str_landed=50,
                ),
                _row(fight_id=3, method="KO/TKO", sig_str_landed=10),
            ],
        )
        assert values["total_fights"] == 1
        assert values["wins"] == 1
        assert values["sig_str_landed"] == 10
        assert values["draws"] == 0

    def test_unknown_method_counts_wl_skips_bucket_and_logs(self) -> None:
        with self.assertLogs(
            "ufc_data_pipeline.fighters.career_stats.counters",
            level="WARNING",
        ) as captured:
            values = calculate_career_stats(
                FIGHTER_ID,
                [
                    _row(
                        fight_id=1,
                        method="Alien Abduction",
                        winner_id=FIGHTER_ID,
                        result="W",
                    ),
                ],
            )

        assert values["wins"] == 1
        assert values["total_fights"] == 1
        assert values["ko_tko_wins"] == 0
        assert any("Unknown method" in message for message in captured.output)

    def test_total_fight_time_formula(self) -> None:
        # Round 3, 90s remaining in round → (3-1)*300 + 90 = 690
        values = calculate_career_stats(
            FIGHTER_ID,
            [
                _row(fight_id=1, round=3, time=90),
                _row(fight_id=2, round=1, time=45),
                _row(fight_id=3, round=None, time=None, winner_id=None, result="D"),
            ],
        )
        assert values["total_fight_time"] == 690 + 45 + 0
        assert values["draws"] == 1
