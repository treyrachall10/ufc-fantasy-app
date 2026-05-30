
"""
Parse fight rows from a UFC Stats *event detail* page (completed card).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from fantasy.models import Fighters, Fights
from shared.utils import normalize_name
from ufc_data_pipeline.fighters.fighter_profile.enqueue import enqueue_fighter_profile_sync

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


def is_fight_row_completed(row: Tag) -> bool:
    """
    A fight is completed when the row has a result banner (``i.b-flag__inner`` with
    child ``i.b-flag__text``).
    """
    flag_inner = row.find("i", class_="b-flag__inner")
    if flag_inner is None:
        return False
    return flag_inner.find("i", class_="b-flag__text") is not None


def parse_fighter_pair_from_row(row: Tag) -> tuple[str, str, str, str] | None:
    """
    Extract the first two fighter names and profile URLs from a fight row.

    Mirrors event-page name extraction in ``parse_fighter_details`` (``a.b-link.b-link_style_black``).
    """
    name_els = row.find_all("a", class_="b-link b-link_style_black")
    if len(name_els) < 2:
        return None

    fighter_a = name_els[0].get_text(strip=True)
    fighter_b = name_els[1].get_text(strip=True)
    url_a = (name_els[0].get("href") or "").strip()
    url_b = (name_els[1].get("href") or "").strip()
    if not fighter_a or not fighter_b:
        return None

    return fighter_a, url_a, fighter_b, url_b


def _weight_class_td(row: Tag) -> Tag | None:
    """
    Return the left-aligned column that holds weight class (no fighter link in its text cell).
    """
    for td in row.find_all(
        "td",
        class_=lambda c: c
        and "b-fight-details__table-col" in c
        and "l-page_align_left" in c,
    ):
        wc_p = td.find("p", class_="b-fight-details__table-text")
        if wc_p is None:
            continue
        if wc_p.find("a", class_="b-link b-link_style_black"): # Skip if in the W/L column (no weight class)
            continue
        return td
    return None


def weight_class_from_row(row: Tag) -> str:
    """
    Read weight class from the fight row's weight-class column.
    """
    wc_td = _weight_class_td(row)
    if wc_td is None:
        return ""

    wc_p = wc_td.find("p", class_="b-fight-details__table-text")
    if wc_p is None:
        return ""
    return wc_p.get_text(strip=True)


def _texts_from_col(td: Tag) -> list[str]:
    ps = td.find_all("p", class_="b-fight-details__table-text")
    return [p.get_text(strip=True) for p in ps if p.get_text(strip=True)]


def time_to_seconds(time_text: str) -> int | None:
    """
    Convert ``M:SS`` fight time to total seconds (e.g. ``2:30`` -> 150).
    """
    text = (time_text or "").strip()
    if not text or text == "--":
        return None
    try:
        minutes, seconds = map(int, text.split(":"))
        return minutes * 60 + seconds
    except (ValueError, AttributeError):
        logger.warning("Could not parse fight time: %r", time_text)
        return None


def parse_event_page_result_fields(row: Tag) -> dict[str, str | int]:
    """
    Parse method, round, time, and optional round_format from trailing event-page columns.

    Missing optional fields are omitted from the returned dict.
    """
    cols = row.find_all(
        "td",
        class_=lambda c: c and "b-fight-details__table-col" in c,
    )
    wc_td = _weight_class_td(row)
    if wc_td is None:
        return {}

    try:
        wc_index = cols.index(wc_td)
    except ValueError:
        return {}

    result: dict[str, str | int] = {}

    if wc_index + 1 < len(cols):
        method_texts = _texts_from_col(cols[wc_index + 1])
        if method_texts:
            result["method"] = method_texts[0]

    if wc_index + 2 < len(cols):
        round_texts = _texts_from_col(cols[wc_index + 2])
        if round_texts:
            try:
                result["round"] = int(round_texts[0])
            except ValueError:
                logger.warning(
                    "Could not parse fight round from row: %r", round_texts[0]
                )

    if wc_index + 3 < len(cols):
        time_texts = _texts_from_col(cols[wc_index + 3])
        if time_texts:
            seconds = time_to_seconds(time_texts[0])
            if seconds is not None:
                result["time"] = seconds

    if wc_index + 4 < len(cols):
        format_texts = _texts_from_col(cols[wc_index + 4])
        if format_texts:
            fmt = format_texts[0]
            if "rnd" in fmt.lower():
                result["round_format"] = fmt

    return result


def build_fighters_lookup(
    normalized_names: list[str],
    profile_urls: list[str],
) -> tuple[dict[str, Fighters], dict[str, Fighters]]:
    """
    Batch-load fighters by normalized name and profile URL for winner resolution.
    """
    norms = [n for n in normalized_names if n]
    urls = [u for u in profile_urls if u]

    fighters_by_norm: dict[str, Fighters] = {
        f.normalized_name: f
        for f in Fighters.objects.filter(normalized_name__in=norms)
        if f.normalized_name
    }

    fighters_by_url: dict[str, Fighters] = {}
    if urls:
        for fighter in Fighters.objects.filter(profile_url__in=urls):
            url = (fighter.profile_url or "").strip()
            if url:
                fighters_by_url[url] = fighter

    return fighters_by_norm, fighters_by_url


def resolve_winner_fighter(
    name: str,
    profile_url: str,
    fighters_by_norm: dict[str, Fighters],
    fighters_by_url: dict[str, Fighters],
) -> Fighters | None:
    """
    Resolve winner to a ``Fighters`` row; prefer profile URL when available.
    """
    url = (profile_url or "").strip()
    if url:
        fighter = fighters_by_url.get(url)
        if fighter is not None:
            return fighter

    norm = normalize_name(name)
    if norm:
        return fighters_by_norm.get(norm)
    return None


def _enqueue_fighter_profile_sync(fighter: Fighters) -> None:
    """
    Create a fighter profile scrape job and publish it to Pub/Sub.
    Receives a Fighters instance and returns nothing.
    """
    enqueue_fighter_profile_sync(fighter)


def ensure_fighters_exist(fighter_name_url_pairs: list[tuple[str, str]]) -> None:
    """
    Ensure each fighter exists by ``normalized_name`` (bulk-insert missing rows).

    ``fighter_name_url_pairs`` is ``(display_name, profile_page_url)`` from the event
    table; the URL is stored on ``Fighters.profile_url`` and sent to the profile sync
    topic when a row is new or had an empty profile URL.

    RETURNS: Nothing; it just ensures that the fighters exist
    """
    first_raw_by_norm: dict[str, str] = {} # dictionary of first raw (display name) by normalized name
    profile_url_by_norm: dict[str, str] = {} # dictionary of profile url by normalized name

    # loop through all fighter name url pairs
    for raw, profile_url in fighter_name_url_pairs:
        raw = (raw or "").strip()
        if not raw:
            continue
        norm = normalize_name(raw)
        if not norm:
            continue
        first_raw_by_norm.setdefault(norm, raw) # set default first raw for normalized name
        pu = (profile_url or "").strip() # get profile url
        # if profile url is not empty, set default profile url for normalized name
        if pu:
            profile_url_by_norm.setdefault(norm, pu)

    # if there are no first raw by normalized name, return
    if not first_raw_by_norm:
        return

    norms = list(first_raw_by_norm.keys()) # get list of normalized names
    # get existing fighters by normalized name
    existing_by_norm: dict[str, Fighters] = {
        f.normalized_name: f
        # if normalized name is in existing fighters, add to existing by normalized name dictionary
        for f in Fighters.objects.filter(normalized_name__in=norms)
        if f.normalized_name
    }

    # create list of missing fighters
    missing = [
        Fighters(
            full_name=first_raw_by_norm[n],
            normalized_name=n,
            profile_url=profile_url_by_norm.get(n, ""),
        )
        # if normalized name is not in existing fighters, add to missing list
        for n in norms
        if n not in existing_by_norm
    ]
    # if there are missing fighters, bulk create them
    if missing:
        # bulk create missing fighters
        try:
            created: list[Fighters] = Fighters.objects.bulk_create(missing)
        except Exception as e:
            raise Exception(
                f"Failed to bulk create missing fighters: {e}"
            ) from e

        for fighter in created:
            #_enqueue_fighter_profile_sync(fighter)
            print(f"Fighter created: {fighter.full_name}")

    to_update: list[Fighters] = []
    # loop through all normalized names, update profile url if it is not empty and fighter profile url is empty
    for n in norms:
        if n not in existing_by_norm:
            continue
        fighter = existing_by_norm[n]
        new_url = profile_url_by_norm.get(n, "")
        # if new url is not empty and fighter profile url is empty, update profile url
        if new_url and not (fighter.profile_url or "").strip():
            fighter.profile_url = new_url
            to_update.append(fighter)

    # if there are fighters to update, bulk update them
    if to_update:
        try:
            Fighters.objects.bulk_update(to_update, ["profile_url"])
        except Exception as e:
            raise Exception(
                f"Failed to bulk update fighters: {e}"
            ) from e
            
        for fighter in to_update:
            #_enqueue_fighter_profile_sync(fighter)
            print(f"Fighter updated: {fighter.full_name}")


def scrape_fights_in_event(soup: BeautifulSoup, event_id: int) -> list[Fights]:
    """
    Extract fight rows, resolve fighters, and return unsaved ``Fights`` rows for ``event``.

    Each row's ``data-link`` is stored on ``Fights.url`` for a later detail scrape when fights are finished
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
        # get profile link for each fighter
        url_a = name_els[0].get("href") 
        url_b = name_els[1].get("href")
        if not fighter_a or not fighter_b:
            continue

        # get weight class from table row (second td in row)
        wc_td = row.find_all(
            "td",
            class_=lambda c: c
            and "b-fight-details__table-col" in c
            and "l-page_align_left" in c,
        )
        wc_td = wc_td[1] # get weight class text
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
