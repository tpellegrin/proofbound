# MLR-B — designing a structurally distinct replication of the q1 question

Written before any fixture code and before any model call. No semantic call is made in this
milestone. `mlr-context-6`, the semantic boundary, the executor and the DeepSeek configuration are
untouched; only the fixture, task and oracle are new.

## 1. What q1 actually found

Reconstructed from [`craft-mlr-deepseek-v4-flash-high-paired-q1.json`](../../results/craft-mlr-deepseek-v4-flash-high-paired-q1.json),
not from a summary.

**Primary, and consistent.** Six scheduled pairs, six completed, six eligible. All twelve
trajectories correct — `both correct` in every pair. `full` consumed 5,976 / 5,630 / 6,170 / 5,630 /
5,630 / 5,630 unique bytes of direct implementation source; `contract` consumed **zero in all six**.
Six positive pair values, none negative, none tied.

**Secondary, and not consistent at all.** The representation that appeared in place of direct source
was heterogeneous to a degree the primary result gives no hint of:

| pair | `contract` runtime-derived | `full` runtime-derived |
|---|---|---|
| 1 | 19,654 | 0 |
| 2 | 36,072 | 18,142 |
| 3 | **109** | 0 |
| 4 | 39,231 | 0 |
| 5 | 31,633 | 102 |
| 6 | **102** | 0 |

Two `contract` trajectories solved the task correctly having reached the module's interior
essentially not at all. Four rebuilt a great deal of it through disassembly. And the behaviour is not
arm-determined: one `full` trajectory disassembled 18,142 bytes while holding readable source.

**So there are two findings, and only one of them is stable.** The response to source *availability*
was uniform. The *procedure* that compensated for its absence was not. The preregistered family
remains **E · Heterogeneous** and is not reinterpreted here.

## 2. What q1 establishes

For the frozen DeepSeek V4 Flash configuration, the object-storage fixture, its external task, its
public contract, its executable runtime and the qualified harness: withholding direct readable
implementation source preserved correctness across six paired opportunities while eliminating direct
implementation-source consumption. How the agent compensated varied substantially.

It does not establish that source is generally unnecessary, that contracts universally substitute for
implementations, that modularity improves agents, that runtime introspection is either required or
irrelevant, that total context fell, or that this DeepSeek behaviour generalises.

## 3. The next uncertainty

Not whether the instrument can separate source from runtime — that is qualified. Not whether this
fixture shows the effect — q1 answered it. The open question is:

> **Does the same phenomenon survive a structurally different software boundary and a structurally
> different external change?**

That is a replication and generalisation question, and it is answered by changing the fixture while
holding the model and the measurement system fixed.

## 4. Why mechanism ablation is deferred

The tempting alternative is to restrict runtime introspection and see whether it was load-bearing.
Deferred, deliberately:

- q1 does not identify one necessary compensating mechanism. Two `contract` trajectories succeeded on
  109 and 102 bytes of runtime representation, so introspection cannot be necessary in general;
  four used tens of thousands, so it is not irrelevant either.
- Restricting runtime would **create a different treatment**, not replicate the existing one. The
  frozen treatment is *source withheld, runtime preserved*.
- Ablating inside one fixture optimises understanding of `objectstore` strategy. If the phenomenon
  turns out to be fixture-specific, that work is wasted on an example.

Generality first, mechanism second. **Do not explain away heterogeneity before testing generality.**

## 5. Repository fixtures inspected

| fixture | what it is | usable as MLR fixture B? |
|---|---|---|
| `modularity-local-reasoning/fixture` (objectstore) | the q1 fixture | it *is* fixture A |
| `craft/notification-provider-boundary` | a System Craft case: accepted intent, declared property, three architectural states, routed questions | no — its subject is where provider knowledge *should live*, which entangles the thing MLR withholds with that fixture's own research question. Its `case-repair-design.md` lesson is imported below |
| `evals/scenarios/*` (11 scenarios) | specification-reflection scenarios; ten carry no Python at all, one carries three files | no — they are review scenarios, not executable modules with a public contract |

Nothing existing fits. Fixture B is new — but one hard-won lesson is carried over.

**The lesson, from the notification case repair:** an external task that asks for *another instance of
a variation point whose shape is already known* is cheap for any implementation, boundary or not.
A boundary earns its keep when the shape of the new demand differs. The q1 task obeyed this by
accident; fixture B's task obeys it on purpose.

## 6. Three candidates

### Candidate 1 — `eventbus`: in-process event fan-out with partial failure

**Boundary.** `subscribe(topic, name, handler)` and `publish(topic, event) -> Receipt`. A publish
delivers to every healthy subscriber, captures any handler that raises, and returns a receipt naming
what was delivered and what failed.

