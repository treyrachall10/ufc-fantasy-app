"""
Tests for Event Watcher identity comparison and no-work orchestration.
"""

from __future__ import annotations

from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from ufc_data_pipeline.events.event_watcher.service import (
    find_unknown_events,
    normalize_event_url,
    watch_events,
)
from ufc_data_pipeline.events.shared.parser import Event
from ufc_data_pipeline.models import EventSyncJob


LISTING_HTML = """
<table>
  <tr class="b-statistics__table-row_type_first">
    <span class="b-statistics__date">March 10, 2026</span>
    <a class="b-link b-link_style_black" href="/event-details/abc">UFC 300</a>
    <td class="b-statistics__table-col b-statistics__table-col_style_big-top-padding">
      Las Vegas, NV
    </td>
  </tr>
</table>
"""


class NormalizeEventUrlTests(SimpleTestCase):
    def test_relative_url_becomes_absolute(self) -> None:
        assert (
            normalize_event_url("/event-details/abc")
            == "http://ufcstats.com/event-details/abc"
        )


class FindUnknownEventsTests(SimpleTestCase):
    def test_existing_url_match_is_known(self) -> None:
        scraped = [
            Event(
                name="Renamed Event",
                url="/event-details/abc",
                location="Las Vegas, NV",
                event_date=date(2026, 3, 10),
            )
        ]
        discovery = {
            "latest_event": None,
            "events": [
                {
                    "event_id": 1,
                    "event": "Original Name",
                    "date": "2026-03-10",
                    "url": "http://ufcstats.com/event-details/abc",
                }
            ],
        }

        assert find_unknown_events(scraped, discovery) == []

    def test_existing_name_and_date_match_is_known(self) -> None:
        scraped = [
            Event(
                name="UFC 300",
                url="/event-details/new-url",
                location="Las Vegas, NV",
                event_date=date(2026, 3, 10),
            )
        ]
        discovery = {
            "latest_event": None,
            "events": [
                {
                    "event_id": 1,
                    "event": "UFC 300",
                    "date": "2026-03-10",
                    "url": "http://ufcstats.com/event-details/old",
                }
            ],
        }

        assert find_unknown_events(scraped, discovery) == []

    def test_no_stored_events_marks_listing_rows_unknown(self) -> None:
        scraped = [
            Event(
                name="UFC 300",
                url="/event-details/abc",
                location="Las Vegas, NV",
                event_date=date(2026, 3, 10),
            )
        ]
        discovery = {"latest_event": None, "events": []}

        unknown = find_unknown_events(scraped, discovery)
        assert len(unknown) == 1
        assert unknown[0].url == "http://ufcstats.com/event-details/abc"


class WatchEventsServiceTests(TestCase):
    @patch("ufc_data_pipeline.events.event_watcher.service.fetch_listing_soup")
    @patch("ufc_data_pipeline.events.event_watcher.service.api_client.get_discovery_source")
    def test_no_newly_discovered_events_completes_job(
        self,
        discovery_mock,
        soup_mock,
    ) -> None:
        discovery_mock.return_value = {
            "latest_event": {
                "event_id": 1,
                "event": "UFC 300",
                "date": "2026-03-10",
                "url": "http://ufcstats.com/event-details/abc",
            },
            "events": [
                {
                    "event_id": 1,
                    "event": "UFC 300",
                    "date": "2026-03-10",
                    "url": "http://ufcstats.com/event-details/abc",
                }
            ],
        }
        soup_mock.return_value = BeautifulSoup(LISTING_HTML, "html.parser")

        job, unknown = watch_events()

        assert unknown == []
        assert job.status == EventSyncJob.Status.COMPLETED
        assert job.completed_at is not None
        assert EventSyncJob.objects.filter(pk=job.pk).exists()

    @patch("ufc_data_pipeline.events.event_watcher.service.fetch_listing_soup")
    @patch("ufc_data_pipeline.events.event_watcher.service.api_client.get_discovery_source")
    def test_api_discovery_failure_marks_job_failed(
        self,
        discovery_mock,
        soup_mock,
    ) -> None:
        discovery_mock.side_effect = RuntimeError("API request failed")

        with self.assertRaises(RuntimeError):
            watch_events()

        job = EventSyncJob.objects.latest("ran_at")
        assert job.status == EventSyncJob.Status.FAILED
        assert "API request failed" in job.error_msg
        soup_mock.assert_not_called()

    @patch("ufc_data_pipeline.events.event_watcher.service.fetch_listing_soup")
    @patch("ufc_data_pipeline.events.event_watcher.service.api_client.get_discovery_source")
    def test_listing_timeout_marks_job_failed(
        self,
        discovery_mock,
        soup_mock,
    ) -> None:
        discovery_mock.return_value = {"latest_event": None, "events": []}
        soup_mock.side_effect = TimeoutError("UFC Stats timeout")

        with self.assertRaises(TimeoutError):
            watch_events()

        job = EventSyncJob.objects.latest("ran_at")
        assert job.status == EventSyncJob.Status.FAILED
        assert "UFC Stats timeout" in job.error_msg

    @patch("ufc_data_pipeline.events.event_watcher.service.parse_completed_events")
    @patch("ufc_data_pipeline.events.event_watcher.service.fetch_listing_soup")
    @patch("ufc_data_pipeline.events.event_watcher.service.api_client.get_discovery_source")
    def test_parser_failure_marks_job_failed(
        self,
        discovery_mock,
        soup_mock,
        parse_mock,
    ) -> None:
        discovery_mock.return_value = {"latest_event": None, "events": []}
        soup_mock.return_value = BeautifulSoup("<html></html>", "html.parser")
        parse_mock.side_effect = ValueError("parser failure")

        with self.assertRaises(ValueError):
            watch_events()

        job = EventSyncJob.objects.latest("ran_at")
        assert job.status == EventSyncJob.Status.FAILED
        assert "parser failure" in job.error_msg


class WatchEventsCommandTests(TestCase):
    @patch("ufc_data_pipeline.management.commands.watch_events.watch_events")
    def test_command_exits_successfully_when_no_work(self, watch_mock) -> None:
        job = MagicMock()
        job.pk = 42
        job.status = EventSyncJob.Status.COMPLETED
        watch_mock.return_value = (job, [])
        out = StringIO()

        call_command("watch_events", stdout=out)

        assert "unknown_events=0" in out.getvalue()
        assert "status=COMPLETED" in out.getvalue()

    @patch("ufc_data_pipeline.management.commands.watch_events.watch_events")
    def test_command_raises_on_service_failure(self, watch_mock) -> None:
        watch_mock.side_effect = RuntimeError("boom")
        with self.assertRaises(CommandError):
            call_command("watch_events")
