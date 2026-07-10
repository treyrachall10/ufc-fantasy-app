"""
Tests for fight detail page metadata and fight-totals parsing.
"""

from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from ufc_data_pipeline.fights.fight_stats.parser import (
    ParsedFightMetadata,
    fighter_stats_to_api_payload,
    metadata_to_api_payload,
    parse_fight_metadata,
    parse_fight_page,
    parse_landed_attempted,
    time_to_seconds,
)


def _stat_cell(fighter_a: str, fighter_b: str) -> str:
    return f"""
    <td class="b-fight-details__table-col">
      <p>{fighter_a}</p>
      <p>{fighter_b}</p>
    </td>
    """


def _totals_and_sig_html() -> str:
    """
    Minimal fight-detail HTML with one totals summary row and one sig-strikes summary row.
    Column order matches UFC Stats totals then significant-strikes tables.
    """
    # Totals: Fighter, KD, SIG.STR., SIG.STR.%, TOTAL STR., TD, TD%, SUB.ATT, REV., CTRL
    totals_row = "".join(
        [
            _stat_cell("Kamaru Usman", "Jorge Masvidal"),
            _stat_cell("1", "0"),
            _stat_cell("45 of 90", "20 of 60"),
            _stat_cell("50%", "33%"),
            _stat_cell("80 of 120", "40 of 70"),
            _stat_cell("2 of 3", "0 of 1"),
            _stat_cell("66%", "0%"),
            _stat_cell("0", "1"),
            _stat_cell("0", "0"),
            _stat_cell("3:20", "0:45"),
        ]
    )
    # Significant strikes: Fighter, SIG.STR., SIG.STR.%, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND
    sig_row = "".join(
        [
            _stat_cell("Kamaru Usman", "Jorge Masvidal"),
            _stat_cell("45 of 90", "20 of 60"),
            _stat_cell("50%", "33%"),
            _stat_cell("30 of 60", "10 of 30"),
            _stat_cell("10 of 20", "5 of 15"),
            _stat_cell("5 of 10", "5 of 15"),
            _stat_cell("20 of 40", "15 of 40"),
            _stat_cell("10 of 20", "3 of 10"),
            _stat_cell("15 of 30", "2 of 10"),
        ]
    )
    return f"""
    <div>
      <h2 class="b-content__title">UFC 261: Usman vs. Masvidal 2</h2>
      <a class="b-link b-fight-details__person-link">Kamaru Usman</a>
      <a class="b-link b-fight-details__person-link">Jorge Masvidal</a>
      <div class="b-fight-details__person"><i>W</i></div>
      <div class="b-fight-details__person"><i>L</i></div>
      <div class="b-fight-details__fight-head">Welterweight Bout</div>
      <i class="b-fight-details__text-item_first">Method: KO/TKO</i>
      <p class="b-fight-details__text">
        <i class="b-fight-details__text-item">Round: 2</i>
        <i class="b-fight-details__text-item">Time: 1:02</i>
        <i class="b-fight-details__text-item">Time format: 5 Rnd (5-5-5-5-5)</i>
      </p>
      <table><tr>{totals_row}</tr></table>
      <table><tr>{sig_row}</tr></table>
    </div>
    """


