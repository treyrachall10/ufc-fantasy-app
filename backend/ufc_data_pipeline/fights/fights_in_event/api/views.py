"""
CSRF-exempt Pub/Sub push endpoint for fights-in-event deliveries.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.shared.pubsub_message_decoder import (
    PubSubPushDecodeError,
    decode_pubsub_push_request,
)

from .resolver import resolve_fights_in_event_message

logger = logging.getLogger(__name__)


@csrf_exempt
def pubsub_push(request: HttpRequest) -> HttpResponse:
    try:
        decoded = decode_pubsub_push_request(request.body)
    except PubSubPushDecodeError:
        logger.exception("Malformed Pub/Sub push envelope")
        return HttpResponse(status=204)

    try:
        result = resolve_fights_in_event_message(
            decoded.message_id,
            decoded.payload,
        )
    except PayloadValidationError:
        logger.exception("Invalid fights-in-event push payload")
        return HttpResponse(status=204)
    except Exception:
        logger.exception("Unexpected fights-in-event push processing error")
        return HttpResponse(status=500)

    if result == DeliveryResult.ACKNOWLEDGE:
        return HttpResponse(status=204)

    return HttpResponse(status=500)
