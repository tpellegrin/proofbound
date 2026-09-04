# Context economy and refactoring economics

> **Research track, not production behavior.** External evidence and hypotheses about how much repository
> context a bounded change requires. Nothing here is implemented, and nothing here may be treated as a
> production invariant. The one normative rule it supports, `P13`, is defined in
> [core-model.md](core-model.md).
>
> Entry point: [README.md](README.md).

## 28. Context economy and refactoring economics

This section is **architecture only**. Nothing in it is implemented, and M2A deliberately contains no
production code that counts tokens, files, or time. It exists so a real result is recorded where it can
shape later milestones, rather than being lost.

### 28.1 The empirical result being incorporated

Giles Edwards-Alexander (Thoughtworks), *The Economic Benefit of Refactoring*, published on
martinfowler.com, 30 July 2026:
<https://martinfowler.com/articles/exploring-gen-ai/refactoring-economic-benefit.html>

The method matters more than the number. A representative bounded change — add a new
`ItemWatchStore` public async trait to the Firestore layer — was replayed by a **fresh agent session**
after each of 15 sequential refactoring steps, with the change discarded between iterations so no
learning carried over. This is close to a controlled experiment on cost-to-change, and it is the part
Proofbound can borrow.

| Metric | Baseline | Step 15 | Change |
|---|---|---|---|
| Data-access-layer LoC | 17,155 | 16,608 | −547 |
| Largest file LoC | 17,155 | 3,695 | −13,460 |
| Total Rust LoC | 50,359 | 49,812 | −547 |
| Input tokens | 159,564 | 27,360 | **−83%** |
| Output tokens | 1,705 | 2,113 | +24% |

**The mechanism is the finding, not the percentage.** Total code barely moved — 547 lines out of
50,359. What collapsed was the *largest file*, and with it the amount of code the agent had to read to
locate its work. Input tokens stayed flat until the monolith began to split and then fell off a cliff.
Output tokens rose slightly: the agent wrote a little more, having read far less.

Honest limits, stated by the author and preserved here: one experiment, one greenfield application
built and maintained by a single developer, one subsystem. Token counts were *approximated* — a
sub-agent counted characters and divided by four via `tiktoken`, because live token counts were not
reliably available. The cost of performing the refactoring was never measured precisely; only an upper
bound of five million tokens is stated. **83% is not a law and must never be quoted as one.**

### 28.2 Two context surfaces

The result refines an existing Proofbound principle. Context economy is not only prompt compression.

**A. Harness context** — what Proofbound deliberately supplies: common protocol, role protocol, task
contract, selected evidence, explicit inputs. DSD already optimizes this aggressively, and it is
bounded by design.

**B. Repository discovery context** — what a worker must inspect to find and change the right code:
files read, bytes read, symbols and dependency surfaces traversed, search results.

DSD has always measured and controlled A. The Fowler result is about **B**, which Proofbound currently
does not observe at all. A well-factored codebase can shrink B dramatically while total LoC barely
moves — which is precisely why LoC is the wrong metric and *relevant context* is the right one (I10).

### 28.3 Why this is not a ledger field

Execution economics must not enter the accepted-artifact record. No `tokens`, `files_read`,
`duration`, `largest_file` or `context_cost` field belongs there.

The ledger answers durable questions: what content was accepted, what it depended on, which declared
review purpose was satisfied, and which accepted review established it. Economics answers operational
ones: how much context a task required, whether an area is becoming expensive to navigate, whether a
refactoring paid for itself. Different trust domain, different lifecycle, different audience — and
model pricing, token accounting and wall-clock time are exactly the kind of facts that go stale and
become incomparable. Freezing them into engineering history would contaminate freeze identity with
data that has no durable meaning. Economics telemetry belongs in run/execution evidence, where model
identity already lives, and a later subsystem may aggregate it separately.

### 28.4 A future capability, in two modes

**Mode 1 — passive context-economy telemetry.** Record mechanically obtainable facts during ordinary
execution: repository files read, repository bytes/chars read, files changed, tool calls, wall-clock
duration, and provider token counts *where reliably exposed*.

Comparability is the hard part, and the Fowler experiment demonstrates it: token counts had to be
approximated from character counts. Caching, context compression, model changes and tool-protocol
changes all move token totals without any change in the code being navigated. Proofbound should
therefore prefer **provider-neutral** measurements — repository files read, repository bytes read — as
the primary signal, with token counts as additional telemetry rather than the metric.

**Mode 2 — controlled refactoring experiment.** Borrow the experimental structure directly:

```
representative bounded change C
    -> fresh worker against baseline R1  -> measure -> discard C
    -> apply one behavior-preserving refactoring step -> R2
    -> fresh worker executes the identical C          -> measure -> discard C
    -> compare
```

This estimates *did this refactoring reduce future cost-to-change?* — a far stronger claim than *the
code looks cleaner*. It should control for the same task contract, the same role, the same repository
semantics apart from the refactoring stage, fresh worker context, and ideally the same
model/provider/runtime version. Noise and non-determinism must be reported honestly; no statistical
machinery is designed here.

Proofbound is unusually well suited to this because a **task contract is already a bounded, repeatable
unit of work**. A contract could later serve as an architecture benchmark. The hazards are real and
must be captured now: benchmark changes drift out of realism as the code evolves; a contract may stop
being valid; worker and model versions change underneath the comparison; fresh execution is
nondeterministic; and benchmark mutation must **never** leak into a real branch.

