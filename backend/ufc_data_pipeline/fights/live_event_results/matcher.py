"""
Compare stored LiveResultsSource fights to scraped event-page fights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ufc_data_pipeline.fights.shared.event_page_fights import ParsedEventFight
from ufc_data_pipeline.shared.ufcstats_urls import normalize_ufcstats_url


class MatchAction(str, Enum):
    MATCH = "match"
    STORED_MISSING_FROM_SOURCE = "stored_missing_from_source"
    SOURCE_MISSING_FROM_STORAGE = "source_missing_from_storage"
    PRESERVE_COMPLETED_WARN = "preserve_completed_warn"
    MALFORMED_STORED = "malformed_stored"
    MALFORMED_SOURCE = "malformed_source"
    DUPLICATE_STORED_URL = "duplicate_stored_url"
    DUPLICATE_SOURCE_URL = "duplicate_source_url"


@dataclass(frozen=True)
class StoredFightRef:
    fight_id: int
    url: str
    bout: str
    fight_status: str


@dataclass(frozen=True)
class PlanItem:
    action: MatchAction
    stored: StoredFightRef | None = None
    scraped: ParsedEventFight | None = None
    normalized_url: str = ""
    detail: str = ""


@dataclass
class CardComparisonPlan:
    """Deterministic reconciliation plan for one event card."""

    matches: list[PlanItem] = field(default_factory=list)
    stored_missing: list[PlanItem] = field(default_factory=list)
    source_missing: list[PlanItem] = field(default_factory=list)
    preserve_completed_warnings: list[PlanItem] = field(default_factory=list)
    anomalies: list[PlanItem] = field(default_factory=list)

    def warning_summary(self) -> str:
        parts: list[str] = []
        for item in self.preserve_completed_warnings + self.anomalies:
            label = item.action.value
            if item.normalized_url:
                parts.append(f"{label}:{item.normalized_url}")
            elif item.stored is not None:
                parts.append(f"{label}:fight_id={item.stored.fight_id}")
            else:
                parts.append(label)
        return "; ".join(parts)


def _stored_refs(snapshot_fights: list[dict]) -> list[StoredFightRef]:
    refs: list[StoredFightRef] = []
    for row in snapshot_fights:
        refs.append(
            StoredFightRef(
                fight_id=int(row["fight_id"]),
                url=normalize_ufcstats_url(row.get("url")),
                bout=(row.get("bout") or ""),
                fight_status=(row.get("fight_status") or "").upper(),
            )
        )
    return refs


def compare_card(
    stored_fights: list[dict],
    scraped: list[ParsedEventFight],
) -> CardComparisonPlan:
    """
    Match stored and scraped fights by unique normalized fight URL only.

    Bout names are never used as an update key. Malformed and duplicate
    identities are recorded as anomalies and are not silently selected.
    """
    plan = CardComparisonPlan()
    stored_refs = _stored_refs(stored_fights)

    # Index stored by normalized URL; track duplicates and empty URLs.
    stored_by_url: dict[str, list[StoredFightRef]] = {}
    for ref in stored_refs:
        if not ref.url:
            plan.anomalies.append(
                PlanItem(
                    action=MatchAction.MALFORMED_STORED,
                    stored=ref,
                    detail="stored fight missing normalized URL",
                )
            )
            continue
        stored_by_url.setdefault(ref.url, []).append(ref)

    unique_stored: dict[str, StoredFightRef] = {}
    for url, refs in stored_by_url.items():
        if len(refs) > 1:
            for ref in refs:
                plan.anomalies.append(
                    PlanItem(
                        action=MatchAction.DUPLICATE_STORED_URL,
                        stored=ref,
                        normalized_url=url,
                        detail="duplicate stored normalized fight URL",
                    )
                )
            continue
        unique_stored[url] = refs[0]

    # Index scraped by normalized URL; track duplicates and empty URLs.
    scraped_by_url: dict[str, list[ParsedEventFight]] = {}
    for record in scraped:
        url = normalize_ufcstats_url(record.fight_url)
        if not url:
            plan.anomalies.append(
                PlanItem(
                    action=MatchAction.MALFORMED_SOURCE,
                    scraped=record,
                    detail="scraped fight missing normalized URL",
                )
            )
            continue
        # Ensure scraped record carries normalized URL for downstream use.
        if url != record.fight_url:
            record = ParsedEventFight(
                fight_url=url,
                bout=record.bout,
                weight_class=record.weight_class,
                fighter_a_name=record.fighter_a_name,
                fighter_a_url=record.fighter_a_url,
                fighter_b_name=record.fighter_b_name,
                fighter_b_url=record.fighter_b_url,
                is_completed=record.is_completed,
                winner_name=record.winner_name,
                winner_url=record.winner_url,
                method=record.method,
                round=record.round,
                time=record.time,
                round_format=record.round_format,
            )
        scraped_by_url.setdefault(url, []).append(record)

    unique_scraped: dict[str, ParsedEventFight] = {}
    for url, records in scraped_by_url.items():
        if len(records) > 1:
            for record in records:
                plan.anomalies.append(
                    PlanItem(
                        action=MatchAction.DUPLICATE_SOURCE_URL,
                        scraped=record,
                        normalized_url=url,
                        detail="duplicate scraped normalized fight URL",
                    )
                )
            continue
        unique_scraped[url] = records[0]

    matched_urls = set(unique_stored) & set(unique_scraped)
    for url in sorted(matched_urls):
        stored = unique_stored[url]
        source = unique_scraped[url]
        if stored.fight_status == "COMPLETED" and not source.is_completed:
            plan.preserve_completed_warnings.append(
                PlanItem(
                    action=MatchAction.PRESERVE_COMPLETED_WARN,
                    stored=stored,
                    scraped=source,
                    normalized_url=url,
                    detail="stored COMPLETED appears UPCOMING on source; do not regress",
                )
            )
            # Still keep the pair available as a known match for later processing.
            plan.matches.append(
                PlanItem(
                    action=MatchAction.MATCH,
                    stored=stored,
                    scraped=source,
                    normalized_url=url,
                )
            )
            continue

        plan.matches.append(
            PlanItem(
                action=MatchAction.MATCH,
                stored=stored,
                scraped=source,
                normalized_url=url,
            )
        )

    for url in sorted(set(unique_stored) - matched_urls):
        plan.stored_missing.append(
            PlanItem(
                action=MatchAction.STORED_MISSING_FROM_SOURCE,
                stored=unique_stored[url],
                normalized_url=url,
            )
        )

    for url in sorted(set(unique_scraped) - matched_urls):
        plan.source_missing.append(
            PlanItem(
                action=MatchAction.SOURCE_MISSING_FROM_STORAGE,
                scraped=unique_scraped[url],
                normalized_url=url,
            )
        )

    return plan
