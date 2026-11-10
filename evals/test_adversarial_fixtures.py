"""Verify causal counterexamples in intentionally defective audit fixtures.

These tests preserve the evals' ground truth; they do not grade an LLM report.
All providers are local doubles. Logical time is assumed, never measured.
"""
from contextlib import contextmanager
import importlib
import itertools
from pathlib import Path
import sys
import types
import unittest


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PACKAGES = itertools.count()


def fixture(name, *modules):
    package_name = f"_systemic_probe_{next(PACKAGES)}"
    package = types.ModuleType(package_name)
    package.__path__ = [str(FIXTURES / name)]
    sys.modules[package_name] = package
    return tuple(importlib.import_module(f"{package_name}.{module}") for module in modules)


class AdversarialFixtures(unittest.TestCase):
    def invoices(self):
        models, operations, api, hooks = fixture(
            "guarded-elsewhere", "models", "operations", "api", "webhooks"
        )
        invoice = models.Invoice("invoice-1")
        operations.add_line(invoice, models.LineItem("SKU", 1, 100))
        return invoice, operations, api, hooks

    def test_successful_payment_replay_is_deduplicated(self):
        invoice, operations, _, hooks = self.invoices()
        operations.issue(invoice)
        event = {"id": "P1", "amount": 100}
        hooks.ROUTES["/webhooks/payment"](invoice, event)
        paid_at = invoice.paid_at
        self.assertEqual(hooks.ROUTES["/webhooks/payment"](invoice, event), "duplicate")
        self.assertEqual((invoice.status, invoice.paid_at), ("paid", paid_at))

    def test_retained_line_item_alias_can_drift_an_issued_total(self):
        models, operations = fixture("guarded-elsewhere", "models", "operations")
        invoice = models.Invoice("invoice-aliased-item")
        retained = models.LineItem("SKU", 1, 100)
        operations.add_line(invoice, retained)
        self.assertEqual(invoice.total, 100)
        operations.issue(invoice)
        retained.qty = 2
        self.assertEqual(invoice.total, 100)
        self.assertEqual(sum(item.qty * item.unit_price for item in invoice.items), 200)

    def test_failed_payment_marks_event_before_success(self):
        invoice, operations, api, hooks = self.invoices()
        event = {"id": "P1", "amount": 100}
        with self.assertRaises(api.InvalidStatus):
            hooks.ROUTES["/webhooks/payment"](invoice, event)
        operations.issue(invoice)
        self.assertEqual(hooks.ROUTES["/webhooks/payment"](invoice, event), "duplicate")
        self.assertEqual(invoice.status, "issued")
        self.assertIsNone(invoice.paid_at)

    def test_guard_only_still_allows_delayed_refund_replay(self):
        invoice, operations, _, hooks = self.invoices()
        operations.issue(invoice)
        payment = hooks.ROUTES["/webhooks/payment"]

        def guarded_refund(event):
            if invoice.status != "paid":
                raise ValueError("refund requires paid")
            hooks.handle_refund_event(invoice, event)

        refund = {"id": "R1", "amount": 100}
        payment(invoice, {"id": "P1", "amount": 100})
        guarded_refund(refund)
        with self.assertRaises(ValueError):
            guarded_refund(refund)
        payment(invoice, {"id": "P2", "amount": 100})
        guarded_refund(refund)
        self.assertEqual(len(hooks.REFUNDS), 2)
        self.assertEqual(sum(row["amount"] for row in hooks.REFUNDS), 200)

    def test_dedupe_only_still_accepts_refund_on_void(self):
        invoice, operations, _, hooks = self.invoices()
        operations.issue(invoice)
        operations.void(invoice)
        refund = hooks.dedupe(hooks.handle_refund_event)
        refund(invoice, {"id": "R1", "amount": 100})
        self.assertEqual(invoice.status, "issued")
        self.assertIsNotNone(invoice.voided_at)
        self.assertEqual(len(hooks.REFUNDS), 1)

    def test_independent_repairs_leave_the_other_ledger_defective(self):
        wallet, loyalty = fixture("independent-ledgers", "wallet", "loyalty")
        for fix_wallet, fix_loyalty in ((True, False), (False, True), (True, True)):
            with self.subTest(wallet_fixed=fix_wallet, loyalty_fixed=fix_loyalty):
                cash, points = wallet.Wallet(5), loyalty.Loyalty(5)
                for target, field, debit, fixed in (
                    (cash, "balance", wallet.withdraw, fix_wallet),
                    (points, "points", loyalty.redeem, fix_loyalty),
                ):
                    if not (fixed and getattr(target, field) < 6):
                        debit(target, 6)
                self.assertEqual(cash.balance, 5 if fix_wallet else -1)
                self.assertEqual(points.points, 5 if fix_loyalty else -1)

    def test_historical_snapshot_does_not_track_live_balance(self):
        wallet, statements = fixture("independent-ledgers", "wallet", "statements")
        cash = wallet.Wallet(5)
        statement = statements.issue_statement(cash)
        wallet.credit(cash, 2)
        self.assertEqual((statement.balance_at_issue, cash.balance), (5, 7))
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            statement.balance_at_issue = 7

    def test_facade_alone_cannot_establish_external_refund_eligibility(self):
        (routes,) = fixture("rerun-external", "routes")
        accepts = types.SimpleNamespace(refund=lambda order_id, amount: "accepted")

        def reject(order_id, amount):
            raise ValueError("external status guard")

        rejects = types.SimpleNamespace(refund=reject)
        self.assertEqual(routes.refund_order("draft-order", {"amount": 100}, accepts), "accepted")
        with self.assertRaises(ValueError):
            routes.refund_order("draft-order", {"amount": 100}, rejects)

    def test_timeout_outcome_depends_on_assumed_latency(self):
        steps, worker = fixture("booking-saga", "steps", "worker")

        class StopProbe(BaseException):
            pass  # Bound the intentionally unbounded worker without changing it.

        for duration, expected_retries in ((0.5, 0), (0.8, 2)):
            with self.subTest(assumed_seconds_per_step=duration):
                elapsed, enqueued = [0.0], []

                def action(*args):
                    elapsed[0] += duration
                    return "reference"

                @contextmanager
                def synthetic_deadline(seconds):
                    # One hypothetical contract for the missing provider timeout.
                    start = elapsed[0]
                    yield
                    if elapsed[0] - start > seconds:
                        raise TimeoutError("assumed cumulative latency exceeded deadline")

                def enqueue(booking):
                    enqueued.append(booking.id)
                    if len(enqueued) == 2:
                        raise StopProbe()

                providers = types.SimpleNamespace(
                    timeout=synthetic_deadline,
                    airline=types.SimpleNamespace(reserve=action, release=action),
                    payments=types.SimpleNamespace(charge=action, refund=action),
                    hotel=types.SimpleNamespace(reserve=action, release=action),
                )
                try:
                    worker.handle(
                        steps.Booking("trip-1", "customer-1"), providers,
                        types.SimpleNamespace(enqueue=enqueue),
                        types.SimpleNamespace(notify=lambda message: None),
                    )
                except StopProbe:
                    pass
                self.assertEqual(len(enqueued), expected_retries)


