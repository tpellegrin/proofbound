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

## 7. M2B and later

M2B is designed in full below. M2C and beyond remain coarse until their own design checks.

### M2B — Change graph  *(IMPLEMENTED)*

Design authority: [`proofbound/artifacts-and-provenance.md` §A3](proofbound/artifacts-and-provenance.md#a3-the-change-graph-m2b--implemented).

**Thesis** *(revised — see the correction below)*:

> A change's contract-candidate artifacts and its required dependency topology can be declared by
> authority in one committed file and enforced mechanically against the accepted ledger, such that
> completeness and topology conformance are derived — without Python judging whether the decomposition is
> good, and without disturbing M2A's meaning of artifact validity.

The clause after the final "and" is new and load-bearing. The earlier thesis said "with staleness
propagating across the declared graph", which invited exactly the wrong implementation: overloading
`needs-revalidation` to also mean "the workflow now expects another artifact". Staleness already
propagates — M2A's closure does it, tested to depth 5000. M2B adds a *second, separate* dimension.

**Correction to the previous readiness assessment.** That table answered "Does M2B need artifact kinds?"
with **Yes**, on the grounds that a required/optional artifact set is meaningless without them. Working
the design through falsifies this. If authority declares paths explicitly, the required set *is* those
paths, and every candidate invariant that might need a kind — review purpose, freeze ordering, consistency
review, decision handling — was tested and needs none
([§A3.8](proofbound/artifacts-and-provenance.md#a38-what-m2b-does-not-do)). The earlier answer was
reasoning from *profiles*, which are themselves deferred. **M2B introduces no artifact kinds.**

### M2B invariants

1. **Graph satisfaction and artifact validity are separate dimensions.** Adding a sibling node must leave
   every existing artifact `valid`. Only a change to a node's *own required dependency set* may require
   its re-review, and that is reported as a graph finding, never by mutating its M2A state.
2. **Exactness is scoped and record-based.** Evaluated over ledger records within the graph file's own
   directory. Never over the filesystem; an undeclared *file* is not a finding, an undeclared *record* is.
3. **Membership and dependency targets are different.** A target that is not a member is external and must
   have an accepted record in the same ledger — which the existing `load_ledger` already enforces.
4. **Parent-owned.** The graph path stays outside every worker's `Allowed source changes`; a worker
   writing it trips the inherited `WRITE-RESTRICTION` (`I6`, `P7`).
5. **No stored state** (`P3`), **no kinds**, **no profiles**, **no scheduler**, **no graph identity in task
   contracts**, **no lock on topology change during live attempts**.
6. **v1 semantics are exact and frozen** (`P6`). A future v2 must not reinterpret a v1 file as a minimum
   graph.

### Likely surface

| File | Change |
|---|---|
| `scripts/_change_graph.py` | **new** — schema load, canonical serialization, path normalization, membership/edge comparison against a ledger, findings |
| `scripts/pb_graph.py` | **new, small** — `validate` (and nothing else until something needs it) |
| `scripts/pb_ledger.py` | extract the shared traversal primitive; **no semantic change** |
| `tests/test_m2b_*.py` | **new** |

**Expected inherited-code diff: near zero.** M2B sits above M2A's accepted-artifact primitive. If
implementation starts needing `dsd_state.py`, worker launch, the evidence gate, or role machinery, the
design is wrong and should be re-checked before continuing.

**One genuine gap found.** `pb_ledger.py` has no way to withdraw a record. Removing a node from the graph
therefore leaves an `undeclared-member` finding that cannot be cleared. M2B needs a small parent-owned
withdrawal operation, or must accept that node removal is unsatisfiable — the former is correct and
belongs in scope; it is a recording operation, not an acceptance one.

**Shared traversal.** `pb_ledger.py` already has `_assert_acyclic` and `_topological_order` over a
`node -> dependencies` mapping. The graph needs identical semantics. The smallest shared primitive is
those two functions generalized to `Mapping[str, Iterable[str]]`. Extract, do not reimplement: two
traversals that could disagree about a cycle would be a defect factory, and freeze aggregation will be a
third caller.

### Tests before production code

1. **Schema and paths** — unknown format fails closed; canonical serialization is stable; every illegal
   path spelling is rejected rather than normalized; case-colliding entries rejected; unknown fields
   rejected; cycles fail closed.
2. **Separation of dimensions** — adding a sibling leaves existing artifacts `valid`; adding an edge to an
   existing node leaves its content `valid` while producing `missing-required-edge`. This is the test that
   protects M2A's meaning, and it should be written first.
3. **Membership** — external dependency targets are legal; a target with no ledger record is
   `unknown-dependency-target`; an undeclared record within scope is `undeclared-member`; a stray
   non-accepted file in the directory is **not** a finding.
4. **Findings** — one per code, table-driven, deterministic.
5. **Run-tree independence** — findings identical with and without run evidence; provenance moves
   independently.

### M2B acceptance scenario

Scratch project, real DSD mechanics, three nodes — because M2A already proved two nodes and one edge, and
three is the smallest graph that has a topology rather than an edge.

Declare `A`, `B → A`, `C → A, B`. Then:

| # | Step | Expected |
|---|---|---|
| 1 | Validate the empty graph | unsatisfied; three `missing-artifact-record` |
| 2 | Author, reflect, accept, record `A` | still unsatisfied (B, C missing) |
| 3 | Same for `B` against `A` | still unsatisfied (C missing) |
| 4 | Same for `C` against `A` and `B` | **satisfied** |
| 5 | Mutate `A`'s bytes | `A` invalid; `B`, `C` `needs-revalidation` transitively; unsatisfied |
| 6 | Restore `A`'s exact accepted bytes | satisfied again |
| 7 | Add undeclared record `D` in scope | unsatisfied — `undeclared-member` |
| 8 | Declare `D` in the graph | unsatisfied — now `missing-artifact-record` is gone but D's record must still be valid; satisfied once it is |
| 9 | **Add sibling `E` to the graph only** | `A`–`D` remain **`valid`**; unsatisfied solely by `missing-artifact-record` for `E`; **no artifact becomes `needs-revalidation`** |
| 10 | **Change the graph so `B → A, C`** | `B`'s content still `valid`; unsatisfied by `missing-required-edge`; satisfied only after `B` is re-accepted against the new set |
| 11 | Remove an edge the ledger still records | `undeclared-edge` |
| 12 | Declare a dependency on an accepted artifact outside the graph | legal; validity propagates through it |
| 13 | Point an edge at a target with no ledger record | `unknown-dependency-target` |
| 14 | Delete the run tree | **identical findings**; provenance → `unavailable` |
| 15 | Worker attempts to write `graph.json` | `WRITE-RESTRICTION`; no acceptance possible |
| 16 | Full suite | green; all 211 existing tests unchanged |

Steps 9 and 10 are the decisive pair: they separate topology incompleteness from artifact staleness, which
is the failure the design exists to prevent.

### Regression surfaces

`pb_ledger.py` only, and only to extract shared traversal. M2A's schema, states, precedence and trust
boundary are unchanged. If a graph change forces an M2A semantic change, stop.

### M2B outcome  *(implemented and validated)*

Design authority: [`artifacts-and-provenance.md` §A3](proofbound/artifacts-and-provenance.md#a3-the-change-graph-m2b--implemented),
with the implementation corrections in
[§A3.9](proofbound/artifacts-and-provenance.md#a39-corrections-from-implementation).

| File | Role |
|---|---|
| `scripts/_dag.py` | **new** — the one DAG traversal, shared by ledger closure and graph topology |
| `scripts/_change_graph.py` | **new** — v1 schema, path rules, exactness scope, findings |
| `scripts/pb_graph.py` | **new** — `validate`, one command |
| `scripts/pb_ledger.py` | DAG extraction (behaviour-neutral) plus parent-owned `withdraw` |

**Zero changes** to `dsd_state.py`, the evidence gate, the role registry, worker launch, snapshot
protocols, or task acceptance. M2B sits above M2A's accepted-artifact primitive, which was the discipline
test for whether the design was right.

**Tests: 251 green on 3.10 and 3.14** — 211 inherited and unchanged, 35 graph unit tests, 5 vertical-slice
tests. The decisive pair is the topology revisions: adding a sibling leaves every artifact `valid`, and
requiring a new edge from an already-accepted node reports `missing-required-edge` while that node's
content stays `valid`. Artifact validity and graph satisfaction are demonstrably separate dimensions.

**Proved end to end** through real DSD mechanics: three nodes declared and accepted in order, satisfaction
only at completion; ordinary files beside the artifacts never becoming members; content drift producing
ordinary M2A transitive staleness and restoration returning satisfaction; a re-authored node requiring its
dependent's revalidation in turn; a worker writing `graph.json` caught by the inherited
`WRITE-RESTRICTION` with no graph-specific blocker; withdrawal clearing a removed node and refusing to
orphan a dependency; and run-tree removal leaving findings and states identical while only provenance
degrades.

### Hard stop for M2B

No freeze, no aggregate identity, no task→freeze binding, no consistency-reflection execution, no decision
provenance, no applicability, no supersession, no coherence audit, no telemetry, no kinds, no profiles, no
scheduler, no human gates, no provider routing, no worktrees, no naming migration.

### M2C — Freeze and binding  *(DESIGNED, NOT IMPLEMENTED — split into three)*

Design authority: [`artifacts-and-provenance.md` §A4](proofbound/freeze-and-binding.md#a4-freeze-and-binding).

M2C contains **three independently falsifiable theses**, and the design check recommends proving them
separately. Bundling them would repeat the mistake the original M2 split already corrected once.

| Slice | Thesis | Proves |
|---|---|---|
| **M2C-A** *(IMPLEMENTED)* | A satisfied graph plus its accepted bindings can be reduced to one deterministic, content-addressed, self-contained contract identity that later ledger or graph mutation cannot rewrite. | Freeze identity is *correct* |
| **M2C-B** *(IMPLEMENTED)* | An aggregate consistency reflection can be bound to an exact candidate identity, so a review of `C1` can never authorize `C2`. | Freeze is *coherent* |
| **M2C-C** *(IMPLEMENTED)* | An implementation task contract can name an exact freeze, and divergent freeze usage across a run is detectable. | Freeze is *executable* |

**M2C-A is the recommended next slice.** The mistakes that would be most expensive to discover later are
all freeze-identity mistakes and all independently testable now: content-only bindings failing to
distinguish different accepted dependency sets; a mutable ledger reference rewriting frozen meaning;
canonical-serialization ordering bugs; withdrawal breaking freeze-source resolution. None of them needs
consistency review or task binding to expose.

#### M2C-A invariants

1. **Copy, never reference.** A freeze contains its bindings and needs no ledger, graph or run tree.
2. **Candidate identity == freeze identity.** One number, recomputable, no stored self-hash.
3. **Bindings carry content, dependencies and purpose** — never role, gate, attempt, or graph identity
   ([§A4.3](proofbound/freeze-and-binding.md#a43-what-a-binding-contains-decisively)).
4. **Deterministic generation.** Same graph + ledger produce byte-identical output.
5. **v1 semantics pinned**, including the purpose vocabulary a v1 freeze may contain (`P6`).
6. **Parent-owned**; the freeze path lies outside worker write boundaries (`I6`, `P7`).
7. **Four separate validation layers**, never one boolean.

#### M2C-A acceptance scenario

Reuses M2B's three-node slice, then:

| # | Step | Expected |
|---|---|---|
| 1 | Freeze a satisfied graph | freeze written; identity recomputable |
| 2 | Re-run generation | byte-identical output, same identity |
| 3 | Re-accept B **byte-identically**, same deps and purpose, new gate/attempt | **candidate identity unchanged** — no contract churn |
| 4 | Re-accept B byte-identically against a **different dependency set** | **candidate identity changes** — the defining test |
| 5 | Re-accept B byte-identically under a **different purpose** | candidate identity changes |
| 6 | Reformat `graph.json` whitespace only | candidate identity **unchanged** |
| 7 | **Withdraw** a frozen artifact's record | freeze still states its full requirement; candidate equivalence now fails |
| 8 | Mutate a frozen artifact's bytes | freeze unchanged; repository satisfaction fails; internal validity unaffected |
| 9 | Hand-edit the freeze file | different identity; the old identity is unaffected |
| 10 | Delete the run tree | internal validity and repository satisfaction identical; provenance → `unavailable` |
| 11 | Unknown freeze format | fails closed |
| 12 | Worker writes a freeze file | inherited `WRITE-RESTRICTION` |

Steps 3, 4 and 6 together are the thesis: engineering meaning is bound, incidental execution history is not.

#### M2C-A outcome  *(implemented and validated)*

| File | Role |
|---|---|
| `scripts/_freeze.py` | **new** — bindings, canonical v1 serialization, identity, internal validation, derivation, comparison |
| `scripts/pb_freeze.py` | **new** — `create`, `validate`, `compare` |

**Zero changes** to `dsd_state.py`, the evidence gate, task contracts, acceptance, worker launch, roles,
`pb_ledger.py` or `pb_graph.py`. M2C-A sits entirely above M2A and M2B.

**Tests: 286 green on 3.10 and 3.14** — 251 inherited and unchanged, 30 freeze unit tests, 5 vertical
slice. The decisive pair: an equivalent re-review through a new attempt and gate leaves the identity
unchanged, while a changed dependency set changes it with byte-identical content. Also proved: a purpose
change alone moves the identity; a graph reformat does not; the freeze survives withdrawal and graph
deletion and remains interpretable from its own bytes alone in an empty directory; run-evidence loss and
corruption move provenance without touching identity; and a worker writing a freeze trips the inherited
`WRITE-RESTRICTION`.

Corrections in [`freeze-and-binding.md` §A4.8](proofbound/freeze-and-binding.md#a48-corrections-from-implementation),
including the resolution of the external-closure question the design check left open.

#### M2C-B — aggregate consistency  *(IMPLEMENTED)*

Design authority: [`freeze-and-binding.md` §A5](proofbound/freeze-and-binding.md#a5-aggregate-consistency-acceptance-m2c-b--implemented).

**Thesis.** An exact candidate can be independently challenged as a whole, and the durable fact that it
*was* challenged survives deletion of the run tree — without Python asserting that the engineering is
coherent, and without a second acceptance engine.

**The durable fact**, worded exactly: *candidate `C` received a qualifying consistency-reflection review,
and the parent accepted it.* Not "C is consistent" (a semantic verdict) and not "C is authorized"
(M2C-C).

**Four models were rejected against code before the fifth was chosen**, most usefully: the artifact
ledger cannot carry it (`derive_states` resolves every key as a file path, so a candidate key is
permanently `invalid`), an attestation artifact cannot be authored by a read-only reflector without
breaking M1 independence, and deriving it from the task contract plus gate fails because `accept_task`
writes acceptance into `run_root/state.json` — which is `L3` and expendable.

**Substrate findings that reduce the slice.** Verified in code, not assumed:

- **Freshness needs nothing new.** `accept_task` checks both that the contract hash still matches and
  that the accepted gate's `task` resolves to that exact contract path. A contract naming `C1` has
  different bytes from one naming `C2`, so a `C1` review cannot be accepted for a `C2` task. No
  reservation field, nonce or freeze revision.
- **No new role.** `consistency-reflection` already maps to `spec-reflector`.
- **No new write restriction.** The record path sits outside worker write boundaries like the ledger,
  graph and freezes.
- **M2C-A stays sound.** Verified empirically: when a graph-external dependency's bytes drift, the
  dependent member goes `needs-revalidation` through ledger closure, the graph stops being satisfied and
  the candidate becomes non-computable. So a computable current candidate implies every external
  dependency is still at its pinned content, and the reviewer may rely on it.

**Expected surface** — small, and entirely above M2A/M2B/M2C-A:

| File | Change |
|---|---|
| `scripts/_consistency.py` | **new** — v1 record schema, pinned qualifying-role constant, internal validation |
| `scripts/pb_consistency.py` | **new, small** — `record`, `validate`, and a lookup answering "has `C` been challenged?" |
| `scripts/_contract.py` | one parser for the declared candidate, reusing the existing helpers as `review_purpose` did |
| `scripts/render_task_contract.py` | one whitelist entry so the supported constructor can build such a contract |

**Expected inherited-core diff: zero.** No change to `dsd_state.py`, the evidence gate, acceptance,
roles, worker launch, the ledger, the graph, or the freeze format. If implementation starts needing any
of them, the design is wrong.

**Tests first**, in this order: the record schema and its pinned historical semantics; that a `C1` review
cannot be accepted for a `C2` contract (the replay proof, through real mechanics); that recording refuses
a task that is not accepted, a gate that is not clean, a wrong purpose and a non-qualifying role; and
that after the run tree is deleted the record still answers "was `C` challenged?" while provenance falls
to `unavailable`.

**Acceptance slice.** Reuse the M2C-A three-node scratch project: derive `C`, launch a
`consistency-reflection` contract naming `C`, accept it, record it. Then prove the orthogonal states —
delete the run tree (record intact, provenance `unavailable`); corrupt the gate (record and identity
unchanged, provenance `contradicted`); change an artifact so the current candidate becomes `C2` (the `C`
record stands, `C2` has none, and the `C1` review cannot be accepted for a contract naming `C2`); and
have a worker attempt to write the record (inherited `WRITE-RESTRICTION`).

**Non-goals.** No task-to-freeze binding, no mixed-freeze reporting, no phase behaviour, no
`current_freeze` or accepted-contract pointer, no consistency fixer or candidate revision, no repository
coherence audit, no freeze schema change, no new review purpose or role.

#### M2C-B outcome  *(implemented and validated)*

| File | Role |
|---|---|
| `scripts/_consistency.py` | **new** — v1 record, pinned v1 purpose/role constants, validation, lookup, provenance |
| `scripts/pb_consistency.py` | **new** — `record` (parent-owned) and `status` |
| `scripts/_contract.py` | `declares_candidate` / `declared_candidate`, reusing the existing bullet parser |
| `scripts/render_task_contract.py` | one whitelist entry so the supported constructor can bind a candidate |

**Inherited core untouched** — no change to `dsd_state.py`, the evidence gate, acceptance, roles, worker
launch, the ledger, the graph, or the freeze format. The two edited files took additive changes only.

**Tests: 318 green on 3.10 and 3.14** — 286 inherited and unchanged, 27 unit, 5 vertical slice. The slice
proves the replay refusal through real mechanics, the four-field record with no verdict of any kind, that
a challenge does not move `C`, re-review refreshing one subject, `C1` and `C2` coexisting, run-tree
deletion leaving the record intact with provenance `unavailable`, corruption leaving it intact with
provenance `contradicted`, and a reflector's forged record caught by three independent barriers.

Corrections in [`freeze-and-binding.md` §A5.10](proofbound/freeze-and-binding.md#a510-corrections-from-implementation).

#### Cross-ledger composition — decided

**A freeze binds bindings drawn from one ledger provenance universe. The recommended layout is a single
project-wide ledger.**

Per-change ledgers make cross-change reuse impossible — `load_ledger` requires every dependency target to
be a key in the same file — and reuse of accepted architecture artifacts and, later, decision records is
not an exotic case but the normal one. A project-wide ledger already works with M2B unchanged, because
exactness is scoped to the *graph's directory* and evaluates only records inside it; records belonging to
other changes are ignored rather than reported.

The cost is honest: one file grows without bound and is touched by every acceptance. It is a merge
hotspot only mildly, since records are per-artifact blocks under sorted keys, so unrelated acceptances
touch unrelated regions.

**The decision is reversible and requires no code change now.** The ledger path is already a CLI
argument, and a freeze names no ledger — after generation it is self-contained. If cross-ledger
composition is ever wanted, it becomes a candidate-construction concern, never a freeze-format change.

#### M2C-C — execution binding  *(IMPLEMENTED)*

Design authority: [`freeze-and-binding.md` §A6](proofbound/freeze-and-binding.md#a6-execution-binding-m2c-c--implemented).

**Requires no new persistent state.** The design check found no invariant that composition of shipped
primitives cannot establish, and the substrate reason is that M2C-B already shipped the contract
primitive: `## Proofbound candidate` is hash-bound by the inherited mechanism and `declared_candidate`
parses it. The M2C-B slice already proves the replay refusal end to end.

**Launch authorization** — three derived checks: the current graph and ledger derive exactly `C`; `C` has
a consistency acceptance record; that record's provenance is not `contradicted`. `verified` and
`unavailable` both authorize, because blocking on absent evidence would make provenance availability into
authority and invert the `L3`/`L4` separation.

**Authority is fixed at launch.** If intent moves to `C2` while a `C1` task runs, the task remains a `C1`
task through review, the fixer loop and acceptance. Rechecking currentness at acceptance would require
either discarding correct work or applicability inference, which is deferred.

**Divergence is reported, not gated** — there is still no mechanical phase close, and an adversarial test
guards against adding one.

**Stated limitation: execution binding only.** Task contracts and acceptance both live in the run tree, so
after deletion nothing in project state records that accepted task `T` was governed by `C`. No current
invariant consumes that fact, so no durable record is added; the trigger for revisiting is a completion
theorem or coherence audit.

##### M2C-C outcome  *(implemented and validated)*

| File | Role |
|---|---|
| `scripts/_execution.py` | **new** — `authorize` (composes current candidate + consistency acceptance + provenance) and `bound_candidates` (derives task bindings from immutable contracts) |
| `scripts/pb_execution.py` | **new** — `authorize`, `report` |
| `scripts/_freeze.py` | `current_candidate` extracted from the CLI so it can be composed rather than duplicated — behaviour-neutral |
| `scripts/pb_freeze.py` | delegates to it; orphaned imports removed |

**No new identity, no persistent state, zero inherited-core change.** Nothing in `dsd_state.py`, the
evidence gate, acceptance, roles, worker launch, the ledger, the graph, the freeze format or the
consistency record was touched.

**Tests: 340 green on 3.10 and 3.14** — 318 inherited and unchanged, 18 unit, 4 vertical slice.

**Proved end to end:** a freeze alone does not authorize (the aggregate challenge is required); a
challenged current candidate does; a task authorized against `C1` stays `C1`-bound through
implementation, review and acceptance after intent moves to `C2`; the historical candidate stops
authorizing *new* work; `C2` must earn its own challenge; divergence is reported without any task being
marked failed and with inherited unbound tasks reported honestly; `C1` review evidence is refused for a
`C2` contract; a worker rewriting the candidate in its own contract breaks acceptance; deleting the
consistency run evidence still authorizes while corrupting it refuses.

**Two refinements from implementation.** Authorization accepts a contract as well as a bare candidate,
since the contract is what becomes the authority and one declaring no candidate must be reported unbound
rather than silently authorized. And a wrong candidate yields two findings — not current, and never
challenged — which is more informative than stopping at the first.

##### Original expected slice

| File | Change |
|---|---|
| `scripts/pb_execution.py` *(name provisional)* | **new, small** — `authorize` (may a task launch against `C`?) and `report` (which candidate does each accepted task name?) |
| `scripts/render_task_contract.py` | none — `candidate` is already whitelisted |
| `scripts/_contract.py` | none — `declared_candidate` already exists |

**Expected inherited-core diff: zero.** Acceptance is deliberately not modified: the contract's binding is
already verified by inherited mechanics, and adding Proofbound semantics to `accept_task` would buy no
invariant.

**Tests first:** authorization refuses a non-derivable candidate, a candidate with no consistency record,
and one whose provenance is `contradicted`, while allowing `unavailable`; an implementation contract
naming `C` is hash-bound (extend the shipped replay proof to an implementation role); a `C1` task remains
acceptable after the current candidate becomes `C2`; the divergence report enumerates two accepted tasks
naming different candidates.

**Acceptance slice:** reuse the M2C-B scratch project — freeze, challenge, accept, then launch an
implementation task bound to `C`, run implementer → reviewer → accept, move intent to `C2`, and show the
`C1` task still accepts while the report surfaces the divergence.

**Non-goals:** durable implementation provenance, phase barriers, mixed-candidate gating, applicability,
completion semantics, coherence audit, any inherited-core change.

#### M2C-C — earlier sketch (superseded by the section above)

The task contract names the freeze in its Markdown:

```
## Proofbound freeze
- <freeze identity>
```

**No new binding machinery is needed, and this was verified in code.** `run_worker.py` records
`task_contract_sha256` over the whole contract file, and `accept_task` re-verifies it, so a freeze
reference in the contract is already immutably bound; changing it produces a different contract. Adding a
launch-reservation field would create a second truth that could disagree.

Workers receive a freeze *identity* plus the task-relevant frozen subset, never the whole contract
(`P13`). No per-task mini-freezes: one freeze is the baseline for a change, and context is sliced from it.

**Mixed-freeze detection: report, do not gate.** Two accepted tasks naming different freezes must not
silently constitute one completion baseline. But there is **no mechanical phase-close operation in this
repository** — phase status is set to `in-progress` at task creation (`dsd_state.py:192`) and never
mechanically closed, and `test_v15_5_adversarial::test_new_phase_state_does_not_create_barrier_machine`
exists specifically to stop gating state accumulating in phases. So M2C-C v1 provides a **read-only
report** enumerating accepted tasks and the freeze each contract names, flagging divergence as a finding
the parent acts on. Introducing a mechanical phase gate is a separate decision with its own design check,
not something to acquire as a side effect of freeze work.

Per-task acceptance deliberately does **not** consult a "current freeze": there is no such persisted
thing (`P3`), and adding one would be the mutable workflow state the architecture has refused throughout.

#### Freeze mutation semantics

| Event | Freeze identity | Old freeze still meaningful? | Repository satisfies it? | Provenance | New freeze needed? | Bound tasks |
|---|---|---|---|---|---|---|
| Re-accept, same content/deps/purpose | **unchanged** | yes | yes | may change | no | unaffected |
| Re-accept, changed dependencies | unchanged (old F) | yes | candidate equivalence fails | — | yes | remain bound to old F |
| Re-accept, changed purpose | unchanged (old F) | yes | candidate equivalence fails | — | yes | remain bound to old F |
| Ledger withdrawal | unchanged | **yes — freeze is self-contained** | candidate equivalence fails | — | yes | remain bound |
| Graph topology edit | unchanged | yes | candidate equivalence fails | — | yes | remain bound |
| Graph whitespace-only edit | unchanged | yes | **still equivalent** | — | no | unaffected |
| Artifact bytes mutate | unchanged | yes | repository satisfaction fails | — | yes | remain bound |
| Run evidence deleted | unchanged | yes | yes | → `unavailable` | no | unaffected |
| Run evidence corrupted | unchanged | yes | yes | → `contradicted` | no | policy question, not identity |

The column that matters: **freeze identity never changes in response to anything.** That is what makes it
a ruler (`P9`).

#### Threat resolutions

`F1` artifact mutation, `F2` dependency-set change, `F3` purpose change, `F5` withdrawal, `F6` overwrite,
`F7` graph change, `F9` evidence deletion, `F11` hand-edit, `F12` copied file — **solved by M2C-A**, all
covered by the table above and the acceptance scenario; `F12` resolves to *same bytes means same freeze*,
since the hash is unsalted and location is not protocol.

`F4` role/gate change only and `F16` unknown format — **solved by M2C-A** via §A4.3 exclusions and
fail-closed versioning. `F17` purpose-registry evolution — **solved by M2C-A** by pinning the v1
vocabulary rather than consulting the live registry (the M0 lesson).

`F8` graph file deleted — **solved incidentally**: a freeze needs no graph, so internal validity and
repository satisfaction are unaffected; only candidate equivalence becomes uncomputable, which is
reported rather than treated as invalidity.

`F10` evidence tampering — **already solved** by M2A's `contradicted`, orthogonal to freeze identity.

`F14` consistency review replayed onto a different candidate — **solved by M2C-B by construction**, since
the candidate identity the review binds changes whenever any binding changes.

`F13` mixed-freeze completion — **deferred to M2C-C, and only reported, not gated**; residual risk is
that a parent ignores the report. `F15` mechanically satisfied but semantically contradictory —
**deferred to M2C-B**; residual risk until then is a freeze that is authoritative and incoherent, which
is why §A4.6 refuses to call an M2C-A freeze "authorized for execution".

`F18` cross-ledger dependency — **explicitly unsupported in v1** and stated as such rather than implied.

#### Hard stop for M2C-A

No consistency-reflection execution, no task freeze field, no run or phase freeze binding, no phase-close
gate, no cross-ledger loader changes, no decision provenance, no applicability, no signatures, no
selective invalidation. Invalidation is whole-contract and conservative in v1: a task bound to `F1`
remains bound to `F1`, and whether execution may continue is a parent routing decision, not a mechanical
one.
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

## 7C. Post-M2C architecture decision  *(design check; nothing implemented)*

M2C is complete, and it left one visible gap: after the run tree is deleted, no project file records that
an accepted implementation task was governed by candidate `C`. The obvious next move is a durable
implementation-provenance record. **That move is wrong right now**, and the investigation that shows why
is more useful than the record would have been.

### The claim that is missing, and why it cannot yet be recorded truthfully

Stated exactly, the missing claim is *"accepted task `T` was governed by `C`"*. Three findings, each
verified against code, say it is the wrong thing to persist today.

**1. Nothing declares what implementation satisfies `C`.** The change graph is scoped to its own
directory — specification artifacts — and a freeze binds exactly those members. The only occurrence of
"implementation" anywhere in the graph, freeze or consistency layers is the `implementation-review`
purpose string. So there is no authoritative denominator: *"`C` has been implemented"* is currently
**undefinable**, and durable per-task provenance could only ever support *"these N tasks were accepted
under `C`"* — a count, not a completion. A record whose only consumer is a theorem that cannot be stated
is speculative state.

**2. Task identity is the wrong durable subject.** Take `C` implemented as `T1, T2, T3`, and the same
repository result reached as `T1, T2`. Task-keyed provenance makes those two histories permanently
different while the engineering fact — *this content implements this accepted intent* — is identical.
Task decomposition is a parent orchestration choice; promoting it to durable provenance would make local
adaptation into permanent architecture, which is exactly what `P7` forbids. Task contracts belong in
`L3`, and M2C-C was right to leave them there.

**3. The artifact ledger can carry implementation output but not its authority.** Verified empirically:
`pb_ledger record` *accepts* a source file from an accepted implementation task, the graph stays satisfied
because source lies outside its scope, and the candidate does not move. But the stored record is
`content_sha256` + `depends_on: {}` + `review_purpose: implementation-review` — it has **no field for the
governing candidate**, and `C` cannot become a `depends_on` entry because that map holds artifact paths
that must already be ledger keys. So Model D records *that* code was reviewed, never *which contract
governed it*. Extending the ledger to carry `C` would change what ledger membership means.

No stable repository-result identity exists to use instead: scope snapshots live in attempt directories
(`L3`), and Git commit identity is unstable across rebase, can span several tasks, and is historical
substrate rather than Proofbound protocol.

### Decision

**Durable implementation provenance is not the next milestone.** The prerequisite is an authoritative
model of what implementation `C` requires — an implementation decomposition that authority declares and
Python can enforce, the way M2B declares required artifacts. Until that exists, the durable subject
cannot be chosen without encoding orchestration accident. Recording the gap is the right outcome; filling
it now would be building a primitive because a box looked empty.

**The recommended next step is the evaluation/regression track**, and the reason is a measurement gap
larger than the durability gap:

> All six vertical slices drive a **stub worker**. The reflector writes a canned line. No test in this
> repository has ever exercised a real model.

The 340-test suite proves the *mechanics* work — hashes, scope, freshness, binding, refusals. It proves
nothing about whether a real spec-reflector catches a real contradiction, whether purpose distinctions
change reviewer behavior, or whether context economy holds under real prompts. Seven milestones rest on
the premise that fresh independent semantic review is worth its cost, and that premise has never been
measured. Meanwhile the durability gap has **no consumer at all**.

The evaluation track also has **no dependency** on the durability relationship: it runs disposable
scenarios and grades outcomes, and the existing slices are natural scenario seeds. It would additionally
supply evidence for the decomposition question above — whether reviewers behave differently across task
granularities is exactly the kind of thing that should be measured before it is designed around.

Two boundaries to carry into that design check: evaluation evidence is **not** architecture authority —
it can show regressions and reliability, and humans still decide what becomes accepted policy; and
deterministic product tests stay separate from model-driven pipeline evaluation. The 340-test suite is
not the harness.

## 7D. Eval V1 — semantic reflection reliability  *(IMPLEMENTED; baseline zero recorded)*

Design authority: [`evaluation.md`](proofbound/evaluation.md).

**Thesis.** A fresh spec-reflector, given an artifact it did not author, reliably detects a planted
engineering contradiction, and the pipeline routes it as findings rather than acceptance.

**The finding that shrinks the milestone.** No provider adapter is needed. `run_worker.py` launches a
worker as `subprocess.Popen(["opencode", "run", "--model", …])` resolved through `shutil.which` — exactly
the seam every vertical slice substitutes with a fake binary on `PATH`. A real trial is the *same pipeline*
with the real binary and credentials present, so evaluation exercises the product rather than a parallel
implementation. `launch-prompt.txt`, `terminal.json`, `worker.log` and the scope diff already supply
prompt bytes, timing, output and effects.

**Expected surface** — outside the deterministic suite, which must never depend on it or on credentials:

| Area | Content |
|---|---|
| `evals/scenarios/<name>/` | Synthetic fixture, accepted context, task contract, planted property, mechanical expectations, rubric |
| `evals/` runner | Copy fixture → run the real pipeline → grade mechanically via Proofbound's own APIs → grade semantically → write a structured result |
| `evals/results/` | Committed summaries; transcripts stay local and uncommitted |

**Outcome.** Implemented in `evals/` (scenario model with identity and a leak check, trial runner over
the real pipeline, mechanical + semantic grading, versioned summary, CLI) with 26 deterministic harness
tests. **366 tests green** on 3.10 and 3.14 — 340 inherited unchanged. Four scenarios ship. Two design
corrections are recorded in [§E14](proofbound/evidence/evaluation-runs.md#e14-eval-v1-implementation-outcome):
the mechanical half of the thesis was overstated, and prompt bytes are not context supplied.

**Baseline zero is recorded** in [§E15](proofbound/evidence/evaluation-runs.md#e15-eval-v1-baseline-zero)
and committed as `evals/results/eval-v1.json`: 20 attempted trials, 20 valid, 20 mechanically clean and
20 detected, against Proofbound `b64e3cc` with stable OpenCode 1.18.29. Collecting it exposed one harness
defect — a trial ran an ambient default model rather than the requested one, so a summary could name a
configuration it had not run — fixed with a regression test before the baseline was collected. The
result establishes that semantic detection happens at all, which is the stated trigger for designing
the control arm; it does not establish reliability, and it does not attribute detection to Proofbound.
A second condition surfaced afterwards from the same evidence — the suite cannot show a difference
between systems — so the control arm waits on §7E rather than following directly from this baseline.

**Scope:** 3–5 planted-contradiction scenarios in the M1 shape, 5 independent trials each, one harness,
mechanical grading through existing domain APIs, one model-grader path plus a human calibration sample,
per-scenario metric vector, no composite score, no CI gate.

**Non-goals:** control arm (deferred to V2 with a stated trigger — see `evaluation.md` E10), aggregate
consistency scenarios, holdouts, scenario mutation, pairwise grading, cost dashboards, scheduled runs,
any evaluation result influencing engineering authority.

## 7E. Eval V2 — scenario calibration  *(IMPLEMENTED; discrimination NOT established)*

Design authority: [`evaluation-comparison.md` §E16](proofbound/evaluation-comparison.md#e16-discrimination--why-baseline-zero-cannot-compare-systems).

**Why this milestone exists.** Baseline zero scored 20/20 and cannot compare systems. The retained
evidence says why: nineteen of twenty trials ran an identical six-call trajectory, the one trial that
went looking for more found the fixture contains no source files at all, and the engineering problem is
1,101 bytes of a 17.5 KB supply. Every candidate configuration receives the same input, so no
intervention in Proofbound could change the result. **Scenario range must be established before any
causal comparison is worth running** — otherwise a tie at ceiling reads as evidence against the
architecture when it is only evidence about the suite.

**Question.** Can a small set of semantically valid scenarios demonstrate non-ceiling behaviour under
legitimate system-under-test configurations?

**Scope.**

| Area | Content |
|---|---|
| Candidate scenarios | 3–5 new directories beside the existing four, exercising dependency distance, competing valid concerns and indirect implication (§E16.4–E16.5) |
| Human validation | A structured manifest review against the §E16.6 criteria before any live call. No annotation tooling |
| Screening | Low trial count per candidate against the shipped configuration and one legitimate weaker probe configuration, changing only `state.worker_runtime.model` |
| Retention | Scenarios meeting the pre-registered criteria receive a full repeated-trial measurement; the rest are recorded as rejected, with the reason |
| Metadata | `system.harness_version`, additive and optional, no format bump (§E16.9) |

**Non-goals:** the control arm (§E16.8 states its readiness criteria and its hypothesis); editing the
four V1 scenarios or their baseline; any change to the spec-reflector prompt, role protocols or grader
rubric; tool-call instrumentation; a scenario taxonomy; a model leaderboard; directory reorganisation
into `regression/` and `capability/`; backfilling historical summaries.

**Anti-goal, stated because it is the obvious way to get this wrong:** the target is informative variance
on meaningful engineering problems, not a lower score. A scenario is never retained because the current
model failed it.

**Built.** Four candidates — `retention-transitive-conflict`, `crowded-availability-review`,
`freshness-batching-conflict`, `pattern-versus-authority` — declaring difficulty dimensions the loader
checks rather than labels it accepts (§E16.5). `system.harness_version` is recorded additively with no
format bump, and `pb_eval compare` reports what differs between two runs without computing an ordering
(§E17). The four V1 scenarios are byte-frozen with their identities pinned in tests.

**Outcome: half the milestone succeeded.** The scenarios put the pipeline on the causal path —
reflectors now glob for source files and follow a design's reference to a policy the contract never
names, where every V1 trial read exactly the two documents it was handed. But **detection did not
separate**: 21 of 21 valid trials found the planted property on both a reference and a deliberately
weaker model, so no scenario was retained on the discrimination limb of the eligibility rule and no
model ordering is observable. The grader was checked rather than trusted — eight negative controls, all
`NOT_DETECTED` — so the tie is real. Diagnosis: the probe was not weak enough, and one-planted-property
detection may simply saturate for any model capable of running the pipeline. Configuration, trajectories,
retention decisions and the probe's setup failures are recorded in
[§E18](proofbound/evidence/evaluation-runs.md#e18-calibration-screening--the-scenarios-got-harder-the-suite-did-not-separate).

## 7F. Eval V3 — multi-property discrimination  *(IMPLEMENTED; dynamic range demonstrated)*

Design authority: [`evaluation.md` §E19](proofbound/evaluation.md#e19-multi-property-scenarios--more-resolution-still-not-a-score);
comparison rules in [`evaluation-comparison.md`](proofbound/evaluation-comparison.md).

**Why.** The observable, not the scenarios, is now the limit. Difficulty rose measurably across two
milestones and detection stayed at 20/20 then 21/21, because one planted property yields one bit per
trial and every capable configuration sets it. Raising resolution beats hunting for a weaker model.

**Question.** Do scenarios carrying several *independent* accepted obligations produce a graded signal
that separates legitimate capable configurations where binary detection cannot?

**Scope.**

| Area | Content |
|---|---|
| Scenarios | 3 new directories, 3 independent planted properties each, ≥1 `dependency-distance` property, distractors ≥ properties, ≥2 difficulty dimensions (§E19.2–E19.3) |
| Schema | `properties` list with scenario-local ids; legacy `property` retained unchanged; **identity computed from the form the manifest uses**, so the existing eight keep their hashes (§E19.7) |
| Grading | One independent grader call per property, same grader and rubric; per-property `grading-unavailable` (§E19.4) |
| Metrics | Property-level counts added; trial-level vocabulary generalised so `K = 1` records keep their exact meaning; both effectiveness views reported (§E19.5, §E19.8) |
| Comparison | Reference `opencode/nemotron-3-ultra-free` vs one capable alternative, low N first; **requires explicit authorization before any paid provider spend** |

**Non-goals:** the P12 control arm; precision/false-positive scoring; a third model; `--variant`
plumbing; prompt or protocol changes; holdouts; editing any existing scenario or recorded summary.

**Success is any of three outcomes**, and none of them is "the new model wins": separation on some
properties; equal completeness with *different* failure profiles, which is still useful; or a third
ceiling, which would mean the observable needs rethinking rather than more scenarios.

**Outcome: the observable moved, the configurations did not separate.** Obligations landed at 25/27
and 26/27 with complete trials at 7/9 and 8/9 — the first non-ceiling evaluation result in three
milestones. Every one of those eighteen trials would have scored *detected* under the single-property
observable, so the previous suites would have reported 18/18 and learned nothing. The decisive case is
a scenario planting two obligations reachable through the same sentence: reports argued that sentence
for the compatibility reason and never for the availability one, and the grader credited the first
while refusing the second — a distinction a single-property suite cannot express. The two
configurations converge on the *same* weak obligation, so there is **no observed ordering** and no
failure-profile separation either. Full record, including the provider confound and the unpinned
reasoning variant, in
[§E20](proofbound/evidence/evaluation-runs.md#e20-multi-property-screening--the-observable-finally-moved).

## 7G. Eval V4 — the P12 fresh-independence control  *(IMPLEMENTED; lower completeness under treatment)*

Design authority: [`evaluation-comparison.md` §E21](proofbound/evaluation-comparison.md#e21-the-p12-control--does-withholding-the-authors-reasoning-help).

**Why now.** The multi-property suite has demonstrated headroom (25/27 and 26/27 obligations, 7/9 and
8/9 complete trials), so a causal arm can produce a difference rather than tying at ceiling — the
condition §E16.8 set for attempting this at all.

**Question.** Does supplying a fresh spec-reflector with the authoring attempt's report reduce the
completeness of its independent reflection?

**What is actually varied.** `P12` bundles two claims. Execution freshness is already enforced by
`_assert_fresh_reviewer`; informational independence has never been enforced or tested and holds only
by construction. **Both arms are fresh executions** — only the information differs, so the
rationale-exposed arm is not "the non-fresh arm".

**Scope.**

| Area | Content |
|---|---|
| Treatment | A frozen synthetic spec-author attempt report per scenario, written to the shipped role protocol's own description, leak-checked per obligation and frozen before the first trial (§E21.5) |
| Transport | `--input`, which already carries exact run artifacts in production and binds the file's SHA-256 into the immutable launch prompt |
| Identity | Treatment lives beside `fixture/`, so scenario identity is provably unchanged; the run binds `system.author_report_sha256`, and the arm label is derived rather than stored (§E21.8) |
| Substrate | `compare` must generalise `controlled` beyond a hardcoded model variable, and must stop treating an absent treatment as unknown (§E21.9) |
| Matrix | Three frozen scenarios × two arms × **5 trials**, arms alternating in a pre-registered order; one worker configuration, `opencode/nemotron-3-ultra-free` |
| Primary outcome | Obligations detected over gradeable opportunities, with per-obligation, per-scenario, complete-trial and end-to-end views alongside |

**Non-goals:** model comparison (settled: no observed ordering); a neutral-context arm; a third arm
that instructs the reflector to challenge the rationale, which would change the system under test;
new scenarios or obligations; any prompt, protocol or rubric change; session reuse.

**Anti-goal.** The experiment must be able to falsify `P12`'s informational limb. Author reasoning
carrying intent and rejected alternatives could legitimately *help* a reviewer, and that outcome is
to be reported as counter-evidence, not explained away.

**Outcome: supplying the author's report lowered observed completeness.** 42/45 obligations and
12/15 complete trials untreated, against 38/45 and 8/15 treated, over 30 valid trials with no setup
or harness failures and `compare` confirming that only `treatment` differed. The difference is not a
general decline: six of nine obligations are identical, one improved under treatment, and the whole
gap is `migration/all-at-once-rollout` — 4/5 untreated, **0/5** treated — the one obligation whose
mechanism the author report explicitly argues for. Treated reports cite the report and do reach the
relevant sentence, but along the compatibility path the narrative lays out, never drawing the second
consequence. That matches the pre-registered reasoning-path shape rather than diffuse context load,
and is **not proof of anchoring**: two arms cannot separate it from added context, so the supported
claim stays operational. Full record in
[§E21.A](proofbound/evidence/evaluation-runs.md#e21a-the-p12-control--result).

## 7H. Eval V5 — the three-state craft calibration  *(IMPLEMENTED; instrument not ready)*

Design authority: [`system-craft.md` §50](proofbound/system-craft.md#50-calibrating-the-instrument--and-why-there-is-no-reference-architecture).
**Amends the earlier two-state form**, which is superseded and must not be implemented: a
good-versus-degraded experiment can be passed by an instrument that merely prefers whatever its designer
built as the good state, so it can demonstrate sensitivity and never specificity.

**Why.** `P10` says valid changes can compose into an incoherent system, `P13` names the surface that
damages, and §28.2 records that Proofbound does not observe it. The evaluation track can now measure it —
but only if the instrument is first shown to recognise quality rather than resemblance.

**Question.** Replaying one contract against three behaviourally equivalent repository states under one
frozen configuration, does the craft instrument identify the planted degradation in `D` *and* leave the
structurally different good state `E` alone?

**Scope.**

| Area | Content |
|---|---|
| Calibration case | One accepted intent; properties stated as scenarios with a response measure, never as adjectives (§50.5) |
| States | `R` good; `E` good, structurally different, independently vetted; `D` degraded on exactly one named property. All behaviourally equivalent, all passing the same tests (§50.4) |
| Replay | One future-change contract, one worker configuration, one harness/version, one grader, one timeout, fixed trial count and arm order — `CE2`'s structure, three states instead of two |
| Mechanical | `CE1` telemetry derived from evidence already retained: files read, bytes read, tool calls, changed paths, context traversed but not changed |
| Semantic | One fresh **state-blind** craft reflection per state under three lenses — composability, domain alignment, change locality. No state ever sees another (§50.2) |
| Grading | An independent grader holds declared status and decides whether the planted degradation was identified in `D`, and whether `E` was reported as degraded — a false positive |

**Success** is sensitivity and specificity together. **Failure** — `E` marked down for differing from
`R`, or `D` passing unnoticed — means the instrument measures resemblance, and more scenarios or trials
would not fix it. Both outcomes are informative.

**Non-goals:** any reference architecture used as a yardstick (§50.1); agent-generated candidates;
multiple cases or multiple degraded properties; longitudinal trajectories; comparison of Proofbound
against a bare model; a craft role or review purpose; CUPID scoring; architecture policy files; a
dependency database; production routing.

**Anti-goal.** Craft has no accepted referent, so nothing here may block, rank good architectures, or
produce a score. A milestone that ends with an architecture number has built the wrong instrument.

**Outcome: neither sensitivity nor specificity was demonstrated.** Sensitivity 3/5; specificity 7/9,
with every false degradation on the structurally different sound state and none on the other. The case
itself held — one identical behaviour suite across all three states, no state already satisfying the
probe, and fourteen of fifteen trials implementing the change correctly, so craft was never confused
with correctness. Two independent defects are now named rather than suspected: a reflector that reads a
small change surface as good locality and calls a file with no boundary "the composition root", and a
grader whose narrow question is not narrow enough to separate the declared property from any report
sentence containing the word "leak". Median files changed was 1 for the degraded state against 3 for
each sound one, so a change-surface heuristic would have ranked the degradation best — the concrete form
of what `P13` states in the abstract. Full record in
[§E50.A](proofbound/evidence/evaluation-runs.md#e50a-system-craft-calibration-v1--the-instrument-is-not-ready).

## 7I. Eval V6 — craft calibration V2, as a context treatment  *(run; hypothesis rejected)*

Design authority: [`system-craft.md` §54](proofbound/system-craft.md#54-calibration-v2--separate-the-explanations).

**Why not an artifact change.** The hypothesis that Calibration V1 failed because Proposal → Design →
Specification are too weak does not survive the evidence: V1 ran on repositories containing no artifacts
at all, and supplying the reflector with accepted design decisions would have converted craft into
conformance review against a referent, which is coherence. The artifact model needs no new artifact, no
protocol field, no kind — kinds were tested and rejected — and no new principle. What was missing was
written down instead: what each review purpose asks
([§51](proofbound/execution-and-review.md#51-what-each-review-purpose-actually-asks)).

**Question.** Does asking the reflector which decisions are expected to vary recover sensitivity without
costing specificity?

**Scope.** One frozen context treatment against V1's frozen case: same three states, property, models,
grader, probe and counterbalanced order. The treated arm additionally receives the decisions expected to
vary, **stated as questions and sourced from the intent** rather than from ground truth. Every
underlying fact was already visible in V1, which is what makes it a routing experiment rather than a
leak.

**Falsifiers, fixed in advance:** unchanged sensitivity means the instrument, not its context, is the
problem; recovered sensitivity at the cost of specificity means the questions are functioning as hints;
both improving means routing was the deficit.

**Separately and not simultaneously**, the grader's property should be decomposed into independently
graded obligations, the resolution the multi-property milestone already established. Treating the
reflector and decomposing the grader in one run would leave V2 as unable to attribute its result as V1
was.

**Non-goals:** artifact semantics implementation; a craft role or purpose; giving the reflector accepted
decisions; a second calibration case; production routing; any score.

**Result: routing is not the deficit.** Fourteen retained V1 implementations, both arms on each, order
counterbalanced. Sensitivity 2/5 untreated and 2/5 routed, with **every degradation pair concordant** —
three missed in both arms, two recognised in both, none discordant. Specificity 6/7 and 5/7, a difference
this size cannot separate from noise. The first falsifier fired: the reflector is not context-starved.

The reports say why. The routed arm answers the questions correctly — it names exactly which
provider knowledge `app.py` acquired — and then concludes the concentration *"aligns with the accepted
intent: provider credentials and endpoints are configuration."* The intent says credentials and endpoints
are configuration; it never says where configuration may live. The invariant the manifest encodes is not
entailed by what the reflector is shown, so the deficit is a **missing criterion, not a missing
question**, and the specificity regressions are the same gap read from the other side. Evidence:
[§E50.B](proofbound/evidence/evaluation-runs.md#e50b-system-craft-calibration-v2--routing-is-not-the-deficit-and-the-instrument-does-not-repeat);
analysis: [§56](proofbound/system-craft.md#56-why-routing-could-not-have-worked-here).

**A prerequisite V2 exposed, which supersedes the grader decomposition as the next step.** The untreated
arm was a byte-identical rerun of V1 on V1's own implementations and disagreed with V1 on **four of
thirteen**. The instrument's test-retest noise exceeds the effect it was built to detect, so no
treatment — grader decomposition included — is measurable at n=1 per cell until repeats per
implementation and a reported spread exist
([§57](proofbound/system-craft.md#57-the-instrument-does-not-repeat-itself)).

**Explicitly not adopted here.** Stating the invariant in the accepted intent is the obvious repair and
is legitimate in principle — it is a product constraint that passes the Field Test without naming an
architecture. Adopting it now, after seeing these outcomes, would fit the benchmark to its own results.
It must be pre-registered and its answer-blindness argued before any run that uses it.

## 7J. Eval V7 — measure the measuring system  *(run; both layers material)*

Design authority: [`evaluation-comparison.md` §E22](proofbound/evaluation-comparison.md#e22-reliability-before-validity).

**Question.** When the same craft evidence is measured repeatedly under one frozen configuration, how
much variation comes from the reflector, how much from the grader, and is the result stable enough to
support controlled calibration at all?

**Scope.** Three layers, never one number: the grader repeated over frozen report bytes; the reflector
repeated over frozen implementations; and the two together, which is what a user experiences. Anchors,
repetition counts, coding rubric and interpretation categories pre-registered before the first call.
Nothing optimised — no criterion, no routing, no decomposition, no prompt or sampling change, no
ensembling, no model comparison.

**Result: both layers move, and the reflector moves more.** On identical bytes the grader contradicts
its own modal answer 17% of the time and only one of six anchors is unanimous. On identical
architecture the reflector's conclusion differs from its own modal conclusion 43% of the time and
*every* instance splits, two of them evenly. End to end, 28%, and zero of six instances unanimous.
Evidence: [§E51](proofbound/evidence/evaluation-runs.md#e51-craft-instrument-repeatability--both-layers-move).

**What it retires.** At this noise floor a five-trial arm carries about one full count of noise, so V2's
zero-count sensitivity difference and one-count specificity difference, and the V1↔V2 movement, are all
inside it. No comparison this instrument has produced at this sample size is a finding.

**Where the deficit is, precisely.** All ten repeats on the `app.py` instance name the same fact — which
provider knowledge moved and where — and split five to four on whether that placement is acceptable. The
observation is stable and the judgement is not, which is the missing criterion of
[§56](proofbound/system-craft.md#56-why-routing-could-not-have-worked-here) measured directly.

**Non-goals honoured:** no missing criterion added; no question routing; no property decomposition; no
reflector or grader change; no temperature or sampling change; no ensembling or majority voting; no
model comparison; no production routing; no reliability state persisted.

**Next.** Reliability design for the semantic evaluation stack, before any Calibration V3. Fixing
validity first would tune a criterion against a measurement that redraws itself 28% of the time.

## 7K. Multi-sample semantic evaluation — design check  *(design only; no live calls)*

Design authority: [`evaluation-comparison.md` §E23](proofbound/evaluation-comparison.md#e23-what-one-semantic-measurement-should-be)
and [`system-craft.md` §58](proofbound/system-craft.md#58-craft-may-not-need-a-verdict-at-all).

**Question.** If one semantic model invocation is an unstable measurement, what should Proofbound treat
as semantic evidence, and under what conditions may several independent judgements support a usable
conclusion?

**Method.** Offline only. Exact combinatorial replay of aggregation policies over the samples already
recorded in `§E51` — no live reflector or grader call, no new evidence, no fixture change.

**Result: aggregation is layer-specific, and the unit was wrong before the sample count was.** Repeated
grading of unchanged bytes converges — policy instability falls 0.167 → 0.059 at N=5 and reaches 0.000
by N=11. Repeated reflection over unchanged architecture does not: 0.433 → 0.325 at N=5, still 0.267 at
N=9, and on one instance it gets *worse* with N, because a 4/4/2 split has no majority to recover.
Majority vote is therefore a legitimate noise-reduction operator on a reading task and a truth-recovery
fiction on a judgement task.

The deeper finding is that the craft measurement unit is a whole-report verdict, which is the wrong
shape: 57 of 60 reports agree on *where* provider knowledge moved while 43% of their conclusions about
*whether it matters* disagree, and the grader collapses "did not address it" into "says it is fine".
Every other review purpose already asks a discovery question, and multi-property grading already grades
per obligation.

**Decisions.** The future calibration unit is **per-pressure discovery frequency over N paired samples**
— `k/N` per pre-registered pressure plus the union of unpredicted concerns as a false-pressure rate.
Minority findings keep their support rather than being outvoted. No `disputed` state, no abstention
enum, no confidence field, no model reputation: `4/10` already says contested, and a derived status
would be a second truth (`P3`) with no mechanical consumer. No universal N — budgets belong to an
experiment, pre-registered against the smallest effect it intends to detect. Grader dispersion is
characterised **once** against a frozen anchor corpus rather than by `R x G` sampling, which `P13`
cannot afford.

**Not adopted:** production multi-sampling of any review purpose — the 43% was measured on the one
instrument with no accepted referent, and `P7` forbids that becoming global policy; heterogeneous panels,
which change the measuring system rather than repeat it; adjudication and debate, which are different
semantic procedures; structured reflector output, which would trade this problem for benchmark leakage
and is deferred to the discovery design.

**Next — superseded by [§7L](#7l-semantic-discovery-finding-identity-and-coverage--design-check--design-only-no-live-calls).** This
milestone named finding consolidation as the blocker. The following design check found that wrong: it
conflated open-world discovery with closed-world measurement, and only the former needs cross-sample
semantic identity.

## 7L. Semantic discovery, finding identity and coverage — design check  *(design only; no live calls)*

Design authority: [`evaluation.md` §E20](proofbound/evaluation.md#e20-two-measurement-problems-wrongly-sequenced-as-one).

**Question.** Must Proofbound solve open-world semantic finding identity before it can resume valid
closed-world System Craft calibration?

**Answer: no, and the previous sequencing was wrong.** A closed-world run declares its pressures before
execution, grades each sample against them independently, and never places two samples side by side.
There is no step in that path requiring cross-sample semantic identity. Doing consolidation first would
also contaminate V3, which exists to introduce a pre-registered criterion while holding measurement
mechanics fixed — grouping, or a reflector output contract designed to make grouping easier, would change
the criterion and the instrument in one run.

**Reused, not built.** The incidence a multi-sample run needs is the per-property vector `semantic()` has
produced since `E19.1`, with one index added: `trial x property` becomes `sample x pressure`. No new
artifact, no protocol noun, no state. One trap is recorded: `trial_verdict` collapses a property vector
with a logical AND, which is correct for its original purpose and would silently reintroduce a
whole-report verdict here.

**The real prerequisite is small.** V3 needs the *discovery* grader — *does this report identify this
specific problem?* — not the craft *verdict* grader whose 16.9% was measured, and which answers "upheld"
both when a report says the property holds and when it never mentions it. The discovery grader's contract
is already canonical; only its dispersion is unmeasured, and characterising it against a frozen anchor
corpus is a run on existing machinery rather than a redesign.

**Rejected.** Canonical finding identity, which fails the Field Test and would destroy the
observation-stable / judgement-split structure the reliability run measured; capture–recapture estimation,
whose independence and homogeneity assumptions are violated here far more severely than in the human
inspections where it is already contested, and whose documented failure direction is underestimating what
remains; heterogeneous panels as a way to raise N, since nine judges across seven model families were
measured as carrying about two votes of independent information.

**Deferred.** Open-world consolidation, justified later as presentation economy rather than measurement;
finding verification, which for craft would recreate the unstable normative judgement; perspective
diversity as a deliberate treatment; marginal-discovery yield as a `P13` observable.

**Next.** The closed-world multi-sample substrate, with the discovery grader characterised as its first
run.

## 7M. Closed-world multi-sample evaluation substrate  *(implemented; grader characterised)*

Design authority: [`evaluation.md` §E20](proofbound/evaluation.md#e20-two-measurement-problems-wrongly-sequenced-as-one)
and [§E24](proofbound/evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement).

**Built.** A pre-registered experiment manifest (`_experiment.py`) declaring claim, measurand,
baseline, treatment, frozen variables, primary comparison, guardrails, falsifier, invalidating
conditions and adoption rule — every one refused if missing, all fixed before measurement. Slots are
preallocated from the manifest alone and addressed by a composite naming instance, arm and pressure,
so the repeated-measurement machinery from `§E51` applies unchanged and a sample taken for one
pressure or arm cannot satisfy another's slot. Arms interleave from an order generated before
execution. Thirty deterministic tests pin sample preservation, minority survival, missingness,
resume, non-splicing, arm separation, order independence of derived counts, and the isolation of the
legacy `trial_verdict` collapse.

**Measured.** The discovery grader — the question a closed-world run actually uses — characterised
over the six committed anchors, 15 gradings each. **Five of six unanimous, 5/90 = 5.6% pooled
non-modal, no parse failures**, against the verdict grader's 1/6 and 16.9%. Dispersion is zero on
sound architectures and 16.7% on ambiguous degraded reports, and the report V1 recorded as a missed
degradation is graded *detected* here: it identifies the planted problem and declines to call it a
breach. Evidence:
[§E52](proofbound/evidence/evaluation-runs.md#e52-the-discovery-grader-characterised-before-anything-relies-on-it).

**Gate: passed with a bound.** At ten samples per cell the grader contributes roughly 1.7 counts of
noise on ambiguous reports, so V3 must pre-declare a minimum effect of three counts or more and a
budget to match, and report per-cell dispersion rather than a pooled figure that hides it.

**Not built:** finding consolidation, verification, adaptive sampling, majority voting, confidence
fields, heterogeneous panels, model reputation, effective-sample-size estimation, capture–recapture,
a metamorphic framework, a mutation engine, production multi-review.

**Next — see [§7N](#7n-calibration-v3-criterion-design-check--case-disqualified-no-live-call).** The criterion
design check ran and disqualified the case rather than the substrate.

## 7N. Calibration V3 criterion design check  *(case disqualified; no live call)*

Design authority: [`system-craft.md` §59](proofbound/system-craft.md#59-the-probe-rewards-the-degradation-it-plants).

**Question.** What architectural consequence should V3 test, and is it entailed by the accepted intent
rather than by benchmark-author preference?

**Answer: no admissible consequence exists on this case.** Three candidates were derived and each
failed. The carried-forward wording constrains a responsibility no fixture has — nothing in any state
*decides* what to notify — and would have to overrule the intent's only placement-adjacent clause
rather than follow from it. The one genuinely entailed alternative, about provider response-code
interpretation reaching the module that owns the stable outcome vocabulary, fails its counterexample
audit: `notifications/status.py` maps generic HTTP semantics, and a shared HTTP outcome mapper is a
defensible design. The case's own rationale is a conjunction of four consequences and cannot be a
single pre-registered column.

**The probe rewards the degradation.** Under the frozen future contract the degraded state edits one
file and both sound states edit three and add one — in every trial ever run. Change locality is one of
the three lenses the reflector answers under, so the reports praising the degraded state's locality
were correct about the probe they were given. Evidence:
[§E53](proofbound/evidence/evaluation-runs.md#e53-why-calibration-v3-cannot-run-on-this-case).

**And the remaining pressure is at ceiling**: 57 of 60 untreated reports already name where provider
knowledge sits, and the two untreated degraded anchors were detected 25 times in 30 by the discovery
grader. A treatment cannot raise what the baseline already finds four times in five.

**Standing condition added.** A calibration probe must satisfy entailment, exercise and headroom, all
checkable before any model call
([§59.1](proofbound/system-craft.md#591-what-a-calibration-probe-has-to-satisfy)).

**Unchanged.** No measurement mechanics were touched: `_experiment.py`, slot allocation, grading,
distributions, the discovery-grader prompt, resume and configuration identity are all as `§7M` froze
them. No fixture was edited, no criterion adopted, no manifest written, no live call made.

**Next.** Repair the calibration case — a probe whose providers differ in rejection semantics, and an
accepted intent stating what must remain true rather than only what is configuration. Two fixture
changes, hence their own milestone, and the criterion experiment follows it rather than accompanying it.

## 7O. Calibration case repair — probe, intent and boundary consequence  *(designed; not encoded)*

Design: [`case-repair-design.md`](../../evals/craft/notification-provider-boundary/case-repair-design.md).
Methodology: [`system-craft.md` §59.1](proofbound/system-craft.md#591-what-a-calibration-probe-has-to-satisfy).

**Diagnosis.** The old probe varied only *representational* facts — a URL, a header key, payload key
names — and the degraded state had already co-located every representational fact in one function.
Co-location is cheap for adding another instance of a variation point that already has a shape, so the
degradation absorbed the change in one file while the sound states paid a boundary's price for nothing.
A boundary earns its keep on a variation point whose shape **differs**.

**Repair.** The decision expected to vary becomes *how a provider reports the outcome of a delivery
attempt*: the second provider answers `200` to every well-formed request and carries the result in the
body, which is ordinary industry behaviour and differs from the first in kind rather than in value. The
accepted intent gains one factual sentence — providers differ in how they report outcomes, and the
product's vocabulary is the same for all of them — naming the volatile decision without saying where
knowledge of it should live. The three states are unchanged.

**Why it discriminates.** In both sound states every changed location is provider-specific work,
boundary composition, or an uninterpreted pass-through. In the degraded state `status.outcome_for(code)`
cannot express a body-reported result, so it must either teach a provider-independent module about a
provider or restate the retry policy in the entry point — and there is no third route, because nothing
in it is specific to a provider. All three states are expected to touch roughly the same number of
locations, which is what removes the old confound: the difference is in **kind**, not count.

**A fourth gate.** `§59.1` now requires **discrimination** alongside entailment, exercise and headroom —
an answer-blind structural account, authored before any call, of why each location had to change.

**Headroom is not established and cannot be here.** It needs a measured baseline, so the sequence is
implement the fixture, run a **baseline-only** single-arm experiment, inspect discovery frequency, and
design a treatment only if room exists. The substrate already permits a single-arm run.

**Unchanged.** No measurement mechanics, no fixture code, no criterion, no treatment, no live call.

## 7Q. Repaired case fixture and baseline  *(encoded; pressure non-specific)*

Pre-registration: [`baseline-preregistration.md`](../../evals/craft/notification-provider-boundary/baseline-preregistration.md).
Evidence: [§E54](proofbound/evidence/evaluation-runs.md#e54-the-repaired-case-measures-and-the-pressure-statement-does-not-discriminate).

**Encoded and frozen before measurement.** Amended intent, `r0002` contract, hidden Beacon gate, and
a reference implementation of the change per state. Seventeen tests hold the case's central property:
with the change applied, every state passes the behaviour suite and the future gate identically, so
**no deterministic result separates sound from degraded**. The old locality confound is gone — three
files changed in every state — and the structural audit before any call confirmed that Beacon's
reporting convention stays inside a Beacon-specific file in both sound states and lands in
`notifications/status.py` in the degraded one.

**Baseline: both failure conditions fired.** `state-c` detected 10/10 — at ceiling, no headroom —
and the sound states detected 7/9 and 5/10, which is non-specificity severe enough that a treatment
could not have been read even with headroom.

**Cause: the pressure statement, not the fixture.** It offered three disjuncts, and the contract
forces two of them true everywhere — `app.notify` must gain a `provider` parameter, so the entry
point changes in every state, and both sound architectures keep each provider's retry loop in that
provider's module. Every sound-state detection cites the entry-point clause; the clause that actually
discriminates appears in 10 of 10 degraded reports and none of `state-b`'s detections.

**Not repaired here.** Re-grading the retained reports against a narrowed pressure would fit numbers
to reports already read. The narrowed pressure must earn its own frozen baseline.

**Next.** Re-pre-register the pressure against the reference implementations — which now exist and
did not when the wording was first written — and re-run the baseline before any treatment.

## 7P. Modularity and local reasoning calibration — design check  *(deferred research)*

**Sequenced after System Craft calibration validity is restored**, and not before. Testing a
context-economy hypothesis while the craft instrument's own validity is unsettled would move two things
at once.

**Hypothesis.** If a boundary genuinely hides a volatile design decision, work outside it should often
be solvable from its public contract without reading the implementation behind it — the empirical form
of `P13`'s second surface.

**Shape.** Same repository, task, model, harness and accepted intent. Control: the external module's
implementation is inspectable. Treatment: it is withheld and replaced by its contract plus the
externally relevant accepted consequences. Observables: correctness, deterministic test success,
semantic findings, context bytes, files opened, repository searches, cross-boundary reads, cost.

**Falsifiers.** Correctness materially drops; the agent repeatedly needs hidden internals; the contract
has to reproduce most of the implementation's semantics; the supposedly local task actually crosses the
boundary; the treatment saves context only by removing information that was needed.

**Two controls it must carry.** An **over-modularisation** arm — entangled, meaningfully modular, and
excessively fragmented architectures compared on the same task — because *more modules is not the
hypothesis and must be able to lose*. And a **minimum sufficient contract** ladder — signature only,
signature plus behavioural contract, plus externally relevant invariants, full implementation — since
the interesting quantity is the smallest context preserving correctness, not the smallest context.

**Not adopted, not named.** No `P14`, no module score, no cohesion or coupling threshold, no ideal
module size, no mandatory structure, and no `minimum_sufficient_contract` protocol term. Information
hiding and change confinement are used here as reasoning aids for building a valid case, never as
Proofbound policy.

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

Not in M2A, and not implicitly acquired by it (artifact kinds were subsequently examined for M2B and
rejected outright — see [§A3.8](proofbound/artifacts-and-provenance.md#a38-what-m2b-does-not-do)): freeze and freeze identity; artifact kinds and
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

**None blocks M2C-A.** Items 1, 2, 4, 10, 11 and 12 are decided. Item 3 is now urgent — it is the same
question as the ledger layout settled in the M2C design check, and should be recorded as a repository
convention before freeze work begins.

1. ~~**Purpose vocabulary granularity**~~ — **decided: keep the fine-grained vocabulary.** Five
   recorded names, two enforcement classes today. `purpose != capability != role`; collapsing names
   because their mechanics currently coincide would discard provenance and force retro-classification
   in M2B. RFC [§27.1](proofbound/execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained).
2. ~~**Artifact line-ending/identity protocol**~~ — **decided: canonical text hashing**
   (`proofbound-artifact-text-v1`), with `.gitattributes text eol=lf` as hygiene only. `-text` was
   evaluated and rejected. RFC [§27.2](proofbound/artifacts-and-provenance.md#272-decision-resolved--canonical-text-identity-and-why--text-was-rejected).
3. **Committed spec root and ledger layout** — `specs/<change-id>/` for graphs and freezes, with a
   **single project-wide ledger**, is the layout the M2C design check recommends and the only one that
   permits cross-change artifact reuse. Nothing in code forces it — the ledger path is a CLI argument and
   a freeze names no ledger — so this is a convention to adopt deliberately rather than a schema change.
   It should be settled before M2C-A, because freeze candidate construction reads one ledger.
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
12. ~~**Cross-ledger composition for freeze**~~ — **decided: one ledger provenance universe per freeze**,
    with cross-ledger composition explicitly unsupported in v1 and stated as such. Reversible: a freeze is
    self-contained after generation, so this is a candidate-construction concern, never a format change.
16. ~~**First evaluation milestone**~~ — **decided: Eval V1, semantic reflection reliability.** Scoped in
    §7D; the provider seam already exists, so the milestone is scenarios and grading rather than
    infrastructure.
14. ~~**What follows M2C**~~ — **decided: the evaluation/regression track, not durable implementation
    provenance.** The durable claim cannot be chosen truthfully before an authoritative implementation
    decomposition exists, and it has no consumer; meanwhile no test has ever exercised a real model. See
    §7C.
15. **Authoritative implementation decomposition** — the real prerequisite for any completion theorem
    and for durable implementation provenance. Not scheduled; not designed.
17. ~~**`evaluation.md` split pressure**~~ — **done.** Recording run outcomes in the protocol document
    pushed it to ~38.5 KB against the 40 KB cap. Split by authority class, the way the corpus already
    works: protocol stays in [`evaluation.md`](proofbound/evaluation.md); what individual runs established
    moved verbatim to [`evidence/evaluation-runs.md`](proofbound/evidence/evaluation-runs.md), which is
    read on demand and exempt from the cap. Section identifiers were preserved, so `E14`/`E15` still name
    the same content. The protocol document no longer grows by one section per evaluation run.
13. **Architecture document split pressure** — `artifacts-and-provenance.md` is now ~38.5 KB against the
    40 KB cap enforced by `tests/test_docs_architecture_refs.py`. The next substantive addition breaches
    it. That cap exists to force this decision rather than let a document drift out of selective-reading
    range; the natural split is a separate `freeze-and-binding.md` when M2C-A lands.
