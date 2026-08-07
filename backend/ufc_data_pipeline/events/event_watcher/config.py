"""
Configuration for the Event Watcher scheduled discovery stage.
"""

from __future__ import annotations

import os

from ufc_data_pipeline.events.shared.config import URL as COMPLETED_EVENTS_LISTING_URL

PIPELINE_API_BASE_URL = os.getenv("PIPELINE_API_BASE_URL", "http://web:8000")
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
FIGHTS_IN_EVENT_TOPIC_ID = os.getenv("PUBSUB_FIGHTS_IN_EVENT_TOPIC", "fights-in-event")

PLAYWRIGHT_TIMEOUT_S = 60
LISTING_PAGE_READY_SELECTOR = ".b-statistics__table-row"
UFCSTATS_BASE_URL = "http://ufcstats.com"

# Re-export listing URL for callers that import from watcher config.
COMPLETED_EVENTS_URL = COMPLETED_EVENTS_LISTING_URL
