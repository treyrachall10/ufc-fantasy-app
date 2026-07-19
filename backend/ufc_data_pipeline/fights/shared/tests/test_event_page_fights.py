"""
Tests for the pure shared event-page fight parser.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from ufc_data_pipeline.fights.shared.event_page_fights import (
    is_fight_row_completed,
    parse_event_fight_rows,
)

_FIGHT_ROW_CLASS = (
    "b-fight-details__table-row b-fight-details__table-row__hover "
    "js-fight-details-click"
)


def _completed_row(
    *,
    fight_url: str = "http://ufcstats.com/fight-details/abc123",
    winner_name: str = "Winner Guy",
    include_flag: bool = True,
) -> str:
    flag = ""
    if include_flag:
        flag = """
      <td class="b-fight-details__table-col">
        <i class="b-flag__inner"><i class="b-flag__text">W</i></i>
      </td>
        """
    return f"""
    <tr class="{_FIGHT_ROW_CLASS}" data-link="{fight_url}">
      {flag}
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black"
             href="http://ufcstats.com/fighter-details/winner-id">{winner_name}</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black"
             href="http://ufcstats.com/fighter-details/loser-id">Loser Guy</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">Lightweight</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">KO/TKO</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">3</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">0:39</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">5 Rnd (5-5-5-5-5)</p>
      </td>
    </tr>
    """


_UPCOMING = f"""
<tr class="{_FIGHT_ROW_CLASS}" data-link="http://ufcstats.com/fight-details/up1">
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">
      <a class="b-link b-link_style_black" href="http://ufcstats.com/fighter-details/a">A</a>
    </p>
  </td>
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">
      <a class="b-link b-link_style_black" href="http://ufcstats.com/fighter-details/b">B</a>
    </p>
  </td>
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">Welterweight</p>
  </td>
</tr>
"""


class SharedEventPageFightParserTests(SimpleTestCase):
    def test_module_has_no_orm_imports(self) -> None:
        import pathlib

        source = pathlib.Path(
            "ufc_data_pipeline/fights/shared/event_page_fights.py"
        ).read_text(encoding="utf-8")
        assert "fantasy.models" not in source
        assert "django.db" not in source
        assert "objects." not in source

    def test_parse_completed_and_upcoming_rows(self) -> None:
        soup = BeautifulSoup(
            f"<table>{_completed_row()}{_UPCOMING}</table>",
            "html.parser",
        )
        records = parse_event_fight_rows(soup)
        assert len(records) == 2

        completed = records[0]
        assert completed.is_completed is True
        assert completed.fight_url == "http://ufcstats.com/fight-details/abc123"
        assert completed.bout == "Winner Guy vs. Loser Guy"
        assert completed.weight_class == "Lightweight"
        assert completed.winner_name == "Winner Guy"
        assert completed.winner_url == "http://ufcstats.com/fighter-details/winner-id"
        assert completed.method == "KO/TKO"
        assert completed.round == 3
        assert completed.time == 39
        assert completed.round_format == "5 Rnd (5-5-5-5-5)"

        upcoming = records[1]
        assert upcoming.is_completed is False
        assert upcoming.winner_name is None
        assert upcoming.method is None

    def test_empty_fight_url_is_retained_as_malformed_candidate(self) -> None:
        soup = BeautifulSoup(
            f"<table>{_completed_row(fight_url='')}</table>",
            "html.parser",
        )
        records = parse_event_fight_rows(soup)
        assert len(records) == 1
        assert records[0].fight_url == ""

    def test_nested_flag_rule_unchanged(self) -> None:
        soup = BeautifulSoup(_UPCOMING, "html.parser")
        assert is_fight_row_completed(soup.find("tr")) is False
        soup2 = BeautifulSoup(_completed_row(), "html.parser")
        assert is_fight_row_completed(soup2.find("tr")) is True
