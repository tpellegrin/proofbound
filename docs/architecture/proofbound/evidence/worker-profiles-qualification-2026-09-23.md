# Worker profiles and configuration qualification — 2026-09-23

Baseline `4f9ffc8d6de6394a7972945852c37803323b1a2a`, fetched without merging. `origin/main` equals
it, and `aff0c75` is its parent. Host: macOS arm64; interpreters 3.10.14 (canonical runs) and
3.14.5; pinned OpenCode 1.18.29, digest `2f24593f…d669`, present as an npm global install. **No
provider request was made. No model was installed, downloaded or qualified, and no paid
experiment ran.** The frozen, unrun CSV protocol-v2 was not touched.

## The working tree that was reported, and the one that was found

The brief reported uncommitted changes to `_launch_budget.py`, `_supervised_launch.py`,
`_workflow_boundary.py` and `pb_workflow.py`, and two new files, `_worker_profiles.py` and
`tests/test_worker_profiles.py`. The checkout was a **fresh clone** (reflog: one `clone` entry,
17:53:10 −03:00). The four tracked files were byte-identical to `HEAD`; nothing was staged,
unstaged or untracked. The two new files existed nowhere under the owner's home directory. A
sibling checkout, `~/Projects/personal/deepseek-and-destroy`, is an older clean clone of the same
remote at `b158e8a`. A snapshot of the four files' bytes and the full Git state was taken before
any edit. **No unfinished implementation was available to retain, repair or replace.** Every file
named in the brief was therefore written or modified from the committed baseline.

## Reproduced before repair

| # | What | Observed |
|---|---|---|
| 1 | `_compare.compare`: scenarios match, only `model` differs, neither run records `harness_version` | `{"controlled": true, "differing_fields": ["model"], "unverified_fields": ["harness_version"]}`; the render said *readable as a controlled model comparison* and *equality is assumed*. The ten `ComparisonTest` cases passed |
| 2 | Implicit worker pricing | `LaunchLedger.admit`, `finish` and the evidence exporter called `spend()` with no model, so any run was priced on the DeepSeek table. Hand-computed: 1,000,000 uncached input tokens off-peak price to $0.22 |
| 3 | Pinned OpenCode against a scripted endpoint that omits `usage` | every finished call recorded `input 0`, `output 0`; accounting reported the run complete, with usage reconciled at zero tokens |
| 4 | The same, with every stream dropped mid-response | **4,649 retries** within the 900 s deadline, each recorded as a finished zero-token call; the launching `continue` returned after 921.7 s; the gate refused: `status='timeout'` |
| 5 | The same, with malformed tool-call arguments | no write executed, the artifact unchanged, the gate classified the attempt `reportless-no-change` |

Rows 3 to 5 were driven through `pb_workflow.py start` → `authorize-resources` → `continue`, inside
the real `sandbox-exec` boundary with loopback-only networking.

## Capability records

**Selectable worker profiles** — [worker-profiles.md](../worker-profiles.md).
*Problem:* the DeepSeek route was hard-coded; a local model could not be configured honestly.
*Invariants:* atomic admission, frozen executor identity, credential minimisation, host-owned
teardown, unknown-usage handling, historical interpretation (`P6`). *Baseline:* `4f9ffc8`.
*Falsifiers exercised:* secret-bearing or non-loopback profiles refused with every problem named;
an edited profile file refused on repeat `start` naming `limits.output`; tampered settings refused;
`--variant` absent and ambient `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`/`OPENCODE_*` absent from the
executor's environment; a moved executor config refused before launch with no slot consumed; a
legacy run-config still resumes; a shared server survives teardown while the attempt's own
process is stopped. *Observed:* with the pinned executor and a scripted endpoint, the tool loop
completed inside the boundary: three requests, two continuations carrying tool results, no
`Authorization` header, `max_tokens` equal to the profile's output limit, `192.0.2.1` refused with
`EPERM`, no credential staged. *Limitations:* no local model has run; the endpoint was a
stand-in; server-side cancellation is unobservable. *Adoption scope:* configurable and
offline-tested; **unqualified** for any real local model.

