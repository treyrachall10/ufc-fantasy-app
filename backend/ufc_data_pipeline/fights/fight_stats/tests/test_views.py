"""
Tests for fight stats Pub/Sub push HTTP mapping.
"""

import base64
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from ufc_data_pipeline.fights.fight_stats.api.views import fight_stats_push_view
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


def _push_body(payload: dict, *, message_id: str = "msg-1") -> bytes:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return json.dumps(
        {
            "message": {
                "data": data,
                "messageId": message_id,
            },
            "subscription": "projects/local-project/subscriptions/fight-stats-jobs-sub",
        }
    ).encode("utf-8")


@override_settings(ROOT_URLCONF="ufc_fantasy.fight_stats_urls")
class FightStatsPushViewTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    @patch(
        "ufc_data_pipeline.fights.fight_stats.api.views.resolve_fight_stats_message",
        return_value=DeliveryResult.ACKNOWLEDGE,
    )
    def test_success_returns_204(self, resolve_mock: MagicMock) -> None:
        body = _push_body(
            {"fight_id": 42, "fight_url": "http://ufcstats.com/fight-details/x"}
        )
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=body,
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 204
        resolve_mock.assert_called_once()

    @patch("ufc_data_pipeline.fights.fight_stats.api.views.resolve_fight_stats_message")
    def test_decode_error_returns_204(self, resolve_mock: MagicMock) -> None:
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=b"not-json",
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 204
        resolve_mock.assert_not_called()

    @patch(
        "ufc_data_pipeline.fights.fight_stats.api.views.resolve_fight_stats_message",
        side_effect=PayloadValidationError("fight_url is empty"),
    )
    def test_validation_error_returns_204(self, _resolve_mock: MagicMock) -> None:
        body = _push_body({"fight_id": 1, "fight_url": "   "})
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=body,
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 204

    @patch(
        "ufc_data_pipeline.fights.fight_stats.api.views.resolve_fight_stats_message",
        return_value=DeliveryResult.RETRY,
    )
    def test_retry_returns_500(self, _resolve_mock: MagicMock) -> None:
        body = _push_body(
            {"fight_id": 42, "fight_url": "http://ufcstats.com/fight-details/x"}
        )
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=body,
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 500

    @patch(
        "ufc_data_pipeline.fights.fight_stats.api.views.resolve_fight_stats_message",
        side_effect=RuntimeError("unexpected"),
    )
    def test_unexpected_error_returns_500(self, _resolve_mock: MagicMock) -> None:
        body = _push_body(
            {"fight_id": 42, "fight_url": "http://ufcstats.com/fight-details/x"}
        )
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=body,
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 500

    def test_malformed_envelope_returns_204(self) -> None:
        request = self.factory.post(
            "/pipeline/pubsub/fight-stats/",
            data=json.dumps({"subscription": "projects/x/subscriptions/y"}).encode(
                "utf-8"
            ),
            content_type="application/json",
        )

        response = fight_stats_push_view(request)

        assert response.status_code == 204
