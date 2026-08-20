"""Tests for fights-in-event message processor and resolver."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.utils import timezone

from fantasy.models import Events
from ufc_data_pipeline.fights.fights_in_event.api.resolver import (
    resolve_fights_in_event_message,
)
from ufc_data_pipeline.fights.fights_in_event.message_processor import (
    process_fights_in_event_message,
)
from ufc_data_pipeline.models import FightCreationJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError


def _mock_playwright(html: str = "<html></html>") -> MagicMock:
    page = MagicMock()
    page.content.return_value = html
    browser = MagicMock()
    browser.new_page.return_value = page
    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser
    cm = MagicMock()
    cm.__enter__.return_value = playwright
    return cm


class ResolveFightsInEventMessageTests(TestCase):
    def test_missing_url_raises_payload_validation_error(self) -> None:
        with pytest.raises(PayloadValidationError, match="url is required"):
            resolve_fights_in_event_message("msg-1", {"event_id": 1})

    def test_empty_url_raises_payload_validation_error(self) -> None:
        with pytest.raises(PayloadValidationError, match="url is empty"):
            resolve_fights_in_event_message("msg-1", {"url": "  ", "event_id": 1})

    def test_non_string_url_raises_payload_validation_error(self) -> None:
        with pytest.raises(PayloadValidationError, match="url must be a string"):
            resolve_fights_in_event_message("msg-1", {"url": 123, "event_id": 1})

    def test_missing_event_id_raises_payload_validation_error(self) -> None:
        with pytest.raises(PayloadValidationError, match="event_id is required"):
            resolve_fights_in_event_message(
                "msg-1",
                {"url": "http://ufcstats.com/event-details/abc"},
            )

    def test_non_integer_event_id_raises_payload_validation_error(self) -> None:
        with pytest.raises(PayloadValidationError, match="event_id must be an integer"):
            resolve_fights_in_event_message(
                "msg-1",
                {"url": "http://ufcstats.com/event-details/abc", "event_id": "nope"},
            )


class ProcessFightsInEventMessageTests(TestCase):
    def setUp(self) -> None:
        self.event = Events.objects.create(
            event="Processor Event",
            date="2026-01-01",
            location="Test",
        )
        self.url = "http://ufcstats.com/event-details/processor-event"

    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.process_fights_in_event")
    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.sync_playwright")
    def test_success_marks_job_completed_and_acknowledges(
        self,
        sync_playwright_mock: MagicMock,
        process_mock: MagicMock,
    ) -> None:
        sync_playwright_mock.return_value = _mock_playwright()

        result = process_fights_in_event_message("msg-success", self.url, self.event.event_id)

        assert result == DeliveryResult.ACKNOWLEDGE
        job = FightCreationJob.objects.get(event_id=self.event.event_id)
        assert job.status == FightCreationJob.Status.COMPLETED
        assert job.pubsub_message_id == "msg-success"
        assert job.completed_at is not None
        process_mock.assert_called_once()

    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.process_fights_in_event")
    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.sync_playwright")
    def test_skip_when_claim_returns_none(
        self,
        sync_playwright_mock: MagicMock,
        process_mock: MagicMock,
    ) -> None:
        FightCreationJob.objects.create(
            event=self.event,
            url=self.url,
            ran_at=timezone.now(),
            status=FightCreationJob.Status.COMPLETED,
            pubsub_message_id="msg-dup",
        )

        result = process_fights_in_event_message("msg-dup", self.url, self.event.event_id)

        assert result == DeliveryResult.ACKNOWLEDGE
        process_mock.assert_not_called()
        sync_playwright_mock.assert_not_called()
        assert FightCreationJob.objects.filter(event_id=self.event.event_id).count() == 1

    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.process_fights_in_event")
    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.sync_playwright")
    def test_retriable_failure_returns_retry(
        self,
        sync_playwright_mock: MagicMock,
        process_mock: MagicMock,
    ) -> None:
        sync_playwright_mock.return_value = _mock_playwright()
        process_mock.side_effect = RuntimeError("temporary failure")

        result = process_fights_in_event_message("msg-retry", self.url, self.event.event_id)

        assert result == DeliveryResult.RETRY
        job = FightCreationJob.objects.get(event_id=self.event.event_id)
        assert job.status == FightCreationJob.Status.RETRYING
        assert job.retry_count == 1

    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.process_fights_in_event")
    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.sync_playwright")
    def test_max_retries_marks_failed_and_acknowledges(
        self,
        sync_playwright_mock: MagicMock,
        process_mock: MagicMock,
    ) -> None:
        sync_playwright_mock.return_value = _mock_playwright()
        process_mock.side_effect = RuntimeError("permanent failure")
        FightCreationJob.objects.create(
            event=self.event,
            url=self.url,
            ran_at=timezone.now(),
            status=FightCreationJob.Status.RETRYING,
            retry_count=2,
            pubsub_message_id="msg-max",
        )

        result = process_fights_in_event_message("msg-max", self.url, self.event.event_id)

        assert result == DeliveryResult.ACKNOWLEDGE
        job = FightCreationJob.objects.get(pubsub_message_id="msg-max")
        assert job.status == FightCreationJob.Status.FAILED
        assert job.retry_count == 3

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.message_processor.process_fights_in_event"
    )
    @patch("ufc_data_pipeline.fights.fights_in_event.message_processor.sync_playwright")
    def test_invalid_payload_rejected_by_resolver_before_processor(
        self,
        sync_playwright_mock: MagicMock,
        process_mock: MagicMock,
    ) -> None:
        with pytest.raises(PayloadValidationError):
            resolve_fights_in_event_message("msg-bad", {"url": "", "event_id": self.event.event_id})

        process_mock.assert_not_called()
        sync_playwright_mock.assert_not_called()
        assert FightCreationJob.objects.filter(event_id=self.event.event_id).count() == 0

    @patch(
        "ufc_data_pipeline.fights.fights_in_event.api.resolver.process_fights_in_event_message"
    )
    def test_resolver_delegates_valid_payload(self, processor_mock: MagicMock) -> None:
        processor_mock.return_value = DeliveryResult.ACKNOWLEDGE

        result = resolve_fights_in_event_message(
            "msg-valid",
            {
                "url": self.url,
                "event_id": self.event.event_id,
                "reason": "card_change",
                "fingerprint": "fp-1",
            },
        )

        assert result == DeliveryResult.ACKNOWLEDGE
        processor_mock.assert_called_once_with("msg-valid", self.url, self.event.event_id)
