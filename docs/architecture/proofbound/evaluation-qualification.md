# Evaluation — configuration qualification and what a comparison can answer

> **Design track.** How an operator finds out what a worker configuration can do through
> Proofbound's own path before selecting it (`E26`), and which question a comparison of two such
> records can support (`E27`). Continues the E-sequence of [evaluation.md](evaluation.md) and
> [evaluation-comparison.md](evaluation-comparison.md), whose `E17`, `E22` and `E24` it applies
> rather than restates. Implementation: `evals/_qualify.py`, `evals/pb_qualify.py`,
> `evals/_compare.py`.
>
> Entry point: [README.md](README.md).

## E26. Qualifying a configuration before selecting it

### E26.1 The question, and what it is not

*Can I configure this model or agent, find out what it can actually do here, and compare the
evidence before choosing it?* Qualification answers that with evidence for a person. It is not a
ranking, a routing service or a promotion mechanism, and it grants nothing. No spending authority,
no engineering authority and no acceptance follow from it. A qualified configuration passes every
ordinary admission and decision rule, exactly as an unqualified one would.

### E26.2 Four cases, reused rather than invented

The first suite is small on purpose. It reuses the authority slice's requirements documents,
enumerating oracle and artifact checker, whose discrimination was already validated.

| Case | Dimension | Graded by |
|---|---|---|
| `tool-loop` | tool request → execution → tool-result continuation → retained artifact | session rows, the artifact's bytes, the gate |
| `requirements-challenge` | a reviewer names requirements that cannot hold together **and** gives a witness that proves it; the coherent document is the sound control | exhaustive enumeration over the declared domain |
| `dispatch-implementation` | the delivered code satisfies the contract, first attempt and after the bounded repair; implementation findings reproduce on the delivered bytes | the slice's checker, re-run on retained bytes |
| `authority-recovery` | a coordinator continues a valid run, stops at a never-earned prerequisite, and recovers — does not refuse — a deleted derived record that retained evidence legitimately recreates | receipts and launch facts |

A case's **identity is a digest of its content**: definition, goal templates and fixture bytes.
Tasks are matched by identity, never by name, and one changed fixture byte is a different task.
The grading modules' bytes are part of the suite digest, because a different checker is a
different instrument. These are development fixtures and regression anchors, not a held-out
evaluation set, and must not become one by tuning against them.

### E26.3 One path, two drivers

Every trial is a supervised run: `pb_workflow.py start --worker-profile …`, launched through the
production admission, boundary, ledger and teardown, graded from what the run retained. There is
no evaluation-only model client.

- **Live.** A live plan is either a **proposal** — frozen, retained, and refused by every command
  that would execute it — or **authorized**. `authorize` turns a proposal into a plan with the
  owner's own statement and changes nothing else; no command writes an authorization on anyone's
  behalf. `prepare-live` runs readiness first, and prepares nothing if it fails. It then starts
  and authorizes one run per planned cell through the ordinary authorization command, checks that
  each run froze the plan's interpreter, executor bytes and worker settings, and launches
  nothing. A real coordinator drives each run to the case's stopping point; `grade` retains and
  grades. A run nobody drove is `not-run`, never a failure.
- **Replay.** A scripted coordinator drives the same front door, and a stand-in does the work.
  The stand-in is a scripted `opencode` for most cases. For a local profile's tool loop it is the
  **real pinned executor** inside the real boundary, pointed at a scripted loopback endpoint. Replay
  exercises malformed tool arguments, dropped streams and omitted usage as well as well-formed
  traffic. Every replay record names its transports and says it qualified no model.

Replay shows that the path and the graders behave as declared. Each stand-in variant declares, in
advance, the grade it must receive. Defective output, invented findings, unsubstantiated witnesses,
false acceptance and missing evidence must all fail to count as the dimension met. A replay whose
graders reproduced every declaration is evidence about the **instrument**, never about a model
(`E16.7`).

### E26.4 Frozen before it runs

A plan freezes, and its digest covers: the suite digest; the resolved worker settings; the
executor's bytes; the control plane's `scripts/` bytes; the interpreter; the harness commit, as
provenance; the planned coordinator; the ordered trial list; per-trial allocations; the deadline,
repair policy and containment; the owner's authorization, or its absence; and the evidence each
trial must retain. The suite digest covers the graders, the qualification CLI that prepares,
retains and grades, the replay stand-ins and the replay corpus, because each shapes the evidence.

Each trial's launch ceiling is enumerated from its case's stages, with one pre-executor allowance.
Its derived-spend limit is that ceiling times a per-launch allowance, and the campaign's totals
are their sum. Allowances never renew across trials, resumes or coordinator contexts.

**Execution** refuses a moved plan, a changed suite, control plane or profile source, another
interpreter minor version, or executor bytes other than the plan's, naming what changed.
**Grading** refuses a changed suite, control plane or interpreter. The checker runs delivered code
under the interpreter, so it names the harness commit to grade from and touches no run.
**Inspection** enforces nothing: an old result stays readable, and a grade that no longer
recomputes under changed graders is reported as `instrument-changed`, not as tampering. The repair
for a flawed plan is a new plan, never an amended one (`E24.1`).

### E26.5 Grading is deterministic, separate, and re-derivable

- **A finding and its witness are graded apart.** A finding is correct when what it names is
  really broken. Its witness is correct when it reproduces the breakage on the retained bytes. A
  right finding with a wrong exhibit is reported as exactly that. The sound controls turn any
  claimed defect into a false finding.
