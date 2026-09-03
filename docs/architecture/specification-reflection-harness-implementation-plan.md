# Implementation Plan — Specification & Reflection Harness

- **Authority:** `docs/architecture/specification-reflection-harness.md` (RFC), especially §17, §19, §25
- **Scope:** M0/M1 executable; M2+ coarse only

## 0. Architecture baseline and provenance

```text
Original upstream commit:        unknown  (see note below)
Upstream version identifier:     v15.5.5  (newest CHANGELOG.md entry; not a commit SHA)
Current project baseline commit: c292eb512113415499211738a8366923f5276eef
  branch:                        main
  subject:                       chore: bootstrap project from deepseek-and-destroy
  tag / git describe:            no tags; describe -> c292eb5
  working tree before doc work:  clean (only untracked path introduced was docs/)

Architecture validation environment
  Exploration / slice simulation: Python 3.9.6 (system python3, macOS/darwin 24.6.0)
  Suite baseline measured on:     Python 3.10.14, 3.12.5, 3.13.14, 3.14.5
  Canonical test command:         python3 -m unittest discover -s tests -t .
  Inherited baseline test count:  82  (green on 3.10+)
  Post-M0 test count:             95

Architecture validation was performed against this exact source revision.
```

**Why the upstream commit is unknown.** The repository's Git history was reinitialized at bootstrap:
`git log` contains exactly one root commit, `git reflog` contains only that commit's creation, and there
are no remotes, no tags, and no packed refs. No file records an upstream SHA. The only upstream identity
the repository exposes is the version heading `v15.5.5` at the top of `CHANGELOG.md`. Recording a SHA
here would be a guess, so none is recorded.

**Source of truth.** The local checkout at `c292eb5` is authoritative for this project. Public upstream
`main` is not consulted for implementation decisions.

## 1. Purpose

Make DSD's existing **mutation → independent review → acceptance** machinery accept *specification
artifacts* as first-class project mutations, without a parallel orchestration system. M0 establishes a
reproducible baseline; M1 proves the thesis with the smallest vertical slice:
`spec-author → spec-reflector → accepted project mutation`.

The RFC's validation pass (§25) executed this slice against the current checkout: it works with two role
registry entries and one changed expression. **If M1 turns out to need substantial new infrastructure,
stop and reassess** — that falsifies the RFC's central claim.

## 2. Invariants

Each is already enforced by existing code or tests. Implementation must not violate them.

1. **Historical runs stay verifiable** against the protocol identity they actually recorded, without
   weakening any check: missing file, hash mismatch, name-set mismatch, and unreproducible fingerprint all
   remain hard failures.
2. **One workflow truth.** Workflow status is a *function* of artifacts and evidence. Execution state
   (`state.json`), artifact status (committed manifest), and derived stage stay distinct — no stored enum.
3. **No spec mutation is acceptable without qualifying, fresh, independent reflection**, enforced by
   `_assert_fresh_reviewer`, not by prompts.
4. **Python proves objective facts only.** Nothing new parses worker prose, assigns PASS/FAIL, or
   reintroduces a report grammar; `decision_packet.py` and friends stay deleted.
5. **The orchestrator routes and approves; it does not re-review.** Parent input is gate JSON plus a
   bounded `gate --surface`, escalating to the read-only Evidence Clerk — never a reflection transcript.
6. **Existing execution/review behaviour is unchanged** (Implementer/Fixer/Reviewer/Verification/Recovery/
   Phase-Auditor/Clerk, phase close, recovery, checkpoint/resume) except where a milestone says otherwise.
7. **Bounded worker context:** run facts + `COMMON.md` + one role + one contract (+ named inputs).
8. **Reversibility:** every M0/M1 change reverts independently.
## 3. M0 — Trustworthy baseline  *(IMPLEMENTED)*

Goal: fresh checkout → documented interpreter → one canonical command → green locally and in CI, with
characterization pinning the protocol/rules-snapshot invariants M1 depends on.

Two planned tasks were **dropped on evidence** during implementation; both are recorded below rather than
silently omitted.

**M0.1 — Canonical environment and command.** *Files:* `tests/__init__.py` (new), `CONTRIBUTING.md` (new).
`python3 -m unittest discover -s tests -t .` failed with `Start directory is not importable`; the empty
package marker fixes it. Verified: 95 tests, exit 0 green / exit 1 on failure. *Invariant:* one
zero-ambiguity command, identical locally and in CI. *Upstreamable:* class 1.