**Hidden interior.** Registry keyed by topic; per-handler isolation so one failure cannot stop the
rest; dedupe so a name subscribed twice receives one delivery per publish; normalisation of arbitrary
handler exceptions into receipt entries; and a re-entrancy queue so an event published *from inside a
handler* is drained after the current fan-out finishes rather than interleaving with it.

**Public contract.** Every healthy subscriber receives each published event exactly once per publish;
one failing subscriber neither prevents nor duplicates delivery to the others; `publish` does not
raise because a handler raised — failures are reported in the receipt; delivery order is unspecified;
an event published from within a handler is delivered after the current publish completes.

**External task.** The application's order workflow publishes `order.placed` and currently reports
success only if the whole fan-out succeeded. Change the caller so a partially failed fan-out is
reported as partial success with the failed consumers named, while a fully successful one is
unchanged — and without re-delivering to consumers that already succeeded.

**Why outside M.** M's delivery semantics do not change. What changes is how the *caller* interprets a
receipt it already receives. The information the caller needs — that failures are per-subscriber, that
they do not abort the fan-out, that `publish` does not raise — is exactly what the contract promises.

**Structural distance.** Dependency direction is inverted (M calls back into application code);
fan-out is 1:N; failure is partial and captured rather than total and raised; state is an in-process
registry rather than durable bytes; there is a registration lifecycle.

**Confounds.** Handler ordering could leak into the oracle if tests assert a sequence — avoided by
asserting sets. Re-entrancy is subtle enough that a careless contract would either omit it or
describe the queue.

**Determinism.** Complete: no clock, no filesystem, no network.

### Candidate 2 — `quota`: token-bucket admission control

**Boundary.** `check(key, cost) -> Decision(allowed, retry_after)` with refill over time.

**Hidden interior.** Bucket storage, refill arithmetic, clock granularity, burst allowance.

**External task.** The API applies per-endpoint quotas and returns `429` with `Retry-After`.

**Why weaker.** The interesting guarantees are time-dependent, so either the fixture injects a clock —
which puts a testing seam into the public contract and invites the agent to manipulate it — or it
depends on wall time, which threatens the determinism every other part of this programme has paid for.
Structurally it is also closer to `objectstore` than it looks: synchronous, 1:1, caller-driven, with
the interesting part being an arithmetic rule the caller must not know.

### Candidate 3 — `ledger`: parsing and normalisation of a record format

**Boundary.** `parse(text) -> Rows` with per-row error reporting and coercion rules.

**Hidden interior.** Tokeniser, error recovery, numeric coercion and precision handling.

**External task.** The importer must report per-row failures rather than aborting a whole file.

**Why weaker.** For a parser the grammar *is* the contract, so a contract complete enough to be
sufficient starts to approximate the implementation — which is exactly the failure mode §12 of the
q1 preregistration warns about. It is also a pure function: no state, no lifecycle, no inversion of
control, so on several axes it is *less* distant from `objectstore` than Candidate 1 despite feeling
different.

## 7. Comparison

| criterion | 1 · eventbus | 2 · quota | 3 · ledger |
|---|---|---|---|
| A contract sufficiency | strong — guarantees are behavioural | strong | **weak** — grammar approaches source |
| B interior meaningfulness | strong — isolation, dedupe, re-entrancy | moderate — arithmetic | moderate |
| C task externality | strong — caller reinterprets a receipt | strong | strong |
| D structural distance from objectstore | **strong** — inverted control, fan-out, partial failure | weak | moderate |
| E oracle neutrality | strong — assert sets and outcomes | moderate — timing assertions are brittle | strong |
| F determinism | **complete** | **at risk** — time | complete |
| G realistic engineering shape | strong | strong | strong |
| H fixture size | moderate | small | moderate |
| I no network or external service | yes | yes | yes |
| J treatment-leakage risk | low | low | **moderate** — contract may leak interior |

Candidate 2 fails on determinism and on structural distance. Candidate 3 fails on contract
sufficiency without leakage. **Candidate 1 is selected.**

It is not chosen for being more complicated. It is chosen because it changes the axes that would make
q1 a poor explanation of it: a module that calls back into the application, delivers to many
subscribers, and fails partially is a different shape of boundary from one that stores bytes and
either succeeds or raises.

## 8. What replication outcomes would mean

Recorded now, as conceptual expectation only. These are **not** result families; the replication's
families belong to its own preregistration.

- Both arms correct, `full` consuming source and `contract` zero → the q1 phenomenon survives a
  different boundary.
- `contract` correctness harmed → the phenomenon is boundary- or task-dependent, which is a real and
  useful finding rather than a disappointment.
