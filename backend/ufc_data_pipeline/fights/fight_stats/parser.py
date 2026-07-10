"""
Pure HTML parsing for UFC Stats fight detail pages (metadata only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


def _parse_int(value: str | None) -> int | None:
    text = (value or "").strip()
    if not text or text == "--":
        return None
    try:
        return int(text)
    except ValueError:
        return None


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
