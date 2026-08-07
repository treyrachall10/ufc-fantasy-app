"""
Tests for LiveResultsSource pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events, Fights


class LiveResultsSourceAPITests(TestCase):
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

    def _url(self, event_id: int | None = None) -> str:
        return f"/api/events/{event_id or self.event.event_id}/LiveResultsSource"

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.get(self._url())
        assert response.status_code in (401, 403)

    def test_missing_event_returns_404(self) -> None:
        response = self.client.get(self._url(event_id=999999), **self.auth_headers)
        assert response.status_code == 404

    def test_returns_event_fights_and_empty_watcher_state(self) -> None:
        upcoming = Fights.objects.create(
            event=self.event,
            url="http://ufcstats.com/fight-details/aaa",
            bout="A vs. B",
            fight_status=Fights.FightStatus.UPCOMING,
        )
        completed = Fights.objects.create(
            event=self.event,
            url="http://ufcstats.com/fight-details/bbb",
            bout="C vs. D",
            fight_status=Fights.FightStatus.COMPLETED,
        )

        response = self.client.get(self._url(), **self.auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["event"]["event_id"] == self.event.event_id
        assert body["event"]["event"] == "UFC Live"
        assert body["event"]["date"] == "2026-07-19"
        assert body["event"]["url"] == "http://ufcstats.com/event-details/live"

        by_id = {row["fight_id"]: row for row in body["fights"]}
        assert set(by_id) == {upcoming.fight_id, completed.fight_id}
        assert by_id[upcoming.fight_id]["url"] == "http://ufcstats.com/fight-details/aaa"
        assert by_id[upcoming.fight_id]["bout"] == "A vs. B"
        assert by_id[upcoming.fight_id]["fight_status"] == "UPCOMING"
        assert by_id[completed.fight_id]["fight_status"] == "COMPLETED"

        assert body["watcher_state"] is None
        assert body["fight_stats_handoffs"] == []
        assert body["rescrape_handoffs"] == []

    def test_returns_watcher_state_when_present(self) -> None:
        from datetime import timedelta
        from uuid import uuid4

        from django.utils import timezone

        from ufc_data_pipeline.models import LiveEventResultsState

        token = uuid4()
        locked_until = timezone.now() + timedelta(minutes=15)
        LiveEventResultsState.objects.create(
            event=self.event,
            status=LiveEventResultsState.Status.RUNNING,
            owner_token=token,
            locked_until=locked_until,
            last_started_at=timezone.now(),
            warnings="note",
            last_error="",
        )

        response = self.client.get(self._url(), **self.auth_headers)
        assert response.status_code == 200
        state = response.json()["watcher_state"]
        assert state["status"] == "RUNNING"
        assert str(state["owner_token"]) == str(token)
        assert state["warnings"] == "note"