class FightMetadataParserTests(SimpleTestCase):
    def test_parse_fight_metadata_extracts_result_fields(self) -> None:
        html = """
        <div>
          <h2 class="b-content__title">UFC 261: Usman vs. Masvidal 2</h2>
          <a class="b-link b-fight-details__person-link">Kamaru Usman</a>
          <a class="b-link b-fight-details__person-link">Jorge Masvidal</a>
          <div class="b-fight-details__person"><i>W</i></div>
          <div class="b-fight-details__person"><i>L</i></div>
          <div class="b-fight-details__fight-head">Welterweight Bout</div>
          <i class="b-fight-details__text-item_first">Method: KO/TKO</i>
          <p class="b-fight-details__text">
            <i class="b-fight-details__text-item">Round: 2</i>
            <i class="b-fight-details__text-item">Time: 1:02</i>
            <i class="b-fight-details__text-item">Time format: 5 Rnd (5-5-5-5-5)</i>
          </p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        metadata = parse_fight_metadata(soup)

        self.assertEqual(metadata.event_name, "UFC 261: Usman vs. Masvidal 2")
        self.assertEqual(metadata.fighter_a_name, "Kamaru Usman")
        self.assertEqual(metadata.fighter_b_name, "Jorge Masvidal")
        self.assertEqual(metadata.fighter_a_result, "W")
        self.assertEqual(metadata.fighter_b_result, "L")
        self.assertEqual(metadata.weight_class, "Welterweight Bout")
        self.assertEqual(metadata.method, "KO/TKO")
        self.assertEqual(metadata.round, 2)
        self.assertEqual(metadata.time_seconds, 62)
        self.assertEqual(metadata.round_format, "5 Rnd (5-5-5-5-5)")

    def test_metadata_to_api_payload_sets_winner_and_status(self) -> None:
        metadata = ParsedFightMetadata(
            fighter_a_name="Kamaru Usman",
            fighter_b_name="Jorge Masvidal",
            fighter_a_result="W",
            fighter_b_result="L",
            method="KO/TKO",
            round=2,
            time_seconds=62,
            round_format="5 Rnd (5-5-5-5-5)",
            weight_class="Welterweight Bout",
        )

        payload = metadata_to_api_payload(metadata)

        self.assertEqual(payload["fight_status"], "COMPLETED")
        self.assertEqual(payload["winner_name"], "Kamaru Usman")
        self.assertEqual(payload["method"], "KO/TKO")
        self.assertEqual(payload["round"], 2)
        self.assertEqual(payload["time"], 62)

    def test_time_to_seconds(self) -> None:
        self.assertEqual(time_to_seconds("1:02"), 62)
        self.assertIsNone(time_to_seconds("--"))


class FightTotalsParserTests(SimpleTestCase):
    def test_parse_landed_attempted(self) -> None:
        self.assertEqual(parse_landed_attempted("19 of 32"), (19, 32))
        self.assertEqual(parse_landed_attempted("--"), (None, None))
        self.assertEqual(parse_landed_attempted(""), (None, None))

    def test_parse_fight_page_returns_two_fighter_totals(self) -> None:
        soup = BeautifulSoup(_totals_and_sig_html(), "html.parser")

        parsed = parse_fight_page(soup)

        self.assertEqual(len(parsed.fighter_stats), 2)
        usman, masvidal = parsed.fighter_stats

        self.assertEqual(usman.fighter_name, "Kamaru Usman")
        self.assertEqual(usman.result, "W")
        self.assertEqual(usman.kd, 1)
        self.assertEqual(usman.sig_str_landed, 45)
        self.assertEqual(usman.sig_str_attempted, 90)
        self.assertEqual(usman.total_str_landed, 80)
        self.assertEqual(usman.total_str_attempted, 120)
        self.assertEqual(usman.td_landed, 2)
        self.assertEqual(usman.td_attempted, 3)
        self.assertEqual(usman.sub_att, 0)
        self.assertEqual(usman.reversals, 0)
        self.assertEqual(usman.ctrl_time, 200)
        self.assertEqual(usman.head_str_landed, 30)
        self.assertEqual(usman.head_str_attempted, 60)
        self.assertEqual(usman.body_str_landed, 10)
        self.assertEqual(usman.leg_str_landed, 5)
        self.assertEqual(usman.distance_str_landed, 20)
        self.assertEqual(usman.clinch_str_landed, 10)
        self.assertEqual(usman.ground_str_landed, 15)

        self.assertEqual(masvidal.fighter_name, "Jorge Masvidal")
        self.assertEqual(masvidal.result, "L")
        self.assertEqual(masvidal.kd, 0)
        self.assertEqual(masvidal.sig_str_landed, 20)
        self.assertEqual(masvidal.ctrl_time, 45)
        self.assertEqual(masvidal.sub_att, 1)

    def test_fighter_stats_to_api_payload(self) -> None:
        soup = BeautifulSoup(_totals_and_sig_html(), "html.parser")
        parsed = parse_fight_page(soup)

        payload = fighter_stats_to_api_payload(parsed.fighter_stats)

        self.assertEqual(len(payload["fighters"]), 2)
        self.assertEqual(payload["fighters"][0]["fighter_name"], "Kamaru Usman")
        self.assertEqual(payload["fighters"][0]["result"], "W")
        self.assertEqual(payload["fighters"][0]["sig_str_landed"], 45)
        self.assertEqual(payload["fighters"][1]["fighter_name"], "Jorge Masvidal")
        self.assertEqual(payload["fighters"][1]["result"], "L")
