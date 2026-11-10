"""Tests for the orders module."""

import unittest

from .models import Item, Order, calc_total
from .operations import add_item, cancel, checkout, deliver, mark_paid, refund, ship
from .webhook import handle_payment_webhook


class FakeInventory:
    def __init__(self):
        self.reserved = []

    def reserve(self, items):
        self.reserved.extend(items)


class FakeCourier:
    def __init__(self):
        self.notified = []

    def notify(self, order_id):
        self.notified.append(order_id)


def placed_order():
    order = Order("o-1")
    add_item(order, Item("SKU-1", 2, 10.0))
    checkout(order)
    return order


class OrderLifecycleTest(unittest.TestCase):
    def test_checkout_totals_the_items(self):
        order = placed_order()
        self.assertEqual(order.status, "pending_payment")
        self.assertEqual(order.total, calc_total(order))

    def test_cancel_a_pending_order(self):
        order = placed_order()
        cancel(order)
        self.assertEqual(order.status, "canceled")

    def test_ship_then_deliver(self):
        order = placed_order()
        mark_paid(order)
        inventory, courier = FakeInventory(), FakeCourier()
        ship(order, inventory, courier)
        deliver(order)
        self.assertEqual(order.status, "delivered")
        self.assertEqual(courier.notified, ["o-1"])

    def test_deliver_rejects_an_unshipped_order(self):
        order = placed_order()
        with self.assertRaises(ValueError):
            deliver(order)

    def test_refund_moves_the_order_to_refund_pending(self):
        order = placed_order()
        mark_paid(order)
        refund(order)
        self.assertEqual(order.status, "refund_pending")


class PaymentWebhookTest(unittest.TestCase):
    def test_full_payment_marks_the_order_paid(self):
        order = placed_order()
        handle_payment_webhook(order, {"id": "evt-1", "amount": 20.0})
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.total_paid, 20.0)
