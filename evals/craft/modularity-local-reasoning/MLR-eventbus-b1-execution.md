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

`--keep` is checked by `b1-preflight`, which is why it is now an argument there too. Retaining a
slot's evidence happens after its trajectory is bought, and the copy used to sit in an unguarded
`finally` that runs on the success path as well: an unwritable path raised out of the attempt after
the outcome, the context ledger and the cost had all been computed, so the money was spent, the
trajectory was lost and the slot was frozen in §11 C by a typo. The copy now reports its failure as
`evidence_error` instead of raising, and a path that cannot be written blocks the launch for free.

**Nothing else may run on this host during a series.** Cross-slot isolation is checked before every
slot against the host's temp directories, and it cannot tell one process's scratch directory from a
previous slot's residue. The test suite materialises arms in `TMPDIR`, so a suite running alongside a
series will be read as an earlier slot leaving state behind and will stop it under §11 G — observed
while preparing this milestone, where two concurrent suite runs failed 25 of each other's tests for
exactly that reason. Run the tests before launching, not during.

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

### §11 A, resolved: the halt on a launcher refusal is the frozen rule, not a departure from it

**Previously recorded here as an undecided deviation.** Two revisions of this document have described
the runner's handling of a launcher refusal as a departure from §11 A: the first called it "accepted
deliberately", the second withdrew that and recorded it as "a deviation, not a policy anyone has
ratified", asserting that "**§11 A would permit up to three retries**". The concern is kept on the
record because it was raised twice and because the reasoning that resolves it is the reasoning the
code was already using. The assertion was wrong, and this is what it got wrong.

The controlling clauses are three, and two of them are conditioned on a fact:

> §9 · "A semantic trajectory that has begun is immutable. An infrastructure failure **before**
> semantic execution begins is not a semantic sample."
>
> §10 · "Infrastructure attempts are bounded at **three per slot** and **may** retry the same slot;
> every attempt is recorded."
>
> §11 A · "an infrastructure attempt fails **before** semantic execution | retry the slot, bounded at
> three; both records retained"
>
> §11 C · "a semantic trajectory **begins** and is interrupted | accounted and preserved, contributes
> no measurement, **not** re-rolled; its pair is incomplete"

**On modality: §11 A permits retries, it does not require them.** §10 carries the operative verb —
*may* retry — and "bounded at three" in both places is a ceiling rather than a quota. §11 B makes
that explicit by defining what happens when all three are used, and §11 J establishes that a series
ending short and reporting how many pairs completed is a defined outcome rather than a failure of
procedure. How many of the three attempts to use is therefore an operational decision inside the
ceiling. What the freeze fixes is the maximum, and that every attempt is recorded.

**On the trigger: the condition is a fact about the world, and the controller does not get to decide
it.** §11 A attaches only to an attempt that failed *before* semantic execution; §11 C attaches only
to a trajectory that *began*. So three cases have to be told apart, and only two of them are in the
table:

| evidence | frozen disposition |
|---|---|
| establishes that no semantic execution began | §11 A · retry permitted, bounded at three, both records retained |
| establishes that a trajectory began | §11 C · accounted, preserved, no measurement, **never** re-rolled |
| establishes neither | §11 A's permission is **unavailable**, because its condition is unproven |

The third row is not a gap to be filled by judgement. §11 A grants nothing until its condition is
established, and the protections that are exposed if it is granted wrongly — §9's immutable
trajectory, §11 C's "not re-rolled" — are the ones the design exists to hold. The costs are also
asymmetric: withholding a retry that was in fact permitted ends a series short, which §11 J and §17 F
both already accommodate, whereas granting one that was not buys a second trajectory for a slot §11 C
says is spent and corrupts the paired unit §9 declares immutable. Under indeterminacy, not retrying
is the frozen rule and not merely the cautious choice.

**A launcher refusal is the third row.** The evidence the runner holds is `launch_returncode != 0` —
the exit status of the process that would have started the worker. That does not establish that the
worker never started: a launcher can start the worker, the worker can call the provider, and the
launcher can still exit non-zero afterwards. Nor does it establish the opposite. The only thing that
points at non-commencement is `_mlr_boundary`'s substring match over the launcher's own log text
(`"not found"`, `"auth"`, `"credential"`, `"rate"`), and a substring match over prose is not evidence
about what a provider did or did not charge for. §11 A was therefore never engaged by a launcher
refusal, so halting is conformant behaviour and there is nothing here for anyone to ratify.

Two things this does **not** say. It does not say the guard is a claim about actual charges: it is a
spending and retry guard, and where the launcher's classification survives at all it survives as the
reported hint `launcher_classified_as_pre_semantic`, never as an input to the retry decision —
`execution_stage` decides on `trajectory_began` and `launch_returncode` alone. And it does not say
§11 A is unreachable. Everything that fails before the launcher is entered — view construction,
staging, the view-scoped hermeticity preflight — carries `trajectory_began: False`, is classified
`before-launch`, and **is** retried, bounded at three. §11 A's permission is exercised wherever its
condition is actually established; it is withheld only where the record cannot establish it.

**Stopping the series, rather than only the slot — the runner's reading, and labelled as one.**
§11 C's row does not say "series stops", unlike §11 B and §11 D–I, and §11's closing paragraph
("incomplete pairs are reported, never replaced") reads as compatible with carrying on through the
remaining slots. The runner stops. Its reason is that §17 evaluates families in order and **F** is
"any instrument or execution validity defect under §11", which an interrupted trajectory looks like,
so continuing would spend more of a $0.50 ceiling on slots that could not change the family — but
that inference is the runner's, not the document's, because §11 files C under *missingness* rather
than among the conditions it says stop the series. Raised in review, and recorded here as an open
reading rather than a settled one.

