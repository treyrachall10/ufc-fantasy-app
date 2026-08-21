from datetime import date
import unittest

from bs4 import BeautifulSoup

from ufc_data_pipeline.events.shared.parser import (
    parse_completed_events,
    parse_completed_events_after,
)


class CompletedEventsParserTests(unittest.TestCase):
    def test_parse_completed_events_returns_all_valid_rows(self) -> None:
        html = """
        <table>
          <tr class="b-statistics__table-row_type_first">
            <span class="b-statistics__date">March 10, 2026</span>
            <a class="b-link b-link_style_black" href="/event/300">UFC 300</a>
            <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
              Las Vegas, NV
            </td>
          </tr>
          <tr class="b-statistics__table-row">
            <span class="b-statistics__date">January 10, 2026</span>
            <a class="b-link b-link_style_white" href="/event/old">UFC Old</a>
            <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
              New York, NY
            </td>
          </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        events = parse_completed_events(soup)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].name, "UFC 300")
        self.assertEqual(events[0].url, "/event/300")
        self.assertEqual(events[0].location, "Las Vegas, NV")
        self.assertEqual(events[0].event_date, date(2026, 3, 10))
        self.assertEqual(events[1].name, "UFC Old")
        self.assertEqual(events[1].event_date, date(2026, 1, 10))

    def test_parse_completed_events_after_returns_events_after_cutoff_date(self) -> None:
        html = """
        <table>
          <tr class="b-statistics__table-row_type_first">
            <span class="b-statistics__date">March 10, 2026</span>
            <a class="b-link b-link_style_black" href="/event/300">UFC 300</a>
            <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
              Las Vegas, NV
            </td>
          </tr>
          <tr class="b-statistics__table-row">
            <span class="b-statistics__date">January 10, 2026</span>
            <a class="b-link b-link_style_white" href="/event/old">UFC Old</a>
            <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
              New York, NY
            </td>
          </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        events = parse_completed_events_after(soup, date(2026, 2, 1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "UFC 300")
        self.assertEqual(events[0].url, "/event/300")
        self.assertEqual(events[0].location, "Las Vegas, NV")
        self.assertEqual(events[0].event_date, date(2026, 3, 10))

    def test_parse_completed_events_after_returns_empty_when_no_event_rows_found(
        self,
    ) -> None:
        html = """
        <div>
          <p>No completed events available.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")

        events = parse_completed_events_after(soup, date(2026, 1, 1))

        self.assertEqual(events, [])

    def test_parse_completed_events_after_excludes_events_on_same_date_as_cutoff(
        self,
    ) -> None:
        html = """
        <table>
          <tr class="b-statistics__table-row_type_first">
            <span class="b-statistics__date">March 10, 2026</span>
            <a class="b-link b-link_style_black" href="/event/300">UFC 300</a>
            <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
              Las Vegas, NV
            </td>
          </tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")

        events = parse_completed_events_after(soup, date(2026, 3, 10))

        self.assertEqual(events, [])
