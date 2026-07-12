"""
Configuration for the fighter career-stats pipeline stage.
"""

from __future__ import annotations

import os

from ufc_data_pipeline.worker_settings import (
    idle_check_interval_seconds,
    idle_timeout_seconds,
    max_messages,
)

# GCP Pub/Sub (local emulator defaults match docker-compose pubsub-init)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
TOPIC_ID = os.getenv("PUBSUB_CAREER_STATS_TOPIC", "career-stats-jobs")
SUBSCRIPTION_ID = os.getenv(
    "PUBSUB_CAREER_STATS_SUBSCRIPTION",
    "career-stats-jobs-sub",
)

# Downstream handoff (slice 015)
SCORE_FIGHT_TOPIC_ID = os.getenv("PUBSUB_SCORE_FIGHT_TOPIC", "score-fight-jobs")

# Main API service (docker-compose web service hostname)
PIPELINE_API_BASE_URL = os.getenv("PIPELINE_API_BASE_URL", "http://web:8000")
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")

# Worker behavior
MAX_RETRY_COUNT = 3
IDLE_SHUTDOWN_S = idle_timeout_seconds()
IDLE_CHECK_INTERVAL_S = idle_check_interval_seconds()
MAX_MESSAGES = max_messages()
