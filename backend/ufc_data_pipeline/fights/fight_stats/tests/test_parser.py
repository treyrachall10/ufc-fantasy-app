"""
Tests for fight detail page metadata parsing.
"""

from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from ufc_data_pipeline.fights.fight_stats.parser import (
    ParsedFightMetadata,
    metadata_to_api_payload,
    parse_fight_metadata,
    time_to_seconds,
)


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
