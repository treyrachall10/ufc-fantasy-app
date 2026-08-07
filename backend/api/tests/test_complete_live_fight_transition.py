"""
Tests for CompleteLiveFightTransition and Fight Stats handoff APIs.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events, Fighters, Fights
from ufc_data_pipeline.models import LiveFightStatsHandoff


class CompleteLiveFightTransitionAPITests(TestCase):
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
        self.winner = Fighters.objects.create(
            full_name="Winner Guy",
            normalized_name="winner guy",
            profile_url="http://ufcstats.com/fighter-details/winner",
        )
        self.loser = Fighters.objects.create(
            full_name="Loser Guy",
            normalized_name="loser guy",
            profile_url="http://ufcstats.com/fighter-details/loser",
        )
        self.fight = Fights.objects.create(
            event=self.event,
            url="http://ufcstats.com/fight-details/abc",
            bout="Winner Guy vs. Loser Guy",
            weight_class="Lightweight",
            fight_status=Fights.FightStatus.UPCOMING,
        )

    def _url(self, fight_id: int | None = None) -> str:
        return (
            f"/api/fights/{fight_id or self.fight.fight_id}/CompleteLiveFightTransition"
        )

    def _payload(self, **overrides) -> dict:
        body = {
            "event_id": self.event.event_id,
            "fight_url": "http://ufcstats.com/fight-details/abc",
            "expected_status": "UPCOMING",
            "winner_name": "Winner Guy",
            "winner_url": "http://ufcstats.com/fighter-details/winner",
            "method": "KO/TKO",
            "round": 2,
            "time": 75,
            "round_format": "3 Rnd (5-5-5)",
            "weight_class": "Lightweight",
        }
        body.update(overrides)
        return body

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.post(self._url(), data=self._payload(), format="json")
        assert response.status_code in (401, 403)

    def test_completes_fight_and_creates_pending_handoff(self) -> None:
        response = self.client.post(
            self._url(),
            data=self._payload(),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["outcome"] == "completed"
        assert body["handoff"]["status"] == "PENDING"

        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.COMPLETED
        assert self.fight.winner_id == self.winner.fighter_id
        assert self.fight.method == "KO/TKO"
        assert self.fight.round == 2
        assert self.fight.time == 75

        handoff = LiveFightStatsHandoff.objects.get(fight_id=self.fight.fight_id)
        assert handoff.status == LiveFightStatsHandoff.Status.PENDING
        assert handoff.event_id == self.event.event_id

    def test_null_winner_completion_is_accepted(self) -> None:
        response = self.client.post(
            self._url(),
            data=self._payload(winner_name=None, winner_url=None),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        self.fight.refresh_from_db()
        assert self.fight.winner_id is None
        assert LiveFightStatsHandoff.objects.filter(fight_id=self.fight.fight_id).exists()

    def test_winner_url_preferred_over_name(self) -> None:
        other = Fighters.objects.create(
            full_name="Winner Guy",
            normalized_name="winner guy alt",
            profile_url="",
        )
        # Same display name as primary winner but different normalized_name —
        # URL should still win.
        response = self.client.post(
            self._url(),
            data=self._payload(winner_name="Winner Guy"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        self.fight.refresh_from_db()
        assert self.fight.winner_id == self.winner.fighter_id
        assert self.fight.winner_id != other.fighter_id

    def test_ambiguous_name_without_url_rejected(self) -> None:
        Fighters.objects.create(
            first_name="Dup",
            last_name="One",
            full_name="Dup Name",
            normalized_name="dup name",
            profile_url="http://ufcstats.com/fighter-details/dup1",
            dob="1990-01-01",
        )
        Fighters.objects.create(
            first_name="Dup",
            last_name="Two",
            full_name="Dup Name",
            normalized_name="dup name",
            profile_url="http://ufcstats.com/fighter-details/dup2",
            dob="1991-01-01",
        )

        response = self.client.post(
            self._url(),
            data=self._payload(
                winner_name="Dup Name",
                winner_url=None,
            ),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 400
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.UPCOMING
        assert not LiveFightStatsHandoff.objects.filter(
            fight_id=self.fight.fight_id
        ).exists()

    def test_unknown_claimed_winner_rejected(self) -> None:
        response = self.client.post(
            self._url(),
            data=self._payload(
                winner_name="Nobody",
                winner_url="http://ufcstats.com/fighter-details/missing",
            ),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 400
        assert not LiveFightStatsHandoff.objects.filter(
            fight_id=self.fight.fight_id
        ).exists()

    def test_idempotent_replay_returns_existing_handoff(self) -> None:
        first = self.client.post(
            self._url(),
            data=self._payload(),
            format="json",
            **self.auth_headers,
        )
        assert first.status_code == 200
        second = self.client.post(
            self._url(),
            data=self._payload(),
            format="json",
            **self.auth_headers,
        )
        assert second.status_code == 200
        assert second.json()["outcome"] == "idempotent"
        assert LiveFightStatsHandoff.objects.filter(fight_id=self.fight.fight_id).count() == 1

    def test_url_mismatch_conflicts(self) -> None:
        response = self.client.post(
            self._url(),
            data=self._payload(fight_url="http://ufcstats.com/fight-details/other"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409

    def test_wrong_event_conflicts(self) -> None:
        other = Events.objects.create(
            event="Other",
            date="2026-01-01",
            location="X",
            url="http://ufcstats.com/event-details/other",
        )
        response = self.client.post(
            self._url(),
            data=self._payload(event_id=other.event_id),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409


class FightStatsHandoffMarkerAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}
        self.handoff = LiveFightStatsHandoff.objects.create(
            fight_id=42,
            event_id=7,
            fight_url="http://ufcstats.com/fight-details/abc",
            status=LiveFightStatsHandoff.Status.PENDING,
        )

    def test_mark_published(self) -> None:
        response = self.client.post(
            "/api/fights/42/MarkFightStatsHandoffPublished",
            data={},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        self.handoff.refresh_from_db()
        assert self.handoff.status == LiveFightStatsHandoff.Status.PUBLISHED
        assert self.handoff.published_at is not None
        assert self.handoff.attempt_count == 1

    def test_record_failed_attempt_keeps_pending(self) -> None:
        response = self.client.post(
            "/api/fights/42/RecordFightStatsHandoffAttempt",
            data={"last_error": "pubsub down"},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        self.handoff.refresh_from_db()
        assert self.handoff.status == LiveFightStatsHandoff.Status.PENDING
        assert self.handoff.last_error == "pubsub down"
        assert self.handoff.attempt_count == 1


class LiveResultsSourceHandoffTests(TestCase):
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

    def test_snapshot_includes_handoffs(self) -> None:
        LiveFightStatsHandoff.objects.create(
            fight_id=9,
            event_id=self.event.event_id,
            fight_url="http://ufcstats.com/fight-details/x",
            status=LiveFightStatsHandoff.Status.PENDING,
            last_error="retry me",
        )
        response = self.client.get(
            f"/api/events/{self.event.event_id}/LiveResultsSource",
            **self.auth_headers,
        )
        assert response.status_code == 200
        handoffs = response.json()["fight_stats_handoffs"]
        assert len(handoffs) == 1
        assert handoffs[0]["fight_id"] == 9
        assert handoffs[0]["status"] == "PENDING"
        assert handoffs[0]["last_error"] == "retry me"
