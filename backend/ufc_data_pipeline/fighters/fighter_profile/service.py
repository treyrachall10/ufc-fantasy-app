"""
Scrape and process fighter profile jobs using Playwright and the main API service.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tenacity import Retrying, stop_after_attempt, wait_exponential

from ufc_data_pipeline.fighters.fighter_profile import api_client
from ufc_data_pipeline.fighters.fighter_profile.config import (
    PLAYWRIGHT_TIMEOUT_S,
    PROFILE_PAGE_READY_SELECTOR,
)
from ufc_data_pipeline.fighters.fighter_profile.parser import (
    parse_fighter_profile,
    profile_data_to_api_payload,
)

logger = logging.getLogger(__name__)


def fetch_profile_soup(profile_url: str) -> BeautifulSoup:
    """
    Load a fighter profile page with Playwright and return parsed soup.
    Receives a profile URL and returns BeautifulSoup for the rendered HTML.
    """
    # Try to load the profile page with Playwright so JavaScript-rendered content is available.
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    ):
        with attempt:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(profile_url, timeout=PLAYWRIGHT_TIMEOUT_S * 1000)
                page.wait_for_selector(
                    PROFILE_PAGE_READY_SELECTOR,
                    timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
                )
                html = page.content()
                browser.close()
            return BeautifulSoup(html, "html.parser")
    raise RuntimeError(f"Failed to load fighter profile page: {profile_url}")


def process_fighter_profile(fighter_id: int, fighter_url: str) -> None:
    """
    Scrape a fighter profile page and update fighter metadata via the API service.
    Receives fighter_id and fighter_url; returns nothing; raises on failure.
    """
    soup = fetch_profile_soup(fighter_url)
    profile_data = parse_fighter_profile(soup)
    payload = profile_data_to_api_payload(profile_data)
    if not payload:
        raise RuntimeError("No fighter profile fields parsed from page")

    api_client.update_fighter_profile(fighter_id, payload)
    logger.info("Updated fighter profile fighter_id=%s", fighter_id)
