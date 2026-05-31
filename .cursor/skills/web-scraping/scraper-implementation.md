# Scraper Implementation Skill

Use this skill when implementing scraper code, parser code, or scraping-related helper functions.

## Core Rule

Use Playwright for web requests and scraping.

Do not use simple request-based scraping unless explicitly instructed.

## Why

Use Playwright because some websites load important page content with JavaScript. Playwright loads the rendered page, which helps avoid missing data that would not appear in raw HTML.

## Implementation Pattern

When loading a page:

1. Open the page with Playwright.
2. Wait for a selector that proves the page loaded correctly.
3. Get the rendered HTML with `page.content()`.
4. Close the browser.
5. Parse the rendered HTML with BeautifulSoup.
6. Add retry logic around the page load when the scrape can fail from timeouts or temporary browser/page issues.

Example:

```python
def fetch_page_soup(url: str) -> BeautifulSoup:
    """
    Load a page with Playwright and return parsed soup.
    Receives a page URL and returns BeautifulSoup for the rendered HTML.
    """
    # Try to load the page with Playwright so JavaScript-rendered content is available.
    for attempt in Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    ):
        with attempt:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                page.goto(url, timeout=PLAYWRIGHT_TIMEOUT_S * 1000)

                page.wait_for_selector(
                    PAGE_READY_SELECTOR,
                    timeout=PLAYWRIGHT_TIMEOUT_S * 1000,
                )

                html = page.content()
                browser.close()

            return BeautifulSoup(html, "html.parser")

    raise RuntimeError(f"Failed to load page: {url}")
```

## Scraping Comments

For scraping logic, add a short comment that explains exactly what the selector is grabbing from the website in plain English.

The comment should describe the real page element or data being scraped, not just the HTML tag or class name.

Good examples:

```python
# Get the two fighter profile links/names listed in this fight row.
fighter_links = row.find_all("a", class_="b-link b-link_style_black")

# Get the completed-fight result banner from this fight row.
result_banner = row.find("i", class_="b-flag__text")

# Get the method, round, and time result columns from this fight row.
result_columns = row.find_all("td", class_="b-fight-details__table-col")
```

Bad examples:

```python
# Get links.
fighter_links = row.find_all("a", class_="b-link b-link_style_black")

# Find i tag.
result_banner = row.find("i", class_="b-flag__text")

# Get td columns.
result_columns = row.find_all("td", class_="b-fight-details__table-col")
```

## Comment Focus

When possible, scraping comments should explain the exact data being extracted, such as:

* fighter name
* fighter profile URL
* winner name
* fight method
* round
* time
* event date
* fight status
* result banner
* profile details

## Keep Scraping Logic Clear

Scraper functions should be easy to read and should separate the major steps:

1. Load the page.
2. Wait for the page to be ready.
3. Parse the rendered HTML.
4. Extract the needed fields.
5. Return structured data.

Do not hide scraping selectors inside unclear helper functions unless the helper name clearly explains what page data is being extracted.