- `contract` consuming source → a leak; the fixture is invalid and no treatment inference follows.
- Both arms behaving alike with `full` never reading source → the task exerts too little informational
  pressure to be informative.
- Secondary representation heterogeneous again → procedural multiplicity starts to look like a
  recurring feature rather than an `objectstore` artefact.
- Secondary representation consistent → q1's heterogeneity may have been fixture-specific.

## 9. What this milestone does not do

It does not choose N, preregister the replication, run a pilot, make a semantic call, change
`mlr-context-6`, explain q1's heterogeneity, start cross-model work, or start Comparative Pipeline
Evaluation. The model stays fixed; the measurement system stays fixed; the software boundary changes.

---

# The built substrate

Frozen. `evals/craft/modularity-local-reasoning/fixture-b/`, package `eventbus`, vendored at
`third_party/eventbus-2.1.0`, contract `docs/eventbus-contract.md`.

| | |
|---|---|
| module | `eventbus` — `__init__`, `_dispatch`, `_registry`, `_receipt`, `_errors` |
| hidden interior | per-consumer failure isolation, a deep copy per consumer, exception→receipt normalisation, a re-entrancy queue, unspecified ordering |
| public surface | `subscribe`, `publish`, `reset`, `Receipt`, `DuplicateConsumer`, `UnknownConsumer` |
| application | an orders service that places an order and announces it |
| external task | report a partly announced order as `202` naming the consumers that refused, without re-announcing to the ones that accepted |
| oracle | `hidden/external_test.py`, product surface only |
| valid solutions | `reads_failures` (reads `receipt.failures`), `subtracts_delivered` (never touches `failures`; takes the set difference against `receipt.delivered`) |
| invalid solutions | `all_or_nothing`, `swallows_the_failure`, `republishes`, `names_the_wrong_side` |

## How the machinery reads a second fixture

`_lineage.py` — the attribution engine — named no module anywhere, so nothing in it changed. What
named `objectstore` was the MLR *adapter* layer, in about twenty places. Those facts now live in a
`Fixture` descriptor, and **no function signature changed**: a caller selects a fixture by passing
its root, exactly as it always passed `FIXTURE`.

The safety property is mechanical and is asserted permanently: **fixture A must not move by a byte.**
Its workspace digests (`9053040a`, `c93d39f6`), source `1f83c3b1f22ab756`, runtime structure
`28ba66e1cd49b157`, contract `af3d3e9be15b51ed` and hermeticity rule `dcbf34fb63821980` are all
unchanged, and `mlr-context-6` is unchanged. There is no `mlr-context-7`; a new fixture is not new
attribution semantics.

## What was mechanically verified

- **Treatment.** `full` carries the five readable source files; `contract` carries none. The only
  workspace difference between the arms is the vendored tree, and nothing appears only in `contract`.
- **Execution.** In *both* arms the module that actually executes is the compiled runtime, not the
  readable copy — the guard that the approved internal control died without.
- **Leakage.** No private module file exists anywhere in the `contract` workspace, and **no file in
  it carries a single line of the implementation** — checked by fingerprint over every readable file,
  including the contract, the shipped tests and the application.
- **Oracle.** The unfixed fixture fails the gate, so the task is real. Two materially different
  correct solutions both pass. Four wrong solutions — all-or-nothing, silent success, re-announcing,
  and naming the wrong side — all fail. Every realization keeps the shipped suite green, so the gate
  is not merely catching regressions.
- **Attribution.** A source read in `full` is `implementation-source` on `artifact-path`. A
  disassembly in `contract` is `implementation-runtime` with zero direct source. And the R6 property
  holds on the new module: `eventbus`'s own docstring has two lines inside its source fingerprint,
  and reaching them through `__doc__` yields `public-contract` with **zero** direct source.

## Does anything need a new field qualification?

Attribution semantics, boundary semantics, hermeticity architecture, extraction, executor and model
are all unchanged, so the `mlr-context-6` field qualification stands. What is new is the fixture, and
the risk it introduces is fixture-local: whether the treatment actually withholds source and whether
the oracle is sound. Both are answered deterministically above, without a provider call.

One judgement is deliberately left to the replication's own preregistration: whether a bounded
treatment-exposure qualification should run before the paired series. The Field Test points at *no* —
the exposure and leakage questions are settled deterministically, and the machinery they run through
is the qualified one — but that is a call for the milestone that spends money, not this one.

## Not decided here

N, the slot order, the budget, the result families and the sampling plan are **not** chosen in this
milestone. They belong to the replication's preregistration, and choosing them here would let the
fixture's construction and the sampling plan be tuned to each other.
