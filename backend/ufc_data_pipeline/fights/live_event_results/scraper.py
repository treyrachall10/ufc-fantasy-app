"""
Fetch one UFC Stats event detail page for the Live Event Results Watcher.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from ufc_data_pipeline.fights.live_event_results.config import (
    EVENT_PAGE_READY_SELECTOR,
    PLAYWRIGHT_TIMEOUT_S,
)


def fetch_event_soup(event_url: str) -> BeautifulSoup:
    """
    Load one event detail page with Playwright and return parsed soup.

    Raises on failure. Callers own retry policy in later issues; this helper
    performs a single attempt so the watcher can assert one page fetch per run.
    """
    url = (event_url or "").strip()
    if not url:
        raise ValueError("event_url is empty")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, timeout=PLAYWRIGHT_TIMEOUT_S * 1000)
            page.wait_for_selector(
                EVENT_PAGE_READY_SELECTOR,
                timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
            )
            html = page.content()
        finally:
            browser.close()
    return BeautifulSoup(html, "html.parser")