**Unbilled accounting and zero-token calls.** *Problem:* rows 2 and 3. *Invariant:* unknown is
never zero. *Falsifiers:* a local run's admission, finish and export never produce a DeepSeek
price; a ledger frozen under one basis refuses another; zero-token calls leave a priced figure
incomplete and an unbilled allowance unsettled; a missing terminal record blocks regardless of
billing. *Observed:* as declared. *Limitation:* a real provider that legitimately reports zero
input would now read as unknown; none is known. *Scope:* adopted for both bases, because it only
ever widens *unknown*.

**Comparison eligibility** — [E27.2](../evaluation-qualification.md#e272-unknown-is-neither-agreement-nor-difference),
[E17.3](../evaluation-comparison.md#e173-what-must-be-equal-before-a-difference-means-anything).
*Problem:* row 1. *Falsifier:* a regression that fails on `4f9ffc8` (`True is not false`) and
passes after the repair; one-sided absence is unverified rather than a difference. Two existing
tests changed deliberately. The model-only fixture now records the treatment field every summary
written since `P12` carries. The historical-treatment test now asserts *unverified, not
controlled* instead of *differs*, keeping its purpose. *Scope:* derived eligibility only; no
historical record or outcome was relabelled.

**Configuration qualification** — [E26](../evaluation-qualification.md#e26-qualifying-a-configuration-before-selecting-it).
*Problem:* no way to find out what a configuration can do here before selecting it.
*Falsifiers:* for each of seventeen stand-in variants, a grade declared in advance. Among them are
malformed tool calls, dropped streams, omitted usage, an invented finding on the sound control, a
right finding with a wrong witness, a missed contradiction, a defective implementation accepted,
a defect repaired, a never-earned prerequisite, and a deleted-but-recoverable derived record.
*Observed:* a full replay of a local-profile plan graded 17 of 17 as declared; the tool loop ran
through the real executor and boundary, everything else through the stand-in executor. A DeepSeek
plan ran 13 and recorded the four tool-loop cells as `not-run`, because a hosted provider cannot be
replayed without its credential. `inspect` re-derived every grade after relocation with no
mismatch. It reported a replaced artifact and a deleted report as mismatches and repaired
neither. The comparison of the two replays named a worker-profile question, listed the unpaired
cells, and flagged tokens as not comparable. *Limitations:* the dispatch case's reference corpus
is readable inside the worker boundary, so withholding is not established there. `authority-recovery`
has no live half yet. Four cases are development fixtures, not a held-out set. *Scope:*
mechanically qualified; live-observed for nothing; comparatively beneficial for nothing.

## Tests

The new modules are `tests.test_worker_profiles` (28) and `tests.test_qualification` (20). There is
one new comparison regression, and two deliberately changed cases, in `tests.test_evals_harness`.
The canonical suite ran once, serially, at the final production code, with
`python3 -m unittest discover -s tests -t .` on Python 3.10.14, macOS arm64: **1,377 tests, OK,
none skipped**, 17 min 49 s. The real-executor and boundary tests ran, because the pinned build and
`sandbox-exec` were available. On a host without them they skip, and on Linux CI the macOS
boundary tests skip, as the existing ones do.

After that run, only tests and documents changed: one test now waits for the process it kills,
and one test file gained a local helper. The new modules and the affected workflow and comparison
modules then passed on Python 3.14.5 (163 tests). A full local-profile replay on the final code
graded 17 of 17 variants as declared, and `inspect` re-derived all 17 with no mismatch.

## What this does not establish

That any local model can do the work, that a local worker is cheaper or better than DeepSeek,
that a qualification replay says anything about a model, or that finite tests exclude
regressions. They cover the paths named above and nothing wider.
