"""
Tests for fights-in-event HTML parsing and winner resolution.
"""

from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import SimpleTestCase, TestCase

from fantasy.models import Events, Fighters, Fights
from ufc_data_pipeline.fights.fights_in_event.parser import (
    _publish_fighter_profile_message,
    is_fight_row_completed,
    parse_event_page_result_fields,
    parse_fighter_pair_from_row,
    scrape_fights_in_event,
    time_to_seconds,
)

_FIGHT_ROW_CLASS = (
    "b-fight-details__table-row b-fight-details__table-row__hover "
    "js-fight-details-click"
)


def _completed_row_html(
    *,
    winner_name: str = "Winner Guy",
    winner_url: str = "http://ufcstats.com/fighter-details/winner-id",
    loser_name: str = "Loser Guy",
    loser_url: str = "http://ufcstats.com/fighter-details/loser-id",
    include_round_format: bool = False,
) -> str:
    format_col = ""
    if include_round_format:
        format_col = """
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">5 Rnd (5-5-5-5-5)</p>
      </td>
        """
    return f"""
    <tr class="{_FIGHT_ROW_CLASS}" data-link="http://ufcstats.com/fight-details/abc123">
      <td class="b-fight-details__table-col">
        <i class="b-flag__inner"><i class="b-flag__text">W</i></i>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black" href="{winner_url}">{winner_name}</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">
          <a class="b-link b-link_style_black" href="{loser_url}">{loser_name}</a>
        </p>
      </td>
      <td class="b-fight-details__table-col l-page_align_left">
        <p class="b-fight-details__table-text">Lightweight</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">KO/TKO</p>
        <p class="b-fight-details__table-text">Punch</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">3</p>
      </td>
      <td class="b-fight-details__table-col">
        <p class="b-fight-details__table-text">0:39</p>
      </td>
      {format_col}
    </tr>
    """


_UPCOMING_ROW_HTML = f"""
<tr class="{_FIGHT_ROW_CLASS}" data-link="http://ufcstats.com/fight-details/upcoming1">
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">
      <a class="b-link b-link_style_black" href="http://ufcstats.com/fighter-details/a">Fighter A</a>
    </p>
  </td>
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">
      <a class="b-link b-link_style_black" href="http://ufcstats.com/fighter-details/b">Fighter B</a>
    </p>
  </td>
  <td class="b-fight-details__table-col l-page_align_left">
    <p class="b-fight-details__table-text">Welterweight</p>
  </td>
</tr>
"""


class FightRowParsingTests(SimpleTestCase):
    def test_is_fight_row_completed_false_for_upcoming_row(self) -> None:
        soup = BeautifulSoup(_UPCOMING_ROW_HTML, "html.parser")
        row = soup.find("tr")

        assert row is not None
        assert is_fight_row_completed(row) is False

    def test_is_fight_row_completed_true_when_result_banner_present(self) -> None:
        soup = BeautifulSoup(_completed_row_html(), "html.parser")
        row = soup.find("tr")

        assert row is not None
        assert is_fight_row_completed(row) is True

    def test_parse_fighter_pair_returns_first_fighter_as_winner_candidate(self) -> None:
        soup = BeautifulSoup(_completed_row_html(), "html.parser")
        row = soup.find("tr")

        assert row is not None
        pair = parse_fighter_pair_from_row(row)

        assert pair is not None
        assert pair[0] == "Winner Guy"
        assert pair[2] == "Loser Guy"

    def test_parse_event_page_result_fields_extracts_method_round_time(self) -> None:
        soup = BeautifulSoup(_completed_row_html(), "html.parser")
        row = soup.find("tr")

        assert row is not None
        fields = parse_event_page_result_fields(row)

        assert fields["method"] == "KO/TKO"
        assert fields["round"] == 3
        assert fields["time"] == 39

    def test_parse_event_page_result_fields_includes_round_format_when_present(
        self,
    ) -> None:
        soup = BeautifulSoup(
            _completed_row_html(include_round_format=True), "html.parser"
        )
        row = soup.find("tr")

        assert row is not None
        fields = parse_event_page_result_fields(row)

        assert fields["round_format"] == "5 Rnd (5-5-5-5-5)"

    def test_time_to_seconds(self) -> None:
        assert time_to_seconds("2:30") == 150
        assert time_to_seconds("--") is None