**This does not carry the §11 A resolution above, and nothing here is load-bearing for it.** That
argument is about whether a slot may be *offered again*, and it turns only on §11 A's condition being
unproven by a launcher return code. Whether the series then continues to slot 2 is a separate
question, it is conservative in the opposite direction — less evidence collected, never more — and it
is the one an operator can revisit without buying anything back.

### A record that cannot say a slot was entered is not evidence that it was not

Found in review of this milestone, and repaired. `write_series` ran when an attempt *returned*, so a
process killed inside one — a SIGKILL, a host timeout, a pulled plug — appended nothing at all and
the slot left no trace. The claim made below in §5, that "the live rule and the resume rule are the
same rule", did not hold in that window: a resume found no prior attempt on the slot, offered it
again, and bought a second trajectory for a slot §11 C may already have spent. The stale view the
kill left behind blocked that resume only until the operator ran `--clear-stale-views`, which §5
itself tells them to run.

Each attempt is now checkpointed **before** it is made, as stage `in-flight`, and that row is
replaced by the attempt's outcome a moment later. What survives is therefore exactly the case where
nothing came back. It carries `trajectory_began: True`, which is the third row of the table above and
not a guess: before an outcome arrives, where the attempt stopped is unknown, so §11 A's permission
is unavailable and the slot is not offered again. Its spend is unpriced for the same reason —
unknown, not zero.

That repair created a second one. A row surviving because the process died and a row surviving
because the attempt *raised* are indistinguishable, and three statements in `run_bounded_attempt`
sat outside the block whose whole contract is "reported, never raised": resolving the fixture,
hashing the executor, and making the extraction directory. Each of them provably precedes the
launcher — §11 A's case, retryable — but raised from there they escaped the series loop and left the
checkpoint as the only row, freezing the slot in §11 C for a failure that never reached the executor.
They are inside the block now, so a pre-launch failure is reported as `before-launch`, replaces the
checkpoint, and is retried. A signal that cannot be caught still leaves the row, which is the case
the row is for.

### The spend account is in the record, not only in the process that printed it

`spend` separates `derived` from `unpriced` precisely so a figure is never read without its
completeness limit, and the runner returned both. It persisted neither: the committed artifact
carried the measurements and left the account to whoever thought to recompute it. Every checkpoint
now writes the account into the record — `derived`, `unpriced`, `complete`, and the claim in words —
and `analyse --paired` reports it too, recomputed from the measurements so a record written before
this also gets one.

Reporting it on *older* records exposed the same defect one layer up, and review caught it. Every
branch of `execution_stage` turns on `trajectory_began`, and a record written before that key
existed has no answer rather than the answer "no" — so its attempts were classified `before-launch`,
dropped from `unpriced`, and the analysis announced that a 33-attempt series had spent $0.00 and
that the figure was whole. Absence of the fact is not the fact: such a measurement is now
`unclassified` and unpriced, and the four reasons an attempt can be unpriced are worded apart
instead of sharing one sentence that said all of them "reached the executor". Records that do carry
the vocabulary are untouched — q1 still reproduces its committed `spent_derived` of `0.207932`,
complete.

A second review round found that fix carrying the defect itself. `unclassified` short-circuited on
`"stage" not in record`, and the loop writes a stage into every measurement, so the row it had just
classified re-read from disk as `before-launch` and the unknown became a zero one layer further
down. The stage the loop wrote is now read back rather than re-derived, the retry gate reads the
classification instead of one raw key, and the `unclassified` wording says what is known — the two
keys are absent — rather than inferring *why*, which on a grader-repeat record was simply wrong.

## 5. Continuation

Re-running `b1` with the same `--out` resumes. `_repeat` refuses to extend a record written under a
different frozen configuration, so a resume across a changed fixture, model, effort or N is rejected
rather than spliced. Completed slots are skipped. A slot whose earlier attempt reached the launcher
halts the resume exactly as it halted the live loop — the live rule and the resume rule are the same
rule, so a restart cannot buy a trajectory the loop refused to buy. That now holds for a killed
process too, because the attempt is checkpointed before it is made rather than only after it
returns; see §4.

If a process was killed, `python3 evals/pb_mlr.py b1-preflight --clear-stale-views` removes views the
context manager's cleanup never ran on. Clearing them does not clear the slot: the `in-flight` row
the kill left in the record still halts the resume, which is the point of writing it before the
attempt rather than after. Cleanup covers how a block ends; it does not cover a killed
process, and the next slot's preflight is what establishes validity.

## 6. Known limitations

- **Five integration tests were skipping silently.** `tests/test_mlr_boundary.py` gated its
  real-executor cases on an absolute path into one machine's nvm install — the executor running in
  the view, building its state only inside the constructed home, seeing no prior session, no host
  configuration and no credentials, and creating its session store inside the slot. On every other
  host they skipped, which is what happened here until this milestone. The executor is now located
  on this host — `PROOFBOUND_EXECUTOR`, then the isolated frozen build, then `PATH`, with a content
  match preferred over position — and on the authoring host all five ran against the frozen
  `1.18.29`. Where no candidate matches, they still run against whatever `opencode` the host has and
  `EXECUTOR_IS_FROZEN` records that it was not the frozen build; the one test whose subject *is* the
  frozen bytes is gated on that flag rather than on mere presence. That test asks the actual staging
  mechanism whether the subject can write the staged executable or mutate the inode it shares with
  the control plane's copy. It cannot: the tools directory is a sibling of the writable root, so the
  policy's one `file-write*` grant does not reach it. It establishes the deny on a throwaway link
  first, because every write it then attempts is aimed at the inode of the binary b1 is pinned to.
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
