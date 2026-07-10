"""
Pure HTML parsing for UFC Stats fight detail pages (metadata and fight totals).
"""

from __future__ import annotations

import itertools
import re
from dataclasses import asdict, dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ParsedFightMetadata:
    """Parsed fight result metadata from a UFC Stats fight detail page."""

    event_name: str | None = None
    fighter_a_name: str | None = None
    fighter_b_name: str | None = None
    fighter_a_result: str | None = None
    fighter_b_result: str | None = None
    weight_class: str | None = None
    method: str | None = None
    round: int | None = None
    time_seconds: int | None = None
    round_format: str | None = None


@dataclass
class ParsedFighterFightStats:
    """Parsed fight-total stats for one fighter on a fight detail page."""

    fighter_name: str
    result: str | None = None
    kd: int | None = None
    sig_str_landed: int | None = None
    sig_str_attempted: int | None = None
    total_str_landed: int | None = None
    total_str_attempted: int | None = None
    td_landed: int | None = None
    td_attempted: int | None = None
    sub_att: int | None = None
    ctrl_time: int | None = None
    reversals: int | None = None
    head_str_landed: int | None = None
    head_str_attempted: int | None = None
    body_str_landed: int | None = None
    body_str_attempted: int | None = None
    leg_str_landed: int | None = None
    leg_str_attempted: int | None = None
    distance_str_landed: int | None = None
    distance_str_attempted: int | None = None
    clinch_str_landed: int | None = None
    clinch_str_attempted: int | None = None
    ground_str_landed: int | None = None
    ground_str_attempted: int | None = None


@dataclass
class ParsedFightPage:
    """Full fight-detail parse result for the current pipeline stage."""

    metadata: ParsedFightMetadata
    fighter_stats: list[ParsedFighterFightStats] = field(default_factory=list)


def _strip_label(text: str) -> str:
    """Remove a leading label prefix such as ``Round:`` from scraped text."""
    return re.sub(r"^(.+?): ?", "", text.strip())


def time_to_seconds(time_text: str | None) -> int | None:
    """
    Convert a fight time string like ``4:19`` to total seconds.
    Receives a time string and returns seconds or None.
    """
    text = (time_text or "").strip()
    if not text or text == "--":
        return None
    try:
        minutes, seconds = map(int, text.split(":"))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        return None


