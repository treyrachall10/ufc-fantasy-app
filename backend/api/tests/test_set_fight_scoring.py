"""Tests for the pipeline-only SetFightScoring endpoint."""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import (
    FightScore,
    FightStats,
    Fighters,
    Fights,
    RoundScore,
    RoundStats,
)


class SetFightScoringAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}

        self.fighter_a = Fighters.objects.create(full_name="A One")
        self.fighter_b = Fighters.objects.create(full_name="B Two")
        self.fight = Fights.objects.create(
            fight_status=Fights.FightStatus.COMPLETED,
            winner=self.fighter_a,
            round=1,
            time=120,
        )
        stats_a = FightStats.objects.create(
            fight=self.fight,
            fighter=self.fighter_a,
        )
        stats_b = FightStats.objects.create(
            fight=self.fight,
            fighter=self.fighter_b,
        )
        self.round_a = RoundStats.objects.create(
            fight_stats=stats_a,
            round_number=1,
        )
        self.round_b = RoundStats.objects.create(
            fight_stats=stats_b,
            round_number=1,
        )

    def _payload(self) -> dict:
        return {
            "fight_scores": [
                {
                    "fighter_id": self.fighter_a.fighter_id,
                    "points_win": 20,
                    "points_round": 30,
                    "points_time": 5.4,
                    "fight_total_points": 91.4,
                },
                {
                    "fighter_id": self.fighter_b.fighter_id,
                    "points_win": 0,
                    "points_round": 0,
                    "points_time": 0,
                    "fight_total_points": 18,
                },
            ],
            "round_scores": [
                {
                    "fighter_id": self.fighter_a.fighter_id,
                    "round_number": 1,
                    "points_knockdowns": 10,
                    "points_sig_str_landed": 15,
                    "points_td_landed": 6,
                    "points_sub_att": 2,
                    "points_ctrl_time": 2,
                    "points_reversals": 1,
                    "round_total_points": 36,
                },
                {
                    "fighter_id": self.fighter_b.fighter_id,
                    "round_number": 1,
                    "points_knockdowns": 0,
                    "points_sig_str_landed": 8,
                    "points_td_landed": 0,
                    "points_sub_att": 0,
                    "points_ctrl_time": 0.5,
                    "points_reversals": 0,
                    "round_total_points": 8.5,
                },
            ],
        }

    def test_persists_complete_fight_scoring(self) -> None:
        response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            self._payload(),
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FightScore.objects.filter(fight=self.fight).count(), 2)
        self.assertEqual(
            FightScore.objects.get(
                fight=self.fight,
                fighter=self.fighter_a,
            ).fight_total_points,
            91.4,
        )
        self.assertEqual(RoundScore.objects.filter(round_stats=self.round_a).count(), 1)
        self.assertEqual(
            RoundScore.objects.get(round_stats=self.round_b).round_total_points,
            8.5,
        )

    def test_retry_updates_existing_scores_without_duplicates(self) -> None:
        first_response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            self._payload(),
            format="json",
            **self.auth_headers,
        )
        updated_payload = self._payload()
        updated_payload["fight_scores"][0]["fight_total_points"] = 99
        updated_payload["round_scores"][0]["round_total_points"] = 44

        retry_response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            updated_payload,
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(retry_response.status_code, 200)
        self.assertEqual(FightScore.objects.filter(fight=self.fight).count(), 2)
        self.assertEqual(
            RoundScore.objects.filter(
                round_stats__fight_stats__fight=self.fight,
            ).count(),
            2,
        )
        self.assertEqual(
            FightScore.objects.get(
                fight=self.fight,
                fighter=self.fighter_a,
            ).fight_total_points,
            99,
        )
        self.assertEqual(
            RoundScore.objects.get(round_stats=self.round_a).round_total_points,
            44,
        )

    def test_removes_stale_round_scores_not_in_complete_payload(self) -> None:
        stale_round = RoundStats.objects.create(
            fight_stats=self.round_a.fight_stats,
            round_number=2,
        )
        stale_score = RoundScore.objects.create(
            round_stats=stale_round,
            round_total_points=123,
        )

        response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            self._payload(),
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(RoundScore.objects.filter(pk=stale_score.pk).exists())
        self.assertEqual(
            RoundScore.objects.filter(
                round_stats__fight_stats__fight=self.fight,
            ).count(),
            2,
        )

    def test_invalid_round_rolls_back_without_changing_existing_scores(self) -> None:
        existing_fight_score = FightScore.objects.create(
            fight=self.fight,
            fighter=self.fighter_a,
            fight_total_points=12,
        )
        existing_round_score = RoundScore.objects.create(
            round_stats=self.round_a,
            round_total_points=7,
        )
        payload = self._payload()
        payload["round_scores"][0]["round_number"] = 99

        response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            payload,
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 400)
        existing_fight_score.refresh_from_db()
        existing_round_score.refresh_from_db()
        self.assertEqual(existing_fight_score.fight_total_points, 12)
        self.assertEqual(existing_round_score.round_total_points, 7)
        self.assertEqual(FightScore.objects.filter(fight=self.fight).count(), 1)

    def test_rejects_fighter_who_does_not_belong_to_fight(self) -> None:
        outsider = Fighters.objects.create(full_name="Outside Fighter")
        payload = self._payload()
        payload["fight_scores"][1]["fighter_id"] = outsider.fighter_id
        payload["round_scores"][1]["fighter_id"] = outsider.fighter_id

        response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            payload,
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FightScore.objects.filter(fight=self.fight).count(), 0)
        self.assertEqual(RoundScore.objects.count(), 0)

    def test_missing_fight_returns_404(self) -> None:
        response = self.client.patch(
            "/api/fights/999999/SetFightScoring",
            self._payload(),
            format="json",
            **self.auth_headers,
        )

        self.assertEqual(response.status_code, 404)

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.patch(
            f"/api/fights/{self.fight.fight_id}/SetFightScoring",
            self._payload(),
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(FightScore.objects.filter(fight=self.fight).count(), 0)