class StockReservations(unittest.TestCase):
    def setUp(self):
        from datetime import datetime, timedelta
        self.models, self.operations = fixture("stock-reservations", "models", "operations")
        self.t0 = datetime(2026, 1, 1, 12, 0)
        self.later = lambda minutes: self.t0 + timedelta(minutes=minutes)

    def store_with(self, *serials):
        store = self.models.Store()
        for serial in serials:
            store.put(self.models.Unit("SKU-1", serial))
        return store

    def test_interleaved_reservations_both_succeed(self):
        store = self.store_with("u1")
        snapshot = store.get("u1")
        stale = types.SimpleNamespace(get=lambda serial: self.models.replace(snapshot),
                                      put=store.put)
        # Both requests read the row before either writes it.
        self.operations.reserve(stale, "u1", "ana", self.t0)
        self.operations.reserve(stale, "u1", "bob", self.t0)
        self.assertEqual(store.get("u1").reserved_by, "bob")

    def test_declined_payment_leaves_the_unit_sold(self):
        store = self.store_with("u1")

        class Declining:
            def charge(self, shopper, sku):
                raise RuntimeError("declined")

        self.operations.reserve(store, "u1", "ana", self.t0)
        with self.assertRaises(RuntimeError):
            self.operations.sell(store, "u1", "ana", Declining(), self.t0)
        self.assertIsNotNone(store.get("u1").sold_at)

    def test_sweep_deletes_the_only_record_of_a_sale(self):
        store = self.store_with("u1", "u2")
        self.operations.reserve(store, "u1", "ana", self.t0)
        self.operations.sell(store, "u1", "ana", types.SimpleNamespace(charge=lambda *a: None), self.t0)
        self.operations.reserve(store, "u2", "bob", self.t0)
        self.operations.sweep(store, self.later(20))
        self.assertEqual(store.all(), [])

    def test_a_sold_unit_changes_hands_after_its_window(self):
        store = self.store_with("u1")
        self.operations.reserve(store, "u1", "ana", self.t0)
        self.operations.sell(store, "u1", "ana", types.SimpleNamespace(charge=lambda *a: None), self.t0)
        self.operations.reserve(store, "u1", "bob", self.later(16))
        unit = store.get("u1")
        self.assertEqual((unit.reserved_by, unit.sold_at), ("bob", self.t0))

    def test_bundle_price_is_a_special_case(self):
        unit = self.models.Unit("BUNDLE-1", "u1")
        catalog = {"BUNDLE-1": 30.0, "BUNDLE-1:parts": ["A", "B", "C"]}
        self.assertEqual(self.operations.price_of(unit, catalog), 10.0)


