"""
Decode Google Pub/Sub push HTTP envelopes.

Parses the wrapped push JSON body, extracts ``message_id``, base64-decodes
``message.data``, and parses the JSON payload. Contains no worker selection
or domain business logic.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from typing import Any


class PubSubPushDecodeError(ValueError):
    """Raised when a Pub/Sub push request body is malformed."""


@dataclass(frozen=True, slots=True)
class DecodedPubSubPushMessage:
    message_id: str
    payload: dict[str, Any]


def decode_pubsub_push_request(body: bytes | str | dict[str, Any]) -> DecodedPubSubPushMessage:
    """
    Decode a Pub/Sub push HTTP body into ``message_id`` and JSON payload.

    Accepts raw request bytes/str or an already-parsed JSON object.
    """
    envelope = _parse_envelope(body)
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise PubSubPushDecodeError("Push body must contain a JSON object field 'message'")

    message_id = message.get("messageId")
    if message_id is None:
        message_id = message.get("message_id")
    if not isinstance(message_id, str) or not message_id.strip():
        raise PubSubPushDecodeError("Push message must include a non-empty messageId")

    raw_data = message.get("data")
    if raw_data is None:
        raise PubSubPushDecodeError("Push message must include a 'data' field")
    if not isinstance(raw_data, str):
        raise PubSubPushDecodeError("Push message 'data' must be a base64-encoded string")

    try:
        decoded_bytes = base64.b64decode(raw_data, validate=True)
    except binascii.Error as exc:
        raise PubSubPushDecodeError("Push message 'data' is not valid base64") from exc

    try:
        payload = json.loads(decoded_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise PubSubPushDecodeError("Push message data is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise PubSubPushDecodeError("Push message data is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise PubSubPushDecodeError("Push message JSON payload must be a JSON object")

    return DecodedPubSubPushMessage(message_id=message_id.strip(), payload=payload)


def _parse_envelope(body: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(body, dict):
        return body

    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PubSubPushDecodeError("Push body is not valid UTF-8") from exc
    elif isinstance(body, str):
        text = body
    else:
        raise PubSubPushDecodeError("Push body must be bytes, str, or dict")

    if not text.strip():
        raise PubSubPushDecodeError("Push body is empty")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PubSubPushDecodeError("Push body is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise PubSubPushDecodeError("Push body must be a JSON object")

    return parsed
