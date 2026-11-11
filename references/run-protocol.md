# Run protocol — when a run leaves the straight path

`SKILL.md` covers a run that goes F0 → F8 with every gate passing. Read the
matching section of this file before acting when one of these happens:

- [Resuming an interrupted run](#resuming-an-interrupted-run)
- [A later phase finds an earlier output wrong](#going-back-to-an-earlier-phase)
- [A gate keeps failing, or its fix is forbidden](#a-gate-that-cannot-pass)
- [`python3` is not available](#without-python)

The rules marked **[gate]** are enforced by `scripts/systemic_check.py`. The
log events named here are the ones `run.json.log` accepts; see
`references/run-contracts.md`.

## Resuming an interrupted run

Each phase reads its inputs from the workspace instead of recalling earlier
reasoning, so an interrupted run resumes at `run.json.phase` — same slug,
same workspace, same mode. It is not a re-audit: `prior_report` stays as it
was.

1. Log a `resumed` event under the current phase in `run.json`.
2. Run `systemic_check.py all <workspace>` before anything else. The sources
   may have changed while the run was stopped, and only the gates can tell.
3. Log its result right after `resumed`, as one entry: `gate_passed` under
   the current phase when it passes, `gate_failed` under the earliest failing
   phase when it does not.
4. If it passes, continue the current phase. A source that changed since F1,
   or any earlier gate that no longer passes, sends the run back to the
   earliest failing phase, as the next section says.

## Going back to an earlier phase

A phase writes only its own files and `run.json`. When a later phase
discovers that an earlier output is wrong — or a resumed run finds a source
changed — go back explicitly; never patch an earlier file silently:

1. Set `phase` to the phase returned to and add a `returned_to` log entry
   with the reason (which file changed, which record was wrong).
2. Delete the files of every later phase. They are stale; deleting them is
   part of the same run, not a fresh one.
3. Redo that phase and everything after it. Redo means rebuilding each
   phase's files from its inputs rather than editing them in place, keeping
   stable ids where the underlying element is unchanged.
4. In the quick profile, keep the `work.md` sections of the phases before
   the one returned to and rewrite the rest.
5. The redone phase's log opens with a line `returned_to: <reason>` (a fixed
   keyword, in every language) **[gate]**. A complete run shows a later
   `gate_passed` for the phase returned to **[gate]**.

## A gate that cannot pass

Fix the violations a gate reports inside the same phase and run it again, at
most two corrections. If it still fails — or at once, when every fix would
break a constraint the user set (a scope they forbade changing, a file they
excluded) — stop:

1. Set `status: incomplete` with an `incomplete_reason` naming the gate and
   the unresolved violations.
2. Keep `phase` at the phase whose gate failed **[gate]**.
3. Write the report with that reason in its first section, and what would
   unblock the run.
4. Close as F8 says: run `all`, log it, and lead the chat reply with what is
   missing and how to unblock it. Do not present findings from records the
   failed gate did not accept.

Log every gate result in `run.json.log`, including the ones that failed.

## Without Python

If `python3` is not available, the gates still apply; you check them by hand:

1. Apply each gate as a checklist against `references/run-contracts.md`:
   every **[gate]** rule, including the counts and the technique markers the
   validator would compute.
2. Log each as `gate_passed` with `checked manually` in its detail, and set
   `validation: "manual"`. Never claim the validator ran, and never invent
   its output.
3. The two helper commands are unavailable, so do their work yourself:
   - `sources.json`: take each `sha256` from `sha256sum`, `shasum -a 256` or
     an equivalent, and count `lines` as the contracts file says. If no tool
     can hash, say so instead of inventing a hash.
   - `tests.json.by_category`: count the coverage entries per category, in
     the shape the contracts file gives.
4. State in the report's scope section that the gates were checked manually.
