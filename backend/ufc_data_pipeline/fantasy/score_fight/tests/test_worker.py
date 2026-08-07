"""Smoke tests for the score-fight worker entry point."""

import signal
from unittest.mock import patch

from django.test import SimpleTestCase

from ufc_data_pipeline.fantasy.score_fight import score_fight_worker


class ScoreFightWorkerTests(SimpleTestCase):
    @patch(
        "ufc_data_pipeline.fantasy.score_fight.score_fight_worker.run_subscriber"
    )
    @patch("ufc_data_pipeline.fantasy.score_fight.score_fight_worker.signal.signal")
    def test_main_registers_shutdown_signals_and_runs_subscriber(
        self,
        signal_mock,
        run_subscriber_mock,
    ) -> None:
        score_fight_worker.main()

        registered_signals = {
            call.args[0] for call in signal_mock.call_args_list
        }
        self.assertEqual(registered_signals, {signal.SIGTERM, signal.SIGINT})
        run_subscriber_mock.assert_called_once()
