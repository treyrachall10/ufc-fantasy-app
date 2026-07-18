"""
Tests for SetEvent pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events


class SetEventAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}
        self.url = "/api/events/SetEvent"
        self.payload = {
            "event": "UFC 300",
            "date": "2026-03-10",
            "location": "Las Vegas, NV",
            "url": "http://ufcstats.com/event-details/abc",
        }

    def test_creates_event_when_unmatched(self) -> None:
        response = self.client.patch(
            self.url,
            data=self.payload,
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        event = Events.objects.get(event_id=body["event_id"])
        assert body["url"] == self.payload["url"]
        assert event.event == "UFC 300"
        assert str(event.date) == "2026-03-10"
        assert event.location == "Las Vegas, NV"
        assert event.url == self.payload["url"]

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.patch(self.url, data=self.payload, format="json")
        assert response.status_code in (401, 403)

    def test_updates_existing_event_matched_by_url(self) -> None:
        existing = Events.objects.create(
            event="Old Name",
            date="2026-01-01",
            location="Old Loc",
            url=self.payload["url"],
        )

        response = self.client.patch(
            self.url,
            data=self.payload,
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == existing.event_id
        existing.refresh_from_db()
        assert existing.event == "UFC 300"
        assert str(existing.date) == "2026-03-10"
        assert existing.location == "Las Vegas, NV"
        assert Events.objects.count() == 1

    def test_updates_existing_event_matched_by_name_and_date(self) -> None:
        existing = Events.objects.create(
            event="UFC 300",
            date="2026-03-10",
            location="Old Loc",
            url="http://ufcstats.com/event-details/old",
        )

        response = self.client.patch(
            self.url,
            data=self.payload,
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == existing.event_id
        assert body["url"] == self.payload["url"]
        existing.refresh_from_db()
        assert existing.url == self.payload["url"]
        assert existing.location == "Las Vegas, NV"
        assert Events.objects.count() == 1
