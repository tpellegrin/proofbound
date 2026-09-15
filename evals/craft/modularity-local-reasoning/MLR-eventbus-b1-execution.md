# `mlr-deepseek-v4-flash-high-paired-eventbus-b1` — how it is executed

**2026-09-15.** A separate record, written after the freeze. Per
[`MLR-eventbus-b1-preregistration.md`](MLR-eventbus-b1-preregistration.md) §21 this cannot alter that
plan and does not try to: it says which committed code runs it, what this host must provide, and what
the runner will and will not do on its own. The experiment's design is unchanged — same fixture,
task, contract, oracle, treatment, model configuration, attribution, profile, N, order, result
families, budget and retry semantics.

## 1. Why this record exists

The preregistration was frozen at `b158e8a` naming a procedure, and the repository could not execute
it. `_mlr_run.grade` resolved the hidden oracle, the public contract and the vendored package from
fixture A's names while everything below it had already been parameterised, so grading an `eventbus`
workspace raised `FileNotFoundError` inside a blanket `except` — every slot would have returned an
infrastructure failure and the series would have stopped under §11 B without a single trajectory
being interpretable. Separately, `pb_mlr`'s series loop drove the *unbounded* attempt path and
retried any attempt that did not come back valid, which §11 C forbids.

**The orchestration that produced q1 is not in this repository and was not recovered.** What is
committed now is a new implementation of the procedure the preregistration describes, written from
the preregistration. It is not claimed to be equivalent to whatever ran q1.

## 2. The two commands

```bash
OC=$HOME/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode

# Dry run. Resolves and validates the exact configuration b1 would execute.
# Contacts no provider, consumes no slot, writes no experimental record. Exit 0 iff launchable.
/usr/bin/python3 evals/pb_mlr.py b1-preflight --executor "$OC" [--clear-stale-views] [--out report.json]

# Execution. Spends money.
/usr/bin/python3 evals/pb_mlr.py b1 \
  --out evals/results/craft-mlr-deepseek-v4-flash-high-paired-eventbus-b1.json \
  --executor "$OC" \
  --credential .local/share/opencode/auth.json=$HOME/.local/share/opencode/auth.json \
  --keep /path/outside/the/repository
```

`/usr/bin/python3` is CPython 3.9.6 on this host, which is what §5 records for the frozen host and
what reproduces the frozen boundary identity. Any ≥3.10 interpreter also runs the runner; it produces
a different boundary digest, which §5 permits as a host fact.

`--credential NAME=PATH` copies `PATH` to `NAME` inside the view's constructed home, which is the
only `HOME` anything inside the boundary sees; it is destroyed with the view. The name above is the
path OpenCode reads its provider auth from, and is the one the boundary tests already stage.

`b1` refuses to start unless `b1-preflight` is launchable, so nothing is spent discovering something
a digest comparison already knew. There is no unbounded fallback: if the semantic boundary cannot be
constructed, the series does not run.

`--keep` retains each slot's extracted evidence. Point it outside the repository — `evals/results/`
commits only the small summary record, and retained sessions are raw local material.

## 3. What this host must provide

| requirement | why | state on the authoring host |
|---|---|---|
| macOS with `/usr/bin/sandbox-exec` | the semantic boundary is a macOS sandbox profile; b1 must run inside it | present |
| `opencode` whose SHA-256 is the frozen one | §5 freezes the executor by content, and the boundary binds its tools by digest | **met** — acquired in isolation, see below |
| a provider credential file for `deepseek` | staged into the constructed home, destroyed with the view | supplied at run time |
| the launching interpreter | compiles the runtime both arms import; §5 records it per slot as a host fact | `/usr/bin/python3` is CPython 3.9.6 here, which is what the frozen host used |

The executor is **not** waived and b1 is **not** amended to accept a different build: §5 freezes it in
the stack table, not among the host-derived identities, and §11 H stops the series on executor drift.
Eligibility is decided on content, never on a reported version string, because two builds calling
themselves the same version are two different boundaries.

### The executor, and how it was obtained

The host's own installation is Homebrew `opencode 1.18.30_1`, `c9621a0cac01d7fc…` — not the frozen
build. It is left exactly where it is; the frozen build is selected explicitly with `--executor`.

**The full 64-character digest survives in committed evidence**, not merely the 16-character prefix
§5 prints: six retained result records carry
`2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669` under `executor.sha256`. So the
acquisition could be checked against the whole digest rather than against a prefix.

