"""Tests for Pub/Sub push HTTP envelope decoding."""

from __future__ import annotations

import base64
import json
import unittest

from ufc_data_pipeline.shared.pubsub_message_decoder import (
    DecodedPubSubPushMessage,
    PubSubPushDecodeError,
    decode_pubsub_push_request,
)


def _envelope(*, payload: dict, message_id: str = "2070443601311540") -> dict:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {
        "message": {
            "data": data,
            "messageId": message_id,
            "message_id": message_id,
        },
        "subscription": "projects/demo/subscriptions/demo-sub",
    }


class PubSubMessageDecoderTests(unittest.TestCase):
    def test_decode_valid_push_envelope(self) -> None:
        body = _envelope(payload={"fight_id": 42})

        decoded = decode_pubsub_push_request(json.dumps(body).encode("utf-8"))

        self.assertEqual(
            decoded,
            DecodedPubSubPushMessage(
                message_id="2070443601311540",
                payload={"fight_id": 42},
            ),
        )

    def test_decode_accepts_already_parsed_dict(self) -> None:
        body = _envelope(payload={"url": "http://example.com", "event_id": 1})

        decoded = decode_pubsub_push_request(body)

        self.assertEqual(decoded.message_id, "2070443601311540")
        self.assertEqual(decoded.payload, {"url": "http://example.com", "event_id": 1})

    def test_decode_accepts_message_id_snake_case_only(self) -> None:
        data = base64.b64encode(b'{"fight_id": 1}').decode("ascii")
        body = {"message": {"data": data, "message_id": "snake-id"}}

        decoded = decode_pubsub_push_request(body)

        self.assertEqual(decoded.message_id, "snake-id")

    def test_decode_rejects_empty_body(self) -> None:
        with self.assertRaisesRegex(PubSubPushDecodeError, "empty"):
            decode_pubsub_push_request(b"")

    def test_decode_rejects_non_json_body(self) -> None:
        with self.assertRaisesRegex(PubSubPushDecodeError, "not valid JSON"):
            decode_pubsub_push_request(b"not-json")

    def test_decode_rejects_missing_message(self) -> None:
        with self.assertRaisesRegex(PubSubPushDecodeError, "message"):
            decode_pubsub_push_request({"subscription": "projects/x/subscriptions/y"})

    def test_decode_rejects_missing_message_id(self) -> None:
        data = base64.b64encode(b'{"fight_id": 1}').decode("ascii")
        with self.assertRaisesRegex(PubSubPushDecodeError, "messageId"):
            decode_pubsub_push_request({"message": {"data": data}})

    def test_decode_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(PubSubPushDecodeError, "base64"):
            decode_pubsub_push_request(
                {"message": {"data": "!!!not-base64!!!", "messageId": "m1"}}
            )

    def test_decode_rejects_non_json_payload(self) -> None:
        data = base64.b64encode(b"not-json").decode("ascii")
        with self.assertRaisesRegex(PubSubPushDecodeError, "not valid JSON"):
            decode_pubsub_push_request({"message": {"data": data, "messageId": "m1"}})

    def test_decode_rejects_non_object_json_payload(self) -> None:
        data = base64.b64encode(b"[1, 2, 3]").decode("ascii")
        with self.assertRaisesRegex(PubSubPushDecodeError, "JSON object"):
            decode_pubsub_push_request({"message": {"data": data, "messageId": "m1"}})
