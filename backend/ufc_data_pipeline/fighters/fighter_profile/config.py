"""
Configuration for the fighter profile scraper pipeline stage.
"""

from __future__ import annotations

import os

from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    idle_timeout_seconds,
)

# GCP Pub/Sub (local emulator defaults match docker-compose pubsub-init)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
TOPIC_ID = os.getenv("PUBSUB_FIGHTER_PROFILE_TOPIC", "fighter-profile-jobs")
SUBSCRIPTION_ID = os.getenv(
    "PUBSUB_FIGHTER_PROFILE_SUBSCRIPTION", "fighter-profile-jobs-sub"
)

# Main API service (docker-compose web service hostname)
PIPELINE_API_BASE_URL = os.getenv("PIPELINE_API_BASE_URL", "http://web:8000")
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")

# Worker behavior
PLAYWRIGHT_TIMEOUT_S = 60
MAX_RETRY_COUNT = 3
IDLE_SHUTDOWN_S = idle_timeout_seconds()
IDLE_CHECK_INTERVAL_S = idle_check_interval_seconds()

# CSS selector waited on after Playwright loads a fighter profile page.
PROFILE_PAGE_READY_SELECTOR = "span.b-content__title-highlight"
