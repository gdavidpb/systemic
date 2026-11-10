"""Unit tests for scripts/systemic_check.py, the run-workspace gate validator.

The golden workspace in fixtures/runs/orders-valid is a complete, valid run
over fixtures/orders. Each mutation test copies it, introduces exactly one
contract violation and asserts the gate that must catch it. These tests grade
the validator, not a model's report.
"""
from contextlib import redirect_stdout
import io
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parent
GOLDEN = HERE / "fixtures" / "runs" / "orders-valid"
RERUN_JSON = HERE / "fixtures" / "rerun-json"
SOURCES = HERE / "fixtures" / "orders"

spec = importlib.util.spec_from_file_location("systemic_check", REPO / "scripts" / "systemic_check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class Workspace:
    """A temporary copy of the golden project with helpers to mutate it."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        shutil.copytree(SOURCES, base / "orders")
        shutil.copytree(GOLDEN, base / "runs" / "orders-valid")
        self.project = base / "runs" / "orders-valid"
        self.run_dir = self.project / "systemic-out" / "orders-module"
        self.report = self.project / "systemic-out" / "orders-module.md"
        self.sources = base / "orders"

    def read(self, name):
        return json.loads((self.run_dir / name).read_text(encoding="utf-8"))

    def write(self, name, data):
        (self.run_dir / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def edit(self, name, fn):
        data = self.read(name)
        fn(data)
        self.write(name, data)

    def check(self, gate="all"):
        out = io.StringIO()
        with redirect_stdout(out):
            code = checker.main([gate, str(self.run_dir)])
        return code, out.getvalue()

    def close(self):
        self.tmp.cleanup()


class GateTestCase(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.close)

    def assertFails(self, gate, fragment, run="all"):
        code, out = self.ws.check(run)
        self.assertEqual(code, 1, out)
        self.assertTrue(
            any(line.startswith(gate) and fragment in line for line in out.splitlines()),
            f"expected a {gate} line containing {fragment!r}, got:\n{out}",
        )


class GoldenRun(GateTestCase):
    def test_golden_run_passes_every_gate(self):
        for gate in ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "all"]:
            code, out = self.ws.check(gate)
            self.assertEqual(code, 0, f"{gate}: {out}")
            self.assertIn(f"OK {gate}", out)

    def test_cli_output_format_and_exit_codes(self):
        self.ws.edit("checks.json", lambda d: d["checks"].pop(6))
        code, out = self.ws.check("G3")
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertTrue(all(line.startswith("G3 ") for line in lines[:-1]), out)
        self.assertRegex(lines[-1], r"^FAIL G3: \d+ violation\(s\)$")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(checker.main(["G9", str(self.ws.run_dir)]), 2)
            self.assertEqual(checker.main(["all", str(self.ws.run_dir / "missing")]), 2)


class G0Scope(GateTestCase):
    def test_full_mode_requires_an_explicit_request(self):
        self.ws.edit("run.json", lambda d: d.update(mode_source="default"))
        self.assertFails("G0", "full requires mode_source 'explicit'")

    def test_report_path_must_not_go_into_a_fixture_directory(self):
        self.ws.edit("run.json", lambda d: d.update(report_path="evals/fixtures/orders/report.md",
                                                    report_path_source="user"))
        self.assertFails("G0", "must not be written inside")

    def test_slug_must_be_kebab_case(self):
        self.ws.edit("run.json", lambda d: d.update(slug="Orders_Module"))
        self.assertFails("G0", "kebab-case")

    def test_missing_target(self):
        self.ws.edit("run.json", lambda d: d["targets"].append("payments.py"))
        self.assertFails("G0", "does not exist under source_root")

    def test_incomplete_run_requires_a_reason(self):
        self.ws.edit("run.json", lambda d: d.update(status="incomplete", incomplete_reason="ok"))
        self.assertFails("G0", "incomplete_reason")

    def test_standard_profile_requires_phase_logs(self):
        self.ws.edit("run.json", lambda d: d.update(profile="standard"))
        self.assertFails("G0", "00-scope.md")

    def test_incomplete_run_may_name_a_missing_target(self):
        self.ws.edit("run.json", lambda d: (d["targets"].append("payments.py"), d.update(
            status="incomplete", phase="F1",
            incomplete_reason="G0 fails: payments.py is a target and no longer exists; the user forbade rescoping")))
        code, out = self.ws.check("all")
        self.assertEqual(code, 0, out)

    def test_incomplete_run_keeps_the_failing_phase(self):
        self.ws.edit("run.json", lambda d: d.update(
            status="incomplete", incomplete_reason="G1 fails: a target was removed and rescoping is forbidden"))
        self.assertFails("ALL", "keeps phase at the phase whose gate failed")

    def test_returned_phase_must_be_redone(self):
        self.ws.edit("run.json", lambda d: d["log"].append(
            {"phase": "F1", "event": "returned_to", "detail": "operations.py changed since it was read"}))
        self.assertFails("ALL", "no later gate_passed shows it was redone")

    def test_log_events_are_fixed_keywords(self):
        self.ws.edit("run.json", lambda d: d["log"].append({"phase": "F2", "event": "done", "detail": "x"}))
        self.assertFails("ALL", "event must be one of")

    def test_needs_scope_requires_a_proposal(self):
        self.ws.edit("run.json", lambda d: d.update(status="needs_scope", phase="F0", scope_proposal="tbd"))
        self.assertFails("G0", "scope_proposal")

    def test_needs_scope_pause_writes_nothing_past_f0(self):
        self.ws.edit("run.json", lambda d: d.update(
            status="needs_scope", phase="F0",
            scope_proposal="Narrow to the order lifecycle in operations.py, the only module with state"))
        self.assertFails("G0", "writes nothing past F0")

    def test_needs_scope_pause_is_valid_before_any_phase_output(self):
        self.ws.edit("run.json", lambda d: d.update(
            status="needs_scope", phase="F0",
            scope_proposal="Narrow to the order lifecycle in operations.py, the only module with state"))
        for name in ("sources.json", "model.json", "checks.json", "findings.json", "tests.json"):
            (self.ws.run_dir / name).unlink()
        self.ws.report.unlink()
        code, out = self.ws.check("all")
        self.assertEqual(code, 0, out)


class G1Sources(GateTestCase):
    def test_hash_must_match_the_file_read(self):
        self.ws.edit("sources.json", lambda d: d["files"][2].update(sha256="0" * 64))
        self.assertFails("G1", "sha256 does not match")

    def test_claim_line_out_of_range(self):
        self.ws.edit("sources.json", lambda d: d["claims"][0].update(line=999))
        self.assertFails("G1", "outside README.md")

    def test_every_target_is_read_or_excluded(self):
        self.ws.edit("sources.json", lambda d: d["files"].pop())
        self.assertFails("G1", "neither read nor excluded")

    def test_citation_outside_a_partial_read(self):
        def partial(d):
            d["files"][2].update(read="partial", ranges=[[1, 10]])
        self.ws.edit("sources.json", partial)
        self.assertFails("G2", "outside the ranges recorded as read")


class G2Model(GateTestCase):
    def test_transition_must_use_a_modeled_operator(self):
        self.ws.edit("model.json", lambda d: d["machines"][0]["transitions"][0].update(operator="O-99"))
        self.assertFails("G2", "is not a modeled operator")

    def test_declared_state_missing_from_the_machine(self):
        self.ws.edit("model.json", lambda d: d["machines"][0]["states"].remove("in_review"))
        self.assertFails("G2", "'in_review' is declared but missing")

    def test_every_claim_is_linked(self):
        self.ws.edit("model.json", lambda d: d.update(claims_satisfied=[]))
        self.assertFails("G2", "claim D-7 is neither satisfied")

    def test_invariant_category_is_a_fixed_keyword(self):
        self.ws.edit("model.json", lambda d: d["invariants"][0].update(category="safety"))
        self.assertFails("G2", "category: must be one of")

    def test_every_machine_has_an_invariant(self):
        def unbind(d):
            for inv in d["invariants"]:
                inv["machine"] = None
        self.ws.edit("model.json", unbind)
        self.assertFails("G2", "machine M-1 has no invariant")

    def test_declared_invariant_names_its_claims(self):
        self.ws.edit("model.json", lambda d: d["invariants"][1].update(claims=[]))
        self.assertFails("G2", "names the claims that declare it")


class G5Tests(GateTestCase):
    def coverage(self, data, invariant):
        return next(c for c in data["coverage"] if c["invariant"] == invariant)

    def test_every_invariant_has_a_coverage_entry(self):
        self.ws.edit("tests.json", lambda d: d["coverage"].pop())
        self.assertFails("G5", "invariant I-8 has no coverage entry")

    def test_asserted_needs_an_assertion_in_a_test_file(self):
        def cite_source(d):
            self.coverage(d, "I-3")["evidence"] = [
                {"file": "operations.py", "line": 52, "quote": 'if order.status != "shipped":'}]
        self.ws.edit("tests.json", cite_source)
        self.assertFails("G5", "is not recorded with role test")

    def test_asserted_without_evidence(self):
        self.ws.edit("tests.json", lambda d: self.coverage(d, "I-3").update(evidence=[]))
        self.assertFails("G5", "at least 1 citation")

    def test_single_delivery_cannot_assert_idempotency(self):
        def promote(d):
            self.coverage(d, "I-6").update(
                level="asserted",
                evidence=[{"file": "test_orders.py", "line": 70, "quote": "self.assertEqual(order.total_paid, 20.0)"}])
        self.ws.edit("tests.json", promote)
        self.assertFails("G5", "a repetition invariant is asserted only by")

    def test_contradicted_names_the_finding_it_enshrines(self):
        self.ws.edit("tests.json", lambda d: self.coverage(d, "I-1").update(finding="operations.py:nope:x:y"))
        self.assertFails("G5", "is not a confirmed fingerprint")

    def test_uncovered_says_what_was_searched(self):
        self.ws.edit("tests.json", lambda d: self.coverage(d, "I-5").update(reason="none"))
        self.assertFails("G5", "coverage[4].reason")

    def test_hole_cells_are_not_tested_cells(self):
        self.ws.edit("tests.json", lambda d: d["cells_tested"].append(
            {"machine": "M-1", "cell": "shipped/O-5", "tests": ["X-2"]}))
        self.assertFails("G5", "is a hole")

    def test_every_finding_is_classified_against_the_suite(self):
        self.ws.edit("tests.json", lambda d: d["finding_gaps"].pop())
        self.assertFails("G5", "is not classified")

    def test_enshrined_needs_the_test_that_asserts_the_defect(self):
        self.ws.edit("tests.json", lambda d: d["finding_gaps"][0].update(tests=[]))
        self.assertFails("G5", "at least 1 test(s) required")

    def test_by_category_is_recomputed(self):
        self.ws.edit("tests.json", lambda d: d["by_category"]["transition"].update(asserted=2))
        self.assertFails("G5", "by_category: must be")

    def test_absent_suite_cannot_assert(self):
        def absent(d):
            d["suite"] = {"status": "absent", "files": [], "searched": "test_*.py and tests/ under the module root",
                          "reason": None}
        self.ws.edit("tests.json", absent)
        self.assertFails("G5", "with no test suite every invariant is uncovered")

    def test_contradicted_finding_must_be_enshrined(self):
        def demote(d):
            d["finding_gaps"][0].update(status="undetected", tests=[], evidence=[])
        self.ws.edit("tests.json", demote)
        self.assertFails("G5", "must mark it enshrined")

    def test_quick_log_needs_a_section_per_phase(self):
        log = self.ws.run_dir / "work.md"
        log.write_text(log.read_text().replace("## F5 Test audit", "## Tests"))
        self.assertFails("G5", "needs a '## F5")

    def test_excluded_suite_assesses_no_finding(self):
        def exclude(d):
            d["suite"] = {"status": "out_of_scope", "files": [], "searched": None,
                          "reason": "The user asked to leave the tests out of this run"}
            d["tests"], d["cells_tested"] = [], []
            for entry in d["coverage"]:
                entry.update(level="not_verifiable", tests=[], evidence=[], finding=None,
                             reason="The tests were excluded at the user's request")
        self.ws.edit("tests.json", exclude)
        self.ws.edit("sources.json", lambda d: d.update(files=[f for f in d["files"] if f.get("role") != "test"]))
        code, out = self.ws.check("G5")
        self.assertIn("every finding is not_assessed", out)
        self.assertNotIn("records test files as read", out)

    def test_concurrency_label_needs_an_interleaving(self):
        self.ws.edit("tests.json", lambda d: d["tests"][2].update(technique="concurrency"))
        self.assertFails("G5", "shows concurrency")

    def test_fault_injection_label_needs_a_failure(self):
        self.ws.edit("tests.json", lambda d: d["tests"][1].update(technique="fault_injection"))
        self.assertFails("G5", "shows fault_injection")

    def test_repetition_label_needs_a_repeated_operation(self):
        self.ws.edit("tests.json", lambda d: d["tests"][5].update(technique="repetition"))
        self.assertFails("G5", "never applies an operation twice")

    def test_technique_is_read_from_the_enclosing_test(self):
        # Citing a line inside the test, not its def, still finds the whole body.
        self.ws.edit("tests.json", lambda d: d["tests"][3].update(
            technique="fault_injection",
            evidence=[{"file": "test_orders.py", "line": 56, "quote": "deliver(order)"}]))
        code, out = self.ws.check("G5")
        self.assertEqual(code, 0, out)

    def test_test_ids_are_unique(self):
        self.ws.edit("tests.json", lambda d: d["tests"][1].update(id="X-1"))
        self.assertFails("G5", "must be a unique X-<n>")


class G3Checks(GateTestCase):
    def test_all_twelve_checks_are_recorded(self):
        self.ws.edit("checks.json", lambda d: d["checks"].pop(6))
        self.assertFails("G3", "ids 1..12 exactly once")

    def test_clean_needs_substantive_evidence(self):
        self.ws.edit("checks.json", lambda d: d["checks"][11].update(verified="ok"))
        self.assertFails("G3", ".verified: required, substantive")

    def test_not_verifiable_needs_what_was_missing(self):
        self.ws.edit("checks.json", lambda d: d["checks"][7].update(missing=""))
        self.assertFails("G3", ".missing: required")

    def test_risk_needs_its_condition(self):
        self.ws.edit("checks.json", lambda d: d["candidates"][6].update(condition=None))
        self.assertFails("G3", ".condition: required")

    def test_ambiguity_needs_its_question(self):
        self.ws.edit("checks.json", lambda d: d["candidates"][4].update(question=None))
        self.assertFails("G3", ".question: required")

    def test_hole_needs_a_candidate_or_note(self):
        self.ws.edit("checks.json", lambda d: d["matrices"][0]["notes"].pop("delivered/O-5"))
        self.assertFails("G3", "hole delivered/O-5")

    def test_small_machine_needs_a_matrix(self):
        # Eight declared states plus the undeclared refund_pending: the
        # undeclared state adds a row, it does not lift the requirement.
        self.ws.edit("checks.json", lambda d: d.update(matrices=[]))
        self.assertFails("G3", "needs a matrix")


class G4Findings(GateTestCase):
    def test_quote_must_exist_at_the_cited_line(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][0]["evidence"][0].update(line=10))
        self.assertFails("G4", "quote not found at operations.py:10")

    def test_altered_quote(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][0]["evidence"][0].update(quote='order.status = "refunded"'))
        self.assertFails("G4", "quote not found")

    def test_source_edited_after_it_was_read(self):
        path = self.ws.sources / "operations.py"
        path.write_text(path.read_text() + "\n# edited\n")
        self.assertFails("G4", "changed since it was read")

    def test_every_candidate_is_resolved(self):
        self.ws.edit("findings.json", lambda d: d.update(rejected=[]))
        self.assertFails("G4", "candidate C-10 is neither confirmed, rejected nor merged")

    def test_a_candidate_is_resolved_once(self):
        self.ws.edit("findings.json", lambda d: d["merged"].append({"candidate": "C-1", "into": d["confirmed"][1]["fingerprint"]}))
        self.assertFails("G4", "C-1 is already resolved")

    def test_duplicate_fingerprint(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][1].update(fingerprint=d["confirmed"][0]["fingerprint"]))
        self.assertFails("G4", "duplicate")

    def test_finding_states_what_impact_is_not_verified(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][0]["impact"].update(not_verified=None))
        self.assertFails("G4", "not_verified")

    def test_critical_requires_scope_and_irrecoverability(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][0].update(severity="critical"))
        self.assertFails("G4", "impact.unrecoverable_because")

    def test_labels_are_fixed_keywords(self):
        self.ws.edit("findings.json", lambda d: d["confirmed"][0].update(label="INCONSISTENCIA"))
        self.assertFails("G4", ".label")


class G6Reaudit(GateTestCase):
    def seed_prior(self):
        prior = self.ws.run_dir / "prior"
        prior.mkdir()
        shutil.copy(RERUN_JSON / "orders-module.md", prior / "report.md")
        shutil.copy(RERUN_JSON / "orders-module" / "findings.json", prior / "findings.json")
        self.ws.edit("run.json", lambda d: d.update(prior_report={"path": "systemic-out/orders-module/prior/report.md", "format": "json"}))
        deliver = next(i for i, line in enumerate((self.ws.sources / "operations.py").read_text().splitlines(), 1)
                       if 'if order.status != "shipped":' in line)
        current = [f["fingerprint"] for f in self.ws.read("findings.json")["confirmed"]]
        self.ws.write("reaudit.json", {
            "prior": {"path": "systemic-out/orders-module/prior/report.md", "format": "json"},
            "prior_findings": [
                {"key": "operations.py:refund:closure:undeclared-state", "title": "refund() writes a status outside the system",
                 "status": "persisting", "current": "operations.py:refund:closure:undeclared-state"},
                {"key": "operations.py:deliver:completeness:no-guard", "title": "deliver() accepts any status",
                 "status": "resolved", "resolution": "deliver now raises unless the order is shipped",
                 "evidence": [{"file": "operations.py", "line": deliver, "quote": 'if order.status != "shipped":'}]},
            ],
            "new": current[1:],
            "counts": {"new": len(current) - 1, "persisting": 1, "resolved": 1, "not_verified": 0},
        })
        report = self.ws.report.read_text()
        report = report.replace("critical: 0 · high: 6", "new: 7 · persisting: 1 · resolved: 1 · not verified: 0\ncritical: 0 · high: 6")
        self.ws.report.write_text(report)

    def test_reaudit_passes_when_every_prior_finding_is_classified(self):
        self.seed_prior()
        code, out = self.ws.check("all")
        self.assertEqual(code, 0, out)

    def test_prior_finding_left_unclassified(self):
        self.seed_prior()
        self.ws.edit("reaudit.json", lambda d: d["prior_findings"].pop())
        self.assertFails("G6", "keys must be the previous fingerprints")

    def test_resolved_needs_evidence_of_the_fix(self):
        self.seed_prior()
        self.ws.edit("reaudit.json", lambda d: d["prior_findings"][1].update(evidence=[]))
        self.assertFails("G6", "at least 1 citation")

    def test_counts_must_match(self):
        self.seed_prior()
        self.ws.edit("reaudit.json", lambda d: d["counts"].update(resolved=0))
        self.assertFails("G6", "counts")

    def test_report_states_the_reaudit_counts(self):
        self.seed_prior()
        self.ws.report.write_text(self.ws.report.read_text().replace("resolved: 1", "resolved: 2"))
        self.assertFails("G7", "resolved: 2")

    def test_legacy_markdown_prior_counts_its_findings(self):
        self.seed_prior()
        (self.ws.run_dir / "prior" / "findings.json").unlink()
        self.ws.edit("run.json", lambda d: d["prior_report"].update(format="md-legacy"))
        self.ws.edit("reaudit.json", lambda d: d["prior_findings"].pop())
        self.assertFails("G6", "previous report has 2 findings, 1 classified")


class G7Report(GateTestCase):
    def test_summary_counts_match_the_records(self):
        self.ws.report.write_text(self.ws.report.read_text().replace("high: 6", "high: 5"))
        self.assertFails("G7", "high: 5")

    def test_every_confirmed_finding_is_reported(self):
        text = self.ws.report.read_text()
        start = text.index("### [high] [INCONSISTENCY] Paused orders can never resume")
        end = text.index("### ", start + 4)
        self.ws.report.write_text(text[:start] + text[end:])
        self.assertFails("G7", "Paused orders can never resume")

    def test_severity_in_report_matches_the_record(self):
        self.ws.report.write_text(self.ws.report.read_text().replace(
            "### [high] [INCONSISTENCY] Paused orders", "### [low] [INCONSISTENCY] Paused orders"))
        self.assertFails("G7", "is shown as")

    def test_full_mode_needs_the_coverage_table(self):
        text = self.ws.report.read_text()
        self.ws.report.write_text(text[:text.index("## Limits and not-verified")])
        self.assertFails("G7", "coverage table")

    def test_functional_mode_hides_methodology(self):
        self.ws.edit("run.json", lambda d: d.update(mode="functional", mode_source="default"))
        code, out = self.ws.check("G7")
        self.assertEqual(code, 1)
        self.assertIn("mermaid", out)
        self.assertIn("check numbers", out)
        self.assertIn("twelve-check coverage table", out)

    def test_invariant_coverage_table_matches_the_records(self):
        self.ws.report.write_text(self.ws.report.read_text().replace(
            "| transition | 2 | 1 | 1 |", "| transition | 2 | 2 | 0 |"))
        self.assertFails("G7", "invariant coverage for transition reads")

    def test_invariant_coverage_table_has_every_category(self):
        self.ws.report.write_text(self.ws.report.read_text().replace("| algebraic | 1 | 0 | 0 | 0 | 1 | 0 |\n", ""))
        self.assertFails("G7", "needs a row for algebraic")

    def test_full_mode_states_matrix_cells_tested(self):
        self.ws.report.write_text(self.ws.report.read_text().replace("M-1 cells tested: 4/19", "M-1 cells tested: 9/19"))
        self.assertFails("G7", "M-1 cells tested reads 9/19")

    def test_functional_mode_keeps_the_invariant_table(self):
        self.ws.edit("run.json", lambda d: d.update(mode="functional", mode_source="default"))
        code, out = self.ws.check("G7")
        self.assertNotIn("invariant coverage", out)
        self.assertNotIn("cells tested", out)

    def test_full_report_discloses_graphify(self):
        self.ws.edit("run.json", lambda d: d.update(graph_informed=True))
        self.assertFails("G7", "says graphify informed the scope")

    def test_functional_report_does_not_mention_graphify(self):
        self.ws.edit("run.json", lambda d: d.update(graph_informed=True, mode="functional", mode_source="default"))
        self.ws.report.write_text(self.ws.report.read_text() + "\nScope chosen with graphify.\n")
        code, out = self.ws.check("G7")
        self.assertIn("does not mention graphify", out)

    def test_functional_mode_hides_internal_ids(self):
        self.ws.edit("run.json", lambda d: d.update(mode="functional", mode_source="default"))
        code, out = self.ws.check("G7")
        self.assertIn("must not show internal ids", out)

    def test_no_html(self):
        self.ws.report.write_text(self.ws.report.read_text() + "\n<div>summary</div>\n")
        self.assertFails("G7", "HTML")


class RunState(GateTestCase):
    def test_complete_requires_the_final_phase(self):
        self.ws.edit("run.json", lambda d: d.update(phase="F7"))
        self.assertFails("ALL", "requires phase F8")

    def test_in_progress_run_only_checks_finished_phases(self):
        self.ws.edit("run.json", lambda d: d.update(status="in_progress", phase="F3"))
        (self.ws.run_dir / "checks.json").unlink()
        (self.ws.run_dir / "findings.json").unlink()
        self.ws.report.unlink()
        code, out = self.ws.check("all")
        self.assertEqual(code, 0, out)


class InterruptedRun(unittest.TestCase):
    """evals/fixtures/resume: a run interrupted at F5 whose source changed after F1."""

    def test_resumed_run_must_return_to_f1(self):
        run_dir = HERE / "fixtures" / "resume" / "systemic-out" / "orders-module"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(checker.main(["G0", str(run_dir)]), 0)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(checker.main(["all", str(run_dir)]), 1)
        lines = out.getvalue().splitlines()
        self.assertTrue(any(l.startswith("G1 ") and "sha256 does not match operations.py" in l for l in lines), lines)
        self.assertFalse(any(l.startswith(("G5", "G6", "G7")) for l in lines), lines)


if __name__ == "__main__":
    unittest.main()
