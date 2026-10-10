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


if __name__ == "__main__":
    unittest.main()
