"""Configuration for fights-in-event reconciliation and downstream handoffs."""

import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "local-project")
FIGHTER_PROFILE_TOPIC_ID = os.getenv(
    "PUBSUB_FIGHTER_PROFILE_TOPIC",
    "fighter-profile-jobs",
)
