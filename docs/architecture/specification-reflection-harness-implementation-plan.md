# Implementation Plan — Specification & Reflection Harness

- **Authority:** [`docs/architecture/proofbound/README.md`](proofbound/README.md) and the normative
  documents it routes to. Historical design intent: RFC [§17](proofbound/evidence/original-rfc.md#17-integration-points-with-current-dsd-code), §19 in
  [`proofbound/evidence/original-rfc.md`](proofbound/evidence/original-rfc.md); validation record: RFC [§25](proofbound/evidence/implementation-findings.md#25-validation-pass-post-authoring-review-against-the-checkout) in
  [`proofbound/evidence/implementation-findings.md`](proofbound/evidence/implementation-findings.md)
- **Scope:** M0/M1 executable; M2+ coarse only

## 0. Architecture baseline and provenance

```text
Project:                         Proofbound  (github.com/tpellegrin/proofbound)
Original DSD upstream commit:    unknown  (see note below)
Inherited DSD version:           v15.5.5  (newest CHANGELOG.md entry; not a commit SHA)

Imported project baseline:       c292eb512113415499211738a8366923f5276eef
  branch:                        main
  subject:                       chore: bootstrap project from deepseek-and-destroy
  tag / git describe:            no tags; describe -> c292eb5
  working tree before doc work:  clean (only untracked path introduced was docs/)

M0 implementation baseline:      6038d296e4df76ad0aadc7df0346b1b8eaf9ce87
  commits:                       dc7baf5 test: add canonical test entrypoint
                                 3e25a0d fix: verify worker-rules snapshots against their
                                         recorded protocol identity
                                 e34d2d1 ci: protect the supported Python baseline
                                 6038d29 docs: establish Proofbound identity and the
                                         architecture baseline
  every commit independently green

M1 final:                        b9cb6565a8a9beea2e92250b0d4e99c9ba4d62da
  commits:                       37dff55 feat: add specification author and reflector roles
                                 4ecd256 test: prove independent reflection of a
                                         specification mutation
                                 b9cb656 docs: record M1 validation and the
                                         capability/purpose boundary
  every commit independently green

Validation environment
  Suite verified on:              Python 3.10.14, 3.12.5, 3.13.14, 3.14.5
  Canonical test command:         python3 -m unittest discover -s tests -t .
  Inherited baseline test count:  82   (green on 3.10+, unmodified)
  Post-M0:                        98   (82 + 16)
  Post-M1:                        111  (82 + 16 + 13)
  Post-authorship-policy:         118  (+ 7 Git authorship policy tests)

Architecture validation was performed against the imported project baseline.
```

**Why the upstream commit is unknown.** The repository's Git history was reinitialized at bootstrap:
`git log` contains exactly one root commit, `git reflog` contains only that commit's creation, and there
are no remotes, no tags, and no packed refs. No file records an upstream SHA. The only upstream identity
the repository exposes is the version heading `v15.5.5` at the top of `CHANGELOG.md`. Recording a SHA
here would be a guess, so none is recorded.

**Source of truth.** The local checkout at `c292eb5` is authoritative for this project. Public upstream
`main` is not consulted for implementation decisions.

### Authorship normalization (object identities changed, content did not)

Before M2, the M0 and M1 commits were rewritten to remove AI attribution trailers
(`Co-Authored-By: Claude …`, `Claude-Session: …`) that a coding-agent harness appended by
default. The rewrite was an interactive `reword` of all seven commits: **every file tree is
byte-identical to its predecessor, no commit message changed except for removing those trailers,
and no commit was squashed or reordered.** The Git author and committer were the human owner
throughout and were never an agent. Object identities nevertheless changed, so the mapping is
recorded here for auditability:

```text
imported project baseline  c292eb51…  ->  c292eb51…   (root commit; NOT rewritten)

acd1ad14ac39a3f2200dd5fde86dcf599e006e66  ->  dc7baf5298fc4d6f54db951a695d35aecaebf3fc
d8c63d11679d6df1a5c89f811d576319647c4452  ->  3e25a0d996c1e1da33d58ebc054894cbe2497950
1eb8b72ecd9f5fba458ab5e2a43e84da13396e3b  ->  e34d2d13d55b7c1baed0e4a67011d15eb3352561
6e30b6574da421641d8b10ca63f80bb07b87b4f8  ->  6038d296e4df76ad0aadc7df0346b1b8eaf9ce87  (M0)
c67268919d07478907be2692081d2b01d9d8ef6b  ->  37dff552652cd90ad29926ff513e508134f02e6d
e6c24e68bc697eb86165332c1baad43044b94873  ->  4ecd256cf10661302d8a30b08fc6446946c6f370
2af2f6a02d19641076fdb513f21245dd1a95f7b5  ->  b9cb6565a8a9beea2e92250b0d4e99c9ba4d62da  (M1)
```

The original DSD upstream commit remains **unknown**; nothing about this rewrite changes that.
Policy and guardrails are in `AGENTS.md` and `tests/test_repo_git_policy.py`.

## 1. Purpose

Make DSD's existing **mutation → independent review → acceptance** machinery accept *specification
artifacts* as first-class project mutations, without a parallel orchestration system. M0 establishes a
reproducible baseline; M1 proves the thesis with the smallest vertical slice:
`spec-author → spec-reflector → accepted project mutation`.

The RFC's validation pass (§25) executed this slice against the current checkout: it works with two role
registry entries and one changed expression. **If M1 turns out to need substantial new infrastructure,
stop and reassess** — that falsifies the RFC's central claim.

## 2. Invariants

**Canonical statement lives elsewhere.** Proofbound's architectural principles are RFC [§33](proofbound/core-model.md#33-consolidated-principles), `P1`–`P13`;
the inherited DSD mechanical invariants are RFC [§3](proofbound/execution-and-review.md#3-existing-invariants-that-must-be-preserved), `I1`–`I15`. This list is neither — it is the
*implementation-facing* restatement of what code in this plan must not break, and it cites the principle
it serves rather than competing with it. If this list and RFC [§33](proofbound/core-model.md#33-consolidated-principles) disagree, §33 wins.

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

98 tests green on Python 3.10, 3.12, 3.13 and 3.14 via the canonical command. Production diff is two
files. Adding two roles to the registry now produces zero test failures, which is the precondition M1
needs.

**Pre-commit audit addition.** Reviewing M0 as an outside PR surfaced one uncovered property rather than a
code defect. M0 narrowed verification from "every *current* protocol file is present and matching" to
"every *recorded* protocol file is present and matching". What makes that safe is a compensating control
elsewhere: launch authority is resolved from the exact snapshot, so a role added after a snapshot was
frozen fails loudly with `missing launch authority` rather than launching without its protocol. That
control was untested, and it is directly load-bearing for M1. Three regression tests were added (16 total
in the module): the compensating control itself, `--reuse-existing` on a historical revision, and refusal
to reuse a tampered one. No production change was required.

The CI workflow was also parsed mechanically with the system Ruby YAML library — no project dependency
added. It is structurally valid. Note that a YAML 1.1 parser reads the bare `on:` key as the boolean
`true`; GitHub Actions uses YAML 1.2 semantics where it is the string `on`, so the idiomatic unquoted form
is correct and was kept.

## 4. M1 — Reflection vertical slice  *(IMPLEMENTED)*

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

### M1 outcome  *(implemented and validated)*

All twelve steps were executed end to end against a scratch git project with a fake `opencode` worker, and
are additionally pinned as tests in `tests/test_m1_spec_reflection_slice.py` (13 tests). Observed
enforcement, all of it inherited:

| Step | Observed |
|---|---|
| 1–2 | `spec-author-1` wrote `specs/CH-001/proposal.md`; gate `integrity_ok: true` |
| 3 | author's own gate → *recorded project mutation requires a fresh independent-review integrity gate* |
| 4–5 | `spec-reflector-1` reserved with `writes_project: false`; gate clean |
| 6 | acceptance succeeded; task `accepted`; evidence bound to `spec-reflector-1`; `check_state` OK |
| 7–8 | findings routed via `--input` into `spec-author-2`; `contracts/` still holds only `r0001.md` |
| 9 | stale reflector → *fresh independent-review requirement violated: accepted review predates later project mutation in spec-author-2* |
| 10 | `spec-reflector-2` accepted |
| 11 | stray write → `WRITE-RESTRICTION: 1 path(s) outside explicit Allowed source changes: src.py` |
| 12 | reflector mutation → `READONLY-SCOPE-MOVED: 1 project path(s)` |

**Production change:** 18 inserted / 4 deleted lines across `scripts/_roles.py` and `scripts/dsd_state.py`,
plus two role protocol files. No new helper, no new state, no new artifact format, no change to the attempt
lifecycle.

**Compatibility, verified with a genuine pre-M0 artifact.** A v2 manifest written by the bootstrap code at
`c292eb5` (11 protocol entries) verifies under the 13-role M1 registry; inherited roles still launch from
it; M1 roles correctly refuse with `missing launch authority`; tampering is still rejected.

**Architectural refinement forced by implementation.** Independent-review *capability* is shareable and
mechanical; review *purpose* is doctrinal. A `reviewer` gate will satisfy a spec mutation and a
`spec-reflector` gate an implementation mutation, because enforcing which review a task warrants would
require Python to classify task semantics. The capability set stays narrow — `evidence-clerk` and other
read-only roles do not qualify, and a second `spec-author` attempt never does. RFC [§9.1](proofbound/evidence/original-rfc.md#91-two-review-classes-deliberately-not-collapsed) was amended;
`tests/test_m1_spec_reflection_slice.py` pins all three facts.

**Deferred to M2 as planned:** `dsd_spec.py`, change/freeze manifests, the artifact DAG, typed staleness,
task↔freeze binding, cross-artifact consistency, provider/model routing, human gates, worktrees, and any
DSD→Proofbound internal migration. M1 operates on one bounded artifact under one contract.
## 6. M2A — Durable artifact provenance  *(IMPLEMENTED)*

Design authority: RFC [§26](proofbound/evidence/implementation-findings.md#26-m2-design-check). M2 was **split** because the original single milestone coupled the artifact
model, the full DAG, and freeze into one landing — which violates I9 and would have shipped three
unproven theses at once.

### Thesis

> An accepted specification artifact can carry durable, version-controlled provenance — its content
> identity, what it was reviewed against, and for what declared purpose — such that validity and
> staleness are **derived** from Git alone, without a second acceptance engine and without Python
> reading engineering prose.

### Why this slice and not something smaller or larger

The highest-risk unknowns, in order:

1. **The ledger write is itself a project mutation by the parent.** It must not be writable by
   workers and must not trip a live attempt's scope check. This is mechanics, and mechanics is where
   this design can actually be wrong.
2. **Declared purpose must close M1's capability/purpose gap** without Python classifying prose.
3. **Dependency staleness must survive the run tree being absent** — the invariant that justifies the
   ledger existing at all.

(3) needs two artifacts and one edge. (1) and (2) need one. Two artifacts with a single dependency
edge is therefore the smallest slice that can falsify all three. Anything smaller cannot test
staleness — the mechanism the rest of M2 is built on.

### Invariants this slice must not violate

Beyond §2: **no stored workflow state** (validity is computed, never written); **no second acceptance
engine** (the ledger records; DSD decides); **no PASS field** (acceptance is the parent's act citing a
gate, not a stored verdict); **an absent `## Review purpose` section preserves today's behavior
exactly**, so every existing contract and all 118 tests are unaffected.

### Expected surface

| File | Change |
|---|---|
| `scripts/pb_ledger.py` | **new** — parent-only: `record`, `validate`. Proofbound-native name, no `dsd_` prefix, but in `scripts/` so the existing sys.path root and helpers apply |
| `scripts/pb_purpose.py` | **new** — the closed purpose vocabulary and its purpose→roles table. Tiny; separate so `_roles.py` stays a role registry |
| `scripts/dsd_state.py` | one call beside `_assert_fresh_reviewer`, enforcing declared purpose against the accepted gate's role |
| `scripts/render_task_contract.py` | `review_purpose` added to `FIELDS`; renders `## Review purpose` |
| `scripts/_contract.py` | `declared_review_purpose(text)` — one call to the existing `_bullet_values`; no new parser |
| `.gitattributes` | **new** — spec artifacts marked `-text` so EOL translation cannot silently move accepted hashes |
| `tests/test_m2a_*.py` | **new** — see below |

Nothing else. If this slice starts needing `dsd_attempt.py`, `evidence_gate.py`, or the scope
machinery, the design is wrong and should be re-checked before continuing.

### Tests required before any production change

1. **Purpose table** — pure-function tests: each vocabulary entry maps to its permitted roles;
   an unknown purpose is rejected; the table is a closed set.
2. **Canonicalization** — a record hashes identically under key reordering and pretty-printing;
   differs under any value change; the recorded `format` selects the canonicalization used.
3. **Derived validity** — table-driven over the §26.14 decision table, including the transitive rule
   (a dependent of an `invalid` artifact is not `accepted` even when its own recorded dependency hash
   still matches).
4. **Characterization** — an existing contract with no `## Review purpose` accepts exactly as today.

### Acceptance scenario

Scratch project, fake worker, two artifacts and one edge (`proposal → design`):

| # | Step | Expected |
|---|---|---|
| 1 | `spec-author` writes `proposal.md`; `spec-reflector` reflects; `accept-task` | accepted, as M1 |
| 2 | `pb_ledger record` for the proposal | ledger committed with content hash, empty `depends_on`, purpose `proposal-reflection`, role, run-relative gate + hash |
| 3 | `pb_ledger validate` | `proposal accepted` |
| 4 | Same cycle for `design.md`, declaring `depends_on: proposal` | `proposal accepted`, `design accepted` |
| 5 | Accept the design citing a **`reviewer`** gate while the contract declares `design-reflection` | **rejected** — the M1 gap, now closed |
| 6 | Hand-edit `design.md` | `design invalid`; exit non-zero |
| 7 | Revert; re-author + re-reflect + re-accept the **proposal**; record it | `design needs-revalidation`, naming the old and new proposal hashes; design's own hash unchanged |
| 8 | Delete the run tree entirely, then `pb_ledger validate` | structural validation still reports the same states; provenance validation reports **unavailable**, not "passed" |
| 9 | Byte-identical re-author of the proposal | nothing invalidated |
| 10 | Worker attempts to write `ledger.json` | `WRITE-RESTRICTION` — inherited confinement |
| 11 | Full suite | green; all 118 inherited tests unchanged |

Step 8 is the one that matters most: it is the invariant that justifies the ledger's existence.

### Regression surfaces

`accept_task` (the only inherited file touched — one call), the contract renderer's field whitelist,
and the parent's write discipline around live attempts. Rollback is per-file: the new scripts are
additive, and the `accept_task` change is one call guarded by an absent-section default.

### Hard stop for M2A

No freeze, no aggregate identity, no artifact kinds, no graph-shape validation, no change profiles,
no implementation-task binding, no consistency reflection, no evidence export, no provider routing,
no human gates.

### M2A outcome  *(implemented and validated)*

Design authority: RFC [§26](proofbound/evidence/implementation-findings.md#26-m2-design-check), with the two open decisions resolved and the implementation corrections
recorded in RFC §27.

**Production surface added** (all additive except one guarded call):

| File | Role |
|---|---|
| `scripts/_artifact_identity.py` | Canonical text identity, `proofbound-artifact-text-v1` |
| `scripts/_review_purpose.py` | Closed purpose vocabulary and the purpose→roles relation |
| `scripts/pb_ledger.py` | `record` (parent-owned) and `validate` (structural + provenance) |
| `scripts/_contract.py` | `declares_review_purpose` / `declared_review_purpose`; `path_allowed` moved here from `evidence_gate` so the ledger does not depend on the gate CLI |
| `scripts/dsd_state.py` | One guarded call in `accept_task`: declared purpose → qualifying role |
| `scripts/render_task_contract.py` | `review_purpose` added to the strict `FIELDS` whitelist; renders `## Review purpose` and rejects an unknown purpose at construction time |
| `.gitattributes` | `text eol=lf` hygiene; **not** `-text` (RFC [§27.2](proofbound/artifacts-and-provenance.md#272-decision-resolved--canonical-text-identity-and-why--text-was-rejected)) |

**Deviations from the designed surface in §6, and why.** `scripts/_review_purpose.py`, not
`pb_purpose.py` — the leading underscore is this repository's convention for a shared helper module
(`_roles.py`, `_contract.py`, `_rules_snapshot.py`), and a bare `pb_` prefix reads as a CLI.
`scripts/_artifact_identity.py` was not anticipated at all; it exists because re-evaluating the
line-ending decision turned artifact identity into a versioned wire format that needed its own home and
its own characterization tests. `.gitattributes` carries `text eol=lf`, not `-text`. `path_allowed` was
moved from `evidence_gate.py` into `_contract.py`, beside the `_safe_prefixes` that produces the
prefixes it tests: the §6 rule *"if this slice starts needing `evidence_gate.py`, the design is wrong"*
caught a real coupling, and moving one pure function was the correct resolution rather than an
exception to the rule.

**Decisions resolved.** Fine-grained review-purpose vocabulary retained (five names, two enforcement
classes today) — RFC [§27.1](proofbound/execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained). Canonical text hashing adopted and `-text` rejected — RFC [§27.2](proofbound/artifacts-and-provenance.md#272-decision-resolved--canonical-text-identity-and-why--text-was-rejected).

**Tests.** 205 green on Python 3.10 and 3.14 via `python3 -m unittest discover -s tests -t .`; the 118
inherited tests are unmodified and still green. New: 20 artifact-identity characterization tests, 21
review-purpose tests, 36 ledger tests, 10 end-to-end slice tests.

**Proved end to end**, through real DSD mechanics with a fake worker transport: two artifacts and one
dependency edge; a `reviewer` refused for a reflection purpose despite holding the independent-review
capability; a worker attempting to write the ledger caught by the inherited `WRITE-RESTRICTION` before
any acceptance could exist; parent recording leaving the accepted attempt's gate bytes, frozen scope
diff and acceptance record byte-identical; A invalid and B needs-revalidation after A drifts; identical
structural classification after the entire run tree is moved away, with provenance falling to
`unavailable` rather than `verified` and never to `invalid`; and both artifacts restored to valid by
restoring A's exact accepted content.

**No second acceptance engine.** `_assert_fresh_reviewer` remains the sole freshness implementation and
is called from exactly one place. `pb_ledger.py` contains zero references to worker reports. `record`
refuses any task whose status is not already `accepted`.

## 7. M2B / M2C and later (coarse)

- **M2B — Artifact graph.** First-class artifact kinds; declared required-artifact set per change
  (parent declares, Python enforces — no policy language, no complexity scoring); graph-shape
  validation; transitive staleness reporting across the full DAG; whether `discovery` requires
  reflection and whether `request` is a dependency-only node.

### M2B readiness after the Part II consolidation

**Scope is unchanged.** Part II added no work to M2B and removed none. It added two constraints and
settled one question that would otherwise have surfaced during M2C.

| Question | Answer |
|---|---|
| Does the artifact graph need to change for future decision artifacts? | **No.** M2A's `depends_on` is already a plain path→identity map with no kind semantics. A decision record is an artifact with content, dependencies and a reviewed purpose — the existing shape carries it. |
| Should the graph be generic enough to represent them later? | **Yes, and this is a constraint on M2B.** Kinds may label nodes and drive required-set validation. Edges must stay kind-agnostic. A kind-specific edge semantic would need a schema break to admit decisions later. |
| Is applicability a dependency edge or a separate relation? | **A separate relation, deferred** (RFC [§36.3](proofbound/artifacts-and-provenance.md#363-applicability-is-not-a-dependency-edge)). A dependency means "reviewed against this exact content; revalidate if it moves". Applicability means "this constraint governs this region". Modelling applicability as a dependency would make superseding one decision invalidate every artifact in its scope. M2B must not add it, and must not add a speculative second edge type either. |
| Does M2B need artifact kinds? | **Yes** — a required/optional artifact set is meaningless without them. But a kind is a *label plus a declared required set*, never behaviour-switching logic. |
| Does M2B need profiles? | **Prefer the explicit declared required graph.** A profile is acceptable only as pure data expansion — a named, reusable declared set — and never as a policy language, a complexity score, or anything that selects a workflow by judging the change. |
| What is the smallest M2B thesis? | *A change's required artifact set and its dependency shape can be declared by authority and enforced mechanically, with staleness propagating across the whole declared graph — without Python judging whether the decomposition is any good.* |
| What stays outside M2B? | Freeze and binding; baseline identity; decision provenance; applicability; executable invariants; drift detection; coherence audit; context telemetry; human gates; provider routing; worktrees; naming migration. |

The M2A slice proved two artifacts and one edge. M2B's proof obligation is the step up: a *declared*
required set, a graph whose shape is validated against that declaration, and staleness that propagates
across more than one hop — which M2A's closure already implements and tests to depth 5000, so the
remaining risk is in declaration and shape validation, not in traversal.
- **M2C — Freeze and binding.** Immutable freeze manifest whose canonical hash is the freeze
  identity; candidate-aggregate consistency reflection (RFC [§26.8](proofbound/evidence/implementation-findings.md#268-direction-for-freeze-and-binding-m2c-not-designed-here)); `spec_freeze` contract binding;
  `SPEC-BINDING-DRIFT` in the integrity gate; supersession with conservative invalidation of all
  tasks bound to the superseded freeze; cross-change replay hardening.
- **M3 — Deterministic evidence and gates.** `evidence_bundle.py`; reviewer/auditor wiring; monotonic
  gate policy and approval records; checkpoint manifest additions.
- **M4 — Provider routing.** `resolve_runtime(state, role)`, `role_routing`, native-transport
  dispatch, adapter contract tests. Provenance records **role**, never model or provider; model
  identity stays in run evidence, where it already is.
- **M5 — Optional.** Evidence export/archival; transport-level permission profiles; worktree
  concurrency; model-neutral naming behind a `workspace_root()` helper.

**Research track — Context economy and refactoring economics.** Architecture recorded in RFC [§28](proofbound/context-economy.md#28-context-economy-and-refactoring-economics); no
production code exists and none is planned before M2C. Two stages, with a genuine dependency between
them:

- **CE1 — passive context-economy telemetry.** Provider-neutral first (repository files read,
  repository bytes read), token counts as secondary telemetry only. Recorded in run/execution evidence,
  never in the artifact ledger (RFC [§28.3](proofbound/context-economy.md#283-why-this-is-not-a-ledger-field)). No prerequisite; could land any time after M2C.
- **CE2 — controlled representative-change experiment.** Replays one task contract against two
  repository revisions with a fresh worker, discarding the mutation each time. **Depends on worktree
  concurrency (M5)**: the experiment must never leak benchmark mutation into a real branch.

Ordering is set by that dependency, not by preference. Neither stage may add fields to the accepted
artifact record, and neither may turn a mechanical signal into an automatic refactoring verdict.

## 7A. Capability dependency graph

RFC Part II (§§29–40) added future capabilities whose ordering is set by real dependencies, not by
preference. Milestone numbers are assigned only where the dependency is settled; the rest are named
capabilities placed in the graph.

```
                    M2A  durable artifact provenance          [DONE]
                          |
                          v
                    M2B  artifact graph                       [NEXT]
                          |  generic kinds + plain path->identity edges
             +------------+------------------+
             |                               |
             v                               v
        M2C  freeze / binding          decision provenance
             |                               |
             v                               v
        baseline identity              applicable-decision selection
             |                               |   (scope prefix intersection)
             v                               |
        execution binding                    +--> executable invariants
             |                               |     (soundness link: an invariant
             |                               |      must cite its source decision)
             +-------------+-----------------+
                           v
                 cumulative coherence audit

  separately, no dependency on the above:

        execution telemetry -> CE1 context economy -> controlled replay -> CE2 refactoring
                                                       (needs worktrees, M5)      economics
```

**Three corrections to the ordering that was assumed before this pass.**

1. **Decision provenance depends on M2B, not on M2C.** A decision record is an artifact with content
   identity, dependencies and a declared review purpose — exactly M2A's model. What it needs beyond M2A is
   artifact *kinds* (M2B), not freeze. Nothing about accepting a scoped decision requires a frozen
   baseline. Placing it after M2C would have delayed it behind an unrelated milestone.
2. **The coherence audit genuinely needs both branches.** It compares repository reality against *baseline
   plus authorized divergence*. With a baseline but no decision provenance it would report every
   authorized change as drift, which makes it worse than useless — high-volume false findings train
   reviewers to ignore it.
3. **Executable invariants are feasible without decision provenance but not *sound* without it.** Lint
   rules can be written today; a rule with no cited source decision is an unattributed cross-cutting
   policy, which is threat T2 arriving through the tooling. The edge is a soundness constraint, not a
   build-order one.

**The CE chain is genuinely independent.** RFC [§37.5](proofbound/context-economy.md#375-coherence-and-context-economy-are-different-measurements)'s reinforcing-loop hypothesis — erosion enlarges the
relevant context surface, which increases pattern imitation, which accelerates erosion — is a *hypothesis
worth measuring*, not a dependency. The two chains stay separate, and the two dimensions are never
collapsed into one health score:

| Dimension | Question |
|---|---|
| Context economy | How much repository context does a bounded change require? |
| Architectural coherence | How well does repository reality align with accepted intent and decisions? |

A subsystem can be cheap to navigate and architecturally incoherent, or coherent and expensive. Merging
them into a single number would destroy both signals and create a gameable target (T10).

## 7B. Threat mitigation status

RFC [§39](proofbound/long-running-autonomy.md#39-long-running-autonomy-threat-model) states the threats. This table is their single mitigation record, kept here rather than in the RFC
so the roadmap and the coverage claim cannot drift apart. **Planned mitigation is not current protection.**

| ID | Threat | Current mitigation | Planned | Residual risk |
|---|---|---|---|---|
| T1 | Context rationale loss | Durable artifacts (M2A ledger); bounded worker context (`I7`); immutable contracts and reports | Decision provenance with rationale + trigger | **High.** M2A records *what* was accepted, never *why*. Rationale currently survives only in commit messages and worker reports, and reports are deletable run evidence. |
| T2 | Local workaround promotion | `Allowed source changes` bounds each task's blast radius; `DECISION_REQUIRED` exists as an escalation path | Decision provenance with mandatory scope; applicability selection | **High.** Nothing today distinguishes a bounded adaptation from a policy. Escalation is doctrinal — a worker that does not recognize the boundary simply does not escalate, and nothing detects that. |
| T3 | Pattern imitation | Role protocols; contract-scoped authority | Authority hierarchy in worker doctrine (RFC [§34.1](proofbound/core-model.md#341-the-evidence-hierarchy)); coherence audit | **High.** Fully unmitigated mechanically, and unmitigable mechanically — distinguishing debt from design is semantic. |
| T4 | Decision compounding | None | Immutable baselines; coherence audit; decision provenance | **High.** The threat that most motivated Part II is the one with the least current coverage. |
| T5 | Baseline drift | Immutable contracts and worker-rules revisions; M0's rule that history is judged by what it recorded | Freeze identity + supersession (M2C) | **Medium.** The *mechanism* (content-addressed, append-only, supersede-don't-mutate) is proven at artifact scale in M2A; no baseline object exists yet to apply it to. |
| T6 | Reviewer contamination | **Real and enforced.** `_assert_fresh_reviewer` requires a fresh independent attempt; reviewers are project-read-only; cross-role transitions start a fresh session | Fresh-context requirement extended to the coherence audit | **Low** per task. **High** across a run: nothing today evaluates anything larger than one task. |
| T7 | Stale defensive policy | None | Trigger provenance + explicit supersession (RFC [§36.4](proofbound/long-running-autonomy.md#364-retirement)) | **High.** No decisions exist, so none can go stale — the risk arrives with the capability, and the design must not ship without retirement. |
| T8 | Guidance accumulation | Hot-doctrine byte caps (`test_v15_4_consolidation.py`); **architecture corpus split into routed documents with an entry point, size caps and a reference checker** (`tests/test_docs_architecture_refs.py`) | Progressive disclosure of applicable decisions, once decision provenance exists | **Low–medium.** Both worker doctrine and architecture documentation are now capped and mechanically checked. Residual: nothing bounds the *number* of normative documents, and the routing map is hand-maintained — an unlinked document is caught, a badly-routed one is not. |
| T9 | Local-pass / global-fail | Per-task independent review; phase audit against frozen evidence | Cumulative coherence audit; completion/coherence split (RFC [§38.4](proofbound/long-running-autonomy.md#384-final-audit-is-two-audits)) | **High.** Phase audit is the closest existing analogue and is scoped to one phase's evidence, not to architectural coherence. |
| T10 | Metric gaming | **By construction.** No metric is a gate anywhere; no composite score exists; every signal terminates in a semantic evaluator (P1, P13) | Keep it that way when CE1 lands | **Low, conditional.** Low only while the "signal, never verdict" rule holds. The first CI check that fails on a context-cost threshold reintroduces it. |

The honest summary: **six of ten threats are largely unmitigated today.** The two that are genuinely
covered — T6 within a task, T10 by construction — are covered because they were designed for. Part II's
value is naming the other eight precisely enough to be built against; it is not a claim that they are
handled.

## 8. Deferred work (explicit)

Not in M2A, and not implicitly acquired by it: freeze and freeze identity; artifact kinds and
graph-shape validation; change profiles; implementation-task binding; consistency reflection;
evidence export or archival; human-gate policy; provider/model routing; worktree concurrency; any
stored workflow-state enum; project renaming or the `DeepSeekAndDestroy` workspace literal; UI,
database, or remote service; replacing the worker transport; changing Evidence Clerk or phase-close
semantics.

Two are worth naming as *deliberate non-solutions* rather than omissions. **Semantic equivalence** —
a wording-only edit changes the hash and costs a fresh reflection; the alternative (re-accept without
re-review) would break I6, so the cost is accepted. **Ledger forgery** — anyone with repository write
access can produce an internally consistent false ledger; Git review and retained run evidence are
the mitigations, and the ledger is never described as cryptographic proof (RFC [§26.10](proofbound/evidence/implementation-findings.md#2610-trust-boundary--what-the-hashes-actually-prove)).

## 9. Risks and rollback

| Surface | Regression risk | Detection | Rollback |
|---|---|---|---|
| `_rules_snapshot` (M0.5) | Weakened integrity or broken launches | Tamper + historical-snapshot tests; full suite exercises all five call sites | Single-file revert |
| ~~Test fixtures (M0.4)~~ | *Dropped — no change made; those fixtures now serve as pinned v2 compatibility coverage* | — | — |
| `_assert_fresh_reviewer` (M1.3) | Widening what counts as independent review | Scenario steps 2 and 7; the set is explicit and closed | One-expression revert |
| Role registry (M1.1) | Fingerprint change for new revisions; unexpected capability | M0.5 tests; M0.6 capability matrix | Remove entries; existing runs pin their own snapshot |
| CI (M0.3) | Flaky process/timing tests | First green run | Delete workflow |
| `accept_task` purpose check (M2A) | Rejecting acceptances that used to work | Absent `## Review purpose` defaults to today's behavior; characterization test pins it | One guarded call reverted |
| Parent ledger write (M2A) | Tripping a live attempt's scope check | Acceptance step 10; parent writes only between attempts | New file; delete it |
| Canonicalization (M2A) | An implicit ordering or encoding input, as in M0.5 | Reorder/pretty-print/EOL tests; `sort_keys` removes hidden ordering | Format is versioned from v1 |

**General property:** M0/M1 add no persisted state, no new artifact formats, and no change to the attempt
lifecycle. Reverting returns the repository to upstream behaviour exactly; already-accepted spec tasks
remain readable as ordinary DSD tasks with an unusual role name.

## 10. Human decisions required

**None blocks M2B.** Items 1, 2 and 4 are decided. Item 3 blocks the *end* of M2B. Items 7–10 arrived with
the RFC Part II consolidation and belong to capabilities that are not yet scheduled.

1. ~~**Purpose vocabulary granularity**~~ — **decided: keep the fine-grained vocabulary.** Five
   recorded names, two enforcement classes today. `purpose != capability != role`; collapsing names
   because their mechanics currently coincide would discard provenance and force retro-classification
   in M2B. RFC [§27.1](proofbound/execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained).
2. ~~**Artifact line-ending/identity protocol**~~ — **decided: canonical text hashing**
   (`proofbound-artifact-text-v1`), with `.gitattributes text eol=lf` as hygiene only. `-text` was
   evaluated and rejected. RFC [§27.2](proofbound/artifacts-and-provenance.md#272-decision-resolved--canonical-text-identity-and-why--text-was-rejected).
3. **Committed spec root** — `specs/<change-id>/` versus an existing repository convention. M2A can
   start against any root; this blocks the *end* of M2B.
4. ~~**Minimum interpreter**~~ — decided in M0: Python ≥3.10.
5. **Upstream posture** — whether the class-1 fixes (M0.2, M0.4, M0.5) are offered upstream. Affects
   branch hygiene, not implementation.
6. **Gate policy vocabulary ownership** — needed for M3 only.
7. **Decision review purpose** — does `design-reflection` cover architecture-decision review, or does a
   distinct `architecture-decision-reflection` belong in the registry? The review questions genuinely
   differ (soundness versus scope boundedness), and §27.1's tie-breaker leans toward adding one. **No
   registry change is made now.** Needed by the milestone that implements decision provenance, not by
   M2B. RFC [§36.5](proofbound/long-running-autonomy.md#365-does-decision-review-need-its-own-purpose).
8. **Scope vocabulary for decisions** — path prefixes reuse the `Allowed source changes` pattern and are
   mechanically selectable, but some scopes are genuinely conceptual ("everything doing authorization")
   and cannot be. How much conceptual scope is acceptable before applicability selection stops working is
   an open design question. RFC [§36.3](proofbound/artifacts-and-provenance.md#363-applicability-is-not-a-dependency-edge).
9. **Coherence audit trigger policy** — which event boundaries actually correlate with incoherence.
   Deliberately unresolved: it should be chosen from evidence, not guessed. RFC [§38.3](proofbound/long-running-autonomy.md#383-when-audits-happen).
10. ~~**RFC documentation split**~~ — **done.** The 195 KB single document became a routed corpus under
    [`proofbound/`](proofbound/README.md): an entry point that routes rather than summarizes, four
    normative documents, one research document, and historical evidence under `evidence/`. Authoritative
    bytes for a bounded task fell 66–92%. Reference integrity is enforced by
    `scripts/check_docs_refs.py` and `tests/test_docs_architecture_refs.py`.
11. ~~**ADRs for Proofbound itself**~~ — **decided: no ADR program now.** Applying the M2A field test,
    no invariant becomes impossible without one: rules live in the normative documents and their
    rationale in [`evidence/implementation-findings.md`](proofbound/evidence/implementation-findings.md),
    one link away. An ADR corpus would add a third document class and a fourth identifier namespace
    (against the namespace discipline in [`README.md`](proofbound/README.md)) to solve a retrieval problem
    the split already solved. It would also compete with the decision-provenance capability Proofbound is
    designing as a product feature. **When that capability ships, Proofbound should dogfood it on its own
    architectural decisions** — the non-duplicating path, and a far stronger test of the feature than a
    synthetic one.
