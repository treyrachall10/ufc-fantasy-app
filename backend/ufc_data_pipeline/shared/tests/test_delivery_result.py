"""Tests for shared DeliveryResult enum."""

import unittest

from ufc_data_pipeline.shared.delivery_result import DeliveryResult


class DeliveryResultTests(unittest.TestCase):
    def test_delivery_result_values(self) -> None:
        self.assertEqual(DeliveryResult.ACKNOWLEDGE.value, "acknowledge")
        self.assertEqual(DeliveryResult.RETRY.value, "retry")
        self.assertEqual(
            set(DeliveryResult),
            {DeliveryResult.ACKNOWLEDGE, DeliveryResult.RETRY},
        )