- **First attempt and bounded repair are separate outcomes.** The production path keeps no
  pre-repair bytes, so a live first-attempt verdict after a repair is `unavailable`. Only a replay
  driver can snapshot it.
- **False acceptance and false refusal are counted.** So are coordinator decisions and repairs.
- **A continuation is causal, or it is not established.** A tool counts as continued when its
  model call's step-finish reason is `tool-calls` and a later call in the same session followed.
  That is the executor's own sequence: one assistant message per call, identifiers ascending
  within the process. Creation order and tool end times must agree with it. Missing identifiers or
  reasons, duplicate parts, an unidentified session or contradictory order make the evidence
  `insufficient-evidence`, never a pass. Counting finished rows passed a trial in which nothing
  followed the tool.
- **A review is graded against the bytes it saw.** Each reviewer's scope baseline records the
  sha256 of what it reviewed. Its findings are graded against retained bytes with that digest, or
  reported `unavailable`. After a repair, the second review is not the first review's evidence.
- **Completed means concluded.** A trial is `completed` only when every attempt has a terminal
  record, every launch slot is classified, and the case's stopping point was reached. Otherwise it
  is `incomplete`, with the reason. An `attempt.json` proves a launch, not a conclusion.
- **Infrastructure is not semantics.** A tool loop whose every "finished" call recorded zero
  tokens and no tool completed saw no complete response; it is an infrastructure failure. It still
  counts against operational reliability, and it is excluded from the semantic denominator.
- **Missing evidence is missing.** A report without a findings block is ungradeable, not clean.
- **Stored once, derived again.** A trial retains an allowlisted copy of what its grade depends on,
  with digests. That means run records, reports, receipts, artifacts, allowlisted per-call usage
  and accounting — never prompts, worker logs, session databases or a staged home. `inspect`
  re-runs the graders on those copies wherever the result now sits, and reports altered files,
  grades that no longer recompute, and vanished evidence. It repairs nothing.

### E26.6 Withholding, stated per case

Where a case needs something kept from the worker, the suite says whether that is *established*.
For `dispatch-implementation` it is **not**: the checker's reference corpus lives in the harness
tree, which the worker boundary can read. The grader scans the session's tool activity locally for
the corpus file's name and retains only the answer. *Not observed there* is weaker than isolation,
and a coordinator's report that the worker did not look is restraint, not observation.

### E26.7 What one trial may claim

One observation per cell, with its denominator (`E24.7`: a qualification observation needs no
significance test). Per case, a result says in how many measured trials the dimension was shown,
and lists the rest. There is no verdict across cases: a configuration that uses tools well and
implements badly has not "mostly qualified".

## E27. What a comparison can answer

### E27.1 The question comes from what varied

A qualification comparison first classifies which **groups** of recorded fields differ. It then
names the question that supports:

| Varied | Question | Attribution |
|---|---|---|
| worker fields only | worker-profile comparison | the worker **bundle**: provider, endpoint, model, variant, limits, network — one field only if only one moved |
| coordinator only | coordinator comparison | worker path and tasks held fixed |
| control plane only | harness-treatment comparison | baseline and candidate under one declared configuration |
| executor, with or without worker fields | executor or agent-system comparison | the bundle, never the model alone |
| nothing | replication — distinct trials of one configuration; the same record twice is recognised as such | repetitions, not an effect |
| measurement kind (replay vs live) | none | not measurements of one question |

A declared treatment may change a bundle. That is recorded as a bundle and is not rejected
because several fields moved. Nor is it ever reported as one member's effect. Cells measured by
different transports are listed and never set side by side.

A result reports its planned configuration and, separately, the configuration its runs recorded:
interpreter, executor bytes, worker model and variant, and coordinator receipts. A comparison
prefers the record. Runs that disagree among themselves leave a field unverified. A record that
contradicts its plan is named, and the comparison is not controlled.

### E27.2 Unknown is neither agreement nor difference

This is the rule [`E17.3`](evaluation-comparison.md#e173-what-must-be-equal-before-a-difference-means-anything)
now states, for every comparison in this repository. A field that either side did not record is
**unverified**. Two records that both lack it are not known to agree; one that lacks it is not
known to differ. **An unverified required control never establishes a controlled effect.** Such a
comparison remains descriptive evidence and says why. Historical records are not relabelled: their
outcomes stand, and only the derived eligibility of comparing them changed. Known-absent values,
such as a local profile's lack of a variant, are recorded as words, so absence keeps meaning
*unknown*.

Reproduced at `4f9ffc8` before the repair. With only `model` differing and `harness_version`
recorded by neither run, `compare` returned `controlled: true`, while its render said equality
"is assumed". A regression now falsifies that shape
([evidence](evidence/worker-profiles-qualification-2026-09-23.md)).

### E27.3 Denominators and dimensions before any number

A comparison reports, in order: the question and every reason it is not controlled; the
configuration table; planned, attempted, completed, gradeable and excluded trials per side, with
exclusions named; unpaired and duplicate trials, which are listed and never scored as zero; then,
per paired trial, each dimension side by side. Those dimensions are outcome, first attempt, after
repair, false acceptance and refusal, finding and witness correctness, repairs, elapsed time,
tokens, usage completeness and derived cost. Tokens across providers, models or executors are
flagged as not directly comparable, because tokenizers and cache conventions differ.

### E27.4 What it deliberately does not do

No score, no ordering, no winner, no promotion and no default change (`E17.4`). One trial per
cell is an observation, not reliability. A later repeated comparison needs a margin declared in
advance, pairing where the design allows it, its own uncertainty, and a named unit of
independence. Calls within one trajectory are not independent samples (`E24.7`).
