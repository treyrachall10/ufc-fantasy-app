"""Tests for fights-in-event Pub/Sub push HTTP view."""

from __future__ import annotations

import base64
import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings

from ufc_data_pipeline.shared.delivery_result import DeliveryResult


def _push_body(*, payload: dict, message_id: str = "push-msg-1") -> bytes:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    body = {
        "message": {
            "data": data,
            "messageId": message_id,
        },
        "subscription": "projects/demo/subscriptions/fights-in-event-sub",
    }
    return json.dumps(body).encode("utf-8")


@override_settings(ROOT_URLCONF="ufc_fantasy.fights_in_event_urls")
class FightsInEventPubSubPushViewTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.url = "/pipeline/pubsub/fights-in-event/"

    def test_malformed_envelope_returns_204(self) -> None:
        response = self.client.post(
            self.url,
            data=b"not-json",
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.api.views.resolve_fights_in_event_message"
    )
    def test_invalid_payload_returns_204(self, resolve_mock) -> None:
        from ufc_data_pipeline.shared.payload_validation import PayloadValidationError

        resolve_mock.side_effect = PayloadValidationError("url is empty")

        response = self.client.post(
            self.url,
            data=_push_body(payload={"url": "", "event_id": 1}),
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.api.views.resolve_fights_in_event_message"
    )
    def test_acknowledge_returns_204(self, resolve_mock) -> None:
        resolve_mock.return_value = DeliveryResult.ACKNOWLEDGE

        response = self.client.post(
            self.url,
            data=_push_body(
                payload={
                    "url": "http://ufcstats.com/event-details/view-test",
                    "event_id": 99,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 204

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.api.views.resolve_fights_in_event_message"
    )
    def test_retry_returns_500(self, resolve_mock) -> None:
        resolve_mock.return_value = DeliveryResult.RETRY

        response = self.client.post(
            self.url,
            data=_push_body(
                payload={
                    "url": "http://ufcstats.com/event-details/view-retry",
                    "event_id": 100,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 500

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.api.views.resolve_fights_in_event_message"
    )
    def test_uncaught_exception_returns_500(self, resolve_mock) -> None:
        resolve_mock.side_effect = RuntimeError("claim failed")

        response = self.client.post(
            self.url,
            data=_push_body(
                payload={
                    "url": "http://ufcstats.com/event-details/view-error",
                    "event_id": 101,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 500