### 28.5 Measurement is mechanical; refactoring is semantic

Python may measure file sizes, largest files, structurally available dependency counts, files read,
bytes read, tool calls, duration, repeated context surface, and test outcomes.

Python must **not** conclude from those facts that a module should be refactored. The experiment itself
is the argument: indiscriminate splitting is not the mechanism of benefit. The benefit came from
*coherent* factoring that let the agent identify a smaller relevant subset — and the author reports
that the agent could neither select the valuable refactorings nor apply them reliably; a human guided
the choice, and the mechanical edits were done with scripts.

So the workflow is:

```
mechanical signal -> semantic refactoring assessment -> optional proposal
                  -> behavior-preserving implementation -> controlled economic experiment
```

and never `file > N lines -> automatic split`. A large-file threshold is a signal, never a verdict
(I9). This is the same boundary the whole harness is built on: Python compares facts, humans and
agents judge engineering quality.

### 28.6 Cost of change, and amortization

A future observation vector for a bounded task might include `repository_context_bytes`,
`repository_files_read`, `input_tokens`, `output_tokens`, `wall_time`, `tool_calls`,
`verification_time`.

These must not be collapsed into a single score. Providers price tokens differently, caching changes
effective cost, one model may consume more tokens yet finish faster or more correctly, and a provider
change invalidates historical monetary comparisons outright. Therefore: **preserve raw observations,
derive views later, and never freeze monetary pricing into engineering history.** The durable insight
is trend detection — *changes in subsystem X now require reading four times more repository context
than a year ago* — which outlives any price list.

Refactoring also has a cost (I11), and the economic claim depends on repeated future change:

```
refactoring cost R, average per-change saving S  ->  break-even after roughly R / S changes
```

The published experiment illustrates why this must be stated rather than assumed: the saving was
132,204 input tokens per change, while the refactoring cost is known only as an upper bound of five
million tokens. Taken at that bound, break-even is roughly **38 similar changes**. That may be an
excellent trade for a hot subsystem and a poor one for a quiet corner — which is the entire point of
measuring rather than asserting.

Not every benefit is token-denominated. Lower defect probability, simpler testing, clearer ownership,
easier human review and better change isolation are real and unpriced. The system must never reduce
the value of refactoring to a token price.

### 28.7 Lifecycle integration — what this must not become

There must be **no mandatory refactoring stage between implementation tasks**. That is the wrong lesson
and would impose a cost the evidence does not justify.

Plausible future hooks instead: a periodic context-economy review that surfaces a refactoring
*candidate* when accumulated evidence shows an area has become expensive to navigate; opportunistic
post-change observation that records metrics without forcing action; an explicit behavior-preserving
refactoring change type that a human or orchestrator opens deliberately and validates with a
representative-task experiment; and a pre-planning signal, where discovery notices that a requested
change requires excessive context and proposes a prerequisite refactoring.

The principle: **refactoring is justified by observed change friction and engineering semantics, never
by automatic aesthetics.**

### 28.8 Why this is deferred past M2A

It depends on nothing in M2A and M2A depends on nothing in it, so bundling them would only have
enlarged an unproven slice (I12). It also has a genuine architectural prerequisite: Mode 2 requires
running the *same task contract* against two repository revisions with a fresh worker and discarding
the mutation each time — which is worktree concurrency, currently listed under M5. Passive telemetry
(Mode 1) has no such prerequisite and could land earlier as its own research track.

---


### 37.5 Coherence and context economy are different measurements

There is a plausible reinforcing loop between architectural erosion and context cost:

```
architecture erodes  ->  the relevant repository surface grows  ->  a bounded change must
read more to find its work  ->  more imitation of whatever is nearby (T3)  ->  more
workaround-shaped changes  ->  architecture erodes further
```

and a mirror-image virtuous one: coherent structure keeps the relevant surface small, which keeps
bounded reasoning bounded, which produces cleaner isolated changes.

**This is a hypothesis worth measuring, not established causation.** Nothing in the Fowler experiment
(§28.1) tested it — that experiment measured context cost across refactoring stages, not coherence, and it
ran on a single greenfield codebase. Proofbound should be able to observe both quantities and look for the
correlation; it must not assume it, and must not design as though it were proven.

Which is why the two stay **separate dimensions and are never combined into one score**:

| Dimension | Question | Measured how |
|---|---|---|
| Context economy | How much repository context does a bounded change require? | Mechanically (§28.4) |
| Architectural coherence | Does repository reality align with accepted intent and decisions? | Semantically, against baseline + decisions (None[§37.3](long-running-autonomy.md#373-what-counts-as-a-drift-finding)) |

A subsystem can be cheap to navigate and incoherent, or coherent and expensive. A single "health score"
would destroy both signals and create precisely the optimizable target T10 warns about.

**No composite technical-debt score.** `large file = bad`, `retry count = bad`, `dependency pins = bad`,
`verbose logs = bad` are not conclusions. Each can be a legitimate response to a real constraint. A future
drift detector may surface that retry behavior expanded substantially, that dependency constraints
tightened, that shared middleware changed, that module coupling increased, or that the context surface
grew — and every one of those terminates in a fresh semantic evaluator that decides whether it represents
justified evolution or erosion (P1, P13). Measurement mechanical; judgment semantic. A number that gates
anything has become a verdict, and has stopped being a measurement.
