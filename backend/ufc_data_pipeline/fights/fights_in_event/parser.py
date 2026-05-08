
"""
Parse fight rows from a UFC Stats *event detail* page (completed card).
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from fantasy.models import Events, Fighters, Fights
from shared.utils import normalize_name

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


def _enqueue_fighter_profile_sync(_fighter: Fighters) -> None:
    """Placeholder: enqueue work to pull full fighter profile from UFC Stats."""
    pass


def ensure_fighters_exist(fighter_names: list[str]) -> None:
    """
    Ensure each fighter exists by ``normalized_name`` (bulk-insert missing rows).
    """
    # create a dictionary to store the first raw by normalized name
    first_raw_by_norm: dict[str, str] = {}
    # loop through all fighter names
    for raw in fighter_names:
        # strip the raw name
        raw = (raw or "").strip()
        if not raw:
            continue
        norm = normalize_name(raw)
        if not norm:
            continue
        first_raw_by_norm.setdefault(norm, raw)

    if not first_raw_by_norm:
        return

    norms = list(first_raw_by_norm.keys())
    present: set[str] = set(
        Fighters.objects.filter(normalized_name__in=norms).values_list(
            "normalized_name", flat=True
        )
    )

    # create a list of missing fighters
    missing = [
        Fighters(
            full_name=first_raw_by_norm[n],
            normalized_name=n,
        )
        for n in norms
        if n not in present
    ]
    if not missing:
        return

    created: list[Fighters] = Fighters.objects.bulk_create(missing) # bulk create missing fighters
    # loop through all created fighters
    for fighter in created:
        _enqueue_fighter_profile_sync(fighter)


def scrape_fights_in_event(soup: BeautifulSoup, event: Events) -> list[Fights]:
    """
    Extract fight rows, resolve fighters, and return unsaved ``Fights`` rows for ``event``.

    Each row's ``data-link`` is stored on ``Fights.url`` for a later detail scrape.
    """
    rows = soup.find_all(is_fight_table_row) # get all fight table rows
    all_names: list[str] = [] # list to store all fighter names
    pending: list[Fights] = [] # list to store unsaved fights

    # loop through all rows in the soup
    for row in rows:
        name_els = row.find_all("a", class_="b-link b-link_style_black") # get all fighter names
        if len(name_els) < 2:
            continue

        fighter_a = name_els[0].get_text(strip=True)
        fighter_b = name_els[1].get_text(strip=True)
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

        all_names.extend((fighter_a, fighter_b))

        # create fight object and add to pending list
        pending.append(
            Fights(
                event=event,
                url=(row.get("data-link") or "").strip(),
                bout=bout_name_from_pair(fighter_a, fighter_b),
                weight_class=weight_class,
            )
        )

    ensure_fighters_exist(all_names)
    return pending