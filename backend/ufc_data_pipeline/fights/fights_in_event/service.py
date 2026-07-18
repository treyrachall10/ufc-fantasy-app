"""Reconcile one event page into stable fight rows and publish downstream work."""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from django.db import transaction

from fantasy.models import Fights
from shared.utils import normalize_name
from ufc_data_pipeline.fights.fights_in_event.parser import scrape_fights_in_event
from ufc_data_pipeline.fights.fights_in_event.publisher import (
    publish_fight_stats_job,
    publish_fighter_profile_job,
)
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

logger = logging.getLogger(__name__)

_RECONCILED_FIELDS = (
    "url",
    "bout",
    "weight_class",
    "fight_status",
    "winner",
    "method",
    "round",
    "round_format",
    "time",
)


def normalized_bout_pair(bout: str | None) -> tuple[str, str] | None:
    """Return an order-independent normalized fighter pair from ``A vs. B``."""
    left, separator, right = (bout or "").partition(" vs. ")
    if not separator:
        return None
    pair = sorted((normalize_name(left), normalize_name(right)))
    if not pair[0] or not pair[1]:
        return None
    return pair[0], pair[1]


def _copy_source_fields(target: Fights, source: Fights) -> None:
    """Apply authoritative event-page fields while preserving target identity."""
    for field in _RECONCILED_FIELDS:
        setattr(target, field, getattr(source, field))


def reconcile_fights(event_id: int, source_fights: list[Fights]) -> list[Fights]:
    """Upsert source fights by event + normalized URL and repair legacy rows."""
    persisted: list[Fights] = []
    seen_urls: set[str] = set()

    with transaction.atomic():
        existing = list(
            Fights.objects.select_for_update()
            .filter(event_id=event_id)
            .order_by("fight_id")
        )
        by_url = {
            normalize_ufcstats_url(fight.url): fight
            for fight in existing
            if normalize_ufcstats_url(fight.url)
        }
        missing_by_pair: dict[tuple[str, str], list[Fights]] = {}
        for fight in existing:
            if normalize_ufcstats_url(fight.url):
                continue
            pair = normalized_bout_pair(fight.bout)
            if pair is not None:
                missing_by_pair.setdefault(pair, []).append(fight)

        for source in source_fights:
            source_url = normalize_ufcstats_url(source.url)
            if not source_url:
                logger.warning(
                    "Skipping fight without source URL event_id=%s bout=%s",
                    event_id,
                    source.bout,
                )
                continue
            if source_url in seen_urls:
                logger.warning(
                    "Skipping duplicate source fight URL event_id=%s url=%s",
                    event_id,
                    source_url,
                )
                continue
            seen_urls.add(source_url)
            source.url = source_url

            target = by_url.get(source_url)
            if target is None:
                pair = normalized_bout_pair(source.bout)
                candidates = missing_by_pair.get(pair, []) if pair is not None else []
                if len(candidates) == 1:
                    target = candidates[0]
                    missing_by_pair[pair] = []
                    logger.info(
                        "Repairing missing fight URL fight_id=%s event_id=%s url=%s",
                        target.fight_id,
                        event_id,
                        source_url,
                    )
                elif len(candidates) > 1:
                    logger.error(
                        "AMBIGUOUS LEGACY FIGHT: skipping event_id=%s bout=%s "
                        "candidate_ids=%s url=%s",
                        event_id,
                        source.bout,
                        [candidate.fight_id for candidate in candidates],
                        source_url,
                    )
                    continue

            if target is None:
                source.event_id = event_id
                source.save(force_insert=True)
                target = source
            else:
                _copy_source_fields(target, source)
                target.save(update_fields=_RECONCILED_FIELDS)

            by_url[source_url] = target
            persisted.append(target)

    return persisted


def process_fights_in_event(soup: BeautifulSoup, event_id: int) -> list[Fights]:
    """Parse, reconcile, commit, then publish all required downstream work."""
    profile_handoffs: list[tuple[int, str]] = []
    with transaction.atomic():
        source_fights = scrape_fights_in_event(
            soup,
            event_id,
            profile_handoffs=profile_handoffs,
        )
        fights = reconcile_fights(event_id, source_fights)

    # These publications intentionally occur after domain writes commit. Any
    # failure propagates so the Pub/Sub delivery is retried; reconciliation and
    # every downstream persistence boundary are idempotent.
    for fighter_id, fighter_url in dict.fromkeys(profile_handoffs):
        publish_fighter_profile_job(fighter_id, fighter_url)

    for fight in fights:
        if fight.fight_status == Fights.FightStatus.COMPLETED:
            publish_fight_stats_job(fight.fight_id, fight.url)

    return fights
