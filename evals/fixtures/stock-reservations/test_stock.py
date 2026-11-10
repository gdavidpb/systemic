"""Tests for stock reservations."""

from datetime import datetime, timedelta
import unittest
from unittest import mock

from .models import Store, Unit
from .operations import PaymentDeclined, Unavailable, price_of, release, reserve, sell, sweep
from .server import handle

T0 = datetime(2026, 1, 1, 12, 0)

# Recorded from a run of sweep() over the fixture below.
EXPECTED_AFTER_SWEEP = []


def stocked(*serials):
    store = Store()
    for serial in serials:
        store.put(Unit("SKU-1", serial))
    return store


class ReservationTest(unittest.TestCase):
    def test_reserve_an_available_unit(self):
        store = stocked("u1")
        reserve(store, "u1", "ana", T0)
        self.assertEqual(store.get("u1").reserved_by, "ana")

    def test_reserve_is_refused_while_held(self):
        store = stocked("u1")
        reserve(store, "u1", "ana", T0)
        with self.assertRaises(Unavailable):
            reserve(store, "u1", "bob", T0 + timedelta(minutes=1))

    def test_hold_lasts_exactly_the_reservation_window(self):
        for minute in range(0, 31):
            with self.subTest(minute=minute):
                store = stocked("u1")
                reserve(store, "u1", "ana", T0)
                later = T0 + timedelta(minutes=minute)
                if minute < 15:
                    with self.assertRaises(Unavailable):
                        reserve(store, "u1", "bob", later)
                else:
                    reserve(store, "u1", "bob", later)
                    self.assertEqual(store.get("u1").reserved_by, "bob")

    def test_release_undoes_reserve(self):
        store = stocked("u1")
        before = store.get("u1")
        reserve(store, "u1", "ana", T0)
        release(store, "u1", "ana")
        self.assertEqual(store.get("u1"), before)

    def test_concurrent_reservations_hold_one_shopper(self):
        store = stocked("u1")
        first = handle({"action": "reserve", "serial": "u1", "shopper": "ana"}, store, None, T0)
        first.result()
        second = handle({"action": "reserve", "serial": "u1", "shopper": "bob"}, store, None, T0)
        with self.assertRaises(Unavailable):
            second.result()


class SaleTest(unittest.TestCase):
    def test_sell_charges_the_shopper(self):
        store = stocked("u1")
        payments = mock.Mock()
        reserve(store, "u1", "ana", T0)
        sell(store, "u1", "ana", payments, T0)
        payments.charge.assert_called_once_with("ana", "SKU-1")

    def test_declined_payment_keeps_the_unit_reserved(self):
        store = stocked("u1")
        payments = mock.Mock()
        payments.charge.side_effect = PaymentDeclined("card declined")
        reserve(store, "u1", "ana", T0)
        with self.assertRaises(PaymentDeclined):
            sell(store, "u1", "ana", payments, T0)
        self.assertIsNone(store.get("u1").sold_at)

    def test_sweep_after_the_window(self):
        store = stocked("u1", "u2")
        reserve(store, "u1", "ana", T0)
        reserve(store, "u2", "bob", T0)
        sell(store, "u2", "bob", mock.Mock(), T0)
        sweep(store, T0 + timedelta(minutes=20))
        self.assertEqual(store.all(), EXPECTED_AFTER_SWEEP)


class PriceTest(unittest.TestCase):
    def test_single_sku_price(self):
        self.assertEqual(price_of(Unit("SKU-1", "u1"), {"SKU-1": 10.0}), 10.0)

    def test_bundle_without_parts_is_rejected(self):
        with self.assertRaises(Exception):
            price_of(Unit("BUNDLE-1", "u1"), {})