**M0.2 — ~~Repair the interpreter-incompatible test module~~ — DROPPED.** The plan assumed the suite was
not runnable on one interpreter. Re-measured: that was true only for the **system** Python 3.9.6 on the
development machine, which is below the declared minimum. On 3.10.14 / 3.12.5 / 3.13.14 / 3.14.5 the
inherited suite is **82 tests, all green, unmodified**. `tests/test_v15_4_lifecycle_regressions.py` is
correct as written for a ≥3.10 interpreter, so adding `from __future__ import annotations` would be pure
style. No change made. *(Interpreter decision: ≥3.10. Evidence — the repository was authored under it,
since that module's un-guarded `Path | None` signature requires it; nothing anywhere requires more than
3.10; and 3.9 reached end of life in October 2025. The observed technical floor after a one-line change
would be 3.9, but the supported floor is a policy choice and 3.10 is the smallest value consistent with
the repository as authored.)*

**M0.3 — CI.** *File:* `.github/workflows/tests.yml` (new). `ubuntu-latest`, matrix `["3.10", "3.14"]` —
declared minimum and current stable — running the canonical command with **no dependency installation**
(the project is standard-library only; verified: no third-party imports, no packaging files). Amended
from the planned 3.12 to 3.14 because 3.14 is the current stable release; both matrix entries were run
green locally. *Invariant:* the known-green orchestration baseline is protected. *Upstreamable:* class 1.

**M0.4 — ~~Test fixtures derive the protocol registry~~ — DROPPED.** The plan recorded 17 failures across
three modules when two roles were added, and proposed deriving `PROTOCOL_NAMES` in those fixtures.
Re-measured **after M0.5**: adding two roles now causes **zero** failures. The 17 failures were a
*symptom* of the M0.5 defect, not an independent fixture problem — those fixtures write manifests
recording the historical protocol membership, which is exactly what M0.5 makes verifiable. Changing them
now would be churn and would destroy the v2-manifest compatibility coverage they incidentally provide.
No change made.

**M0.5 — Historical worker-rules snapshot compatibility.** *Files:* `scripts/_rules_snapshot.py`,
`scripts/prepare_worker_rules.py`.

*Defect:* `protocol_fingerprint()` and `current_payload()` measured a snapshot using the **current**
`PROTOCOL_NAMES`, so a snapshot recorded under a smaller registry failed with
`worker protocol snapshot is incomplete` — at all five verification call sites
(`render_worker_prompt.py:43`, `run_worker.py:130`, `evidence_gate.py:205`, `check_state.py:92`,
`native_worker_attempt.py:60`). `context_checkpoint.py` does not call it, so checkpoint/resume was never
affected.

*Fix:*
1. `recorded_protocol_order(manifest)` returns the sequence the snapshot itself recorded. A v3 manifest
   records `protocol_names` explicitly. A v2 manifest recorded only the membership map — serialized with
   `sort_keys=True`, so its key order is **not** the fingerprint order — and its sequence is reconstructed
   as the canonical registry order restricted to the recorded membership, with any name unknown to the
   current registry kept in a stable sorted tail.
2. That reconstruction is a **hypothesis, proved by the fingerprint**: `verify_snapshot` recomputes the
   ordered fingerprint over the reconstructed sequence and fails closed when it does not reproduce the
   recorded value. Nothing is skipped, ignored, or regenerated.
3. `MANIFEST_FORMAT` becomes `dsd-worker-rules-manifest-v3`, which records `protocol_names`;
   `SUPPORTED_MANIFEST_FORMATS` accepts v2 and v3 and rejects anything else by name.
4. `prepare_worker_rules.py --reuse-existing` carried the same latent assumption (it required every
   *current* protocol file to exist before reusing an older revision); it now checks only that the rules
   and manifest exist and lets `verify_snapshot` be the authority.

*Invariant protected:* a historical run stays verifiable under a newer harness, while a tampered
historical run stays rejected. *Upstreamable:* class 1 — a latent upstream defect.

**M0.6 — Characterization.** *File:* `tests/test_m0_protocol_snapshot_compat.py` (new, 13 tests). Written
**before** the M0.5 change; 5 failed against the defect and all 13 pass after it. Coverage: historical
subset snapshot verifies after registry growth (library **and** through the `check_state.py` call site);
tampered protocol content rejected; tampered rules body rejected; missing recorded protocol rejected;
a fingerprint recorded over sorted key order rejected; an unreproducible fingerprint rejected; an
explicitly recorded non-canonical order treated as authoritative; `protocol_names` disagreeing with the
protocol map rejected; unknown manifest format rejected; a newly created snapshot round-trips and records
its own order. Two guard tests pin the fixture's premises (the pinned history is a strict subset of the
current registry, and its sorted order genuinely differs from its canonical order) so the ordering tests
cannot become vacuous.

The historical membership in this file is **deliberately pinned, not derived** — deriving it from the
code under test would make the compatibility tests tautological.

