"""
Tests for Live Results lease claim/renew/complete/fail APIs.
"""

from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events
from ufc_data_pipeline.models import LiveEventResultsState


class LiveResultsLeaseAPITests(TestCase):
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
        self.owner_a = str(uuid4())
        self.owner_b = str(uuid4())

    def _url(self, action: str, event_id: int | None = None) -> str:
        eid = event_id if event_id is not None else self.event.event_id
        return f"/api/events/{eid}/LiveResultsLease/{action}"

    def test_claim_requires_pipeline_api_key(self) -> None:
        response = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_claim_creates_running_lease(self) -> None:
        before = timezone.now()
        response = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        after = timezone.now()

        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "claimed"
        assert body["status"] == "RUNNING"
        assert str(body["owner_token"]) == self.owner_a

        state = LiveEventResultsState.objects.get(event=self.event)
        assert state.status == LiveEventResultsState.Status.RUNNING
        assert str(state.owner_token) == self.owner_a
        assert state.locked_until is not None
        assert before + timedelta(minutes=14) < state.locked_until < after + timedelta(minutes=16)

    def test_same_owner_claim_is_idempotent(self) -> None:
        first = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        assert first.status_code == 200

        second = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        assert second.status_code == 200
        assert second.json()["outcome"] == "claimed"
        assert LiveEventResultsState.objects.filter(event=self.event).count() == 1

    def test_active_other_owner_skips_successfully(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_b},
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "skipped"
        assert body["skip_reason"] == "ACTIVE_LEASE"
        state = LiveEventResultsState.objects.get(event=self.event)
        assert str(state.owner_token) == self.owner_a

    def test_expired_lease_can_be_reclaimed(self) -> None:
        LiveEventResultsState.objects.create(
            event=self.event,
            status=LiveEventResultsState.Status.RUNNING,
            owner_token=self.owner_a,
            locked_until=timezone.now() - timedelta(minutes=1),
            last_started_at=timezone.now() - timedelta(minutes=20),
        )

        response = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_b},
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["outcome"] == "claimed"
        state = LiveEventResultsState.objects.get(event=self.event)
        assert str(state.owner_token) == self.owner_b
        assert state.locked_until > timezone.now()

    def test_renew_extends_active_lease(self) -> None:
        claim = self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        original_until = claim.json()["locked_until"]

        response = self.client.post(
            self._url("Renew"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "renewed"
        assert response.json()["locked_until"] >= original_until

    def test_stale_owner_cannot_renew(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Renew"),
            data={"owner_token": self.owner_b},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409

    def test_complete_releases_lease_for_owner(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Complete"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "completed"

        state = LiveEventResultsState.objects.get(event=self.event)
        assert state.status == LiveEventResultsState.Status.COMPLETED
        assert state.owner_token is None
        assert state.locked_until is None
        assert state.last_completed_at is not None

    def test_stale_owner_cannot_complete(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Complete"),
            data={"owner_token": self.owner_b},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409
        state = LiveEventResultsState.objects.get(event=self.event)
        assert str(state.owner_token) == self.owner_a

    def test_fail_releases_lease_and_records_error(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Fail"),
            data={"owner_token": self.owner_a, "last_error": "boom"},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "failed"

        state = LiveEventResultsState.objects.get(event=self.event)
        assert state.status == LiveEventResultsState.Status.FAILED
        assert state.last_error == "boom"
        assert state.owner_token is None
        assert state.locked_until is None

    def test_complete_persists_optional_warnings(self) -> None:
        self.client.post(
            self._url("Claim"),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        response = self.client.post(
            self._url("Complete"),
            data={
                "owner_token": self.owner_a,
                "warnings": "preserve_completed_warn:http://x",
            },
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        state = LiveEventResultsState.objects.get(event=self.event)
        assert state.warnings == "preserve_completed_warn:http://x"
        assert state.status == LiveEventResultsState.Status.COMPLETED

    def test_claim_missing_event_returns_404(self) -> None:
        response = self.client.post(
            self._url("Claim", event_id=999999),
            data={"owner_token": self.owner_a},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 404