| | |
|---|---|
| source | GitHub release `v1.18.29`, repository `anomalyco/opencode` (the `sst/opencode` path redirects there) |
| asset | `opencode-darwin-arm64.zip`, 46,205,298 bytes, published 2026-09-04 |
| archive sha256 | `fe764f7f360c584a83e18dd5f23fb1a6b2725f5ee8854b0252fe558f7798e946` |
| **extracted executable sha256** | **`2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669`** — exact match to the historical digest |
| binary | Mach-O 64-bit arm64, 144,107,234 bytes, reports `1.18.29` |
| held at | `~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode`, outside the repository |

The digest verified is the **extracted executable's**, never the archive's or a release label's.

**A correction.** An earlier assessment inferred the frozen binary was a Homebrew bottle, because the
host's current one is. No committed record names any package manager, path or distribution channel —
that inference had no evidence behind it, and the digest match now shows it was wrong: the frozen
executor is the upstream release build.

### The boundary reproduces under the frozen host's interpreter

Launched with `/usr/bin/python3` (CPython 3.9.6, what §5 records for the frozen host), the semantic
boundary identity comes out as **`b88bd43109184459`** — the value the preregistration recorded.
Launched with Homebrew's CPython 3.14.7 it is `ea507fcde13b58d4`, because the boundary exposes the
launching interpreter's install path. Both are permitted; the first is closer to the frozen stack and
is what the commands below use.

The hermeticity rule digest is `e86a9147867ceb7f` against the frozen host's `23a6e8001a46b70f` under
either interpreter. That rule's identity includes its absolute scan roots and this is a fresh clone
at a different path, so the difference is positional. What the rule *checks* — five categories,
eventbus's own source by digest and fingerprint, the hidden gate, the reference solution, prior
sessions, result records, nothing declared exposed — is pinned directly by
`tests/test_mlr_b1_execution_path.py::SubstantiveFrozenPropertyTest`, because a digest cannot say
*why* it moved and "reported, never compared" must not be a place for a substantive change to hide.

### Host-derived identities are reported, never compared

§5 records the interpreter, the semantic boundary digest and the hermeticity rule digest per slot as
execution facts. `b1-preflight` prints this host's values beside the frozen host's and does not
compare them — a difference there is a host difference, not drift. On the authoring host the
fixture-B hermeticity rule resolves to `e86a9147867ceb7f` rather than the preregistration's
`23a6e8001a46b70f`, because that rule's identity includes its absolute scan roots and this is a fresh
clone at a different path. Whether to run under CPython 3.9.6, which the frozen host used and which
is available here, is a decision for whoever executes; the preregistration permits either.

## 4. What the runner does on its own, and what it refuses to

Ordered slots, bounded attempts, checkpoint after every attempt, and a stop rather than a guess.

| situation | behaviour | source |
|---|---|---|
| twelve slots in the frozen order | `pb_mlr.slots(["full","contract"], 6)`, three pairs leading with each arm | §9 |
| an attempt fails **before** the launcher is entered | retried, bounded at three; every attempt retained | §11 A |
| three attempts on one slot all fail before launch | series **stops** | §11 B |
| an attempt **entered** the launcher and did not come back valid | accounted, preserved, series **stops**; never automatically re-rolled | §11 C |
| a completed slot | immutable; never re-run, on resume or otherwise | §10 |
| extraction, attribution, contradiction, leak, drift or grading defects | series **stops**, naming the §11 condition | §11 D–I |
| the ceiling would be exceeded before a slot | that slot is not launched; the series ends short | §11 J, §19 |

