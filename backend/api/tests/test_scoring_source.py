"""
Tests for ScoringSource pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import FightStats, Fighters, Fights, RoundStats


class ScoringSourceAPITests(TestCase):
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

    def _create_scoreable_fight(self, **fight_overrides) -> Fights:
        values = {
            "fight_status": Fights.FightStatus.COMPLETED,
            "method": "KO/TKO",
            "round": 1,
            "time": 120,
            "winner": self.fighter_a,
        }
        values.update(fight_overrides)
        fight = Fights.objects.create(**values)

        stats_a = FightStats.objects.create(fight=fight, fighter=self.fighter_a, result="W")
        stats_b = FightStats.objects.create(fight=fight, fighter=self.fighter_b, result="L")
        RoundStats.objects.create(
            fight_stats=stats_a,
            round_number=1,
            kd=1,
            sig_str_landed=15,
            td_landed=2,
            sub_att=1,
            ctrl_time=40,
            reversals=1,
        )
        RoundStats.objects.create(
            fight_stats=stats_b,
            round_number=1,
            kd=0,
            sig_str_landed=8,
            td_landed=0,
            sub_att=0,
            ctrl_time=10,
            reversals=0,
        )
        return fight

    def test_requires_pipeline_api_key(self) -> None:
        fight = Fights.objects.create(fight_status=Fights.FightStatus.COMPLETED)
        response = self.client.get(f"/api/fights/{fight.fight_id}/ScoringSource")
        assert response.status_code in (401, 403)

    def test_missing_fight_returns_404(self) -> None:
        response = self.client.get(
            "/api/fights/999999/ScoringSource",
            **self.auth_headers,
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_returns_scoreable_snapshot(self) -> None:
        fight = self._create_scoreable_fight()

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["fight"] == {
            "fight_id": fight.fight_id,
            "fight_status": "COMPLETED",
            "method": "KO/TKO",
            "round": 1,
            "time": 120,
            "winner_id": self.fighter_a.fighter_id,
        }
        by_id = {row["fighter_id"]: row for row in body["fighters"]}
        assert set(by_id) == {self.fighter_a.fighter_id, self.fighter_b.fighter_id}
        assert by_id[self.fighter_a.fighter_id]["rounds"] == [
            {
                "round_number": 1,
                "kd": 1,
                "sig_str_landed": 15,
                "td_landed": 2,
                "sub_att": 1,
                "ctrl_time": 40,
                "reversals": 1,
            }
        ]
        assert by_id[self.fighter_b.fighter_id]["rounds"][0]["sig_str_landed"] == 8

    def test_incomplete_when_not_completed(self) -> None:
        fight = self._create_scoreable_fight(fight_status=Fights.FightStatus.UPCOMING)

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 409
        body = response.json()
        assert body["error_code"] == "SCORING_SOURCE_INCOMPLETE"
        assert "detail" in body

    def test_incomplete_when_missing_fight_stats(self) -> None:
        fight = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            method="KO/TKO",
            round=1,
            time=60,
            winner=self.fighter_a,
        )
        FightStats.objects.create(fight=fight, fighter=self.fighter_a, result="W")

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "SCORING_SOURCE_INCOMPLETE"

    def test_incomplete_when_missing_round_stats(self) -> None:
        fight = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            method="KO/TKO",
            round=1,
            time=60,
            winner=self.fighter_a,
        )
        FightStats.objects.create(fight=fight, fighter=self.fighter_a, result="W")
        FightStats.objects.create(fight=fight, fighter=self.fighter_b, result="L")

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "SCORING_SOURCE_INCOMPLETE"

    def test_unscoreable_no_contest(self) -> None:
        fight = self._create_scoreable_fight(
            method="Could Not Continue",
            winner=None,
            round=1,
            time=90,
        )

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 422
        body = response.json()
        assert body["error_code"] == "SCORING_SOURCE_UNSCOREABLE"
        assert "detail" in body

    def test_draw_is_scoreable(self) -> None:
        fight = self._create_scoreable_fight(
            method="Draw",
            winner=None,
            round=3,
            time=300,
        )

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["fight"]["winner_id"] is None
        assert response.json()["fight"]["method"] == "Draw"

    def test_incomplete_when_winner_missing_finish_fields(self) -> None:
        fight = self._create_scoreable_fight(round=None, time=None)

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "SCORING_SOURCE_INCOMPLETE"

    def test_decision_split_without_winner_is_scoreable(self) -> None:
        fight = self._create_scoreable_fight(
            method="Decision - Split",
            winner=None,
            round=3,
            time=300,
        )

        response = self.client.get(
            f"/api/fights/{fight.fight_id}/ScoringSource",
            **self.auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["fight"]["method"] == "Decision - Split"
