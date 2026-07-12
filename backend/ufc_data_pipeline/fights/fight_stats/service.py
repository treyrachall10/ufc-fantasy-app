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
    CAREER_STATS_TOPIC_ID,
    FIGHT_PAGE_READY_SELECTOR,
    PLAYWRIGHT_TIMEOUT_S,
    PROJECT_ID,
)
from ufc_data_pipeline.fights.fight_stats.parser import (
    fighter_stats_to_api_payload,
    metadata_to_api_payload,
    parse_fight_page,
    round_stats_to_api_payload,
)
from ufc_data_pipeline.pubsub_publish import publish_json

logger = logging.getLogger(__name__)


# Receives a fight URL and returns BeautifulSoup for the rendered HTML.
# This function loads a fight detail page with Playwright for parsing.
def fetch_fight_soup(fight_url: str) -> BeautifulSoup:
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    ):
        # Loop through Playwright fetch attempts until the page loads or retries are exhausted.
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


# Receives fight_id and fight_url; returns nothing; raises on failure.
# This function scrapes a fight detail page and upserts metadata, FightStats, and RoundStats via API.
def process_fight_stats(fight_id: int, fight_url: str) -> None:
    logger.info(
        "Started fight stats job fight_id=%s fight_url=%s",
        fight_id,
        fight_url,
    )

    soup = fetch_fight_soup(fight_url)
    # Try to parse the fight detail HTML into metadata, totals, and round stats.
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

    # Loop through each fighter bundle to confirm per-round stats were parsed.
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
        "Completed API updates for fight stats job fight_id=%s fight_url=%s",
        fight_id,
        fight_url,
    )


# Receives a fight_id and returns the Pub/Sub message id.
# This function publishes the career-stats handoff after a successful fight-stats scrape.
def publish_career_stats_job(fight_id: int) -> str:
    message_id = publish_json(
        CAREER_STATS_TOPIC_ID,
        {"fight_id": fight_id},
        project_id=PROJECT_ID,
    )
    logger.info(
        "Published career-stats job fight_id=%s topic=%s message_id=%s",
        fight_id,
        CAREER_STATS_TOPIC_ID,
        message_id,
    )
    return message_id
