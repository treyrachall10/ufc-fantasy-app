"""
Tests for Live Event Results Watcher API client.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results import api_client


class LiveResultsApiClientTests(SimpleTestCase):
    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.get")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_get_live_results_source(self, get_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"event":{"event_id":1},"fights":[]}'
        response.json.return_value = {"event": {"event_id": 1}, "fights": []}
        get_mock.return_value = response

        body = api_client.get_live_results_source(1)

        assert body["event"]["event_id"] == 1
        args, kwargs = get_mock.call_args
        assert args[0] == "http://web:8000/api/events/1/LiveResultsSource"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.post")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_claim_lease(self, post_mock) -> None:
        token = uuid4()
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"outcome":"claimed"}'
        response.json.return_value = {"outcome": "claimed"}
        post_mock.return_value = response

        body = api_client.claim_lease(9, token)

        assert body["outcome"] == "claimed"
        args, kwargs = post_mock.call_args
        assert args[0] == "http://web:8000/api/events/9/LiveResultsLease/Claim"
        assert kwargs["headers"]["Authorization"] == "Api-Key secret"

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.post")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_complete_live_fight_transition(self, post_mock) -> None:
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.content = b'{"outcome":"completed"}'
        response.json.return_value = {"outcome": "completed"}
        post_mock.return_value = response

        body = api_client.complete_live_fight_transition(
            42,
            {
                "event_id": 7,
                "fight_url": "http://ufcstats.com/fight-details/a",
                "expected_status": "UPCOMING",
            },
        )

        assert body["outcome"] == "completed"
        args, kwargs = post_mock.call_args
        assert args[0] == (
            "http://web:8000/api/fights/42/CompleteLiveFightTransition"
        )

    @patch("ufc_data_pipeline.fights.live_event_results.api_client.requests.post")
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_SERVICE_API_KEY",
        "secret",
    )
    @patch(
        "ufc_data_pipeline.fights.live_event_results.api_client.PIPELINE_API_BASE_URL",
        "http://web:8000",
    )
    def test_complete_transition_raises_api_client_error(self, post_mock) -> None:
        response = MagicMock()
        response.ok = False
        response.status_code = 409
        response.text = '{"detail":"conflict"}'
        post_mock.return_value = response

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
