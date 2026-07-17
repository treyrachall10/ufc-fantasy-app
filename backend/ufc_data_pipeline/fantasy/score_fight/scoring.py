"""Pure fantasy scoring calculations with no I/O dependencies."""

from __future__ import annotations

from typing import Any, Mapping


class ScoringInputError(ValueError):
    """Raised when a scoring-source payload is structurally invalid."""


class UnscoreableFightError(ValueError):
    """Raised when existing scoring rules intentionally skip a fight outcome."""


# Preserve the batch scorer's exact no-winner allowlist.
_DRAW_METHODS = frozenset({"Decision - Split", "Decision - Majority", "Draw"})


def score_knockdowns(knockdowns: int) -> int:
    return knockdowns * 10


def score_td_landed(takedowns_landed: int) -> int:
    return takedowns_landed * 3


def score_sub_att(submission_attempts: int) -> int:
    return submission_attempts * 2


def score_ctrl_time(control_time: int) -> float:
    return control_time * 0.05


def score_win(winner: Any, fighter: Any) -> int:
    return 20 if winner == fighter else 0


def score_round_finish(round: int, time: int) -> int:
    # Preserve the existing full-distance five-round exception.
    if round == 5 and time == 300:
        return 0
    if round == 1:
        return 30
    if round == 2:
        return 20
    return 10


def score_time(time: int) -> float:
    return (300 - time) * 0.03


def calculate_round_score(
    fighter_id: int, round_stats: Mapping[str, Any]
) -> dict[str, Any]:
    """Calculate one complete RoundScore payload row."""
    try:
        points = {
            "points_knockdowns": score_knockdowns(round_stats["kd"]),
            "points_sig_str_landed": round_stats["sig_str_landed"],
            "points_td_landed": score_td_landed(round_stats["td_landed"]),
            "points_sub_att": score_sub_att(round_stats["sub_att"]),
            "points_ctrl_time": score_ctrl_time(round_stats["ctrl_time"]),
            "points_reversals": round_stats["reversals"],
        }
        return {
            "fighter_id": int(fighter_id),
            "round_number": int(round_stats["round_number"]),
            **points,
            "round_total_points": sum(points.values()),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ScoringInputError(f"Invalid round stats: {exc}") from exc


def calculate_fight_scoring(source: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Calculate score payload rows from one fight scoring-source snapshot."""
    try:
        fight = source["fight"]
        fighters = source["fighters"]
        winner_id = fight["winner_id"]
    except (KeyError, TypeError) as exc:
        raise ScoringInputError(f"Invalid scoring source: {exc}") from exc

    if len(fighters) != 2:
        raise ScoringInputError("Scoring source must contain exactly two fighters")

    # No-contests and unsupported no-winner outcomes must not write zeroed scores.
    if winner_id is None and fight["method"] not in _DRAW_METHODS:
        raise UnscoreableFightError(
            f"Fight outcome is unscoreable: {fight['method']}"
        )

    round_scores: list[dict[str, Any]] = []
    round_totals: dict[int, float] = {}
    for fighter in fighters:
        for round_stats in fighter["rounds"]:
            fighter_id = int(fighter["fighter_id"])
            round_score = calculate_round_score(fighter_id, round_stats)
            round_scores.append(round_score)
            round_totals[fighter_id] = round_totals.get(fighter_id, 0) + round_score[
                "round_total_points"
            ]

    fight_scores: list[dict[str, Any]] = []
    for fighter in fighters:
        fighter_id = int(fighter["fighter_id"])
        is_winner = winner_id is not None and int(winner_id) == fighter_id
        points_win = score_win(winner_id, fighter_id)
        points_round = (
            score_round_finish(fight["round"], fight["time"]) if is_winner else 0
        )
        points_time = score_time(fight["time"]) if is_winner else 0
        fight_scores.append(
            {
                "fighter_id": fighter_id,
                "points_win": points_win,
                "points_round": points_round,
                "points_time": points_time,
                "fight_total_points": (
                    round_totals[fighter_id]
                    + points_win
                    + points_round
                    + points_time
                ),
            }
        )

    return {"fight_scores": fight_scores, "round_scores": round_scores}
