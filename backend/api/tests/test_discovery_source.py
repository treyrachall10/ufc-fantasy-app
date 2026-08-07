"""
Tests for DiscoverySource pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events


class DiscoverySourceAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}

    def test_empty_database_returns_null_latest_and_empty_events(self) -> None:
        response = self.client.get("/api/events/DiscoverySource", **self.auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["latest_event"] is None
        assert body["events"] == []

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.get("/api/events/DiscoverySource")
        assert response.status_code in (401, 403)

    def test_returns_latest_and_full_identity_set(self) -> None:
        older = Events.objects.create(
            event="UFC Older",
            date="2026-01-10",
            location="New York, NY",
            url="http://ufcstats.com/event-details/older",
        )
        newer = Events.objects.create(
            event="UFC Newer",
            date="2026-03-10",
            location="Las Vegas, NV",
            url="http://ufcstats.com/event-details/newer",
        )

        response = self.client.get("/api/events/DiscoverySource", **self.auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["latest_event"]["event_id"] == newer.event_id
        assert body["latest_event"]["event"] == "UFC Newer"
        assert body["latest_event"]["date"] == "2026-03-10"
        assert body["latest_event"]["url"] == "http://ufcstats.com/event-details/newer"

        by_id = {row["event_id"]: row for row in body["events"]}
        assert set(by_id) == {older.event_id, newer.event_id}
        assert by_id[older.event_id]["url"] == "http://ufcstats.com/event-details/older"
        assert by_id[older.event_id]["event"] == "UFC Older"
        assert by_id[older.event_id]["date"] == "2026-01-10"
