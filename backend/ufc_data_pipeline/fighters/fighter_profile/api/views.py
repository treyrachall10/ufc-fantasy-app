"""CSRF-exempt Pub/Sub push view for fighter profile deliveries."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.shared.pubsub_message_decoder import (
    PubSubPushDecodeError,
    decode_pubsub_push_request,
)

from .resolver import resolve_fighter_profile_message

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def fighter_profile_pubsub_push(request: HttpRequest) -> HttpResponse:
    """Decode a Pub/Sub push envelope and run fighter profile processing."""
    try:
        decoded = decode_pubsub_push_request(request.body)
    except PubSubPushDecodeError as exc:
        logger.exception("Invalid Pub/Sub push envelope: %s", exc)
        return HttpResponse(status=204)

    try:
        result = resolve_fighter_profile_message(decoded.message_id, decoded.payload)
    except PayloadValidationError as exc:
        logger.exception("Invalid fighter profile payload: %s", exc)
        return HttpResponse(status=204)

    if result is DeliveryResult.RETRY:
        return HttpResponse(status=500)
    return HttpResponse(status=204)
