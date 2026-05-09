
"""
Parse fight rows from a UFC Stats *event detail* page (completed card).
"""

from __future__ import annotations

import json
import logging
import os

from bs4 import BeautifulSoup
from google.cloud import pubsub_v1

from fantasy.models import Fighters, Fights
from shared.utils import normalize_name

logger = logging.getLogger(__name__)

_FIGHT_ROW_CLASSES = frozenset(
    {
        "b-fight-details__table-row",
        "b-fight-details__table-row__hover",
        "js-fight-details-click",
    }
)

def is_fight_table_row(tag) -> bool:
    """
    Check if the tag is a fight table row.
    """
    if getattr(tag, "name", None) != "tr":
        return False
    classes = tag.get("class") or []
    return _FIGHT_ROW_CLASSES.issubset(classes)


def bout_name_from_pair(fighter_a: str, fighter_b: str) -> str:
    """
    Create a bout name from a pair of fighter names.
    """
    return f"{fighter_a} vs. {fighter_b}"



def _enqueue_fighter_profile_sync(fighter: Fighters) -> None:
    """Publish a fighter profile scrape job (same shape as fights-in-event: url + id)."""
    profile_url = (fighter.profile_url or "").strip()
    if not profile_url:
        return
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    topic_id = os.getenv("PUBSUB_FIGHTER_PROFILE_TOPIC")
    if not project_id or not topic_id:
        return
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic_id)
        publisher.publish(
            topic_path,
            json.dumps(
                {"url": profile_url, "fighter_id": fighter.fighter_id}
            ).encode("utf-8"),
        )
    except Exception:
        logger.exception(
            "Failed to publish fighter profile job fighter_id=%s",
            fighter.fighter_id,
        )


def ensure_fighters_exist(fighter_name_url_pairs: list[tuple[str, str]]) -> None:
    """
    Ensure each fighter exists by ``normalized_name`` (bulk-insert missing rows).

    ``fighter_name_url_pairs`` is ``(display_name, profile_page_url)`` from the event
    table; the URL is stored on ``Fighters.profile_url`` and sent to the profile sync
    topic when a row is new or had an empty profile URL.
    """
    first_raw_by_norm: dict[str, str] = {}
    profile_url_by_norm: dict[str, str] = {}
    for raw, profile_url in fighter_name_url_pairs:
        raw = (raw or "").strip()
        if not raw:
            continue
        norm = normalize_name(raw)
        if not norm:
            continue
        first_raw_by_norm.setdefault(norm, raw)
        pu = (profile_url or "").strip()
        if pu:
            profile_url_by_norm.setdefault(norm, pu)

    if not first_raw_by_norm:
        return

    norms = list(first_raw_by_norm.keys())
    existing_by_norm: dict[str, Fighters] = {
        f.normalized_name: f
        for f in Fighters.objects.filter(normalized_name__in=norms)
        if f.normalized_name
    }

    missing = [
        Fighters(
            full_name=first_raw_by_norm[n],
            normalized_name=n,
            profile_url=profile_url_by_norm.get(n, ""),
        )
        for n in norms
        if n not in existing_by_norm
    ]
    if missing:
        created: list[Fighters] = Fighters.objects.bulk_create(missing)
        for fighter in created:
            #_enqueue_fighter_profile_sync(fighter)
            print(f"Fighter created: {fighter.full_name}")

    to_update: list[Fighters] = []
    for n in norms:
        if n not in existing_by_norm:
            continue
        fighter = existing_by_norm[n]
        new_url = profile_url_by_norm.get(n, "")
        if new_url and not (fighter.profile_url or "").strip():
            fighter.profile_url = new_url
            to_update.append(fighter)

    if to_update:
        Fighters.objects.bulk_update(to_update, ["profile_url"])
        for fighter in to_update:
            #_enqueue_fighter_profile_sync(fighter)
            print(f"Fighter updated: {fighter.full_name}")


def scrape_fights_in_event(soup: BeautifulSoup, event_id: int) -> list[Fights]:
    """
    Extract fight rows, resolve fighters, and return unsaved ``Fights`` rows for ``event``.

    Each row's ``data-link`` is stored on ``Fights.url`` for a later detail scrape.
    """
    rows = soup.find_all(is_fight_table_row) # get all fight table rows
    fighter_name_url_pairs: list[tuple[str, str]] = []
    pending: list[Fights] = []

    # loop through all rows in the soup
    for row in rows:
        name_els = row.find_all("a", class_="b-link b-link_style_black") # get all fighter names
        if len(name_els) < 2:
            continue

        fighter_a = name_els[0].get_text(strip=True)
        fighter_b = name_els[1].get_text(strip=True)
        url_a = name_els[0].get("href")
        url_b = name_els[1].get("href")
        if not fighter_a or not fighter_b:
            continue

        # get weight class from table row
        wc_td = row.find_all(
            "td",
            class_=lambda c: c
            and "b-fight-details__table-col" in c
            and "l-page_align_left" in c,
        )
        wc_td = wc_td[1]
        weight_class = ""
        if wc_td is not None:
            wc_p = wc_td.find("p", class_="b-fight-details__table-text") # get weight class text
            if wc_p is not None:
                weight_class = wc_p.get_text(strip=True)

        fighter_name_url_pairs.extend(
            ((fighter_a, url_a), (fighter_b, url_b))
        )

        # create fight object and add to pending list
        pending.append(
            Fights(
                event_id=event_id,
                url=(row.get("data-link") or "").strip(),
                bout=bout_name_from_pair(fighter_a, fighter_b),
                weight_class=weight_class,
            )
        )

    ensure_fighters_exist(fighter_name_url_pairs)
    return pending
