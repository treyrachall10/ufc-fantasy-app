"""Shared validation error for domain Pub/Sub payloads."""


class PayloadValidationError(ValueError):
    """Raised when required payload fields are missing or the wrong type."""
