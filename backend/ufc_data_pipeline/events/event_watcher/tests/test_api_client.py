"""
Tests for Event Watcher discovery API client.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from ufc_data_pipeline.events.event_watcher import api_client


class GetDiscoverySourceTests(SimpleTestCase):
    @patch("ufc_data_pipeline.events.event_watcher.api_client.requests.get")
    @patch(
        "ufc_data_pipeline.events.event_watcher.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.events.event_watcher.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_get_discovery_source_calls_endpoint(self, get_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.content = b'{"latest_event":null,"events":[]}'
        response.json.return_value = {"latest_event": None, "events": []}
        get_mock.return_value = response

        payload = api_client.get_discovery_source()

        assert payload == {"latest_event": None, "events": []}
        get_mock.assert_called_once()
        args, kwargs = get_mock.call_args
        assert args[0] == "http://web:8000/api/events/DiscoverySource"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"


class UpsertEventTests(SimpleTestCase):
    @patch("ufc_data_pipeline.events.event_watcher.api_client.requests.patch")
    @patch(
        "ufc_data_pipeline.events.event_watcher.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.events.event_watcher.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_upsert_event_calls_set_event(self, patch_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.content = b'{"event_id":9,"url":"http://ufcstats.com/event-details/abc"}'
        response.json.return_value = {
            "event_id": 9,
            "url": "http://ufcstats.com/event-details/abc",
        }
        patch_mock.return_value = response

        payload = {
            "event": "UFC 300",
            "date": "2026-03-10",
            "location": "Las Vegas, NV",
            "url": "http://ufcstats.com/event-details/abc",
        }
        body = api_client.upsert_event(payload)

        assert body["event_id"] == 9
        patch_mock.assert_called_once()
        args, kwargs = patch_mock.call_args
        assert args[0] == "http://web:8000/api/events/SetEvent"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"
