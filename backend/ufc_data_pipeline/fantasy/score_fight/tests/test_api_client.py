"""Tests for score-fight pipeline API error classification."""

from unittest import TestCase
from unittest.mock import Mock, call, patch

from ufc_data_pipeline.fantasy.score_fight import api_client
from ufc_data_pipeline.fantasy.score_fight.api_client import (
    ScoringSourceIncompleteError,
    ScoringSourceUnscoreableError,
)


class ScoreFightAPIClientTests(TestCase):
    @patch("ufc_data_pipeline.fantasy.score_fight.api_client.requests.request")
    def test_get_and_patch_use_pipeline_contract(self, mock_request) -> None:
        source = {"fight": {"fight_id": 123}, "fighters": []}
        get_response = Mock(ok=True, status_code=200, content=b"source")
        get_response.json.return_value = source
        patch_response = Mock(ok=True, status_code=200, content=b"result")
        patch_response.json.return_value = {"detail": "ok"}
        mock_request.side_effect = [get_response, patch_response]
        score_payload = {"fight_scores": [], "round_scores": []}

        with patch.multiple(
            api_client,
            PIPELINE_API_BASE_URL="http://web:8000/",
            PIPELINE_SERVICE_API_KEY="secret",
        ):
            returned_source = api_client.fetch_scoring_source(123)
            api_client.set_fight_scoring(123, score_payload)

        self.assertEqual(returned_source, source)
        self.assertEqual(
            mock_request.call_args_list,
            [
                call(
                    "GET",
                    "http://web:8000/api/fights/123/ScoringSource",
                    json=None,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Api-Key secret",
                    },
                    timeout=60,
                ),
                call(
                    "PATCH",
                    "http://web:8000/api/fights/123/SetFightScoring",
                    json=score_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Api-Key secret",
                    },
                    timeout=60,
                ),
            ],
        )

    @patch("ufc_data_pipeline.fantasy.score_fight.api_client.requests.request")
    def test_incomplete_source_maps_to_retryable_typed_error(
        self,
        mock_request,
    ) -> None:
        response = Mock(
            ok=False,
            status_code=409,
            text='{"error_code":"SCORING_SOURCE_INCOMPLETE"}',
            content=b'{"error_code":"SCORING_SOURCE_INCOMPLETE"}',
        )
        response.json.return_value = {
            "error_code": "SCORING_SOURCE_INCOMPLETE",
            "detail": "RoundStats are missing.",
        }
        mock_request.return_value = response

        with patch.multiple(
            api_client,
            PIPELINE_API_BASE_URL="http://web:8000",
            PIPELINE_SERVICE_API_KEY="secret",
        ):
            with self.assertRaisesRegex(
                ScoringSourceIncompleteError,
                "RoundStats are missing",
            ):
                api_client.fetch_scoring_source(123)

    @patch("ufc_data_pipeline.fantasy.score_fight.api_client.requests.request")
    def test_unscoreable_source_maps_to_permanent_typed_error(
        self,
        mock_request,
    ) -> None:
        response = Mock(
            ok=False,
            status_code=422,
            text='{"error_code":"SCORING_SOURCE_UNSCOREABLE"}',
            content=b'{"error_code":"SCORING_SOURCE_UNSCOREABLE"}',
        )
        response.json.return_value = {
            "error_code": "SCORING_SOURCE_UNSCOREABLE",
            "detail": "No contest fights are not scored.",
        }
        mock_request.return_value = response

        with patch.multiple(
            api_client,
            PIPELINE_API_BASE_URL="http://web:8000",
            PIPELINE_SERVICE_API_KEY="secret",
        ):
            with self.assertRaisesRegex(
                ScoringSourceUnscoreableError,
                "No contest fights are not scored",
            ):
                api_client.fetch_scoring_source(123)
