"""
Parse the UFC Stats completed-events listing.

Fetch HTML from ``ufc_data_pipeline.events.event_page_sync.config.URL``, build a
``BeautifulSoup``, and pass it to :func:`parse_completed_events_after`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime

from bs4 import BeautifulSoup

_DATE_FORMAT = "%B %d, %Y"

@dataclass(frozen=True)
class Event:
    """One completed event row from the listing page."""

    name: str
    url: str
    location: str
    event_date: Date


def parse_completed_events_after(soup: BeautifulSoup, date: Date) -> list[Event]:
    """
    Walk event table rows and return events strictly after ``date``.

    Rows are ``<tr>`` elements with class ``b-statistics__table-row_type_first`` or
    ``b-statistics__table-row``. For each row, reads the date from
    ``b-statistics__date``; skips the row if missing or if the event date is on or
    before ``date``. For rows past the cutoff, reads name and URL from
    ``a.b-link.b-link_style_black`` if present, otherwise
    ``a.b-link.b-link_style_white``, and location from the big-padding statistics
    column.

    Parameters
    ----------
    soup
        Parsed HTML of the completed-events page (see ``config.URL``).
    date
        Only events with a parsed date **after** this calendar day are returned.

    Returns
    -------
    list[Event]
        Events in document order (newest-first on the live site).
    """
    events: list[Event] = []

    # loop through all rows in the soup
    for row in soup.find_all(
        "tr",
        # find rows with class 'b-statistics__table-row_type_first' or 'b-statistics__table-row'
        class_=lambda c: c
        and (
            "b-statistics__table-row_type_first" in c
            or "b-statistics__table-row" in c
        ),
    ):
        date_el = row.find("span", class_="b-statistics__date") # find date element in row
        if date_el is None:
            continue

        raw_date = date_el.get_text(strip=True) # get text of date element
        try:
            event_date = datetime.strptime(raw_date, _DATE_FORMAT).date()
        except ValueError:
            continue

        # if event date is on or before the date, skip
        if event_date <= date:
            continue

        link = row.find("a", class_="b-link b-link_style_black") # find link element in row
        if link is None:
            link = row.find("a", class_="b-link b-link_style_white") # find link element in row
        if link is None:
            continue

        name = link.get_text(strip=True) # get text of link element
        href = link.get("href", "").strip() # get href of link element
        if not name or not href:
            continue

        loc_el = row.find(
            "td",
            class_="b-statistics__table-col b-statistics__table-col_style_big-top-padding",
        )
        if loc_el is None:
            continue

        # get text of location element
        location = loc_el.get_text(strip=True)
        events.append(
            Event(name=name, url=href, location=location, event_date=event_date)
        )

    return events