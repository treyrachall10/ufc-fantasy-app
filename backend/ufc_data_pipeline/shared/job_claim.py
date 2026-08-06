"""
Shared Pub/Sub job claim helpers for pipeline workers.

Claim rules (all Pub/Sub job tables):
- Same ``pubsub_message_id`` already exists and is not ``RETRYING`` → skip (ack).
- Same ``pubsub_message_id`` in ``RETRYING`` → reclaim that row.
- Different message id, but ``PENDING``/``RUNNING`` exists for the logical key → skip.
- ``RETRYING`` for the logical key → reclaim and bind the new message id.
- Only ``COMPLETED``/``FAILED`` (or no rows) → create a new job (intentional rescrape).
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Model
from django.utils import timezone

from ufc_data_pipeline.models import BaseJobModel

logger = logging.getLogger(__name__)

# Statuses that block a second concurrent logical job (different message id).
ACTIVE_BLOCK_STATUSES = (
    BaseJobModel.Status.PENDING,
    BaseJobModel.Status.RUNNING,
)


def claim_pubsub_job(
    *,
    model: type[Model],
    message_id: str,
    logical_filters: dict[str, Any],
    create_kwargs: dict[str, Any],
    retry_update_fields: dict[str, Any] | None = None,
) -> Model | None:
    """
    Claim a job row for one Pub/Sub delivery, or return None to ack-and-skip.

    ``logical_filters`` identify the business key (e.g. ``{"fight_id": 1}``).
    ``create_kwargs`` are model fields for a new RUNNING row (excluding status /
    ran_at / retry_count / error_msg / pubsub_message_id, which are set here).
    """
    if not message_id:
        raise ValueError("message_id is required")

    retry_updates = dict(retry_update_fields or {})

    with transaction.atomic():
        existing = (
            model.objects.select_for_update()
            .filter(pubsub_message_id=message_id)
            .first()
        )
        # Check if the message_id already exists and is not RETRYING
        if existing is not None:
            # If the message_id already exists and is RETRYING, reclaim the job
            if existing.status == BaseJobModel.Status.RETRYING:
                return _reclaim_retrying(
                    existing,
                    message_id=message_id,
                    retry_updates=retry_updates,
                )
            # If the message_id already exists and is not RETRYING, skip the job
            logger.info(
                "Skipping %s; pubsub_message_id=%s already status=%s",
                model.__name__,
                message_id,
                existing.status,
            )
            return None

        # Check if there is a PENDING/RUNNING job for the logical key
        if (
            model.objects.select_for_update()
            .filter(**logical_filters, status__in=ACTIVE_BLOCK_STATUSES)
            .exists()
        ):
            logger.info(
                "Skipping %s; active PENDING/RUNNING job exists filters=%s",
                model.__name__,
                logical_filters,
            )
            return None

        # Check if there is a RETRYING job for the logical key
        retrying = (
            model.objects.select_for_update()
            .filter(**logical_filters, status=BaseJobModel.Status.RETRYING)
            .order_by("-ran_at")
            .first()
        )
        if retrying is not None:
            # If a RETRYING job exists, reclaim the job
            return _reclaim_retrying(
                retrying,
                message_id=message_id,
                retry_updates=retry_updates,
            )

        # If no job exists, create a new job
        try:
            return model.objects.create(
                pubsub_message_id=message_id,
                ran_at=timezone.now(),
                status=BaseJobModel.Status.RUNNING,
                retry_count=0,
                error_msg="",
                **create_kwargs,
            )
        except IntegrityError:
            # Only treat uniqueness races as skip; other integrity errors (FK, etc.)
            # should propagate so the consumer can nack/retry.
            if (
                model.objects.filter(pubsub_message_id=message_id).exists()
                or model.objects.filter(
                    **logical_filters,
                    status__in=(
                        *ACTIVE_BLOCK_STATUSES,
                        BaseJobModel.Status.RETRYING,
                    ),
                ).exists()
            ):
                logger.info(
                    "Skipping %s; concurrent claim lost filters=%s message_id=%s",
                    model.__name__,
                    logical_filters,
                    message_id,
                )
                return None
            raise


def _reclaim_retrying(
    job: Model,
    *,
    message_id: str,
    retry_updates: dict[str, Any],
) -> Model:
    job.status = BaseJobModel.Status.RUNNING
    job.pubsub_message_id = message_id
    job.error_msg = ""
    update_fields = ["status", "pubsub_message_id", "error_msg"]
    for field, value in retry_updates.items():
        setattr(job, field, value)
        update_fields.append(field)
    job.save(update_fields=update_fields)
    return job
