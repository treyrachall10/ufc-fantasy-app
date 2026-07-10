"""
Scrape and process fight stats jobs using Playwright and the main API service.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tenacity import Retrying, stop_after_attempt, wait_exponential

from ufc_data_pipeline.fights.fight_stats import api_client
from ufc_data_pipeline.fights.fight_stats.config import (
    FIGHT_PAGE_READY_SELECTOR,
    PLAYWRIGHT_TIMEOUT_S,
)
from ufc_data_pipeline.fights.fight_stats.parser import (
    fighter_stats_to_api_payload,
    metadata_to_api_payload,
    parse_fight_page,
    round_stats_to_api_payload,
)

logger = logging.getLogger(__name__)


def fetch_fight_soup(fight_url: str) -> BeautifulSoup:
    """
    Load a fight detail page with Playwright and return parsed soup.
    Receives a fight URL and returns BeautifulSoup for the rendered HTML.
    """
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    ):
        with attempt:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(fight_url, timeout=PLAYWRIGHT_TIMEOUT_S * 1000)
                page.wait_for_selector(
                    FIGHT_PAGE_READY_SELECTOR,
                    timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
                )
                html = page.content()
                browser.close()
            return BeautifulSoup(html, "html.parser")
    raise RuntimeError(f"Failed to load fight detail page: {fight_url}")


def process_fight_stats(fight_id: int, fight_url: str) -> None:
    """
    Scrape a fight detail page and upsert metadata, FightStats, and RoundStats via API.
    Receives fight_id and fight_url; returns nothing; raises on failure.
    """
    soup = fetch_fight_soup(fight_url)
    try:
        parsed = parse_fight_page(soup)
    except ValueError as exc:
        logger.error("Fight stats parse failed fight_id=%s: %s", fight_id, exc)
        raise RuntimeError(str(exc)) from exc

    metadata_payload = metadata_to_api_payload(parsed.metadata)
    if len(metadata_payload) <= 1:
        raise RuntimeError("No fight metadata fields parsed from page")

    if len(parsed.fighter_stats) != 2:
        raise RuntimeError(
            f"Expected two fighter fight-stat bundles, got {len(parsed.fighter_stats)}"
        )

    for stats in parsed.fighter_stats:
        if not stats.rounds:
            raise RuntimeError(
                f"No per-round stats found for fighter={stats.fighter_name}"
            )

    stats_payload = fighter_stats_to_api_payload(parsed.fighter_stats)
    rounds_payload = round_stats_to_api_payload(parsed.fighter_stats)

    api_client.update_fight_result_metadata(fight_id, metadata_payload)
    api_client.upsert_fight_stats_totals(fight_id, stats_payload)
    api_client.upsert_round_stats(fight_id, rounds_payload)
    logger.info(
        "Updated fight metadata, FightStats totals, and RoundStats fight_id=%s",
        fight_id,
    )
