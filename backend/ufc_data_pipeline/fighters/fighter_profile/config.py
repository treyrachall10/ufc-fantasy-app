"""
Configuration for the fighter profile scraper pipeline stage.
"""

from __future__ import annotations

import os

# GCP Pub/Sub (local emulator defaults match docker-compose pubsub-init)
PROJECT_ID = "local-project"
TOPIC_ID = "fighter-profile-jobs"
SUBSCRIPTION_ID = "fighter-profile-jobs-sub"

# Main API service (docker-compose web service hostname)
PIPELINE_API_BASE_URL = "http://web:8000"
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")

# Worker behavior
PLAYWRIGHT_TIMEOUT_S = 60
MAX_RETRY_COUNT = 3
IDLE_SHUTDOWN_S = 60
IDLE_CHECK_INTERVAL_S = 5

# CSS selector waited on after Playwright loads a fighter profile page.
PROFILE_PAGE_READY_SELECTOR = "span.b-content__title-highlight"