@patch(
    "ufc_data_pipeline.fights.fights_in_event.parser._publish_fighter_profile_message",
)
class ScrapeFightsInEventTests(TestCase):
    def setUp(self) -> None:
        self.event = Events.objects.create(
            event="Test Event",
            date="2020-01-01",
            location="Test",
        )

    def test_scrape_fights_in_event_sets_upcoming_status_without_results(
        self, _mock_enqueue
    ) -> None:
        soup = BeautifulSoup(f"<table>{_UPCOMING_ROW_HTML}</table>", "html.parser")

        fights = scrape_fights_in_event(soup, self.event.event_id)

        assert len(fights) == 1
        fight = fights[0]
        assert fight.fight_status == Fights.FightStatus.UPCOMING
        assert fight.weight_class == "Welterweight"
        assert fight.winner is None
        assert fight.method is None
        assert fight.round is None

    def test_scrape_fights_in_event_sets_completed_status_and_results(
        self, _mock_enqueue
    ) -> None:
        soup = BeautifulSoup(
            f"<table>{_completed_row_html()}</table>", "html.parser"
        )

        fights = scrape_fights_in_event(soup, self.event.event_id)

        assert len(fights) == 1
        fight = fights[0]
        assert fight.fight_status == Fights.FightStatus.COMPLETED
        assert fight.method == "KO/TKO"
        assert fight.round == 3
        assert fight.time == 39
        assert fight.winner is not None
        assert fight.winner.full_name == "Winner Guy"

    def test_winner_resolved_by_profile_url_when_available(
        self, _mock_enqueue
    ) -> None:
        winner = Fighters.objects.create(
            full_name="Winner Guy",
            normalized_name="winner guy",
            profile_url="http://ufcstats.com/fighter-details/winner-id",
        )
        Fighters.objects.create(
            full_name="Loser Guy",
            normalized_name="loser guy",
            profile_url="http://ufcstats.com/fighter-details/loser-id",
        )
        soup = BeautifulSoup(
            f"<table>{_completed_row_html()}</table>", "html.parser"
        )

        fights = scrape_fights_in_event(soup, self.event.event_id)

        assert fights[0].winner_id == winner.fighter_id

    def test_winner_resolved_by_name_when_profile_url_missing(
        self, _mock_enqueue
    ) -> None:
        winner = Fighters.objects.create(
            full_name="Winner Guy",
            normalized_name="winner guy",
            profile_url="",
        )
        Fighters.objects.create(
            full_name="Loser Guy",
            normalized_name="loser guy",
            profile_url="",
        )
        row_html = _completed_row_html(winner_url="", loser_url="")
        soup = BeautifulSoup(f"<table>{row_html}</table>", "html.parser")

        fights = scrape_fights_in_event(soup, self.event.event_id)

        assert fights[0].winner_id == winner.fighter_id


class PublishFighterProfileMessageTests(TestCase):
    @patch("ufc_data_pipeline.fights.fights_in_event.parser.publish_json")
    @patch.dict(
        "os.environ",
        {
            "GOOGLE_CLOUD_PROJECT": "local-project",
            "PUBSUB_FIGHTER_PROFILE_TOPIC": "fighter-profile-jobs",
        },
    )
    def test_publish_fighter_profile_message_publishes_payload(
        self, publish_mock
    ) -> None:
        publish_mock.return_value = "msg-1"

        _publish_fighter_profile_message(
            99, "http://ufcstats.com/fighter-details/test"
        )

        publish_mock.assert_called_once_with(
            "fighter-profile-jobs",
            {
                "fighter_id": 99,
                "fighter_url": "http://ufcstats.com/fighter-details/test",
            },
            project_id="local-project",
        )

    @patch("ufc_data_pipeline.fights.fights_in_event.parser.publish_json")
    def test_publish_fighter_profile_message_skips_empty_url(
        self, publish_mock
    ) -> None:
        _publish_fighter_profile_message(99, "")

        publish_mock.assert_not_called()
