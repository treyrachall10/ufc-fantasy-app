"""
Process one fights-in-event Pub/Sub delivery without transport ack/nack.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup
from django.db import transaction
from django.utils import timezone
from playwright.sync_api import sync_playwright

from ufc_data_pipeline.models import FightCreationJob
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.job_claim import claim_pubsub_job

from .service import process_fights_in_event

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_S = 60
_MAX_RETRY_COUNT_BEFORE_FAIL = 3


def _scrape_event_page(url: str) -> BeautifulSoup:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, timeout=_REQUEST_TIMEOUT_S * 1000)
            page.wait_for_selector(
                ".b-fight-details__table-row",
                timeout=_REQUEST_TIMEOUT_S * 1000,
            )
            html = page.content()
            return BeautifulSoup(html, "html.parser")
        finally:
            browser.close()


def process_fights_in_event_message(
    message_id: str,
    url: str,
    event_id: int,
) -> DeliveryResult:
    """
    Claim a job, scrape the event page, reconcile fights, and update job status.
    """
    job = claim_pubsub_job(
        model=FightCreationJob,
        message_id=message_id,
        logical_filters={"event_id": event_id},
        create_kwargs={"url": url, "event_id": event_id},
        retry_update_fields={"url": url},
    )
    if job is None:
        return DeliveryResult.ACKNOWLEDGE

    try:
        soup = _scrape_event_page(job.url)
        process_fights_in_event(soup, job.event_id)

        with transaction.atomic():
            job.status = FightCreationJob.Status.COMPLETED
            job.completed_at = timezone.now()
            job.error_msg = ""
            job.save(update_fields=["status", "completed_at", "error_msg"])

        return DeliveryResult.ACKNOWLEDGE
    except Exception as exc:
        err_text = str(exc)
        logger.exception("Fight creation failed for job id=%s", job.pk)
        job.retry_count += 1
        job.error_msg = err_text
        if job.retry_count >= _MAX_RETRY_COUNT_BEFORE_FAIL:
            job.status = FightCreationJob.Status.FAILED
            job.save(update_fields=["retry_count", "error_msg", "status"])
            return DeliveryResult.ACKNOWLEDGE

        job.status = FightCreationJob.Status.RETRYING
        job.save(update_fields=["retry_count", "error_msg", "status"])
        return DeliveryResult.RETRY
