"""Verify causal counterexamples in intentionally defective audit fixtures.

These tests preserve the evals' ground truth; they do not grade an LLM report.
All providers are local doubles. Logical time is assumed, never measured.
"""
from contextlib import contextmanager
import importlib
import itertools
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
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


class Approvals(unittest.TestCase):
    """Held-out fixture: the defenses live in the schema and in one transition function."""

    def setUp(self):
        self.operations, self.reviews, self.transitions = fixture(
            "approvals", "operations", "reviews", "transitions")
        self.conn = self.operations.connect()
        self.operations.create(self.conn, "r1", "ana")

    def event(self, event_id="e1"):
        return {"id": event_id, "request_id": "r1", "reviewer": "bob", "verdict": "approved", "at": "t"}

    def test_withdraw_leaves_the_pending_count_behind(self):
        # The one planted defect: submit adds, decide subtracts, withdraw forgets.
        self.operations.submit(self.conn, "r1")
        self.operations.withdraw(self.conn, "r1")
        self.assertEqual(self.operations.status_of(self.conn, "r1"), "draft")
        self.assertEqual(self.operations.pending_count(self.conn, "ana"), 1)
        self.operations.submit(self.conn, "r1")
        self.assertEqual(self.operations.pending_count(self.conn, "ana"), 2)

    def test_a_failed_event_is_not_remembered(self):
        # Defended: the marker and the decision share a transaction.
        with self.assertRaises(self.transitions.StaleRequest):
            self.reviews.handle_review_event(self.conn, self.event())
        self.operations.submit(self.conn, "r1")
        self.assertEqual(self.reviews.handle_review_event(self.conn, self.event()), "applied")
        self.assertEqual(self.reviews.handle_review_event(self.conn, self.event()), "duplicate")
        self.assertEqual(self.operations.pending_count(self.conn, "ana"), 0)

    def test_two_writers_cannot_both_decide(self):
        # Defended: the UPDATE compares the status it expects.
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "approvals.db")
            first = self.operations.connect(path)
            self.operations.create(first, "r1", "ana")
            self.operations.submit(first, "r1")
            second = sqlite3.connect(path)
            self.operations.decide(first, "r1", "bob", "approved", "t1")
            with self.assertRaises(self.transitions.StaleRequest):
                self.operations.decide(second, "r1", "cleo", "rejected", "t2")
            self.assertEqual(self.operations.status_of(second, "r1"), "approved")
            first.close()
            second.close()

    def test_the_schema_refuses_illegal_combinations(self):
        self.operations.submit(self.conn, "r1")
        for statement in (
            "UPDATE requests SET status = 'approved' WHERE id = 'r1'",
            "UPDATE requests SET decided_by = 'bob', decided_at = 't' WHERE id = 'r1'",
            "UPDATE requests SET status = 'archived' WHERE id = 'r1'",
        ):
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(statement)

    def test_a_refused_event_lands_on_the_resubmission(self):
        # Not planted, but real: rules 3 and 4 together let an approval issued for
        # one submission be applied to the next one. A report may raise it.
        self.operations.submit(self.conn, "r1")
        self.operations.withdraw(self.conn, "r1")
        with self.assertRaises(self.transitions.StaleRequest):
            self.reviews.handle_review_event(self.conn, self.event())
        self.operations.submit(self.conn, "r1")
        self.assertEqual(self.reviews.handle_review_event(self.conn, self.event()), "applied")
        self.assertEqual(self.operations.status_of(self.conn, "r1"), "approved")

    def test_connect_cannot_reopen_a_database(self):
        # Not planted, but real: connect() runs CREATE TABLE on every connection.
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "approvals.db")
            self.operations.connect(path).close()
            with self.assertRaises(sqlite3.OperationalError):
                self.operations.connect(path)

    def test_a_decision_and_its_count_are_one_transaction(self):
        # Defended: if the count cannot be written, the decision is rolled back.
        self.operations.submit(self.conn, "r1")
        self.conn.execute("UPDATE authors SET pending_count = 0 WHERE id = 'ana'")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.operations.decide(self.conn, "r1", "bob", "approved", "t")
        self.assertEqual(self.operations.status_of(self.conn, "r1"), "submitted")