class MonorepoBilling(unittest.TestCase):
    def setUp(self):
        self.subs, self.dunning = fixture("monorepo/billing", "subscriptions", "dunning")

    def test_a_failed_renewal_revives_a_canceled_subscription(self):
        sub = self.subs.Subscription("s-1")
        self.subs.cancel(sub)
        self.dunning.on_renewal_failed(sub)
        self.assertEqual(sub.status, "past_due")

    def test_old_failures_survive_a_successful_renewal(self):
        sub = self.subs.Subscription("s-1")
        for _ in range(2):
            self.dunning.on_renewal_failed(sub)
        self.subs.activate(sub, paid_through=None)
        self.dunning.on_renewal_failed(sub)
        self.assertEqual(sub.status, "canceled")

    def test_nothing_reads_trial_ends(self):
        for name in ("subscriptions.py", "dunning.py"):
            source = (FIXTURES / "monorepo" / "billing" / name).read_text(encoding="utf-8")
            self.assertNotIn("trial_ends <", source)
            self.assertNotIn("sub.trial_ends", source)


class FixtureSuites(unittest.TestCase):
    """The test suites planted in fixtures, which the test-audit phase reads."""

    def run_suite(self, name, module):
        (suite,) = fixture(name, module)
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromModule(suite).run(result)
        return result

    def test_orders_suite_is_green_on_defective_code(self):
        # A green suite is not a correct system: one test asserts the closure
        # defect, and none exercises the others.
        result = self.run_suite("orders", "test_orders")
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertEqual(result.testsRun, 6)

    def test_orders_suite_enshrines_refund_pending(self):
        models, operations = fixture("orders", "models", "operations")
        order = models.Order("o-1")
        operations.refund(order)
        self.assertNotIn(order.status, models.STATUS)
        source = (FIXTURES / "orders" / "test_orders.py").read_text(encoding="utf-8")
        self.assertIn('self.assertEqual(order.status, "refund_pending")', source)

    def test_orders_suite_never_redelivers_a_webhook(self):
        models, operations, webhook = fixture("orders", "models", "operations", "webhook")
        order = models.Order("o-1")
        operations.add_item(order, models.Item("SKU-1", 2, 10.0))
        operations.checkout(order)
        event = {"id": "evt-1", "amount": 20.0}
        webhook.handle_payment_webhook(order, event)
        webhook.handle_payment_webhook(order, event)
        self.assertEqual(order.total_paid, 40.0)
        source = (FIXTURES / "orders" / "test_orders.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("handle_payment_webhook(order"), 1)

    def test_stock_suite_catches_exactly_the_charge_ordering_defect(self):
        result = self.run_suite("stock-reservations", "test_stock")
        self.assertEqual(result.testsRun, 10)
        self.assertEqual(result.errors, [])
        failed = [test.id().rsplit(".", 1)[-1] for test, _ in result.failures]
        self.assertEqual(failed, ["test_declined_payment_keeps_the_unit_reserved"])

    def test_clean_ticket_suite_is_green(self):
        result = self.run_suite("clean-ticket", "test_tickets")
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)


if __name__ == "__main__":
    unittest.main()
