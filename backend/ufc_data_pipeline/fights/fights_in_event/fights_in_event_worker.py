"""
Entry point for the fights-in-event worker process.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ufc_fantasy.settings")

import django

django.setup()

import logging
import signal
import sys

from ufc_data_pipeline.fights.fights_in_event.consumer import run_subscriber

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Bootstrap logging and start the fights-in-event Pub/Sub consumer.
    """
    logging.basicConfig(level=logging.INFO)

    def _handle_shutdown(signum, frame) -> None:
        logger.info("Received signal %s; shutting down fights-in-event worker.", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    run_subscriber()


if __name__ == "__main__":
    main()
