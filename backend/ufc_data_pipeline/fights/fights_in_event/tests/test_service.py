"""Replay and downstream handoff tests for fights-in-event."""

from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import TestCase

from fantasy.models import Events, Fighters, FightScore, FightStats, Fights
from ufc_data_pipeline.fights.fights_in_event.service import (
    process_fights_in_event,
    reconcile_fights,
)

_ROW_CLASSES = (
    "b-fight-details__table-row b-fight-details__table-row__hover "
    "js-fight-details-click"
)


def _row(
    *,
    fight_url: str | None = "http://ufcstats.com/fight-details/abc",
    fighter_a: str = "Alpha One",
    fighter_b: str = "Beta Two",
    completed: bool = True,
) -> str:
    data_link = "" if fight_url is None else f'data-link="{fight_url}"'
    result = (
        '<td class="b-fight-details__table-col">'
        '<i class="b-flag__inner"><i class="b-flag__text">W</i></i></td>'
        if completed
        else ""
    )
    result_columns = (
        """
        <td class="b-fight-details__table-col">
          <p class="b-fight-details__table-text">KO/TKO</p>
        </td>
        <td class="b-fight-details__table-col">
          <p class="b-fight-details__table-text">2</p>
        </td>
        <td class="b-fight-details__table-col">
          <p class="b-fight-details__table-text">1:30</p>
        </td>
        """
        if completed
        else ""
    )
    return f"""
    <tr class="{_ROW_CLASSES}" {data_link}>
      {result}
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black"
             href="/fighter-details/a">{fighter_a}</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black"
             href="/fighter-details/b">{fighter_b}</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">Lightweight</p>
      </td>
      {result_columns}
    </tr>
    """


class FightReconciliationTests(TestCase):
    def setUp(self) -> None:
        self.event = Events.objects.create(
            event="Replay Event",
            date="2026-01-01",
            location="Test",
        )

    def test_url_variants_update_one_stable_fight(self) -> None:
        existing = Fights.objects.create(
            event=self.event,
            url="http://ufcstats.com/fight-details/abc",
            bout="Old vs. Bout",
        )
        source = Fights(
            event=self.event,
            url=" HTTP://UFCSTATS.COM/fight-details/abc/?x=1#result ",
            bout="Alpha One vs. Beta Two",
            fight_status=Fights.FightStatus.COMPLETED,
            method="KO/TKO",
        )

        first = reconcile_fights(self.event.event_id, [source])
        second = reconcile_fights(
            self.event.event_id,
            [
                Fights(
                    event=self.event,
                    url="/fight-details/abc",
                    bout="Alpha One vs. Beta Two",
                    fight_status=Fights.FightStatus.COMPLETED,
                    method="KO/TKO",
                )
            ],
        )

        assert first[0].fight_id == existing.fight_id
        assert second[0].fight_id == existing.fight_id
        assert Fights.objects.filter(event=self.event).count() == 1
        existing.refresh_from_db()
        assert existing.url == "http://ufcstats.com/fight-details/abc"
        assert existing.bout == "Alpha One vs. Beta Two"

    def test_repairs_one_legacy_missing_url_and_preserves_references(self) -> None:
        fighter = Fighters.objects.create(full_name="Alpha One")
        legacy = Fights.objects.create(
            event=self.event,
            url=None,
            bout="Beta Two vs. Alpha One",
        )
        stats = FightStats.objects.create(fight=legacy, fighter=fighter)
        score = FightScore.objects.create(fight=legacy, fighter=fighter)

        persisted = reconcile_fights(
            self.event.event_id,
            [
                Fights(
                    event=self.event,
                    url="/fight-details/repaired",
                    bout="Alpha One vs. Beta Two",
                    fight_status=Fights.FightStatus.COMPLETED,
                )
            ],
        )

        assert persisted[0].fight_id == legacy.fight_id
        legacy.refresh_from_db()
        stats.refresh_from_db()
        score.refresh_from_db()
        assert legacy.url == "http://ufcstats.com/fight-details/repaired"
        assert stats.fight_id == legacy.fight_id
        assert score.fight_id == legacy.fight_id

    def test_ambiguous_legacy_pair_is_skipped_without_creating(self) -> None:
        for _ in range(2):
            Fights.objects.create(
                event=self.event,
                url=None,
                bout="Alpha One vs. Beta Two",
            )

        with self.assertLogs(
            "ufc_data_pipeline.fights.fights_in_event.service",
            level="ERROR",
        ) as logs:
            persisted = reconcile_fights(
                self.event.event_id,
                [
                    Fights(
                        event=self.event,
                        url="/fight-details/ambiguous",
                        bout="Beta Two vs. Alpha One",
                    )
                ],
            )

        assert persisted == []
        assert Fights.objects.filter(event=self.event).count() == 2
        assert "AMBIGUOUS LEGACY FIGHT" in "\n".join(logs.output)


class FightProcessingTests(TestCase):
    def setUp(self) -> None:
        self.event = Events.objects.create(
            event="Processing Event",
            date="2026-01-02",
            location="Test",
        )

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service."
        "publish_fighter_profile_job"
    )
    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service.publish_fight_stats_job"
    )
    def test_publishes_completed_fight_after_reconciliation(
        self,
        fight_publish,
        profile_publish,
    ) -> None:
        soup = BeautifulSoup(f"<table>{_row(completed=True)}</table>", "html.parser")

        fights = process_fights_in_event(soup, self.event.event_id)

        assert len(fights) == 1
        fight = Fights.objects.get(event=self.event)
        assert fight.fight_status == Fights.FightStatus.COMPLETED
        fight_publish.assert_called_once_with(
            fight.fight_id,
            "http://ufcstats.com/fight-details/abc",
        )
        assert profile_publish.call_count == 2

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service."
        "publish_fighter_profile_job"
    )
    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service.publish_fight_stats_job"
    )
    def test_does_not_publish_upcoming_fight_stats(
        self,
        fight_publish,
        _profile_publish,
    ) -> None:
        soup = BeautifulSoup(f"<table>{_row(completed=False)}</table>", "html.parser")

        fights = process_fights_in_event(soup, self.event.event_id)

        assert fights[0].fight_status == Fights.FightStatus.UPCOMING
        fight_publish.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service."
        "publish_fighter_profile_job"
    )
    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service.publish_fight_stats_job"
    )
    def test_missing_source_url_is_skipped_and_event_continues(
        self,
        fight_publish,
        profile_publish,
    ) -> None:
        soup = BeautifulSoup(f"<table>{_row(fight_url=None)}</table>", "html.parser")

        with self.assertLogs(
            "ufc_data_pipeline.fights.fights_in_event.parser",
            level="WARNING",
        ):
            fights = process_fights_in_event(soup, self.event.event_id)

        assert fights == []
        assert Fights.objects.filter(event=self.event).count() == 0
        fight_publish.assert_not_called()
        profile_publish.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.service."
        "publish_fighter_profile_job",
        side_effect=RuntimeError("profile publish failed"),
    )
    def test_required_profile_publish_failure_propagates(self, _publish) -> None:
        soup = BeautifulSoup(f"<table>{_row(completed=False)}</table>", "html.parser")

        with self.assertRaisesRegex(RuntimeError, "profile publish failed"):
            process_fights_in_event(soup, self.event.event_id)

        assert Fights.objects.filter(event=self.event).count() == 1
