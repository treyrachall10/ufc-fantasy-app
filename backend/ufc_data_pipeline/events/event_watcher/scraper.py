"""
Fetch the UFC Stats completed-events listing for the Event Watcher.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tenacity import Retrying, stop_after_attempt, wait_exponential

from ufc_data_pipeline.events.event_watcher.config import (
    COMPLETED_EVENTS_URL,
    LISTING_PAGE_READY_SELECTOR,
    PLAYWRIGHT_TIMEOUT_S,
)


def fetch_listing_soup() -> BeautifulSoup:
    """
    Load the completed-events listing with Playwright and return parsed soup.
    Receives no parameters; returns BeautifulSoup; raises on failure.
    """
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    ):
        with attempt:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page()
                    page.goto(
                        COMPLETED_EVENTS_URL,
                        timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
                    )
                    page.wait_for_selector(
                        LISTING_PAGE_READY_SELECTOR,
                        timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
                    )
                    html = page.content()
                finally:
                    browser.close()
            return BeautifulSoup(html, "html.parser")
    raise RuntimeError(f"Failed to load completed-events listing: {COMPLETED_EVENTS_URL}")
