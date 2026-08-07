"""Pub/Sub push HTTP endpoint for career-stats jobs."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ufc_data_pipeline.fighters.career_stats.api.resolver import (
    resolve_career_stats_message,
)
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.shared.pubsub_message_decoder import (
    PubSubPushDecodeError,
    decode_pubsub_push_request,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def career_stats_pubsub_push(request: HttpRequest) -> HttpResponse:
    try:
        decoded = decode_pubsub_push_request(request.body)
        result = resolve_career_stats_message(decoded.message_id, decoded.payload)
    except (PubSubPushDecodeError, PayloadValidationError) as exc:
        logger.warning("Dropping invalid career-stats push message: %s", exc)
        return HttpResponse(status=204)
    except Exception:
        logger.exception("Unexpected error handling career-stats push")
        return HttpResponse(status=500)

    if result is DeliveryResult.RETRY:
        return HttpResponse(status=500)
    return HttpResponse(status=204)
