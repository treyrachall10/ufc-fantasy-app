"""Shared Pub/Sub delivery outcome for pull and push adapters."""

from __future__ import annotations

from enum import Enum


class DeliveryResult(Enum):
    """Whether the transport should acknowledge/drop or request redelivery."""

    ACKNOWLEDGE = "acknowledge"
    RETRY = "retry"
