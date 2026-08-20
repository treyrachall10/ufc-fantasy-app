"""
Entry point for the fight stats scraper worker process.
"""

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
    """
    Bootstrap logging and start the fight stats Pub/Sub consumer.
    Receives no parameters and returns nothing.
    """
    from ufc_data_pipeline.fights.fight_stats.consumer import run_subscriber

    logging.basicConfig(level=logging.INFO)

    def _handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s; shutting down fight stats worker.", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    run_subscriber()


if __name__ == "__main__":
    main()
