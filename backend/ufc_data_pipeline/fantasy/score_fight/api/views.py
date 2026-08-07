"""Pub/Sub push HTTP endpoint for score-fight jobs."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ufc_data_pipeline.fantasy.score_fight.api.resolver import (
    resolve_score_fight_message,
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
def score_fight_pubsub_push(request: HttpRequest) -> HttpResponse:
    try:
        decoded = decode_pubsub_push_request(request.body)
        result = resolve_score_fight_message(decoded.message_id, decoded.payload)
    except (PubSubPushDecodeError, PayloadValidationError) as exc:
        logger.warning("Dropping invalid score-fight push message: %s", exc)
        return HttpResponse(status=204)
    except Exception:
        logger.exception("Unexpected error handling score-fight push")
        return HttpResponse(status=500)

    if result is DeliveryResult.RETRY:
        return HttpResponse(status=500)
    return HttpResponse(status=204)
