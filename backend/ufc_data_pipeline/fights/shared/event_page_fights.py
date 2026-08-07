"""
Pure UFC Stats event-page fight-row parsing (no ORM).

Shared by Fights In Event and the Live Event Results Watcher.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

logger = logging.getLogger(__name__)

_FIGHT_ROW_CLASSES = frozenset(
    {
        "b-fight-details__table-row",
        "b-fight-details__table-row__hover",
        "js-fight-details-click",
    }
)


@dataclass(frozen=True)
class ParsedEventFight:
    """Immutable event-page fight record with no ORM dependencies."""

    fight_url: str
    bout: str
    weight_class: str
    fighter_a_name: str
    fighter_a_url: str
    fighter_b_name: str
    fighter_b_url: str
    is_completed: bool
    winner_name: str | None = None
    winner_url: str | None = None
    method: str | None = None
    round: int | None = None
    time: int | None = None
    round_format: str | None = None


def is_fight_table_row(tag) -> bool:
    """Return whether ``tag`` is a UFC Stats fight table row."""
    if getattr(tag, "name", None) != "tr":
        return False
    classes = tag.get("class") or []
    return _FIGHT_ROW_CLASSES.issubset(classes)


def bout_name_from_pair(fighter_a: str, fighter_b: str) -> str:
    """Create a bout label from two fighter display names."""
    return f"{fighter_a} vs. {fighter_b}"


def is_fight_row_completed(row: Tag) -> bool:
    """
    A fight is completed when the row has a result banner (``i.b-flag__inner`` with
    child ``i.b-flag__text``).
    """
    flag_inner = row.find("i", class_="b-flag__inner")
    if flag_inner is None:
        return False
    return flag_inner.find("i", class_="b-flag__text") is not None


def parse_fighter_pair_from_row(row: Tag) -> tuple[str, str, str, str] | None:
    """
    Extract the first two fighter names and profile URLs from a fight row.

    Returns ``(fighter_a, url_a, fighter_b, url_b)`` or ``None``.
    """
    name_els = row.find_all("a", class_="b-link b-link_style_black")
    if len(name_els) < 2:
        return None

    fighter_a = name_els[0].get_text(strip=True)
    fighter_b = name_els[1].get_text(strip=True)
    url_a = normalize_ufcstats_url(name_els[0].get("href"))
    url_b = normalize_ufcstats_url(name_els[1].get("href"))
    if not fighter_a or not fighter_b:
        return None

    return fighter_a, url_a, fighter_b, url_b


def _weight_class_td(row: Tag) -> Tag | None:
    """Return the left-aligned column that holds weight class."""
    for td in row.find_all(
        "td",
        class_=lambda c: c
        and "b-fight-details__table-col" in c
        and "l-page_align_left" in c,
    ):
        wc_p = td.find("p", class_="b-fight-details__table-text")
        if wc_p is None:
            continue
        # Skip the W/L column (contains fighter links).
        if wc_p.find("a", class_="b-link b-link_style_black"):
            continue
        return td
    return None


def weight_class_from_row(row: Tag) -> str:
    """Read weight class from the fight row's weight-class column."""
    wc_td = _weight_class_td(row)
    if wc_td is None:
        return ""

    wc_p = wc_td.find("p", class_="b-fight-details__table-text")
    if wc_p is None:
        return ""
    return wc_p.get_text(strip=True)


def _texts_from_col(td: Tag) -> list[str]:
    ps = td.find_all("p", class_="b-fight-details__table-text")
    return [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]


def time_to_seconds(time_text: str) -> int | None:
    """Convert ``M:SS`` fight time to total seconds (e.g. ``2:30`` -> 150)."""
    text = (time_text or "").strip()
    if not text or text == "--":
        return None
    try:
        minutes, seconds = map(int, text.split(":"))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        logger.warning("Could not parse fight time: %r", time_text)
        return None


def parse_event_page_result_fields(row: Tag) -> dict[str, str | int]:
    """
    Parse method, round, time, and optional round_format from trailing columns.

    Missing optional fields are omitted from the returned dict.
    """
    cols = row.find_all(
        "td",
        class_=lambda c: c and "b-fight-details__table-col" in c,
    )
    wc_td = _weight_class_td(row)
    if wc_td is None:
        return {}

    try:
        wc_index = cols.index(wc_td)
    except ValueError:
        return {}

    result: dict[str, str | int] = {}

    if wc_index + 1 < len(cols):
        method_texts = _texts_from_col(cols[wc_index + 1])
        if method_texts:
            result["method"] = method_texts[0]

    if wc_index + 2 < len(cols):
        round_texts = _texts_from_col(cols[wc_index + 2])
        if round_texts:
            try:
                result["round"] = int(round_texts[0])
            except ValueError:
                logger.warning(
                    "Could not parse fight round from row: %r", round_texts[0]
                )

    if wc_index + 3 < len(cols):
        time_texts = _texts_from_col(cols[wc_index + 3])
        if time_texts:
            seconds = time_to_seconds(time_texts[0])
            if seconds is not None:
                result["time"] = seconds

    if wc_index + 4 < len(cols):
        format_texts = _texts_from_col(cols[wc_index + 4])
        if format_texts:
            fmt = format_texts[0]
            if "rnd" in fmt.lower():
                result["round_format"] = fmt

    return result


def parse_event_fight_rows(soup: BeautifulSoup) -> list[ParsedEventFight]:
    """
    Parse every fight table row into immutable records.

    Rows without a fighter pair are skipped. Rows with an empty fight URL are
    still returned so callers can treat them as malformed identities.
    Completed rows may legitimately have no resolvable winner downstream; the
    event page still lists fighter A as the winner-column candidate.
    """
    records: list[ParsedEventFight] = []
    for row in soup.find_all(is_fight_table_row):
        pair = parse_fighter_pair_from_row(row)
        if pair is None:
            continue

        fighter_a, url_a, fighter_b, url_b = pair
        fight_url = normalize_ufcstats_url(row.get("data-link"))
        weight_class = weight_class_from_row(row)
        is_completed = is_fight_row_completed(row)

        winner_name: str | None = None
        winner_url: str | None = None
        method: str | None = None
        round_number: int | None = None
        time_seconds: int | None = None
        round_format: str | None = None

        if is_completed:
            # UFC Stats lists the winner first in the result column when present.
            winner_name = fighter_a
            winner_url = url_a or None
            fields = parse_event_page_result_fields(row)
            method = fields.get("method")  # type: ignore[assignment]
            round_number = fields.get("round")  # type: ignore[assignment]
            time_seconds = fields.get("time")  # type: ignore[assignment]
            round_format = fields.get("round_format")  # type: ignore[assignment]

        records.append(
            ParsedEventFight(
                fight_url=fight_url,
                bout=bout_name_from_pair(fighter_a, fighter_b),
                weight_class=weight_class,
                fighter_a_name=fighter_a,
                fighter_a_url=url_a,
                fighter_b_name=fighter_b,
                fighter_b_url=url_b,
                is_completed=is_completed,
                winner_name=winner_name,
                winner_url=winner_url,
                method=method,
                round=round_number,
                time=time_seconds,
                round_format=round_format,
            )
        )
    return records
