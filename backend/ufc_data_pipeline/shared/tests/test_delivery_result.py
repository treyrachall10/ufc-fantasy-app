"""Tests for shared DeliveryResult enum."""

from ufc_data_pipeline.shared.delivery_result import DeliveryResult


def test_delivery_result_values() -> None:
    assert DeliveryResult.ACKNOWLEDGE.value == "acknowledge"
    assert DeliveryResult.RETRY.value == "retry"
    assert set(DeliveryResult) == {DeliveryResult.ACKNOWLEDGE, DeliveryResult.RETRY}
