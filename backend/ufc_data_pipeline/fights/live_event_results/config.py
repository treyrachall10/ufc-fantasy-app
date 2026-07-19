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

# In-command retries for transition/publish boundaries (issue 035).
HANDOFF_MAX_ATTEMPTS = int(os.getenv("LIVE_EVENT_RESULTS_HANDOFF_MAX_ATTEMPTS", "3"))
HANDOFF_BACKOFF_BASE_S = float(
    os.getenv("LIVE_EVENT_RESULTS_HANDOFF_BACKOFF_BASE_S", "1")
)

# Card-change rescrape cooldown and publication bound (issue 037).
RESCRAPE_COOLDOWN_SECONDS = int(
    os.getenv("LIVE_EVENT_RESULTS_RESCRAPE_COOLDOWN_SECONDS", "1800")
)
RESCRAPE_MAX_PUBLICATIONS = int(
    os.getenv("LIVE_EVENT_RESULTS_RESCRAPE_MAX_PUBLICATIONS", "3")
)
