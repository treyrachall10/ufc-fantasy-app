"""
Tests for SetFighterCareerStats pipeline API endpoint.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey

from fantasy.models import FighterCareerStats, Fighters


def _career_stats_payload(**overrides) -> dict:
    payload = {
        "total_fights": 2,
        "wins": 1,
        "losses": 1,
        "draws": 0,
        "ko_tko_wins": 1,
        "tko_doctor_stoppage_wins": 0,
        "submission_wins": 0,
        "unanimous_decision_wins": 0,
        "split_decision_wins": 0,
        "majority_decision_wins": 0,
        "dq_wins": 0,
        "ko_tko_losses": 0,
        "tko_doctor_stoppage_losses": 0,
        "submission_losses": 1,
        "unanimous_decision_losses": 0,
        "split_decision_losses": 0,
        "majority_decision_losses": 0,
        "dq_losses": 0,
        "sig_str_landed": 40,
        "sig_str_attempted": 80,
        "total_str_landed": 50,
        "total_str_attempted": 90,
        "td_landed": 2,
        "td_attempted": 5,
        "sub_att": 1,
        "ctrl_time": 120,
        "reversals": 0,
        "total_fight_time": 600,
        "head_str_landed": 20,
        "head_str_attempted": 40,
        "body_str_landed": 10,
        "body_str_attempted": 20,
        "leg_str_landed": 10,
        "leg_str_attempted": 20,
        "distance_str_landed": 30,
        "distance_str_attempted": 60,
        "clinch_str_landed": 5,
        "clinch_str_attempted": 10,
        "ground_str_landed": 5,
        "ground_str_attempted": 10,
        "sig_str_landed_opp": 35,
        "sig_str_attempted_opp": 70,
        "td_landed_opp": 1,
        "td_attempted_opp": 3,
        "ctrl_time_opp": 90,
    }
    payload.update(overrides)
    return payload


class SetFighterCareerStatsAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        _api_key, key = APIKey.objects.create_key(name="ufc_data_pipeline_service")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Api-Key {key}"}
        self.fighter = Fighters.objects.create(
            first_name="A",
            last_name="One",
            full_name="A One",
            normalized_name="a one",
        )

    def test_creates_career_stats_when_missing(self) -> None:
        payload = _career_stats_payload()
        response = self.client.patch(
            f"/api/fighters/{self.fighter.fighter_id}/SetFighterCareerStats",
            data=payload,
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        career_stats = FighterCareerStats.objects.get(fighter=self.fighter)
        assert career_stats.wins == 1
        assert career_stats.losses == 1
        assert career_stats.sig_str_landed == 40
        assert career_stats.total_fight_time == 600
        assert career_stats.sig_str_landed_opp == 35
        assert response.json()["fighter_career_stats_id"] == career_stats.pk

    def test_updates_existing_career_stats(self) -> None:
        existing = FighterCareerStats.objects.create(
            fighter=self.fighter,
            wins=9,
            losses=9,
            sig_str_landed=1,
        )
        payload = _career_stats_payload(wins=3, losses=0, sig_str_landed=99)

        response = self.client.patch(
            f"/api/fighters/{self.fighter.fighter_id}/SetFighterCareerStats",
            data=payload,
            format="json",
            **self.auth_headers,
        )

        assert response.status_code == 200
        existing.refresh_from_db()
        assert FighterCareerStats.objects.filter(fighter=self.fighter).count() == 1
        assert existing.wins == 3
        assert existing.losses == 0
        assert existing.sig_str_landed == 99
        assert existing.ko_tko_wins == 1

    def test_missing_fighter_returns_404(self) -> None:
        response = self.client.patch(
            "/api/fighters/999999/SetFighterCareerStats",
            data=_career_stats_payload(),
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 404

    def test_requires_pipeline_api_key(self) -> None:
        response = self.client.patch(
            f"/api/fighters/{self.fighter.fighter_id}/SetFighterCareerStats",
            data=_career_stats_payload(),
            format="json",
        )
        assert response.status_code in (401, 403)

    def test_rejects_incomplete_payload(self) -> None:
        response = self.client.patch(
            f"/api/fighters/{self.fighter.fighter_id}/SetFighterCareerStats",
            data={"wins": 1},
            format="json",
            **self.auth_headers,
        )
        assert response.status_code == 400
