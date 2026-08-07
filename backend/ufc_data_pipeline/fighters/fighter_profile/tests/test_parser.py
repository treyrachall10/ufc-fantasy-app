"""
Tests for fighter profile HTML parsing.
"""

from datetime import date

from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from ufc_data_pipeline.fighters.fighter_profile.parser import (
    FighterProfileData,
    convert_dob,
    convert_height_to_inches,
    convert_reach_to_inches,
    convert_weight_to_lbs,
    parse_fighter_profile,
    profile_data_to_api_payload,
)


class FighterProfileParserTests(SimpleTestCase):
    def test_parse_fighter_profile_extracts_metadata(self) -> None:
        html = """
        <div>
          <span class="b-content__title-highlight">Jon Jones</span>
          <p class="b-content__Nickname">Bones</p>
          <a class="b-link b-link_style_black">Wrong Fighter</a>
          <a class="b-link b-link_style_black">Other Link</a>
          <ul class="b-list__box-list">
            <li><i>Height:</i> 6' 4"</li>
            <li><i>Weight:</i> 205 lbs.</li>
            <li><i>Reach:</i> 84"</li>
            <li><i>STANCE:</i> Orthodox</li>
            <li><i>DOB:</i> Jul 19, 1987</li>
          </ul>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        profile = parse_fighter_profile(soup)

        self.assertEqual(profile.full_name, "Jon Jones")
        self.assertEqual(profile.first_name, "Jon")
        self.assertEqual(profile.last_name, "Jones")
        self.assertEqual(profile.nick_name, "Bones")
        self.assertEqual(profile.height, 76)
        self.assertEqual(profile.weight, 205)
        self.assertEqual(profile.reach, 84)
        self.assertEqual(profile.stance, "Orthodox")
        self.assertEqual(profile.dob, date(1987, 7, 19))

    def test_parse_fighter_profile_handles_missing_values(self) -> None:
        html = """
        <div>
          <span class="b-content__title-highlight">Unknown Fighter</span>
          <ul class="b-list__box-list">
            <li><i>Height:</i> --</li>
            <li><i>Weight:</i> --</li>
            <li><i>Reach:</i> --</li>
            <li><i>STANCE:</i> --</li>
            <li><i>DOB:</i> --</li>
          </ul>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        profile = parse_fighter_profile(soup)

        self.assertEqual(profile.full_name, "Unknown Fighter")
        self.assertIsNone(profile.height)
        self.assertIsNone(profile.weight)
        self.assertIsNone(profile.reach)
        self.assertIsNone(profile.stance)
        self.assertIsNone(profile.dob)

    def test_parse_fighter_profile_ignores_bout_links_for_name(self) -> None:
        html = """
        <div>
          <span class="b-content__title-highlight">Melquizael Costa</span>
          <p class="b-content__Nickname">The Future</p>
          <a class="b-link b-link_style_black">Melquizael Costa</a>
          <a class="b-link b-link_style_black">Arnold Allen</a>
          <a class="b-link b-link_style_black">UFC Fight Night: Allen vs. Costa</a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        profile = parse_fighter_profile(soup)

        self.assertEqual(profile.full_name, "Melquizael Costa")
        self.assertEqual(profile.first_name, "Melquizael")
        self.assertEqual(profile.last_name, "Costa")
        self.assertEqual(profile.nick_name, "The Future")

    def test_parse_fighter_profile_splits_multi_word_last_name(self) -> None:
        html = """
        <div>
          <span class="b-content__title-highlight">Song Yadong</span>
          <p class="b-content__Nickname">Kung Fu Kid</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        profile = parse_fighter_profile(soup)

        self.assertEqual(profile.first_name, "Song")
        self.assertEqual(profile.last_name, "Yadong")
        self.assertEqual(profile.nick_name, "Kung Fu Kid")

    def test_conversion_helpers(self) -> None:
        self.assertEqual(convert_height_to_inches("5' 7\""), 67)
        self.assertEqual(convert_weight_to_lbs("145 lbs."), 145)
        self.assertEqual(convert_reach_to_inches('72"'), 72)
        self.assertEqual(convert_dob("Jan 01, 1990"), date(1990, 1, 1))

    def test_profile_data_to_api_payload(self) -> None:
        profile = FighterProfileData(
            first_name="Jon",
            last_name="Jones",
            full_name="Jon Jones",
            height=76,
            dob=date(1987, 7, 19),
        )

        payload = profile_data_to_api_payload(profile)

        self.assertEqual(payload["first_name"], "Jon")
        self.assertEqual(payload["dob"], "1987-07-19")
        self.assertNotIn("nick_name", payload)