*The plan's other five characterization items were dropped as redundant:* the inherited suite already
covers non-`reviewer` acceptance rejection, stale-reviewer rejection, write-restriction confinement,
read-only scope movement, and contract-renderer field rejection. One property the plan listed is genuinely
uncovered — *a byte-identical rewrite is not recorded as a mutation* — but M1 changes no scope-snapshot
behavior, so it is new coverage rather than characterization; it moves to M1's test list.

### M0 outcome

95 tests green on Python 3.10, 3.12, 3.13 and 3.14 via the canonical command. Production diff is two
files. Adding two roles to the registry now produces zero test failures, which is the precondition M1
needs.

## 4. M1 — Reflection vertical slice

**M1.1 — Role registry.** *File:* `scripts/_roles.py`. **Append** `spec-author` and `spec-reflector` to
`ROLE_SKILLS` (**append-only**: v2 manifests recorded no order, so M0.5 reconstructs theirs from the
canonical order restricted to recorded membership; v3 manifests record their own order and are immune).
Add
`spec-author` to `ALWAYS_PROJECT_WRITER_ROLES`; `spec-reflector` needs no entry because
`ALWAYS_READ_ONLY_ROLES` is a computed complement. Add
`INDEPENDENT_REVIEW_ROLES = frozenset({"reviewer", "spec-reflector"})`. Everything downstream follows for
free: `--role` choices in four scripts, `role_writes_project`, the reservation's `writes_project`, prompt
rendering, and `prepare_worker_rules.PROTOCOL_FILES`.

**M1.2 — Role protocol files.** *Files:* `worker/roles/dsd-spec-author/SKILL.md`,
`worker/roles/dsd-spec-reflector/SKILL.md` (new), terse and in house style (existing role skills are
672–1395 bytes; the reviewer skill is 1373 against a 1400-byte cap).
*spec-author:* author exactly one specification artifact from named upstream inputs; write only the file
named in `Allowed source changes`; never write code; never review own work; escalate consequential
product decisions via `DECISION_REQUIRED`.
*spec-reflector:* adversarially review one candidate artifact against its authoritative upstream and the
real repository; project read-only; classify findings blocking / should-fix / suggestion; "no findings"
is a valid outcome; review the reasoning, not the formatting.
These files enter every **new** worker-rules snapshot and change its fingerprint — which is why M0.5
comes first.

**M1.3 — Independent-review qualification.** *File:* `scripts/dsd_state.py`. In `_assert_fresh_reviewer`,
replace the literal `!= "reviewer"` test with membership in `INDEPENDENT_REVIEW_ROLES` and reword the
error to *independent-review*. The freshness/timestamp logic below it is already role-agnostic and must
not change. Update the one message assertion in
`test_v15_3_semantic_boundary.py::test_mutating_task_acceptance_requires_fresh_reviewer_provenance_not_implementer`.
*Upstreamable:* class 2.

**M1.4 — Minimal parent doctrine.** *File:* `SPEC-HARNESS.md` (new, cold, root). How to run one spec
task: render a contract whose `Allowed source changes` names exactly the artifact being authored; launch
`spec-author`; gate; launch `spec-reflector`; gate; `accept-task` on the reflector's gate. State
explicitly that revision rounds are new *attempts on the same contract*. **Not in M1:** the `SKILL.md`
pointer — `SKILL.md` sits exactly at its 7500-byte test cap, and that byte trade belongs with M2.

**M1.5 — Slice acceptance test.** *File:* `tests/test_spec_reflection_slice.py` (new). See §5. Also add
the one property M0 identified as genuinely uncovered: *a byte-identical rewrite is not recorded as a
mutation*, which is what keeps a prior reflection fresh across a no-op re-author.

**Not implemented in M1:** `dsd_spec.py`, manifest, ledger, freeze, `spec_freeze`/`requirements` contract
fields, `SPEC-BINDING-DRIFT`, evidence bundles, human gates, `resolve_runtime`, the dependency DAG, and
the `discovery`/`design`/`specification`/`tasks` artifacts. M1 authors and accepts **one artifact**.

## 5. M1 acceptance scenario

One test against a scratch git project with a fake `opencode` on `PATH` (the `test_v15_helpers.py`
pattern). This scenario has already been executed against the checkout; outcomes below are **observed**.

*Initial state:* project committed with `src.py`, `PLAN.md`, `specs/CH-001/request.md`; run root with a
prepared worker-rules revision; task `spec/CH-001-proposal`, contract `r0001` whose
`## Allowed source changes` is `` `specs/CH-001/proposal.md` ``.

