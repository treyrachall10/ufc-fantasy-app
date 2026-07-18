"""
Backward-compatible re-exports from ``events.shared``.

Prefer importing from ``ufc_data_pipeline.events.shared`` for new code.
"""

from ufc_data_pipeline.events.shared.config import URL
from ufc_data_pipeline.events.shared.parser import Event, parse_completed_events_after

__all__ = ["URL", "Event", "parse_completed_events_after"]
