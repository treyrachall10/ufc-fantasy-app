"""
Parse fight rows from a UFC Stats event detail page and build ORM Fight rows.

Pure HTML parsing lives in ``fights.shared.event_page_fights``; this module
adapts those records into ``Fights`` instances and fighter get-or-create work.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from fantasy.models import Fighters, Fights
from shared.utils import normalize_name
from ufc_data_pipeline.fights.shared.event_page_fights import (
    ParsedEventFight,
    bout_name_from_pair,
    is_fight_row_completed,
    is_fight_table_row,
    parse_event_fight_rows,
    parse_event_page_result_fields,
    parse_fighter_pair_from_row,
    time_to_seconds,
    weight_class_from_row,
)
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

logger = logging.getLogger(__name__)

# Re-export pure helpers so existing imports keep working.
__all__ = [
    "ParsedEventFight",
    "bout_name_from_pair",
    "build_fighters_lookup",
    "ensure_fighters_exist",
    "is_fight_row_completed",
    "is_fight_table_row",
    "parse_event_fight_rows",
    "parse_event_page_result_fields",
    "parse_fighter_pair_from_row",
    "resolve_winner_fighter",
    "scrape_fights_in_event",
    "time_to_seconds",
    "weight_class_from_row",
]


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


def _profile_is_missing(fighter: Fighters) -> bool:
    """Return whether a fighter still needs the profile worker."""
    return not (fighter.first_name or "").strip() or not (
        fighter.last_name or ""
    ).strip()


def ensure_fighters_exist(
    fighter_name_url_pairs: list[tuple[str, str]],
) -> list[tuple[int, str]]:
    """
    Ensure each fighter exists by ``normalized_name`` (bulk-insert missing rows).

    Returns fighter-profile handoffs required after the caller commits.
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
        pu = normalize_ufcstats_url(profile_url)
        if pu:
            profile_url_by_norm.setdefault(norm, pu)

    if not first_raw_by_norm:
        return []

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
        try:
            Fighters.objects.bulk_create(missing)
        except Exception as e:
            raise Exception(
                f"Failed to bulk create missing fighters: {e}"
            ) from e

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
        try:
            Fighters.objects.bulk_update(to_update, ["profile_url"])
        except Exception as e:
            raise Exception(
                f"Failed to bulk update fighters: {e}"
            ) from e

    refreshed = {
        fighter.normalized_name: fighter
        for fighter in Fighters.objects.filter(normalized_name__in=norms)
        if fighter.normalized_name
    }
    return [
        (fighter.fighter_id, normalize_ufcstats_url(fighter.profile_url))
        for fighter in refreshed.values()
        if fighter.profile_url and _profile_is_missing(fighter)
    ]


def _fights_from_parsed(
    event_id: int,
    records: list[ParsedEventFight],
    profile_handoffs: list[tuple[int, str]] | None,
) -> list[Fights]:
    """Adapt pure parsed records into unsaved ``Fights`` rows."""
    fighter_name_url_pairs: list[tuple[str, str]] = []
    usable: list[ParsedEventFight] = []

    for record in records:
        if not record.fight_url:
            logger.warning(
                "Skipping fight row without source URL event_id=%s bout=%s",
                event_id,
                record.bout,
            )
            continue
        usable.append(record)
        fighter_name_url_pairs.extend(
            (
                (record.fighter_a_name, record.fighter_a_url),
                (record.fighter_b_name, record.fighter_b_url),
            )
        )

    required_profile_handoffs = ensure_fighters_exist(fighter_name_url_pairs)
    if profile_handoffs is not None:
        profile_handoffs.extend(required_profile_handoffs)

    norms: list[str] = []
    urls: list[str] = []
    for raw, profile_url in fighter_name_url_pairs:
        norm = normalize_name(raw)
        if norm:
            norms.append(norm)
        pu = normalize_ufcstats_url(profile_url)
        if pu:
            urls.append(pu)

    fighters_by_norm, fighters_by_url = build_fighters_lookup(norms, urls)

    pending: list[Fights] = []
    for parsed in usable:
        fight_kwargs: dict = {
            "event_id": event_id,
            "url": parsed.fight_url,
            "bout": parsed.bout,
            "weight_class": parsed.weight_class,
        }

        if parsed.is_completed:
            fight_kwargs["fight_status"] = Fights.FightStatus.COMPLETED
            winner = resolve_winner_fighter(
                parsed.fighter_a_name,
                parsed.fighter_a_url,
                fighters_by_norm,
                fighters_by_url,
            )
            if winner is not None:
                fight_kwargs["winner"] = winner

            if parsed.method is not None:
                fight_kwargs["method"] = parsed.method
            if parsed.round is not None:
                fight_kwargs["round"] = parsed.round
            if parsed.time is not None:
                fight_kwargs["time"] = parsed.time
            if parsed.round_format is not None:
                fight_kwargs["round_format"] = parsed.round_format
        else:
            fight_kwargs["fight_status"] = Fights.FightStatus.UPCOMING

        pending.append(Fights(**fight_kwargs))

    return pending


def scrape_fights_in_event(
    soup: BeautifulSoup,
    event_id: int,
    profile_handoffs: list[tuple[int, str]] | None = None,
) -> list[Fights]:
    """
    Extract fight rows, resolve fighters, and return unsaved ``Fights`` rows.

    Each row's ``data-link`` is stored on ``Fights.url``. Completed rows also
    receive event-page result summaries (method, round, time, winner).
    """
    records = parse_event_fight_rows(soup)
    return _fights_from_parsed(event_id, records, profile_handoffs)
