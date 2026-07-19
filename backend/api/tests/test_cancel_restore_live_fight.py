"""
Tests for CancelLiveFightTransition and RestoreLiveFightUpcoming APIs.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import Events, Fighters, Fights
from ufc_data_pipeline.models import LiveFightStatsHandoff


class CancelAndRestoreLiveFightAPITests(TestCase):
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
        self.other_event = Events.objects.create(
            event="UFC Other",
            date="2026-07-12",
            location="NY",
            url="http://ufcstats.com/event-details/other",
        )
        self.winner = Fighters.objects.create(
            full_name="Winner Guy",
            normalized_name="winner guy",
            profile_url="http://ufcstats.com/fighter-details/winner",
        )
        self.fight = Fights.objects.create(
            event=self.event,
            url="http://ufcstats.com/fight-details/abc",
            bout="A vs. B",
            weight_class="Lightweight",
            fight_status=Fights.FightStatus.UPCOMING,
        )

    def _cancel_url(self, fight_id: int | None = None) -> str:
        return (
            f"/api/fights/{fight_id or self.fight.fight_id}/CancelLiveFightTransition"
        )

    def _restore_url(self, fight_id: int | None = None) -> str:
        return (
            f"/api/fights/{fight_id or self.fight.fight_id}/RestoreLiveFightUpcoming"
        )

    def _payload(self, **overrides) -> dict:
        body = {
            "event_id": self.event.event_id,
            "fight_url": "http://ufcstats.com/fight-details/abc",
            "expected_status": "UPCOMING",
        }
        body.update(overrides)
        return body

    def test_cancel_requires_pipeline_api_key(self) -> None:
        response = self.client.post(
            self._cancel_url(),
            data=self._payload(),
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_cancels_upcoming_without_handoff(self) -> None:
        response = self.client.post(
            self._cancel_url(),
            data=self._payload(),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "cancelled"
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.CANCELLED
        assert not LiveFightStatsHandoff.objects.filter(
            fight_id=self.fight.fight_id
        ).exists()

    def test_cancel_is_idempotent(self) -> None:
        self.fight.fight_status = Fights.FightStatus.CANCELLED
        self.fight.save(update_fields=["fight_status"])

        response = self.client.post(
            self._cancel_url(),
            data=self._payload(expected_status="UPCOMING"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "idempotent"
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.CANCELLED

    def test_completed_cannot_cancel(self) -> None:
        self.fight.fight_status = Fights.FightStatus.COMPLETED
        self.fight.save(update_fields=["fight_status"])

        response = self.client.post(
            self._cancel_url(),
            data=self._payload(expected_status="UPCOMING"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.COMPLETED

    def test_cancel_rejects_wrong_event(self) -> None:
        response = self.client.post(
            self._cancel_url(),
            data=self._payload(event_id=self.other_event.event_id),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409

    def test_cancel_rejects_wrong_url(self) -> None:
        response = self.client.post(
            self._cancel_url(),
            data=self._payload(fight_url="http://ufcstats.com/fight-details/other"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 409

    def test_restore_cancelled_to_upcoming_clears_result_fields(self) -> None:
        self.fight.fight_status = Fights.FightStatus.CANCELLED
        self.fight.winner = self.winner
        self.fight.method = "KO/TKO"
        self.fight.round = 1
        self.fight.time = 30
        self.fight.round_format = "3 Rnd (5-5-5)"
        self.fight.save()

        response = self.client.post(
            self._restore_url(),
            data=self._payload(expected_status="CANCELLED"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "restored"
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.UPCOMING
        assert self.fight.winner_id is None
        assert self.fight.method is None
        assert self.fight.round is None
        assert self.fight.time is None
        assert self.fight.round_format is None
        assert self.fight.url == "http://ufcstats.com/fight-details/abc"
        assert self.fight.bout == "A vs. B"
        assert self.fight.weight_class == "Lightweight"

    def test_restore_is_idempotent_when_already_upcoming(self) -> None:
        response = self.client.post(
            self._restore_url(),
            data=self._payload(expected_status="CANCELLED"),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "idempotent"

    def test_complete_from_cancelled_creates_handoff(self) -> None:
        self.fight.fight_status = Fights.FightStatus.CANCELLED
        self.fight.save(update_fields=["fight_status"])

        response = self.client.post(
            f"/api/fights/{self.fight.fight_id}/CompleteLiveFightTransition",
            data={
                "event_id": self.event.event_id,
                "fight_url": "http://ufcstats.com/fight-details/abc",
                "expected_status": "CANCELLED",
                "winner_name": "Winner Guy",
                "winner_url": "http://ufcstats.com/fighter-details/winner",
                "method": "Decision - Unanimous",
                "round": 3,
                "time": 300,
            },
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "completed"
        self.fight.refresh_from_db()
        assert self.fight.fight_status == Fights.FightStatus.COMPLETED
        assert LiveFightStatsHandoff.objects.filter(
            fight_id=self.fight.fight_id,
            status=LiveFightStatsHandoff.Status.PENDING,
        ).exists()