| # | Step | Expected outcome |
|---|---|---|
| 1 | `spec-author` writes `specs/CH-001/proposal.md` | gate `integrity_ok: true` |
| 2 | `accept-task` on the **author's own** gate | fails: *recorded project mutation requires a fresh independent-review integrity gate* |
| 3 | `spec-reflector` (PASS-shaped report) | gate `integrity_ok: true`, `writes_project: false` |
| 4 | `accept-task` on the **reflector's** gate | succeeds; task `accepted`; `accepted.semantic_report` points into the reflector attempt |
| 5 | `check_state.py` | `STATE OK` |
| 6 | FAIL path: findings → `spec-author-2` on the *same* contract via `--input`, different content | gate clean; `contracts/` still holds only `r0001.md` |
| 7 | `accept-task` on the now-stale reflector-1 gate | fails: *accepted Reviewer predates later project mutation in spec-author-2* |
| 8 | `spec-reflector-2`, then accept on its gate | succeeds |
| 9 | Negative: `spec-author` also writes `src.py` | `WRITE-RESTRICTION: 1 path(s) outside explicit Allowed source changes: src.py` |
| 10 | Negative: `spec-reflector` edits the artifact it reviews | `READONLY-SCOPE-MOVED: 1 project path(s)` |
| 11 | Regression: implementer→reviewer flow and capability matrix | unchanged (M0.6) |
| 12 | Compatibility: a pre-M1 worker-rules snapshot | still verifies (M0.5) |

**"M1 complete" means** steps 1–12 pass, the suite is green in CI, and the orchestrator never read the
proposal's content to accept it — only gate JSON and a bounded surface.

## 6. M2 and later (coarse)

- **M2 — Artifact model and lifecycle.** Committed `specs/<id>/manifest.json`; dependency DAG with typed
  staleness (`needs-revalidation` vs `invalid`, each with a reason); `dsd_spec.py` (`init/record/status`);
  the five artifacts plus the cross-artifact consistency reflection; the `SKILL.md` byte trade.
- **M3 — Freeze and contract binding.** Immutable freeze manifest whose own hash is the specification
  identity; `spec_freeze`/`requirements` contract fields; `_contract.spec_binding`; `SPEC-BINDING-DRIFT`;
  amendment/supersession; the traceability query.
- **M4 — Deterministic evidence and gates.** `evidence_bundle.py`; reviewer/auditor wiring; monotonic gate
  policy and approval records; checkpoint manifest additions.
- **M5 — Provider routing.** `resolve_runtime(state, role)`, `role_routing`, native-transport dispatch,
  adapter contract tests.
- **M6 — Optional.** Transport-level permission profiles; worktree concurrency; model-neutral naming
  behind a `workspace_root()` helper.

## 7. Deferred work (explicit)

Project renaming; the `DeepSeekAndDestroy` workspace literal; worktree/concurrency orchestration; any
stored workflow-state enum; the lifecycle beyond one artifact; provider routing; a policy language; UI,
database, or remote service; plugin framework; file reorganization; replacing the worker transport;
changing Evidence Clerk or phase-close semantics.

## 8. Risks and rollback

| Surface | Regression risk | Detection | Rollback |
|---|---|---|---|
| `_rules_snapshot` (M0.5) | Weakened integrity or broken launches | Tamper + historical-snapshot tests; full suite exercises all five call sites | Single-file revert |
| ~~Test fixtures (M0.4)~~ | *Dropped — no change made; those fixtures now serve as pinned v2 compatibility coverage* | — | — |
| `_assert_fresh_reviewer` (M1.3) | Widening what counts as independent review | Scenario steps 2 and 7; the set is explicit and closed | One-expression revert |
| Role registry (M1.1) | Fingerprint change for new revisions; unexpected capability | M0.5 tests; M0.6 capability matrix | Remove entries; existing runs pin their own snapshot |
| CI (M0.3) | Flaky process/timing tests | First green run | Delete workflow |

**General property:** M0/M1 add no persisted state, no new artifact formats, and no change to the attempt
lifecycle. Reverting returns the repository to upstream behaviour exactly; already-accepted spec tasks
remain readable as ordinary DSD tasks with an unusual role name.

## 9. Human decisions required

None blocks starting M0.

1. ~~**Minimum interpreter**~~ — **decided in M0: Python ≥3.10**, on the evidence in §3 (M0.2). Reopen
   only if 3.9 support is a product requirement; production scripts would run there after a one-line
   change to one test module.
2. **Committed spec root** — `specs/<change-id>/` versus an existing convention. Blocks the *end* of M2.
3. **Upstream posture** — whether the class-1 fixes (M0.2, M0.4, M0.5) are offered to
   `frozenpepper/deepseek-and-destroy`. Affects branch hygiene, not implementation.
4. **Gate policy vocabulary ownership** — needed for M4 only.