JOB_LEASES_PROBE = r"""
const { Store } = require('./store');
const q = require('./queue');
const { runOne } = require('./worker');
const T0 = 1000000;
const out = {};

(async () => {
  // Two workers poll at once: both read the queued job before either saves.
  let store = new Store();
  await q.enqueue(store, 'a', {});
  const [first, second] = await Promise.all([q.lease(store, 'w1', T0), q.lease(store, 'w2', T0)]);
  out.race = { sameJob: first.id === second.id, holders: [first.leasedBy, second.leasedBy] };

  // A retried complete counts the job again, and the lease survives on a done job.
  store = new Store();
  let stats = { completed: 0 };
  await q.enqueue(store, 'a', {});
  let job = await q.lease(store, 'w1', T0);
  await q.complete(store, stats, job.id, 'w1', T0 + 1);
  await q.complete(store, stats, job.id, 'w1', T0 + 2);
  const done = await store.get(job.id);
  out.retry = { completed: stats.completed, status: done.status, leasedBy: done.leasedBy };

  // The holder check still passes on a done job, so fail() takes it out of a terminal state.
  await q.fail(store, job.id, 'w1', T0 + 3, 'late error');
  out.terminalLeft = (await store.get(job.id)).status;

  // The worker reaches that path by itself when notify fails after complete.
  store = new Store();
  stats = { completed: 0 };
  await q.enqueue(store, 'a', {});
  let runs = 0;
  const handler = async () => { runs += 1; };
  await runOne(store, stats, 'w1', handler, async () => { throw new Error('producer down'); }, () => T0);
  await runOne(store, stats, 'w1', handler, async () => {}, () => T0);
  out.worker = { runs, completed: stats.completed };

  // MAX_ATTEMPTS is never enforced: a job that always fails is queued for ever.
  store = new Store();
  await q.enqueue(store, 'poison', {});
  for (let i = 0; i < 10; i += 1) {
    job = await q.lease(store, 'w1', T0);
    await q.fail(store, job.id, 'w1', T0 + 1, 'boom');
  }
  const poison = (await store.all())[0];
  out.poison = { status: poison.status, attempts: poison.attempts, max: q.MAX_ATTEMPTS };

  // The counter moves before the completion is stored.
  store = new Store();
  stats = { completed: 0 };
  await q.enqueue(store, 'a', {});
  job = await q.lease(store, 'w1', T0);
  const save = store.save.bind(store);
  store.save = async () => { throw new Error('store down'); };
  await q.complete(store, stats, job.id, 'w1', T0 + 1).catch(() => {});
  store.save = save;
  out.outage = { completed: stats.completed, status: (await store.get(job.id)).status };

  // Not planted, but real: every write is unconditional, so the reaper can undo a completion
  // that lands between its read and its write.
  store = new Store();
  stats = { completed: 0 };
  await q.enqueue(store, 'a', {});
  job = await q.lease(store, 'w1', T0);
  const stale = await store.findExpired(T0 + q.LEASE_MS);
  await q.complete(store, stats, job.id, 'w1', T0 + q.LEASE_MS - 1);
  await store.save({ ...stale[0], status: 'queued', leasedBy: null, leaseUntil: null });
  out.reaperRace = (await store.get(job.id)).status;

  // Defended: keys are unique in the store, and an expired or reaped lease cannot act.
  store = new Store();
  const a = await q.enqueue(store, 'k', {});
  const b = await q.enqueue(store, 'k', {});
  job = await q.lease(store, 'w1', T0);
  const expired = await q.complete(store, { completed: 0 }, job.id, 'w1', T0 + q.LEASE_MS).catch((e) => e.constructor.name);
  await q.reap(store, T0 + q.LEASE_MS);
  const reaped = await q.complete(store, { completed: 0 }, job.id, 'w1', T0 + 5).catch((e) => e.constructor.name);
  out.defended = { oneJobPerKey: a.id === b.id, expired, reaped };

  console.log(JSON.stringify(out));
})();
"""


@unittest.skipUnless(shutil.which("node"), "node is needed to execute the JavaScript fixture")
class JobLeases(unittest.TestCase):
    """Held-out fixture in JavaScript: a job queue with leases."""

    @classmethod
    def setUpClass(cls):
        done = subprocess.run(["node", "-e", JOB_LEASES_PROBE], cwd=FIXTURES / "job-leases",
                              capture_output=True, text=True, timeout=60)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        cls.out = json.loads(done.stdout)

    def test_two_workers_lease_the_same_job(self):
        self.assertEqual(self.out["race"], {"sameJob": True, "holders": ["w1", "w2"]})

    def test_a_retried_complete_counts_the_job_twice(self):
        self.assertEqual(self.out["retry"], {"completed": 2, "status": "done", "leasedBy": "w1"})

    def test_a_done_job_returns_to_the_queue(self):
        self.assertEqual(self.out["terminalLeft"], "queued")
        self.assertEqual(self.out["worker"], {"runs": 2, "completed": 2})

    def test_a_job_that_always_fails_is_never_dead(self):
        self.assertEqual(self.out["poison"], {"status": "queued", "attempts": 10, "max": 3})
        source = (FIXTURES / "job-leases" / "queue.js").read_text(encoding="utf-8")
        self.assertNotIn("'dead'", source.replace("const STATUS = ['queued', 'leased', 'done', 'dead'];", "")
                         .replace("const TERMINAL = ['done', 'dead'];", ""))

    def test_a_failed_save_still_counts_the_job(self):
        self.assertEqual(self.out["outage"], {"completed": 1, "status": "leased"})

    def test_a_stale_reaper_write_undoes_a_completion(self):
        self.assertEqual(self.out["reaperRace"], "queued")
        worker = (FIXTURES / "job-leases" / "worker.js").read_text(encoding="utf-8")
        self.assertNotIn("reap", worker)
        self.assertNotIn("renew", worker)

    def test_the_defended_paths_hold(self):
        self.assertEqual(self.out["defended"],
                         {"oneJobPerKey": True, "expired": "LeaseExpired", "reaped": "NotHolder"})

    def test_the_suite_catches_exactly_the_counter_ordering_defect(self):
        done = subprocess.run(["node", "--test", "--test-reporter=tap", "queue.test.js"], cwd=FIXTURES / "job-leases",
                              capture_output=True, text=True, timeout=120)
        failed = [line.split(" - ", 1)[1] for line in done.stdout.splitlines() if line.startswith("not ok")]
        self.assertEqual(failed, ["a store outage during complete does not count the job"])
        self.assertIn("# tests 11", done.stdout)


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

    def test_approvals_suite_is_green(self):
        # Green, and strong where it matters; it never checks the count after a withdrawal.
        result = self.run_suite("approvals", "test_approvals")
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertEqual(result.testsRun, 11)
        source = (FIXTURES / "approvals" / "test_approvals.py").read_text(encoding="utf-8")
        withdrawal = source.split("def test_withdrawing_returns_the_request_to_draft")[1]
        self.assertNotIn("pending_count", withdrawal)


if __name__ == "__main__":
    unittest.main()
