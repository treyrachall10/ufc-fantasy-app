"""Entry point for the score-fight worker process."""

from __future__ import annotations

import logging
import os
import signal
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")
django.setup()

logger = logging.getLogger(__name__)


def main() -> None:
    """Configure process lifecycle and start the score-fight subscriber."""
    from ufc_data_pipeline.fantasy.score_fight.consumer import run_subscriber

    logging.basicConfig(level=logging.INFO)

    def _handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s; shutting down score-fight worker.", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    run_subscriber()


if __name__ == "__main__":
    main()