def parse_landed_attempted(value: str | None) -> tuple[int | None, int | None]:
    """
    Parse a landed/attempted string like ``19 of 32``.
    Receives a raw stat string and returns (landed, attempted) or (None, None).
    """
    text = (value or "").strip()
    if not text or text == "--":
        return None, None
    match = re.match(r"^(\d+)\s+of\s+(\d+)$", text)
    if match is None:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _parse_int(value: str | None) -> int | None:
    text = (value or "").strip()
    if not text or text == "--":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _extract_raw_fighter_stat_lists(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """
    Collect alternating fighter A/B cell values from fight-detail stat tables.
    Receives BeautifulSoup and returns two flat string lists.
    """
    fighter_a_stats: list[str] = []
    fighter_b_stats: list[str] = []

    # Loop through each totals/significant-strikes table cell on the fight page.
    for tag in soup.find_all("td", class_="b-fight-details__table-col"):
        # Each cell holds one value for fighter A and one for fighter B (even/odd).
        for index, p_text in enumerate(tag.find_all("p")):
            value = p_text.get_text(strip=True)
            if index % 2 == 0:
                fighter_a_stats.append(value)
            else:
                fighter_b_stats.append(value)

    return fighter_a_stats, fighter_b_stats


def _organise_stats_by_fighter_name(stats_from_soup: list[str]) -> list[list[str]]:
    """
    Group a flat fighter stat list into blocks that each start with the fighter name.
    Receives a flat list and returns a list of per-block lists.
    """
    if not stats_from_soup:
        return []

    fighter_name = stats_from_soup[0]
    organised: list[list[str]] = []
    for is_name, values in itertools.groupby(
        stats_from_soup, lambda value: value == fighter_name
    ):
        if is_name:
            organised.append([])
        organised[-1].extend(values)
    return organised


def _summary_totals_from_block(block: list[str]) -> dict[str, int | None]:
    """
    Map a totals summary block to FightStats field values.
    Block shape: [name, kd, sig, sig%, total, td, td%, sub, rev, ctrl].
    """
    if len(block) < 10:
        return {}

    sig_landed, sig_attempted = parse_landed_attempted(block[2])
    total_landed, total_attempted = parse_landed_attempted(block[4])
    td_landed, td_attempted = parse_landed_attempted(block[5])

    return {
        "kd": _parse_int(block[1]),
        "sig_str_landed": sig_landed,
        "sig_str_attempted": sig_attempted,
        "total_str_landed": total_landed,
        "total_str_attempted": total_attempted,
        "td_landed": td_landed,
        "td_attempted": td_attempted,
        "sub_att": _parse_int(block[7]),
        "reversals": _parse_int(block[8]),
        "ctrl_time": time_to_seconds(block[9]),
    }


def _summary_sig_strikes_from_block(block: list[str]) -> dict[str, int | None]:
    """
    Map a significant-strikes summary block to FightStats field values.
    Block shape: [name, sig, sig%, head, body, leg, distance, clinch, ground].
    """
    if len(block) < 9:
        return {}

    head_landed, head_attempted = parse_landed_attempted(block[3])
    body_landed, body_attempted = parse_landed_attempted(block[4])
    leg_landed, leg_attempted = parse_landed_attempted(block[5])
    distance_landed, distance_attempted = parse_landed_attempted(block[6])
    clinch_landed, clinch_attempted = parse_landed_attempted(block[7])
    ground_landed, ground_attempted = parse_landed_attempted(block[8])

    return {
        "head_str_landed": head_landed,
        "head_str_attempted": head_attempted,
        "body_str_landed": body_landed,
        "body_str_attempted": body_attempted,
        "leg_str_landed": leg_landed,
        "leg_str_attempted": leg_attempted,
        "distance_str_landed": distance_landed,
        "distance_str_attempted": distance_attempted,
        "clinch_str_landed": clinch_landed,
        "clinch_str_attempted": clinch_attempted,
        "ground_str_landed": ground_landed,
        "ground_str_attempted": ground_attempted,
    }


def _parse_fighter_summary_stats(
    organised: list[list[str]],
    result: str | None,
) -> ParsedFighterFightStats | None:
    """
    Build one fighter's fight-total stats from organised totals + sig-strike blocks.
    Receives organised blocks and optional result; returns ParsedFighterFightStats or None.
    """
    if len(organised) < 2:
        return None

    totals_summary = organised[0]
    sig_summary = organised[len(organised) // 2]
    fighter_name = (totals_summary[0] or "").strip()
    if not fighter_name:
        return None

    stats = ParsedFighterFightStats(fighter_name=fighter_name, result=result)
    for key, value in _summary_totals_from_block(totals_summary).items():
        setattr(stats, key, value)
    for key, value in _summary_sig_strikes_from_block(sig_summary).items():
        setattr(stats, key, value)
    return stats


def parse_fight_totals(
    soup: BeautifulSoup,
    metadata: ParsedFightMetadata | None = None,
) -> list[ParsedFighterFightStats]:
    """
    Parse per-fighter fight-total summary stats from a fight detail page.
    Receives BeautifulSoup and optional metadata for W/L/D; returns two fighter bundles.
    """
    fighter_a_raw, fighter_b_raw = _extract_raw_fighter_stat_lists(soup)
    fighter_a_organised = _organise_stats_by_fighter_name(fighter_a_raw)
    fighter_b_organised = _organise_stats_by_fighter_name(fighter_b_raw)

    result_a = metadata.fighter_a_result if metadata is not None else None
    result_b = metadata.fighter_b_result if metadata is not None else None

    bundles: list[ParsedFighterFightStats] = []
    fighter_a = _parse_fighter_summary_stats(fighter_a_organised, result_a)
    fighter_b = _parse_fighter_summary_stats(fighter_b_organised, result_b)
    if fighter_a is not None:
        bundles.append(fighter_a)
    if fighter_b is not None:
        bundles.append(fighter_b)
    return bundles


def parse_fight_page(soup: BeautifulSoup) -> ParsedFightPage:
    """
    Parse fight metadata and per-fighter totals from a fight detail page.
    Receives BeautifulSoup and returns ParsedFightPage.
    """
    metadata = parse_fight_metadata(soup)
    return ParsedFightPage(
        metadata=metadata,
        fighter_stats=parse_fight_totals(soup, metadata),
    )


def parse_fight_metadata(soup: BeautifulSoup) -> ParsedFightMetadata:
    """
    Parse fight result metadata from a UFC Stats fight detail page soup.
    Receives BeautifulSoup and returns ParsedFightMetadata.
    """
    metadata = ParsedFightMetadata()

    event_el = soup.find("h2", class_="b-content__title")
    if event_el is not None:
        metadata.event_name = event_el.get_text(strip=True) or None

    # Get the two fighter profile links/names listed in the fight header.
    person_links = soup.find_all("a", class_="b-link b-fight-details__person-link")
    if len(person_links) >= 2:
        metadata.fighter_a_name = person_links[0].get_text(strip=True) or None
        metadata.fighter_b_name = person_links[1].get_text(strip=True) or None

    outcomes: list[str] = []
    for person_div in soup.find_all("div", class_="b-fight-details__person"):
        for outcome_el in person_div.find_all("i"):
            outcomes.append(outcome_el.get_text(strip=True).upper())
    if len(outcomes) >= 2:
        metadata.fighter_a_result = outcomes[0] or None
        metadata.fighter_b_result = outcomes[1] or None

    # Get the weight class banner from the fight header.
    head_el = soup.find("div", class_="b-fight-details__fight-head")
    if head_el is not None:
        metadata.weight_class = head_el.get_text(strip=True) or None

    # Get the win method from the result summary row.
    method_el = soup.find("i", class_="b-fight-details__text-item_first")
    if method_el is not None:
        metadata.method = _strip_label(method_el.get_text()) or None

    # Get round, time, and round format from the result detail columns.
    text_paragraphs = soup.find_all("p", class_="b-fight-details__text")
    if text_paragraphs:
        detail_items = text_paragraphs[0].find_all("i", class_="b-fight-details__text-item")
        if len(detail_items) >= 1:
            metadata.round = _parse_int(_strip_label(detail_items[0].get_text()))
        if len(detail_items) >= 2:
            metadata.time_seconds = time_to_seconds(
                _strip_label(detail_items[1].get_text())
            )
        if len(detail_items) >= 3:
            metadata.round_format = _strip_label(detail_items[2].get_text()) or None

    return metadata


def metadata_to_api_payload(metadata: ParsedFightMetadata) -> dict:
    """
    Convert ParsedFightMetadata into a JSON-serializable API payload.
    Receives ParsedFightMetadata and returns a dict for SetFightResultMetadata.
    """
    payload: dict = {"fight_status": "COMPLETED"}

    field_map = {
        "method": metadata.method,
        "round": metadata.round,
        "time": metadata.time_seconds,
        "round_format": metadata.round_format,
        "weight_class": metadata.weight_class,
        "fighter_a_name": metadata.fighter_a_name,
        "fighter_b_name": metadata.fighter_b_name,
    }
    for key, value in field_map.items():
        if value is not None:
            payload[key] = value

    winner_name: str | None = None
    if metadata.fighter_a_result == "W":
        winner_name = metadata.fighter_a_name
    elif metadata.fighter_b_result == "W":
        winner_name = metadata.fighter_b_name
    if winner_name:
        payload["winner_name"] = winner_name

    return payload


def fighter_stats_to_api_payload(
    fighter_stats: list[ParsedFighterFightStats],
) -> dict:
    """
    Convert fighter fight-total bundles into a SetFightStatsTotals API payload.
    Receives a list of ParsedFighterFightStats and returns a dict with a fighters list.
    """
    fighters: list[dict] = []
    for stats in fighter_stats:
        row = asdict(stats)
        # API resolves fighters by name; keep only populated numeric/result fields.
        fighters.append({key: value for key, value in row.items() if value is not None})
    return {"fighters": fighters}
