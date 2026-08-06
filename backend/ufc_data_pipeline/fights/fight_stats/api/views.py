"""HTTP push adapter for fight-stats Pub/Sub deliveries."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ufc_data_pipeline.fights.fight_stats.api.resolver import resolve_fight_stats_message
from ufc_data_pipeline.shared.delivery_result import DeliveryResult
from ufc_data_pipeline.shared.payload_validation import PayloadValidationError
from ufc_data_pipeline.shared.pubsub_message_decoder import (
    PubSubPushDecodeError,
    decode_pubsub_push_request,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def fight_stats_push_view(request: HttpRequest) -> HttpResponse:
    """Decode a Pub/Sub push envelope and process one fight-stats delivery."""
    try:
        decoded = decode_pubsub_push_request(request.body)
        result = resolve_fight_stats_message(decoded.message_id, decoded.payload)
    except (PubSubPushDecodeError, PayloadValidationError):
        return HttpResponse(status=204)
    except Exception:
        logger.exception("Unexpected fight-stats push handler failure")
        return HttpResponse(status=500)

    if result is DeliveryResult.RETRY:
        return HttpResponse(status=500)
    return HttpResponse(status=204)