Each attempt records how far it got: `not-offered` (an environment refusal that never reached the
executor, and which does not spend one of the slot's three), `before-launch`, `launcher-refused`, or
`worker-executed`. A stop is a property of the evidence rather than of the process that noticed it,
so resuming re-applies §11 D–I to every attempt already on disk: a series stopped for a leak stays
stopped, and a restart cannot turn it into a record that reads as clean and complete.

### An undecided deviation from §11 A, disclosed rather than accepted

When the launcher is entered and then refuses — an absent executable, an expired credential, a
provider rate limit — the failure very probably preceded semantic execution, and **§11 A would
permit up to three retries**. This runner halts instead, and once halted `_unfinished_trajectory`
refuses every later resume of that slot.

That is stricter than the frozen rules, and it is a **deviation, not a policy anyone has ratified**.
An earlier revision of this document called it "accepted deliberately"; nothing had accepted it but
the author, and the claim is withdrawn here. What can be said for it: the launcher's classification
is a substring match over its own log text rather than evidence, so treating it as permission could
buy a second trajectory for a slot §11 C says is spent — and that is the one error the design most
needs to avoid. What must be said against it: an expired token on slot 1 stops a twelve-slot series
and leaves a record that cannot be resumed without a person editing it.

The direction matters. The deviation can only **stop a series early**; it can never add a sample,
re-roll one, or change a measurement. So a series it halts is an incomplete experiment honestly
reported, not a corrupted one. The hint is recorded (`launcher_classified_as_pre_semantic`) so a
person can see immediately which side of the boundary the failure fell on. **If this fires during
b1, the run stops and is reported as stopped** — it is not to be worked around, and whether §11 A
should have been followed instead is a decision for a separate review, not for the runner and not
for whoever is mid-series.

The retry decision turns on one recorded fact — `trajectory_began`, set the instant the launcher is
entered and never cleared. Everything below that call is the executor and its provider, so no later
failure (a lost extraction, a grading crash, a killed process) is read as evidence that no model call
happened, and none of them authorises a second trajectory. **A grading failure is never assumed to
have consumed no tokens**: usage is recorded from the session whenever one exists, and spend counts
failed and interrupted attempts as well as successful ones.

**Unknown spend is reported as unknown, not as zero.** Cost is derived from the extracted session, so
an attempt that reached the executor and failed before extraction carries none. Those attempts are
counted and named in `spend.unpriced`, `spend.complete` says whether the derived figure is the whole
of it, and the ceiling gate refuses to launch a further slot on a spend it cannot establish rather
than treating the gap as nothing. An attempt that never reached the executor — a ceiling refusal, a
residue refusal, a failure before the launcher — genuinely cost nothing and is not counted as
unpriced.

The runner names the §11 condition that stopped a series and records the evidence. **It does not
assign a result family.** A family is a reading of an experiment; that is a person's to write.

## 5. Continuation

Re-running `b1` with the same `--out` resumes. `_repeat` refuses to extend a record written under a
different frozen configuration, so a resume across a changed fixture, model, effort or N is rejected
rather than spliced. Completed slots are skipped. A slot whose earlier attempt reached the launcher
halts the resume exactly as it halted the live loop — the live rule and the resume rule are the same
rule, so a restart cannot buy a trajectory the loop refused to buy.

If a process was killed, `python3 evals/pb_mlr.py b1-preflight --clear-stale-views` removes views the
context manager's cleanup never ran on. Cleanup covers how a block ends; it does not cover a killed
process, and the next slot's preflight is what establishes validity.

## 6. Known limitations

- **Deterministic tests are not a field qualification.** `tests/test_mlr_b1_execution_path.py`
  exercises the orchestration with controlled attempts and the grading path with the fixture's own
  known-correct and known-wrong realizations. Nothing there establishes that the instrument measures
  what it claims; §6 of the preregistration is the argument for why no live fixture qualification is
  bought, and it is unchanged.
- **The bounded path runs on macOS only.** Linux CI exercises every rule in the procedure — ordering,
  retry bounds, budget, continuation, immutability, stop conditions, executor eligibility — through
  controlled inputs, and skips nothing; what it cannot do is construct the view.
- **The record's measurement keys are `item`/`repeat`/`slot`/`arm`**, which is `_repeat`'s shape and
  what `pb_mlr.paired_analysis` reads. q1's record used `arm`/`pair`/`slot`. §18's cross-fixture
  comparison is performed by a person and compares values, not key names, but a reader should expect
  the difference.
- **`execution_commit` says which tree produced the attempts.** It is not evidence of when a semantic
  call was made, and a matching digest elsewhere does not establish that either.

## 7. Analysis afterwards

```bash
python3 evals/pb_mlr.py analyse --record <the record> --paired

# Diagnosis only, never a result: re-attribute retained sessions under the attribution in force.
python3 evals/pb_mlr.py retrospect --record <the record> --evidence-root <the --keep directory>
```

Correctness resolves first and gates the representation comparison; source and runtime-derived
representation stay separate columns and are never summed. The result family (§17) and the
cross-fixture comparison (§18, performed **only after** the within-fixture-B result is recorded) are
written by hand into a run document, as q1's was.
