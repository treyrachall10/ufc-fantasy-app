"""
Pure career-stats counters: source fight rows → FighterCareerStats values dict.

No HTTP, ORM, or Pub/Sub. Logging only for unknown / skipped method buckets.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Sequence

logger = logging.getLogger(__name__)

# Additive FightStats fields summed into FighterCareerStats (null → 0).
_ADDITIVE_FIELDS: tuple[str, ...] = (
    "sig_str_landed",
    "sig_str_attempted",
    "total_str_landed",
    "total_str_attempted",
    "td_landed",
    "td_attempted",
    "sub_att",
    "ctrl_time",
    "reversals",
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
)

_METHOD_BUCKETS: tuple[str, ...] = (
    "ko_tko",
    "tko_doctor_stoppage",
    "submission",
    "unanimous_decision",
    "split_decision",
    "majority_decision",
    "dq",
)

# Normalized method string → bucket key (win/loss field prefix without _wins/_losses).
_METHOD_ALIASES: dict[str, str] = {
    # Long UFC Stats forms
    "ko/tko": "ko_tko",
    "tko - doctor's stoppage": "tko_doctor_stoppage",
    "tko - doctors stoppage": "tko_doctor_stoppage",
    "submission": "submission",
    "decision - unanimous": "unanimous_decision",
    "decision - split": "split_decision",
    "decision - majority": "majority_decision",
    "dq": "dq",
    # Short aliases
    "tko": "ko_tko",
    "ko": "ko_tko",
    "sub": "submission",
    "u-dec": "unanimous_decision",
    "udec": "unanimous_decision",
    "s-dec": "split_decision",
    "sdec": "split_decision",
    "m-dec": "majority_decision",
    "mdec": "majority_decision",
}

_NC_METHODS: frozenset[str] = frozenset(
    {
        "could not continue",
        "cnc",
        "overturned",
    }
)


def _empty_career_stats() -> dict[str, int]:
    """Return a zeroed dict matching SetFighterCareerStats fields."""
    values: dict[str, int] = {
        "total_fights": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
    }
    for bucket in _METHOD_BUCKETS:
        values[f"{bucket}_wins"] = 0
        values[f"{bucket}_losses"] = 0
    for field in _ADDITIVE_FIELDS:
        values[field] = 0
    values["total_fight_time"] = 0
    return values


def _normalize_method(method: str | None) -> str | None:
    if method is None:
        return None
    text = " ".join(str(method).strip().lower().split())
    return text or None


def _is_nc_excluded(row: Mapping[str, Any]) -> bool:
    """NC: Could Not Continue / Overturned (etc.) with null FightStats.result."""
    method = _normalize_method(row.get("method"))
    if method is None or method not in _NC_METHODS:
        return False
    return row.get("result") is None


def _fight_seconds(row: Mapping[str, Any]) -> int:
    """Per included fight: (round - 1) * 300 + time."""
    round_number = row.get("round")
    time_seconds = row.get("time")
    if round_number is None and time_seconds is None:
        return 0
    rounds = int(round_number) if round_number is not None else 1
    elapsed = int(time_seconds) if time_seconds is not None else 0
    return max(rounds - 1, 0) * 300 + elapsed


def _as_int(value: Any) -> int:
    if value is None:
        return 0
    return int(value)


def _method_bucket(method: str | None) -> str | None:
    normalized = _normalize_method(method)
    if normalized is None:
        return None
    return _METHOD_ALIASES.get(normalized)


def _classify_outcome(fighter_id: int, row: Mapping[str, Any]) -> str:
    """
    Return 'W', 'L', or 'D'.

    Draw: winner_id is null (NC rows already excluded). Prefer result == 'D'
    when present; null winner still counts as draw per locked rules.
    Win/Loss: from winner_id vs fighter_id.
    """
    winner_id = row.get("winner_id")
    if winner_id is None:
        return "D"
    if int(winner_id) == int(fighter_id):
        return "W"
    return "L"


def calculate_career_stats(
    fighter_id: int,
    fights: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """
    Recalculate full FighterCareerStats values for one fighter from source rows.

    :param fighter_id: Fighter whose history is being aggregated
    :param fights: Completed-fight source rows (CareerStatsSource fight dicts)
    :return: Complete values dict suitable for SetFighterCareerStats
    """
    totals: MutableMapping[str, int] = _empty_career_stats()

    for row in fights:
        if _is_nc_excluded(row):
            continue

        outcome = _classify_outcome(fighter_id, row)
        totals["total_fights"] += 1
        if outcome == "W":
            totals["wins"] += 1
        elif outcome == "L":
            totals["losses"] += 1
        else:
            totals["draws"] += 1

        # Method buckets only for wins/losses; unknown → log and skip bucket.
        if outcome in ("W", "L"):
            bucket = _method_bucket(row.get("method"))
            if bucket is None:
                logger.warning(
                    "Unknown method for career-stats bucket; counted W/L only. "
                    "fighter_id=%s fight_id=%s method=%r",
                    fighter_id,
                    row.get("fight_id"),
                    row.get("method"),
                )
            else:
                suffix = "wins" if outcome == "W" else "losses"
                totals[f"{bucket}_{suffix}"] += 1

        for field in _ADDITIVE_FIELDS:
            totals[field] += _as_int(row.get(field))
        totals["total_fight_time"] += _fight_seconds(row)

    return dict(totals)
