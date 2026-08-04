"""
Tests for Live Event Results bounded retry classification and backoff.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from ufc_data_pipeline.fights.live_event_results.api_client import ApiClientError
from ufc_data_pipeline.fights.live_event_results.retry import (
    LeaseOwnerLostError,
    PermanentError,
    TransportError,
    call_with_retries,
    compute_backoff_seconds,
    is_retryable_exception,
    is_retryable_status,
    parse_retry_after,
)


class RetryClassificationTests(SimpleTestCase):
    def test_status_table(self) -> None:
        cases = [
            (None, False),
            (400, False),
            (401, False),
            (403, False),
            (404, False),
            (408, True),
            (409, False),
            (429, True),
            (500, True),
            (502, True),
            (503, True),
        ]
        for status, expected in cases:
            assert is_retryable_status(status) is expected, status

    def test_exception_table(self) -> None:
        cases = [
            (PermanentError("config"), False),
            (LeaseOwnerLostError("stale"), False),
            (ValueError("bad"), False),
            (TransportError("down"), True),
            (TimeoutError("t"), True),
            (RuntimeError("pubsub"), True),
            (ApiClientError("bad", status_code=400), False),
            (ApiClientError("conflict", status_code=409), False),
            (ApiClientError("too many", status_code=429, retry_after_seconds=2), True),
            (ApiClientError("server", status_code=503), True),
        ]
        for exc, expected in cases:
            assert is_retryable_exception(exc) is expected, repr(exc)


class RetryAfterAndBackoffTests(SimpleTestCase):
    def test_parse_retry_after_bounds(self) -> None:
        assert parse_retry_after(None) is None
        assert parse_retry_after("abc") is None
        assert parse_retry_after("1.5") == 1.5
        assert parse_retry_after("999", max_seconds=30) == 30

    def test_backoff_exponential_with_deterministic_jitter(self) -> None:
        # rng always 0.5 => factor 1.0 (no jitter swing)
        delays = [
            compute_backoff_seconds(
                attempt,
                base_seconds=1,
                cap_seconds=8,
                jitter_ratio=0.25,
                rng=lambda: 0.5,
            )
            for attempt in (1, 2, 3)
        ]
        assert delays == [1.0, 2.0, 4.0]

    def test_retry_after_raises_floor(self) -> None:
        delay = compute_backoff_seconds(
            1,
            base_seconds=1,
            cap_seconds=8,
            jitter_ratio=0,
            retry_after_seconds=5,
        )
        assert delay == 5


class CallWithRetriesTests(SimpleTestCase):
    def test_retries_retryable_then_succeeds(self) -> None:
        sleeps: list[float] = []
        fn = MagicMock(
            side_effect=[TransportError("1"), TransportError("2"), "ok"]
        )
        result = call_with_retries(
            "op",
            fn,
            max_attempts=3,
            sleep_fn=sleeps.append,
            rng=lambda: 0.5,
        )
        assert result == "ok"
        assert fn.call_count == 3
        assert sleeps == [1.0, 2.0]

    def test_does_not_retry_permanent(self) -> None:
        fn = MagicMock(side_effect=PermanentError("nope"))
        with self.assertRaises(PermanentError):
            call_with_retries("op", fn, max_attempts=3, sleep_fn=lambda _d: None)
        assert fn.call_count == 1

    def test_honors_retry_after_on_api_error(self) -> None:
        sleeps: list[float] = []
        fn = MagicMock(
            side_effect=[
                ApiClientError("rate", status_code=429, retry_after_seconds=3),
                "ok",
            ]
        )
        result = call_with_retries(
            "op",
            fn,
            max_attempts=3,
            sleep_fn=sleeps.append,
            rng=lambda: 0.5,
        )
        assert result == "ok"
        assert sleeps == [3.0]

    def test_exhausts_after_three_attempts(self) -> None:
        fn = MagicMock(side_effect=RuntimeError("still down"))
        with self.assertRaises(RuntimeError):
            call_with_retries(
                "op",
                fn,
                max_attempts=3,
                sleep_fn=lambda _d: None,
            )
        assert fn.call_count == 3
