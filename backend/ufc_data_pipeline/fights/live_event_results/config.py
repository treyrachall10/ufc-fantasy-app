"""
Configuration for the Live Event Results Watcher.
"""

from __future__ import annotations

import os

PIPELINE_API_BASE_URL = os.getenv("PIPELINE_API_BASE_URL", "http://web:8000")
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")

# Required IANA timezone for today/yesterday eligibility (no silent default).
LIVE_EVENT_RESULTS_TIMEZONE = os.getenv("LIVE_EVENT_RESULTS_TIMEZONE", "")

# Rolling lease duration; default 15 minutes.
LIVE_EVENT_RESULTS_LEASE_SECONDS = int(
    os.getenv("LIVE_EVENT_RESULTS_LEASE_SECONDS", "900")
)

PLAYWRIGHT_TIMEOUT_S = 60
EVENT_PAGE_READY_SELECTOR = "tr.b-fight-details__table-row"

# Bounded in-command retry policy (issue 038).
RETRY_MAX_ATTEMPTS = int(os.getenv("LIVE_EVENT_RESULTS_RETRY_MAX_ATTEMPTS", "3"))
RETRY_BACKOFF_BASE_S = float(
    os.getenv("LIVE_EVENT_RESULTS_RETRY_BACKOFF_BASE_S", "1")
)
RETRY_BACKOFF_CAP_S = float(
    os.getenv("LIVE_EVENT_RESULTS_RETRY_BACKOFF_CAP_S", "8")
)
RETRY_JITTER_RATIO = float(
    os.getenv("LIVE_EVENT_RESULTS_RETRY_JITTER_RATIO", "0.25")
)
RETRY_AFTER_MAX_S = float(
    os.getenv("LIVE_EVENT_RESULTS_RETRY_AFTER_MAX_S", "30")
)

# Backward-compatible aliases used by earlier handoff code/tests.
HANDOFF_MAX_ATTEMPTS = RETRY_MAX_ATTEMPTS
HANDOFF_BACKOFF_BASE_S = RETRY_BACKOFF_BASE_S

# Card-change rescrape cooldown and publication bound (issue 037).
RESCRAPE_COOLDOWN_SECONDS = int(
    os.getenv("LIVE_EVENT_RESULTS_RESCRAPE_COOLDOWN_SECONDS", "1800")
)
RESCRAPE_MAX_PUBLICATIONS = int(
    os.getenv("LIVE_EVENT_RESULTS_RESCRAPE_MAX_PUBLICATIONS", "3")
)
