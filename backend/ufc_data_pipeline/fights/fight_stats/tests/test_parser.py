"""
Tests for fight detail page metadata, fight-totals, and round-stats parsing.
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
    round_stats_to_api_payload,
    time_to_seconds,
)


def _stat_cell(fighter_a: str, fighter_b: str) -> str:
    return f"""
    <td class="b-fight-details__table-col">
      <p>{fighter_a}</p>
      <p>{fighter_b}</p>
    </td>
    """


def _totals_row(
    fighter_a: str,
    fighter_b: str,
    *,
    kd_a: str,
    kd_b: str,
    sig_a: str,
    sig_b: str,
    total_a: str,
    total_b: str,
    td_a: str,
    td_b: str,
    sub_a: str,
    sub_b: str,
    rev_a: str,
    rev_b: str,
    ctrl_a: str,
    ctrl_b: str,
) -> str:
    return "".join(
        [
            _stat_cell(fighter_a, fighter_b),
            _stat_cell(kd_a, kd_b),
            _stat_cell(sig_a, sig_b),
            _stat_cell("50%", "33%"),
            _stat_cell(total_a, total_b),
            _stat_cell(td_a, td_b),
            _stat_cell("66%", "0%"),
            _stat_cell(sub_a, sub_b),
            _stat_cell(rev_a, rev_b),
            _stat_cell(ctrl_a, ctrl_b),
        ]
    )


def _sig_row(
    fighter_a: str,
    fighter_b: str,
    *,
    sig_a: str,
    sig_b: str,
    head_a: str,
    head_b: str,
    body_a: str,
    body_b: str,
    leg_a: str,
    leg_b: str,
    distance_a: str,
    distance_b: str,
    clinch_a: str,
    clinch_b: str,
    ground_a: str,
    ground_b: str,
) -> str:
    return "".join(
        [
            _stat_cell(fighter_a, fighter_b),
            _stat_cell(sig_a, sig_b),
            _stat_cell("50%", "33%"),
            _stat_cell(head_a, head_b),
            _stat_cell(body_a, body_b),
            _stat_cell(leg_a, leg_b),
            _stat_cell(distance_a, distance_b),
            _stat_cell(clinch_a, clinch_b),
            _stat_cell(ground_a, ground_b),
        ]
    )


def _totals_and_sig_html() -> str:
    """Summary-only fixture (no per-round rows)."""
    totals_row = _totals_row(
        "Kamaru Usman",
        "Jorge Masvidal",
        kd_a="1",
        kd_b="0",
        sig_a="45 of 90",
        sig_b="20 of 60",
        total_a="80 of 120",
        total_b="40 of 70",
        td_a="2 of 3",
        td_b="0 of 1",
        sub_a="0",
        sub_b="1",
        rev_a="0",
        rev_b="0",
        ctrl_a="3:20",
        ctrl_b="0:45",
    )
    sig_row = _sig_row(
        "Kamaru Usman",
        "Jorge Masvidal",
        sig_a="45 of 90",
        sig_b="20 of 60",
        head_a="30 of 60",
        head_b="10 of 30",
        body_a="10 of 20",
        body_b="5 of 15",
        leg_a="5 of 10",
        leg_b="5 of 15",
        distance_a="20 of 40",
        distance_b="15 of 40",
        clinch_a="10 of 20",
        clinch_b="3 of 10",
        ground_a="15 of 30",
        ground_b="2 of 10",
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


def _two_round_fight_html() -> str:
    """
    Multi-round fixture: totals summary + 2 rounds, then sig summary + 2 rounds.
    """
    a = "Kamaru Usman"
    b = "Jorge Masvidal"
    totals_summary = _totals_row(
        a,
        b,
        kd_a="1",
        kd_b="0",
        sig_a="45 of 90",
        sig_b="20 of 60",
        total_a="80 of 120",
        total_b="40 of 70",
        td_a="2 of 3",
        td_b="0 of 1",
        sub_a="0",
        sub_b="1",
        rev_a="0",
        rev_b="0",
        ctrl_a="3:20",
        ctrl_b="0:45",
    )
    totals_r1 = _totals_row(
        a,
        b,
        kd_a="0",
        kd_b="0",
        sig_a="20 of 40",
        sig_b="10 of 30",
        total_a="35 of 50",
        total_b="18 of 30",
        td_a="1 of 1",
        td_b="0 of 0",
        sub_a="0",
        sub_b="0",
        rev_a="0",
        rev_b="0",
        ctrl_a="1:10",
        ctrl_b="0:20",
    )
    totals_r2 = _totals_row(
        a,
        b,
        kd_a="1",
        kd_b="0",
        sig_a="25 of 50",
        sig_b="10 of 30",
        total_a="45 of 70",
        total_b="22 of 40",
        td_a="1 of 2",
        td_b="0 of 1",
        sub_a="0",
        sub_b="1",
        rev_a="0",
        rev_b="0",
        ctrl_a="2:10",
        ctrl_b="0:25",
    )
    sig_summary = _sig_row(
        a,
        b,
        sig_a="45 of 90",
        sig_b="20 of 60",
        head_a="30 of 60",
        head_b="10 of 30",
        body_a="10 of 20",
        body_b="5 of 15",
        leg_a="5 of 10",
        leg_b="5 of 15",
        distance_a="20 of 40",
        distance_b="15 of 40",
        clinch_a="10 of 20",
        clinch_b="3 of 10",
        ground_a="15 of 30",
        ground_b="2 of 10",
    )
    sig_r1 = _sig_row(
        a,
        b,
        sig_a="20 of 40",
        sig_b="10 of 30",
        head_a="12 of 25",
        head_b="5 of 15",
        body_a="5 of 10",
        body_b="3 of 8",
        leg_a="3 of 5",
        leg_b="2 of 7",
        distance_a="10 of 20",
        distance_b="8 of 20",
        clinch_a="5 of 10",
        clinch_b="1 of 5",
        ground_a="5 of 10",
        ground_b="1 of 5",
    )
    sig_r2 = _sig_row(
        a,
        b,
        sig_a="25 of 50",
        sig_b="10 of 30",
        head_a="18 of 35",
        head_b="5 of 15",
        body_a="5 of 10",
        body_b="2 of 7",
        leg_a="2 of 5",
        leg_b="3 of 8",
        distance_a="10 of 20",
        distance_b="7 of 20",
        clinch_a="5 of 10",
        clinch_b="2 of 5",
        ground_a="10 of 20",
        ground_b="1 of 5",
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
      <table>
        <tr>{totals_summary}</tr>
        <tr>{totals_r1}</tr>
        <tr>{totals_r2}</tr>
      </table>
      <table>
        <tr>{sig_summary}</tr>
        <tr>{sig_r1}</tr>
        <tr>{sig_r2}</tr>
      </table>
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

    def test_fighter_stats_to_api_payload_excludes_rounds(self) -> None:
        soup = BeautifulSoup(_two_round_fight_html(), "html.parser")
        parsed = parse_fight_page(soup)

        payload = fighter_stats_to_api_payload(parsed.fighter_stats)

        self.assertEqual(len(payload["fighters"]), 2)
        self.assertEqual(payload["fighters"][0]["fighter_name"], "Kamaru Usman")
        self.assertEqual(payload["fighters"][0]["result"], "W")
        self.assertEqual(payload["fighters"][0]["sig_str_landed"], 45)
        self.assertNotIn("rounds", payload["fighters"][0])
        self.assertEqual(payload["fighters"][1]["fighter_name"], "Jorge Masvidal")
        self.assertEqual(payload["fighters"][1]["result"], "L")


class FightRoundStatsParserTests(SimpleTestCase):
    def test_parse_fight_page_returns_per_round_stats(self) -> None:
        soup = BeautifulSoup(_two_round_fight_html(), "html.parser")

        parsed = parse_fight_page(soup)

        self.assertEqual(len(parsed.fighter_stats), 2)
        usman, masvidal = parsed.fighter_stats

        self.assertEqual(len(usman.rounds), 2)
        self.assertEqual(usman.rounds[0].round_number, 1)
        self.assertEqual(usman.rounds[0].kd, 0)
        self.assertEqual(usman.rounds[0].sig_str_landed, 20)
        self.assertEqual(usman.rounds[0].sig_str_attempted, 40)
        self.assertEqual(usman.rounds[0].ctrl_time, 70)
        self.assertEqual(usman.rounds[0].head_str_landed, 12)
        self.assertEqual(usman.rounds[0].ground_str_landed, 5)

        self.assertEqual(usman.rounds[1].round_number, 2)
        self.assertEqual(usman.rounds[1].kd, 1)
        self.assertEqual(usman.rounds[1].sig_str_landed, 25)
        self.assertEqual(usman.rounds[1].ctrl_time, 130)
        self.assertEqual(usman.rounds[1].head_str_landed, 18)

        self.assertEqual(len(masvidal.rounds), 2)
        self.assertEqual(masvidal.rounds[0].round_number, 1)
        self.assertEqual(masvidal.rounds[0].sig_str_landed, 10)
        self.assertEqual(masvidal.rounds[1].sub_att, 1)
        self.assertEqual(masvidal.rounds[1].ctrl_time, 25)

    def test_round_stats_to_api_payload(self) -> None:
        soup = BeautifulSoup(_two_round_fight_html(), "html.parser")
        parsed = parse_fight_page(soup)

        payload = round_stats_to_api_payload(parsed.fighter_stats)

        self.assertEqual(len(payload["fighters"]), 2)
        self.assertEqual(payload["fighters"][0]["fighter_name"], "Kamaru Usman")
        self.assertEqual(len(payload["fighters"][0]["rounds"]), 2)
        self.assertEqual(payload["fighters"][0]["rounds"][0]["round_number"], 1)
        self.assertEqual(payload["fighters"][0]["rounds"][0]["sig_str_landed"], 20)
        self.assertEqual(payload["fighters"][1]["rounds"][1]["round_number"], 2)
        self.assertEqual(payload["fighters"][1]["rounds"][1]["sub_att"], 1)

    def test_missing_stats_tables_raise(self) -> None:
        html = """
        <div>
          <h2 class="b-content__title">Old Fight</h2>
          <a class="b-link b-fight-details__person-link">Fighter A</a>
          <a class="b-link b-fight-details__person-link">Fighter B</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        with self.assertRaises(ValueError):
            parse_fight_page(soup)
