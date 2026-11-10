#!/usr/bin/env python3
"""Deterministic gate validator for a systemic run workspace.

Usage:
    python3 systemic_check.py <G0|G1|G2|G3|G4|G5|G6|all> <run-dir> [--project-root DIR]

<run-dir> is the workspace a run writes, normally <project>/systemic-out/<slug>/.
The project root defaults to two levels above it. Exit codes: 0 when the gate
passes, 1 when it finds violations (one line per violation on stdout),
2 when the arguments or the workspace cannot be read.

The validator checks structure, cross-references and that quoted evidence
exists in the cited files. It cannot judge whether a diagnosis is correct;
that is what the refutation phase is for. The contracts it enforces are
specified in references/run-contracts.md. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

PHASES = ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
GATE_OF_PHASE = {"F0": "G0", "F1": "G1", "F2": "G2", "F3": "G3", "F4": "G4", "F5": "G5", "F6": "G6"}
STATUSES = {"in_progress", "needs_scope", "complete", "incomplete"}
MODES = {"functional", "full"}
LABELS = {"INCONSISTENCY", "RISK", "AMBIGUITY"}
SEVERITIES = ["critical", "high", "medium", "low"]
VERDICTS = {"findings", "clean", "not_verifiable"}
REPORT_VERDICTS = {"findings": "findings", "clean": "clean", "not_verifiable": "not verifiable"}
CELLS = {"defined", "guarded", "hole"}
CONFIDENCE = {"high", "medium", "low"}
REAUDIT = {"persisting", "resolved", "not_verified"}
FORBIDDEN_DIRS = {"node_modules", "vendor", ".git", "fixtures", "site-packages", ".venv", "venv"}
FILLER = {"ok", "n/a", "na", "none", "-", "todo", "tbd", "yes", "no", "done", "checked", "fine", "verified"}
MIN_TEXT = 12
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FINGERPRINT = re.compile(r"^[a-z0-9][a-z0-9._:/-]*$")
LOG_NAMES = {
    "G0": "00-scope.md", "G1": "01-sources.md", "G2": "02-model.md",
    "G3": "03-checks.md", "G4": "04-audit.md", "G5": "05-reaudit.md",
}


class Unreadable(Exception):
    """The workspace cannot be read well enough to validate it."""


# ---------------------------------------------------------------- helpers

def substantive(value) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return len(text) >= MIN_TEXT and text.lower().strip(".!") not in FILLER


def norm(text: str) -> str:
    return " ".join(text.split())


def ids(items, prefix):
    out = []
    for item in items or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].startswith(prefix):
            out.append(item["id"])
    return out


class Ctx:
    def __init__(self, run_dir: Path, project_root: Path):
        self.run_dir = run_dir
        self.root = project_root
        self.cache = {}
        self.run = self.load("run.json", required=True)
        source_root = self.run.get("source_root") if isinstance(self.run, dict) else None
        if not isinstance(source_root, str) or not source_root:
            source_root = "."
        base = Path(source_root)
        self.source_root = (base if base.is_absolute() else self.root / base).resolve()

    def load(self, name, required=False):
        if name in self.cache:
            return self.cache[name]
        path = self.run_dir / name
        if not path.exists():
            if required:
                raise Unreadable(f"{name} not found in {self.run_dir}")
            self.cache[name] = None
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Unreadable(f"{name} is not valid JSON: {exc}") from exc
        self.cache[name] = data
        return data

    def source_lines(self, rel):
        key = ("lines", rel)
        if key not in self.cache:
            path = self.source_root / rel
            try:
                raw = path.read_bytes()
            except OSError:
                self.cache[key] = None
            else:
                text = raw.decode("utf-8", errors="replace")
                self.cache[key] = (hashlib.sha256(raw).hexdigest(), text.splitlines())
        return self.cache[key]

    def files_index(self):
        sources = self.load("sources.json") or {}
        index = {}
        for entry in sources.get("files", []) or []:
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                index[entry["path"]] = entry
        return index

    @property
    def profile(self):
        return (self.run or {}).get("profile", "standard")


def check_cite(ctx, cite, where, errors, gate, need_quote=False):
    """Validate one evidence citation {file, line, quote?} against sources.json."""
    if not isinstance(cite, dict):
        errors.append(f"{gate} {where}: citation must be an object with file and line")
        return
    rel, line = cite.get("file"), cite.get("line")
    index = ctx.files_index()
    if rel not in index:
        errors.append(f"{gate} {where}: {rel!r} is not a file recorded as read in sources.json")
        return
    entry = index[rel]
    if not isinstance(line, int) or line < 1 or line > entry.get("lines", 0):
        errors.append(f"{gate} {where}: line {line!r} is outside {rel} (1..{entry.get('lines')})")
        return
    if entry.get("read") == "partial":
        ranges = entry.get("ranges") or []
        if not any(isinstance(r, list) and len(r) == 2 and r[0] <= line <= r[1] for r in ranges):
            errors.append(f"{gate} {where}: {rel}:{line} lies outside the ranges recorded as read")
    quote = cite.get("quote")
    if quote is None:
        if need_quote:
            errors.append(f"{gate} {where}: a quote is required")
        return
    if not isinstance(quote, str) or not quote.strip():
        errors.append(f"{gate} {where}: quote must be non-empty text")
        return
    loaded = ctx.source_lines(rel)
    if loaded is None:
        errors.append(f"{gate} {where}: cannot read {rel}")
        return
    digest, lines = loaded
    if digest != entry.get("sha256"):
        errors.append(f"{gate} {where}: {rel} changed since it was read (sha256 differs); re-run F1")
        return
    lo, hi = max(1, line - 2), min(len(lines), line + 2)
    window = norm(" ".join(lines[lo - 1:hi]))
    if norm(quote) not in window:
        errors.append(f"{gate} {where}: quote not found at {rel}:{line}±2")


def check_cites(ctx, cites, where, errors, gate, need_quote=False, minimum=1):
    if not isinstance(cites, list) or len(cites) < minimum:
        errors.append(f"{gate} {where}: at least {minimum} citation(s) required")
        return
    for i, cite in enumerate(cites):
        check_cite(ctx, cite, f"{where}[{i}]", errors, gate, need_quote)


def need_text(obj, key, where, errors, gate):
    if not substantive((obj or {}).get(key)):
        errors.append(f"{gate} {where}.{key}: required, substantive text (not empty or filler)")


def need_log(ctx, gate, errors):
    name = "work.md" if ctx.profile == "quick" else LOG_NAMES.get(gate)
    if name and not (ctx.run_dir / name).is_file():
        errors.append(f"{gate} {name}: the phase log is missing")


# ---------------------------------------------------------------- gates

def g0(ctx):
    e, run = [], ctx.run
    if not isinstance(run, dict):
        return ["G0 run.json: must be an object"]
    if run.get("schema") != "systemic.run/1":
        e.append("G0 run.json.schema: must be 'systemic.run/1'")
    slug = run.get("slug")
    if not isinstance(slug, str) or not SLUG.match(slug):
        e.append("G0 run.json.slug: must be kebab-case")
    need_text(run, "scope", "run.json", e, "G0")
    if run.get("mode") not in MODES:
        e.append("G0 run.json.mode: must be functional or full")
    if run.get("mode_source") not in {"explicit", "default"}:
        e.append("G0 run.json.mode_source: must be explicit or default")
    if run.get("mode") == "full" and run.get("mode_source") != "explicit":
        e.append("G0 run.json.mode: full requires mode_source 'explicit' (the user asked for it)")
    if not isinstance(run.get("language"), str) or not run["language"].strip():
        e.append("G0 run.json.language: required")
    if run.get("language_source") not in {"explicit", "conversation"}:
        e.append("G0 run.json.language_source: must be explicit or conversation")
    if run.get("profile") not in {"quick", "standard"}:
        e.append("G0 run.json.profile: must be quick or standard")
    if run.get("status") not in STATUSES:
        e.append(f"G0 run.json.status: must be one of {sorted(STATUSES)}")
    if run.get("phase") not in PHASES:
        e.append("G0 run.json.phase: must be F0..F7")
    if run.get("validation") not in {"script", "manual"}:
        e.append("G0 run.json.validation: must be script or manual")
    if not ctx.source_root.is_dir():
        e.append(f"G0 run.json.source_root: {ctx.source_root} is not a directory")
    targets = run.get("targets")
    if not isinstance(targets, list) or not targets:
        e.append("G0 run.json.targets: at least one target is required")
    else:
        for i, target in enumerate(targets):
            if not isinstance(target, str) or not (ctx.source_root / target).exists():
                e.append(f"G0 run.json.targets[{i}]: {target!r} does not exist under source_root")
    report = run.get("report_path")
    if not isinstance(report, str) or not report.endswith(".md"):
        e.append("G0 run.json.report_path: must be a .md path")
    else:
        parts = PurePosixPath(report).parts
        if PurePosixPath(report).is_absolute() or ".." in parts:
            e.append("G0 run.json.report_path: must be relative to the project root, without '..'")
        bad = FORBIDDEN_DIRS.intersection(parts)
        if bad:
            e.append(f"G0 run.json.report_path: must not be written inside {sorted(bad)}")
        if run.get("report_path_source", "default") == "default" and isinstance(slug, str):
            if report != f"systemic-out/{slug}.md":
                e.append(f"G0 run.json.report_path: default location is systemic-out/{slug}.md")
        if ctx.run_dir.resolve() != (ctx.root / report[:-3]).resolve():
            e.append("G0 run.json.report_path: the workspace must be the report path without .md")
    prior = run.get("prior_report")
    if prior is not None:
        if not isinstance(prior, dict) or prior.get("format") not in {"json", "md-legacy"}:
            e.append("G0 run.json.prior_report: must be null or {path, format: json|md-legacy}")
        elif not (ctx.run_dir / "prior" / "report.md").is_file():
            e.append("G0 prior/report.md: the previous report must be archived before it is replaced")
        elif prior["format"] == "json" and not (ctx.run_dir / "prior" / "findings.json").is_file():
            e.append("G0 prior/findings.json: format json requires the archived previous findings")
    if run.get("status") == "needs_scope":
        need_text(run, "scope_proposal", "run.json", e, "G0")
    if run.get("status") == "incomplete":
        need_text(run, "incomplete_reason", "run.json", e, "G0")
    need_log(ctx, "G0", e)
    return e


def g1(ctx):
    e = []
    sources = ctx.load("sources.json")
    if not isinstance(sources, dict):
        return ["G1 sources.json: missing or not an object"]
    files = sources.get("files")
    if not isinstance(files, list) or not files:
        return ["G1 sources.json.files: at least one file must be recorded as read"]
    seen = set()
    for i, entry in enumerate(files):
        where = f"sources.json.files[{i}]"
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            e.append(f"G1 {where}: needs path")
            continue
        rel = entry["path"]
        if rel in seen:
            e.append(f"G1 {where}: duplicate path {rel}")
        seen.add(rel)
        loaded = ctx.source_lines(rel)
        if loaded is None:
            e.append(f"G1 {where}: {rel} cannot be read under source_root")
            continue
        digest, lines = loaded
        if entry.get("sha256") != digest:
            e.append(f"G1 {where}: sha256 does not match {rel} on disk")
        if entry.get("lines") != len(lines):
            e.append(f"G1 {where}: lines is {entry.get('lines')!r}, file has {len(lines)}")
        if entry.get("read") not in {"full", "partial"}:
            e.append(f"G1 {where}.read: must be full or partial")
        if entry.get("read") == "partial":
            ranges = entry.get("ranges")
            if not isinstance(ranges, list) or not ranges or not all(
                isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r)
                and 1 <= r[0] <= r[1] <= len(lines) for r in ranges):
                e.append(f"G1 {where}.ranges: partial reads need [[start, end], ...] within the file")
    excluded = {}
    for i, entry in enumerate(sources.get("excluded", []) or []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            e.append(f"G1 sources.json.excluded[{i}]: needs path")
            continue
        need_text(entry, "reason", f"sources.json.excluded[{i}]", e, "G1")
        excluded[entry["path"]] = entry
    for i, target in enumerate(ctx.run.get("targets") or []):
        if not isinstance(target, str):
            continue
        prefix = target.rstrip("/") + "/"
        covered = (target in seen or target in excluded or target in {".", "./"}
                   or any(p.startswith(prefix) for p in seen | set(excluded)))
        if not covered:
            e.append(f"G1 run.json.targets[{i}]: {target} is neither read nor excluded with a reason")
    claim_ids = set()
    for i, claim in enumerate(sources.get("claims", []) or []):
        where = f"sources.json.claims[{i}]"
        cid = claim.get("id") if isinstance(claim, dict) else None
        if not isinstance(cid, str) or not re.match(r"^D-\d+$", cid):
            e.append(f"G1 {where}.id: must be D-<n>")
        elif cid in claim_ids:
            e.append(f"G1 {where}.id: duplicate {cid}")
        claim_ids.add(cid)
        need_text(claim, "text", where, e, "G1")
        check_cite(ctx, claim, where, e, "G1")
    need_log(ctx, "G1", e)
    return e


def g2(ctx):
    e = []
    model = ctx.load("model.json")
    if not isinstance(model, dict):
        return ["G2 model.json: missing or not an object"]
    elements = {x: True for x in ids(model.get("elements"), "E-")}
    operators = {x: True for x in ids(model.get("operators"), "O-")}
    systems = model.get("systems") or []
    if not systems:
        e.append("G2 model.json.systems: at least one system is required")
    for i, system in enumerate(systems):
        where = f"model.json.systems[{i}]"
        need_text(system, "objective", where, e, "G2")
        for ref in system.get("elements", []) or []:
            if ref not in elements:
                e.append(f"G2 {where}.elements: unknown element {ref}")
        for ref in system.get("operators", []) or []:
            if ref not in operators:
                e.append(f"G2 {where}.operators: unknown operator {ref}")
    for i, element in enumerate(model.get("elements") or []):
        check_cites(ctx, element.get("evidence"), f"model.json.elements[{i}].evidence", e, "G2")
    for i, op in enumerate(model.get("operators") or []):
        where = f"model.json.operators[{i}]"
        check_cites(ctx, op.get("evidence"), f"{where}.evidence", e, "G2")
        for ref in op.get("acts_on", []) or []:
            if ref not in elements:
                e.append(f"G2 {where}.acts_on: unknown element {ref}")
    transition_ids = set()
    for i, machine in enumerate(model.get("machines") or []):
        where = f"model.json.machines[{i}]"
        if machine.get("kind") not in {"explicit", "implicit"}:
            e.append(f"G2 {where}.kind: must be explicit or implicit")
        if machine.get("kind") == "implicit" and not machine.get("fields"):
            e.append(f"G2 {where}.fields: an implicit machine lists the fields that co-vary")
        states = machine.get("states") or []
        if len(set(states)) != len(states):
            e.append(f"G2 {where}.states: duplicate states")
        state_set = set(states)
        for state in machine.get("declared_states") or []:
            if state not in state_set:
                e.append(f"G2 {where}.declared_states: {state!r} is declared but missing from states")
        if machine.get("declared_in") is not None:
            check_cite(ctx, machine["declared_in"], f"{where}.declared_in", e, "G2")
        if machine.get("initial") is not None and machine["initial"] not in state_set:
            e.append(f"G2 {where}.initial: {machine['initial']!r} is not a state")
        for state in machine.get("terminal") or []:
            if state not in state_set:
                e.append(f"G2 {where}.terminal: {state!r} is not a state")
        for j, tr in enumerate(machine.get("transitions") or []):
            tw = f"{where}.transitions[{j}]"
            tid = tr.get("id")
            if not isinstance(tid, str) or not re.match(r"^T-\d+$", tid) or tid in transition_ids:
                e.append(f"G2 {tw}.id: must be a unique T-<n>")
            transition_ids.add(tid)
            for end in ("from", "to"):
                value = tr.get(end)
                if not (value in state_set or (end == "from" and value == "*")):
                    e.append(f"G2 {tw}.{end}: {value!r} is not a state of this machine")
            if tr.get("operator") not in operators:
                e.append(f"G2 {tw}.operator: {tr.get('operator')!r} is not a modeled operator")
            check_cites(ctx, tr.get("evidence"), f"{tw}.evidence", e, "G2")
    claims = set(ids((ctx.load("sources.json") or {}).get("claims"), "D-"))
    linked = set(model.get("claims_satisfied") or [])
    for i, div in enumerate(model.get("divergences") or []):
        where = f"model.json.divergences[{i}]"
        need_text(div, "description", where, e, "G2")
        for ref in div.get("claims") or []:
            if ref not in claims:
                e.append(f"G2 {where}.claims: unknown claim {ref}")
            linked.add(ref)
        check_cites(ctx, div.get("evidence"), f"{where}.evidence", e, "G2")
    for claim in sorted(claims - linked):
        e.append(f"G2 model.json: claim {claim} is neither satisfied nor linked to a divergence")
    need_log(ctx, "G2", e)
    return e


def g3(ctx):
    e = []
    data = ctx.load("checks.json")
    if not isinstance(data, dict):
        return ["G3 checks.json: missing or not an object"]
    model = ctx.load("model.json") or {}
    candidates = {}
    for i, cand in enumerate(data.get("candidates") or []):
        where = f"checks.json.candidates[{i}]"
        cid = cand.get("id")
        if not isinstance(cid, str) or not re.match(r"^C-\d+$", cid) or cid in candidates:
            e.append(f"G3 {where}.id: must be a unique C-<n>")
            continue
        candidates[cid] = cand
        if cand.get("label") not in LABELS:
            e.append(f"G3 {where}.label: must be INCONSISTENCY, RISK or AMBIGUITY")
        if not isinstance(cand.get("check"), int) or not 1 <= cand["check"] <= 12:
            e.append(f"G3 {where}.check: must be 1..12")
        need_text(cand, "claim", where, e, "G3")
        if cand.get("label") == "RISK":
            need_text(cand, "condition", where, e, "G3")
        if cand.get("label") == "AMBIGUITY":
            need_text(cand, "question", where, e, "G3")
        check_cites(ctx, cand.get("evidence"), f"{where}.evidence", e, "G3", need_quote=True)
    checks = data.get("checks")
    if not isinstance(checks, list):
        return e + ["G3 checks.json.checks: must list the twelve checks"]
    found = [c.get("id") for c in checks if isinstance(c, dict)]
    if sorted(x for x in found if isinstance(x, int)) != list(range(1, 13)) or len(found) != 12:
        e.append(f"G3 checks.json.checks: must contain ids 1..12 exactly once, found {found}")
    claimed = {}
    for i, check in enumerate(checks):
        where = f"checks.json.checks[{i}]"
        verdict = check.get("verdict")
        if verdict not in VERDICTS:
            e.append(f"G3 {where}.verdict: must be findings, clean or not_verifiable")
            continue
        refs = check.get("candidates") or []
        if verdict == "clean":
            need_text(check, "verified", where, e, "G3")
            check_cites(ctx, check.get("evidence"), f"{where}.evidence", e, "G3")
        if verdict == "not_verifiable":
            need_text(check, "missing", where, e, "G3")
        if verdict == "findings" and not refs:
            e.append(f"G3 {where}: verdict findings requires at least one candidate")
        if verdict != "findings" and refs:
            e.append(f"G3 {where}: only verdict findings may list candidates")
        for ref in refs:
            if ref not in candidates:
                e.append(f"G3 {where}.candidates: unknown candidate {ref}")
            elif candidates[ref].get("check") != check.get("id"):
                e.append(f"G3 {where}.candidates: {ref} belongs to check {candidates[ref].get('check')}")
            claimed[ref] = check.get("id")
    for cid in candidates:
        if cid not in claimed:
            e.append(f"G3 checks.json: candidate {cid} is not listed under its check")
    machines = {m.get("id"): m for m in model.get("machines") or [] if isinstance(m, dict)}
    operators = set(ids(model.get("operators"), "O-"))
    matrices = {}
    for i, matrix in enumerate(data.get("matrices") or []):
        where = f"checks.json.matrices[{i}]"
        machine = machines.get(matrix.get("machine"))
        if machine is None:
            e.append(f"G3 {where}.machine: unknown machine {matrix.get('machine')!r}")
            continue
        matrices[matrix["machine"]] = matrix
        ops = matrix.get("operators") or []
        for op in ops:
            if op not in operators:
                e.append(f"G3 {where}.operators: unknown operator {op}")
        rows = matrix.get("rows") or {}
        notes = matrix.get("notes") or {}
        for state in machine.get("states") or []:
            row = rows.get(state)
            if not isinstance(row, list) or len(row) != len(ops):
                e.append(f"G3 {where}.rows.{state}: needs one cell per operator ({len(ops)})")
                continue
            for op, cell in zip(ops, row):
                if cell not in CELLS:
                    e.append(f"G3 {where}.rows.{state}: cell {cell!r} must be defined, guarded or hole")
                if cell == "hole":
                    note = notes.get(f"{state}/{op}") or {}
                    if note.get("candidate") not in candidates and not substantive(note.get("note")):
                        e.append(f"G3 {where}: hole {state}/{op} needs a candidate or a note")
    check3 = next((c for c in checks if isinstance(c, dict) and c.get("id") == 3), {})
    if check3.get("verdict") != "not_verifiable":
        for mid, machine in machines.items():
            size = len(machine.get("declared_states") or machine.get("states") or [])
            if size <= 8 and mid not in matrices:
                e.append(f"G3 checks.json.matrices: machine {mid} has <=8 declared states and needs a matrix")
    need_log(ctx, "G3", e)
    return e


def g4(ctx):
    e = []
    data = ctx.load("findings.json")
    if not isinstance(data, dict):
        return ["G4 findings.json: missing or not an object"]
    candidates = {c.get("id") for c in (ctx.load("checks.json") or {}).get("candidates") or []}
    owner = {}

    def assign(cid, where):
        if cid not in candidates:
            e.append(f"G4 {where}: unknown candidate {cid!r}")
        elif cid in owner:
            e.append(f"G4 {where}: {cid} is already resolved in {owner[cid]}")
        else:
            owner[cid] = where

    fingerprints = set()
    for i, finding in enumerate(data.get("confirmed") or []):
        where = f"findings.json.confirmed[{i}]"
        fp = finding.get("fingerprint")
        if not isinstance(fp, str) or not FINGERPRINT.match(fp):
            e.append(f"G4 {where}.fingerprint: lowercase, stable, [a-z0-9._:/-]")
        elif fp in fingerprints:
            e.append(f"G4 {where}.fingerprint: duplicate {fp}")
        fingerprints.add(fp)
        assign(finding.get("candidate"), f"{where}.candidate")
        if not isinstance(finding.get("title"), str) or not finding["title"].strip():
            e.append(f"G4 {where}.title: required")
        if finding.get("label") not in LABELS:
            e.append(f"G4 {where}.label: must be INCONSISTENCY, RISK or AMBIGUITY")
        if finding.get("severity") not in SEVERITIES:
            e.append(f"G4 {where}.severity: must be critical, high, medium or low")
        if not isinstance(finding.get("check"), int) or not 1 <= finding["check"] <= 12:
            e.append(f"G4 {where}.check: must be 1..12")
        for key in ("root_cause", "recommendation"):
            need_text(finding, key, where, e, "G4")
        if finding.get("label") == "RISK":
            need_text(finding, "condition", where, e, "G4")
        if finding.get("label") == "AMBIGUITY":
            need_text(finding, "question", where, e, "G4")
        impact = finding.get("impact") or {}
        need_text(impact, "demonstrated", f"{where}.impact", e, "G4")
        if finding.get("severity") == "critical":
            need_text(impact, "scope", f"{where}.impact", e, "G4")
            need_text(impact, "unrecoverable_because", f"{where}.impact", e, "G4")
        confidence = finding.get("confidence") or {}
        if confidence.get("level") not in CONFIDENCE:
            e.append(f"G4 {where}.confidence.level: must be high, medium or low")
        need_text(confidence, "basis", f"{where}.confidence", e, "G4")
        check_cites(ctx, finding.get("evidence"), f"{where}.evidence", e, "G4", need_quote=True)
    for i, rejected in enumerate(data.get("rejected") or []):
        where = f"findings.json.rejected[{i}]"
        assign(rejected.get("candidate"), f"{where}.candidate")
        need_text(rejected, "reason", where, e, "G4")
        check_cites(ctx, rejected.get("evidence"), f"{where}.evidence", e, "G4", need_quote=True)
    for i, merged in enumerate(data.get("merged") or []):
        where = f"findings.json.merged[{i}]"
        assign(merged.get("candidate"), f"{where}.candidate")
        if merged.get("into") not in fingerprints:
            e.append(f"G4 {where}.into: {merged.get('into')!r} is not a confirmed fingerprint")
    for cid in sorted(c for c in candidates if isinstance(c, str)):
        if cid not in owner:
            e.append(f"G4 findings.json: candidate {cid} is neither confirmed, rejected nor merged")
    need_log(ctx, "G4", e)
    return e


def legacy_headings(text):
    return re.findall(r"^###\s+\[(?:critical|high|medium|low)\]\s+\[[A-Z]+\]", text, re.M | re.I)


def g5(ctx):
    e = []
    prior = ctx.run.get("prior_report")
    if prior is None:
        return e
    data = ctx.load("reaudit.json")
    if not isinstance(data, dict):
        return ["G5 reaudit.json: missing or not an object (a previous report exists)"]
    current = {f.get("fingerprint") for f in (ctx.load("findings.json") or {}).get("confirmed") or []}
    entries = data.get("prior_findings") or []
    counts = {"new": 0, "persisting": 0, "resolved": 0, "not_verified": 0}
    persisted_into = {}
    keys = []
    for i, entry in enumerate(entries):
        where = f"reaudit.json.prior_findings[{i}]"
        keys.append(entry.get("key"))
        status = entry.get("status")
        if status not in REAUDIT:
            e.append(f"G5 {where}.status: must be persisting, resolved or not_verified")
            continue
        counts[status] += 1
        if status == "persisting":
            target = entry.get("current")
            if target not in current:
                e.append(f"G5 {where}.current: {target!r} is not a confirmed fingerprint")
            elif target in persisted_into:
                e.append(f"G5 {where}.current: {target} already continues {persisted_into[target]}")
            persisted_into[target] = entry.get("key")
        if status == "resolved":
            need_text(entry, "resolution", where, e, "G5")
            check_cites(ctx, entry.get("evidence"), f"{where}.evidence", e, "G5", need_quote=True)
        if status == "not_verified":
            for key in ("last_evidence", "changed", "needed"):
                need_text(entry, key, where, e, "G5")
    if len(set(keys)) != len(keys):
        e.append("G5 reaudit.json.prior_findings: each previous finding is classified once")
    new = data.get("new") or []
    for fp in new:
        if fp not in current:
            e.append(f"G5 reaudit.json.new: {fp!r} is not a confirmed fingerprint")
        if fp in persisted_into:
            e.append(f"G5 reaudit.json.new: {fp} is also persisting")
    counts["new"] = len(new)
    for fp in sorted(x for x in current if isinstance(x, str)):
        if fp not in persisted_into and fp not in new:
            e.append(f"G5 reaudit.json: confirmed {fp} is neither new nor persisting")
    if data.get("counts") != counts:
        e.append(f"G5 reaudit.json.counts: must be {counts}")
    if isinstance(prior, dict) and prior.get("format") == "json":
        old = json.loads((ctx.run_dir / "prior" / "findings.json").read_text(encoding="utf-8"))
        expected = {f.get("fingerprint") for f in old.get("confirmed") or []}
        if set(keys) != expected:
            e.append(f"G5 reaudit.json.prior_findings: keys must be the previous fingerprints {sorted(expected)}")
    elif isinstance(prior, dict):
        text = (ctx.run_dir / "prior" / "report.md").read_text(encoding="utf-8")
        expected = len(legacy_headings(text))
        if len(entries) != expected:
            e.append(f"G5 reaudit.json.prior_findings: previous report has {expected} findings, {len(entries)} classified")
    need_log(ctx, "G5", e)
    return e


def strip_code(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


def g6(ctx):
    e = []
    report_rel = ctx.run.get("report_path")
    path = ctx.root / report_rel if isinstance(report_rel, str) else None
    if path is None or not path.is_file():
        return [f"G6 {report_rel}: the report has not been written"]
    text = path.read_text(encoding="utf-8")
    if ctx.run.get("status") == "incomplete":
        return e
    findings = (ctx.load("findings.json") or {}).get("confirmed") or []
    headings = re.findall(r"^###\s+\[(critical|high|medium|low)\]\s+\[([A-Z]+)\]\s+(.+?)\s*$", text, re.M | re.I)
    by_title = {}
    for severity, label, title in headings:
        by_title.setdefault(norm(title).lower(), []).append((severity.lower(), label))
    if len(headings) != len(findings):
        e.append(f"G6 report: {len(headings)} finding headings, findings.json has {len(findings)} confirmed")
    for i, finding in enumerate(findings):
        title = norm(str(finding.get("title", ""))).lower()
        found = by_title.get(title)
        if not found:
            e.append(f"G6 report: confirmed[{i}] '{finding.get('title')}' has no '### [severity] [LABEL] title' heading")
        elif len(found) > 1:
            e.append(f"G6 report: '{finding.get('title')}' appears more than once")
        elif found[0] != (finding.get("severity"), finding.get("label")):
            e.append(f"G6 report: '{finding.get('title')}' is shown as {found[0]}, recorded as "
                     f"({finding.get('severity')}, {finding.get('label')})")
    summary = text.split("\n### ", 1)[0]
    for severity in SEVERITIES:
        expected = sum(1 for f in findings if f.get("severity") == severity)
        match = re.search(rf"\b{severity}:\s*(\d+)", summary)
        if not match:
            e.append(f"G6 report summary: missing the count line entry '{severity}: N'")
        elif int(match.group(1)) != expected:
            e.append(f"G6 report summary: {severity}: {match.group(1)}, findings.json has {expected}")
    if ctx.run.get("prior_report") is not None:
        counts = (ctx.load("reaudit.json") or {}).get("counts") or {}
        for key, label in (("new", "new"), ("persisting", "persisting"),
                           ("resolved", "resolved"), ("not_verified", "not verified")):
            match = re.search(rf"\b{label}:\s*(\d+)", summary)
            if not match:
                e.append(f"G6 report summary: missing the re-audit count '{label}: N'")
            elif int(match.group(1)) != counts.get(key):
                e.append(f"G6 report summary: {label}: {match.group(1)}, reaudit.json has {counts.get(key)}")
    prose = strip_code(text)
    if re.search(r"<\s*/?\s*(div|span|br|table|tr|td|html|body|script|style|p|img)\b", prose, re.I):
        e.append("G6 report: contains HTML tags; the report is plain Markdown")
    rows = re.findall(r"^\|\s*(\d{1,2})\s*\|[^|\n]*\|\s*([^|\n]+?)\s*\|", text, re.M)
    mode = ctx.run.get("mode")
    if mode == "full":
        checks = {c.get("id"): c.get("verdict") for c in (ctx.load("checks.json") or {}).get("checks") or []}
        table = {}
        for num, verdict in rows:
            table.setdefault(int(num), []).append(verdict)
        if sorted(k for k in table if 1 <= k <= 12) != list(range(1, 13)):
            e.append("G6 report: full mode needs the coverage table with one row per check 1..12")
        for num in range(1, 13):
            cells = table.get(num) or []
            word = REPORT_VERDICTS.get(checks.get(num), "")
            if cells and not any(c.lower().startswith(word) for c in cells):
                e.append(f"G6 report: check {num} verdict must read '{word}' as in checks.json")
    if mode == "functional":
        if "```mermaid" in text:
            e.append("G6 report: functional mode must not include mermaid diagrams")
        if re.search(r"^\s*[-*]\s*\*\*Check\*\*", text, re.M):
            e.append("G6 report: functional mode must not include check numbers")
        if len({int(n) for n, _ in rows if 1 <= int(n) <= 12}) == 12:
            e.append("G6 report: functional mode must not include the twelve-check coverage table")
    return e


GATES = {"G0": g0, "G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6}


def run_all(ctx):
    errors = g0(ctx)
    run = ctx.run
    status, phase = run.get("status"), run.get("phase")
    if status == "needs_scope" or phase not in PHASES:
        return errors
    reached = PHASES.index(phase)
    # A gate applies once its phase is finished: every phase before the current
    # one, plus the current one when the run is complete.
    last = reached if status == "complete" else reached - 1
    for name in PHASES[1:last + 1]:
        gate = GATE_OF_PHASE.get(name)
        if gate:
            errors += GATES[gate](ctx)
    if status == "complete" and phase != "F7":
        errors.append("ALL run.json: status complete requires phase F7")
    if status == "incomplete":
        report = run.get("report_path")
        if not isinstance(report, str) or not (ctx.root / report).is_file():
            errors.append("ALL run.json: an incomplete run still writes a report that discloses why")
    return errors


def main(argv):
    args = list(argv)
    root = None
    if "--project-root" in args:
        i = args.index("--project-root")
        if i + 1 >= len(args):
            print("usage: systemic_check.py <G0..G6|all> <run-dir> [--project-root DIR]")
            return 2
        root = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 2 or (args[0] not in GATES and args[0] != "all"):
        print("usage: systemic_check.py <G0..G6|all> <run-dir> [--project-root DIR]")
        return 2
    gate, run_dir = args[0], Path(args[1]).resolve()
    if not run_dir.is_dir():
        print(f"ERROR {run_dir} is not a directory")
        return 2
    project_root = (root or run_dir.parent.parent).resolve()
    try:
        ctx = Ctx(run_dir, project_root)
        errors = run_all(ctx) if gate == "all" else GATES[gate](ctx)
    except Unreadable as exc:
        print(f"ERROR {exc}")
        return 2
    for line in errors:
        print(line)
    if errors:
        print(f"FAIL {gate}: {len(errors)} violation(s)")
        return 1
    print(f"OK {gate}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
