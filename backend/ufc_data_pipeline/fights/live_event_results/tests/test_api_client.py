"""
Tests for Live Event Results Watcher API client.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results import api_client
from ufc_data_pipeline.fights.live_event_results.retry import (
    LeaseOwnerLostError,
    TransportError,
)


class LiveResultsApiClientTests(SimpleTestCase):
    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.request")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_get_live_results_source(self, request_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"event":{"event_id":1},"fights":[]}'
        response.json.return_value = {"event": {"event_id": 1}, "fights": []}
        request_mock.return_value = response

        body = api_client.get_live_results_source(1)

        assert body["event"]["event_id"] == 1
        args, kwargs = request_mock.call_args
        assert args[0] == "GET"
        assert args[1] == "http://web:8000/api/events/1/LiveResultsSource"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.request")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_claim_lease(self, request_mock) -> None:
        token = uuid4()
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"outcome":"claimed"}'
        response.json.return_value = {"outcome": "claimed"}
        request_mock.return_value = response

        body = api_client.claim_lease(9, token)

        assert body["outcome"] == "claimed"
        args, kwargs = request_mock.call_args
        assert args[0] == "POST"
        assert args[1] == "http://web:8000/api/events/9/LiveResultsLease/Claim"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.request")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_complete_live_fight_transition(self, request_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"outcome":"completed"}'
        response.json.return_value = {"outcome": "completed"}
        request_mock.return_value = response

        body = api_client.complete_live_fight_transition(
            42,
            {
                "event_id": 7,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "expected_status": "UPCOMING",
            },
        )

        assert body["outcome"] == "completed"
        args, _kwargs = request_mock.call_args
        assert args[1] == (
            "http://web:8000/api/fights/42/CompleteLiveFightTransition"
        )

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.request")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_complete_transition_raises_api_client_error(self, request_mock) -> None:
        response = MagicMock()
        response.ok = False
        response.status_code = 409
        response.text = '{"detail":"conflict"}'
        response.headers = {}
        request_mock.return_value = response

        with self.assertRaises(api_client.ApiClientError) as ctx:
            api_client.complete_live_fight_transition(
                42,
                {
                    "event_id": 7,
                    "fight_url": "http://ufcstats.com/fight-details/a",
                    "expected_status": "UPCOMING",
                },
            )
        assert ctx.exception.status_code == 409
        assert ctx.exception.is_conflict
        assert not ctx.exception.is_retryable

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.request")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_lease_conflict_is_owner_lost(self, request_mock) -> None:
        response = MagicMock()
        response.ok = False
        response.status_code = 409
        response.text = '{"detail":"Stale lease owner."}'
        response.headers = {}
        request_mock.return_value = response

        with self.assertRaises(LeaseOwnerLostError):
            api_client.renew_lease(9, uuid4())

    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.requests.request",
        side_effect=api_client.requests.Timeout("timed out"),
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_timeout_is_transport_error(self, _request_mock) -> None:
        with self.assertRaises(TransportError):
            api_client.get_discovery_source()
