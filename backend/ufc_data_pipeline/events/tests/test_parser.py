from datetime import date

from bs4 import BeautifulSoup

from ufc_data_pipeline.events.event_page_sync.parser import parse_completed_events_after


def test_parse_completed_events_after_returns_events_after_cutoff_date() -> None:
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

    assert len(events) == 1
    assert events[0].name == "UFC 300"
    assert events[0].url == "/event/300"
    assert events[0].location == "Las Vegas, NV"
    assert events[0].event_date == date(2026, 3, 10)


def test_parse_completed_events_after_returns_empty_when_no_event_rows_found() -> None:
    html = """
    <div>
      <p>No completed events available.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    events = parse_completed_events_after(soup, date(2026, 1, 1))

    assert events == []


def test_parse_completed_events_after_excludes_events_on_same_date_as_cutoff() -> None:
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

    assert events == []
