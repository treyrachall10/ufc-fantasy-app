"""Configuration for the score-fight pipeline stage."""

from __future__ import annotations

import os


PIPELINE_API_BASE_URL = os.getenv("PIPELINE_API_BASE_URL", "http://web:8000")
PIPELINE_SERVICE_API_KEY = os.getenv("PIPELINE_SERVICE_API_KEY", "")
