"""
Deterministic card fingerprints for Live Event Results rescrape handoffs.
"""

from __future__ import annotations

import hashlib

from ufc_data_pipeline.fights.live_event_results.matcher import (
    CardComparisonPlan,
    MatchAction,
)
from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url

_IDENTITY_ANOMALY_ACTIONS = frozenset(
    {
        MatchAction.MALFORMED_STORED,
        MatchAction.MALFORMED_SOURCE,
        MatchAction.DUPLICATE_STORED_URL,
        MatchAction.DUPLICATE_SOURCE_URL,
    }
)


def card_needs_rescrape(plan: CardComparisonPlan) -> bool:
    """True when unmatched source fights or identity anomalies require FIE repair."""
    if plan.source_missing:
        return True
    return any(item.action in _IDENTITY_ANOMALY_ACTIONS for item in plan.anomalies)


def rescrape_reason(plan: CardComparisonPlan) -> str:
    """Pick a durable rescrape reason for the current comparison plan."""
    if any(item.action in _IDENTITY_ANOMALY_ACTIONS for item in plan.anomalies):
        return "MALFORMED_IDENTITY"
    if plan.source_missing:
        return "MISSING_FIGHT"
    return "CARD_CHANGED"


def build_card_fingerprint(
    scraped: list[ParsedEventFight],
    plan: CardComparisonPlan,
) -> str:
    """
    Build a deterministic fingerprint from normalized source URLs and anomaly markers.
    """
    urls: list[str] = []
    for record in scraped:
        url = normalize_ufcstats_url(record.fight_url)
        if url:
            urls.append(url)
    urls = sorted(set(urls))

    markers: list[str] = []
    for item in plan.anomalies:
        if item.action == MatchAction.MALFORMED_SOURCE:
            markers.append("malformed_source")
        elif item.action == MatchAction.MALFORMED_STORED:
            fight_id = item.stored.fight_id if item.stored is not None else "?"
            markers.append(f"malformed_stored:{fight_id}")
        elif item.action == MatchAction.DUPLICATE_SOURCE_URL:
            markers.append(f"dup_source:{item.normalized_url}")
        elif item.action == MatchAction.DUPLICATE_STORED_URL:
            markers.append(f"dup_stored:{item.normalized_url}")
    markers = sorted(set(markers))

    raw = "|".join([*urls, *markers])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
