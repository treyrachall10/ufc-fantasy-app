"""
Tests for Live Event Rescrape handoff APIs.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events
from ufc_data_pipeline.models import LiveEventRescrapeHandoff


class LiveEventRescrapeHandoffAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}
        self.event = Events.objects.create(
            event="UFC Live",
            date="2026-07-19",
            location="Las Vegas, NV",
            url="http://ufcstats.com/event-details/live",
        )

    def _ensure_url(self) -> str:
        return f"/api/events/{self.event.event_id}/EnsureLiveEventRescrapeHandoff"

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "abc", "reason": "MISSING_FIGHT"},
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_creates_and_reuses_handoff(self) -> None:
        response = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp1", "reason": "MISSING_FIGHT"},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "created"
        assert body["handoff"]["status"] == "PENDING"
        handoff_id = body["handoff"]["id"]

        response = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp1", "reason": "CARD_CHANGED"},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "reused"
        assert body["handoff"]["id"] == handoff_id
        assert body["handoff"]["reason"] == "CARD_CHANGED"
        assert LiveEventRescrapeHandoff.objects.filter(event_id=self.event.event_id).count() == 1

    def test_mark_published_applies_cooldown(self) -> None:
        ensure = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp2", "reason": "MALFORMED_IDENTITY"},
            format="json",
            **self.auth_headers,
        ).json()
        handoff_id = ensure["handoff"]["id"]

        response = self.client.post(
            f"/api/events/{self.event.event_id}/LiveEventRescrapeHandoffs/"
            f"{handoff_id}/MarkPublished",
            data={},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        handoff = response.json()["handoff"]
        assert handoff["status"] == "PUBLISHED"
        assert handoff["publication_count"] == 1
        assert handoff["next_eligible_at"] is not None

        row = LiveEventRescrapeHandoff.objects.get(id=handoff_id)
        assert row.next_eligible_at is not None
        assert row.next_eligible_at > timezone.now() + timedelta(minutes=29)

    def test_record_attempt_leaves_pending(self) -> None:
        ensure = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp3", "reason": "MISSING_FIGHT"},
            format="json",
            **self.auth_headers,
        ).json()
        handoff_id = ensure["handoff"]["id"]

        response = self.client.post(
            f"/api/events/{self.event.event_id}/LiveEventRescrapeHandoffs/"
            f"{handoff_id}/RecordAttempt",
            data={"last_error": "pubsub down"},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["handoff"]["status"] == "PENDING"
        assert response.json()["handoff"]["last_error"] == "pubsub down"

    def test_resolve_and_fail(self) -> None:
        ensure = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp4", "reason": "MISSING_FIGHT"},
            format="json",
            **self.auth_headers,
        ).json()
        handoff_id = ensure["handoff"]["id"]

        resolved = self.client.post(
            f"/api/events/{self.event.event_id}/LiveEventRescrapeHandoffs/"
            f"{handoff_id}/Resolve",
            data={},
            format="json",
            **self.auth_headers,
        )
        assert resolved.status_code == 200
        assert resolved.json()["handoff"]["status"] == "RESOLVED"

        # Re-open from resolved when card needs rescrape again.
        reopened = self.client.post(
            self._ensure_url(),
            data={"card_fingerprint": "fp4", "reason": "MISSING_FIGHT"},
            format="json",
            **self.auth_headers,
        ).json()
        assert reopened["handoff"]["status"] == "PENDING"
        assert reopened["handoff"]["publication_count"] == 0

        failed = self.client.post(
            f"/api/events/{self.event.event_id}/LiveEventRescrapeHandoffs/"
            f"{handoff_id}/Fail",
            data={"last_error": "operator action required"},
            format="json",
            **self.auth_headers,
        )
        assert failed.status_code == 200
        assert failed.json()["handoff"]["status"] == "FAILED"

    def test_snapshot_includes_rescrape_handoffs(self) -> None:
        LiveEventRescrapeHandoff.objects.create(
            event_id=self.event.event_id,
            card_fingerprint="snap-fp",
            reason=LiveEventRescrapeHandoff.Reason.MISSING_FIGHT,
            status=LiveEventRescrapeHandoff.Status.PENDING,
        )
        response = self.client.get(
            f"/api/events/{self.event.event_id}/LiveResultsSource",
            **self.auth_headers,
        )
        assert response.status_code == 200
        handoffs = response.json()["rescrape_handoffs"]
        assert len(handoffs) == 1
        assert handoffs[0]["card_fingerprint"] == "snap-fp"
