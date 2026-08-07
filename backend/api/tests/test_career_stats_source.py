"""
Tests for CareerStatsSource pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import FightStats, Fighters, Fights


class CareerStatsSourceAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}

        self.fighter_a = Fighters.objects.create(
            first_name="A",
            last_name="One",
            full_name="A One",
            normalized_name="a one",
        )
        self.fighter_b = Fighters.objects.create(
            first_name="B",
            last_name="Two",
            full_name="B Two",
            normalized_name="b two",
        )
        self.fight = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            method="KO/TKO",
            round=2,
            time=90,
            winner=self.fighter_a,
        )
        FightStats.objects.create(
            fight=self.fight,
            fighter=self.fighter_a,
            result="W",
            sig_str_landed=10,
            sig_str_attempted=20,
            sig_str_landed_opp=5,
        )
        FightStats.objects.create(
            fight=self.fight,
            fighter=self.fighter_b,
            result="L",
            sig_str_landed=5,
            sig_str_attempted=15,
            sig_str_landed_opp=10,
        )

        # Older completed fight for fighter A only (history).
        self.prior = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            method="Submission",
            round=1,
            time=120,
            winner=self.fighter_a,
        )
        FightStats.objects.create(
            fight=self.prior,
            fighter=self.fighter_a,
            result="W",
            sig_str_landed=3,
            sig_str_attempted=7,
        )

        # Upcoming fight should not appear in history.
        self.upcoming = Fights.objects.create(fight_status=Fights.FightStatus.UPCOMING)
        FightStats.objects.create(
            fight=self.upcoming,
            fighter=self.fighter_a,
            result=None,
            sig_str_landed=99,
        )

    def test_returns_both_fighters_completed_history(self) -> None:
        response = self.client.get(
            f"/api/fights/{self.fight.fight_id}/CareerStatsSource",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert "fight" not in body
        assert len(body["fighters"]) == 2
        by_id = {row["fighter_id"]: row for row in body["fighters"]}
        assert self.fighter_a.fighter_id in by_id
        assert self.fighter_b.fighter_id in by_id

        fighter_a_fights = by_id[self.fighter_a.fighter_id]["fights"]
        assert len(fighter_a_fights) == 2
        fight_ids = {row["fight_id"] for row in fighter_a_fights}
        assert self.fight.fight_id in fight_ids
        assert self.prior.fight_id in fight_ids
        assert self.upcoming.fight_id not in fight_ids
        assert {row["sig_str_landed"] for row in fighter_a_fights} == {10, 3}

        fighter_b_fights = by_id[self.fighter_b.fighter_id]["fights"]
        assert len(fighter_b_fights) == 1
        assert fighter_b_fights[0]["result"] == "L"
        assert fighter_b_fights[0]["method"] == "KO/TKO"
        assert fighter_b_fights[0]["winner_id"] == self.fighter_a.fighter_id
        assert fighter_b_fights[0]["sig_str_landed_opp"] == 10

    def test_missing_fight_returns_404(self) -> None:
        response = self.client.get(
            "/api/fights/999999/CareerStatsSource",
            **self.auth_headers,
        )
        assert response.status_code == 404

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.get(
            f"/api/fights/{self.fight.fight_id}/CareerStatsSource",
        )
        assert response.status_code in (401, 403)
