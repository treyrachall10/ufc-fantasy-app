"""Tests for the pure fight-scoring interface."""

from unittest import TestCase

from ufc_data_pipeline.fantasy.score_fight.scoring import (
    ScoringInputError,
    UnscoreableFightError,
    calculate_fight_scoring,
    calculate_round_score,
    score_round_finish,
    score_time,
)


class FightScoringTests(TestCase):
    def test_scores_round_categories_and_total(self):
        round_stats = {
            "round_number": 1,
            "kd": 1,
            "sig_str_landed": 15,
            "td_landed": 2,
            "sub_att": 1,
            "ctrl_time": 40,
            "reversals": 1,
        }

        result = calculate_round_score(1, round_stats)

        self.assertEqual(
            result,
            {
                "fighter_id": 1,
                "round_number": 1,
                "points_knockdowns": 10,
                "points_sig_str_landed": 15,
                "points_td_landed": 6,
                "points_sub_att": 2,
                "points_ctrl_time": 2.0,
                "points_reversals": 1,
                "round_total_points": 36.0,
            },
        )

    def test_scores_winner_and_loser_fight_totals(self):
        source = _fight_source(
            winner_id=1,
            finish_round=2,
            finish_time=100,
            fighter_round_points={1: 10, 2: 7},
        )

        result = calculate_fight_scoring(source)

        self.assertEqual(
            result["fight_scores"],
            [
                {
                    "fighter_id": 1,
                    "points_win": 20,
                    "points_round": 20,
                    "points_time": 6.0,
                    "fight_total_points": 56.0,
                },
                {
                    "fighter_id": 2,
                    "points_win": 0,
                    "points_round": 0,
                    "points_time": 0,
                    "fight_total_points": 7.0,
                },
            ],
        )

    def test_draw_gives_both_fighters_round_points_only(self):
        source = _fight_source(
            winner_id=None,
            method="Draw",
            fighter_round_points={1: 12, 2: 9},
        )

        result = calculate_fight_scoring(source)

        self.assertEqual(
            result["fight_scores"],
            [
                {
                    "fighter_id": 1,
                    "points_win": 0,
                    "points_round": 0,
                    "points_time": 0,
                    "fight_total_points": 12.0,
                },
                {
                    "fighter_id": 2,
                    "points_win": 0,
                    "points_round": 0,
                    "points_time": 0,
                    "fight_total_points": 9.0,
                },
            ],
        )

    def test_no_contest_is_unscoreable(self):
        source = _fight_source(
            winner_id=None,
            method="Could Not Continue",
        )

        with self.assertRaisesRegex(UnscoreableFightError, "Could Not Continue"):
            calculate_fight_scoring(source)

    def test_requires_exactly_two_fighters(self):
        source = _fight_source(winner_id=1)
        source["fighters"].pop()

        with self.assertRaisesRegex(ScoringInputError, "exactly two fighters"):
            calculate_fight_scoring(source)

    def test_preserves_finish_round_and_time_bonuses(self):
        self.assertEqual(score_round_finish(round=1, time=60), 30)
        self.assertEqual(score_round_finish(2, 60), 20)
        self.assertEqual(score_round_finish(3, 300), 10)
        self.assertEqual(score_round_finish(5, 300), 0)
        self.assertEqual(score_time(100), 6.0)

    def test_preserves_no_winner_decision_allowlist(self):
        for method in ("Decision - Split", "Decision - Majority"):
            with self.subTest(method=method):
                result = calculate_fight_scoring(
                    _fight_source(winner_id=None, method=method)
                )
                self.assertTrue(
                    all(score["points_win"] == 0 for score in result["fight_scores"])
                )

    def test_rejects_missing_round_values(self):
        source = _fight_source(winner_id=1)
        source["fighters"][0]["rounds"][0]["kd"] = None

        with self.assertRaisesRegex(ScoringInputError, "Invalid round stats"):
            calculate_fight_scoring(source)


def _fight_source(
    *,
    winner_id,
    finish_round: int = 3,
    finish_time: int = 300,
    method: str = "KO/TKO",
    fighter_round_points: dict[int, int] | None = None,
) -> dict:
    points = fighter_round_points or {1: 0, 2: 0}
    return {
        "fight": {
            "fight_id": 123,
            "winner_id": winner_id,
            "method": method,
            "round": finish_round,
            "time": finish_time,
        },
        "fighters": [
            {
                "fighter_id": fighter_id,
                "rounds": [
                    {
                        "round_number": 1,
                        "kd": 0,
                        "sig_str_landed": round_points,
                        "td_landed": 0,
                        "sub_att": 0,
                        "ctrl_time": 0,
                        "reversals": 0,
                    }
                ],
            }
            for fighter_id, round_points in points.items()
        ],
    }
