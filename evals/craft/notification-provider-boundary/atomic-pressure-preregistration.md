# Atomic pressure — re-pre-registration

The fixture stays exactly as frozen at `4e0784a`. Only the sentence handed to the discovery grader
changes, and it changes by **deletion**.

## 1. Why the previous column failed

The frozen pressure offered three ways to fail. Checked against the frozen reference
implementations rather than against labels:

| Clause | `state-a` | `state-b` | `state-c` |
|---|---|---|---|
| 1. The application entry point gains provider selection | **true** — `app.py` gains `provider` | **true** | **true** |
| 2. The retry policy is restated | **true** — `beacon.py` has its own loop | **true** — same | **false** — one shared loop |
| 3. Provider-independent code acquires how a provider reports outcomes | **false** — only `beacon.py` | **false** — only `providers/beacon.py` | **true** — `notifications/status.py` |

Clause 1 is true everywhere *because the future contract requires it*: `app.notify` must gain a
`provider` parameter, so no architecture can avoid it. Clause 2 is worse than non-discriminating —
it is **inverted**, true in both sound states and false in the degraded one, because keeping a retry
loop inside each provider is what a provider-specific integration does.

Only clause 3 discriminates, and it discriminates perfectly. A disjunction is satisfied by any
disjunct, so a report noticing clause 1 — which every honest report about this change notices —
earned a detection. That is a **measurement atomicity failure**: three independently satisfiable
propositions were bundled into one cell, and the cell stopped meaning anything.

## 2. Candidates considered

**P1 — "Provider-independent code acquired knowledge of how a particular provider represents
delivery outcomes."** Atomic and close. Rejected as the final wording only because "knowledge of how
a provider represents outcomes" does not say *why* that knowledge was needed, and a report noting
that a shared module merely mentions a provider name could arguably satisfy it.

**P3 — "Adding Beacon caused provider-independent code to distinguish Beacon's response-body outcome
convention from another provider's HTTP-status convention."** Rejected on two counts. It names the
conventions, which tells a reader where to look and edges away from answer-blindness. And it is
narrower than the proposition: an implementation that handled only Beacon's body without
distinguishing it from Acme's status would still be the pressure, and P3 would miss it.

**P2, refined — selected.**

## 3. The pressure

> **Code that is not specific to any one delivery provider had to interpret how a particular
> provider reports the result of a delivery attempt, in order to produce the product's delivery
> outcome.**

One proposition. No disjunction. No path, no file, no module, no package, no interface, adapter,
registry, protocol or injection. It describes a responsibility acquiring knowledge and the purpose
that knowledge served.

## 4. Entailment

Every part traces to text the reflector already receives.

| Part | Source |
|---|---|
| "the product's delivery outcome" | Accepted intent: `status` is `sent`, `rejected` or `failed`, and *"the outcome vocabulary above is part of the product contract and does not change"* |
| "how a particular provider reports the result" | Accepted intent: *"Providers differ in how they report the outcome of a delivery attempt — some in the HTTP status, some in the response body"* |
| "had to interpret … in order to produce" | Future contract `r0002` AC-003: the outcome vocabulary is identical for both providers, so something must map each provider's report onto it |
| "not specific to any one delivery provider" | Accepted intent: more than one provider is expected over time, so code that is not about a provider outlives any particular one |

Nothing is supplied that the intent does not already say, and nothing states where the
interpretation should live — which is what a later treatment would supply, and why it is absent here.

## 5. What does not satisfy it

Deliberately outside the proposition, because each is either required by the contract or is ordinary
composition: knowing a provider's name; selecting a provider; passing a `provider` parameter;
endpoints; credentials; header keys; payload field names; that more than one provider exists; that a
retry loop exists; where a retry loop lives. A report raising only these has not found this pressure.

Counterexamples checked against the wording: a **composition root** assembling providers does not
interpret a result; a **generic HTTP helper** reading `2xx` is not interpreting how a *particular*
provider reports; a **provider capability registry** describes what a provider can do, not how it
reports; a **provider-specific plugin** interpreting its own provider is exactly what should happen
and is excluded by "not specific to any one delivery provider". A **shared normalisation utility**
that interprets one provider's reply *is* the pressure, correctly.

## 6. Reference truth table

Derived from the frozen code, not from labels.

**`state-a` — false.** Beacon's reply is read in `delivery/beacon.py`, a file that exists to be
Beacon. `app.py` gains a parameter it passes through without inspecting; `delivery/__init__.py`
selects a sender by name. Neither interprets a result. Nothing that is not Beacon-specific needs to
know that Beacon answers `200` and carries its verdict in a body.

**`state-b` — false.** The same, by a materially different mechanism: no protocol class and no
injection, a self-registering module. Beacon's reply is read only in
`delivery/providers/beacon.py`. The registry maps a name to a handler and never sees a response.
**This state is the control against form preference: a pressure that fired here would be measuring
architecture style rather than knowledge placement.**

**`state-c` — true.** `notifications/status.py::outcome_for` gains a `provider` parameter and a
branch that reads `body["result"]` to decide `sent`, `rejected` or `retry`. That module's purpose is
the product's outcome vocabulary; it is not about any provider, and it now cannot produce the
product outcome without knowing how Beacon reports one. `notifications/retry.py` grows a `provider`
parameter to carry that through.

False, false, true — established before any semantic call.

## 7. Anti-fitting

**Stated limitation: the previous baseline's thirty reports have been read.** Blindness to that
evidence cannot be claimed, so the derivation is constrained instead.

The wording is clause 3 of the pre-baseline pressure with the other two clauses deleted, and clause 3
is verbatim the criterion the **pre-baseline** case-repair design already used in its own state
analyses: *"No module that is not specific to a provider acquires knowledge of how any provider
reports outcomes."* That sentence was written and committed before a single report existed. This
re-pre-registration removes material rather than adding it, and adds nothing that the earlier design
did not already argue.

No wording was tested against the retained reports. No phrasing was chosen because it would have
flipped a particular report. The retained reports are used for one purpose only — as **grader
anchors**, to characterise the column — and never to estimate what the new baseline will show.

## 8. Historical evidence

[§E54](../../../docs/architecture/proofbound/evidence/evaluation-runs.md#e54-the-repaired-case-measures-and-the-pressure-statement-does-not-discriminate)
stands unchanged and keeps its conclusion. It was a valid result for the pressure frozen at the
time. The old series is not re-graded, not relabelled, and not spliced with anything measured here.

## 9. Grader adequacy check, pre-registered

The machinery is unchanged but the semantic question is new, so the previous 5.6% dispersion does
not transfer. Before spending reflector calls, the existing discovery grader is characterised
against this exact column.

**Anchors** — six retained reports, selected by semantic category, **including the three the old
pressure false-credited**, so the set is biased toward difficulty rather than away from it. No
anchor is edited.

| Anchor | Source | Category | Expected |
|---|---|---|---|
| `d1` | `state-c` #1 | identifies the leakage plainly | detected |
| `d2` | `state-c` #8 | identifies the leakage and calls it reasonable — discovery is not a verdict | detected |
| `d3` | `state-b` #1 | says response interpretation is **correctly isolated** in the provider module | not-detected |
| `d4` | `state-b` #3 | criticises the `provider` parameter reaching `app.notify` and a central import | not-detected |
| `d5` | `state-a` #1 | provider identity and selection only | not-detected |
| `d6` | `state-a` #7 | generic provider concerns, no interpretation claim | not-detected |

**N = 15** repeats per anchor, 90 gradings, fixed before execution — the count both previous grader
characterisations used, so their dispersions are comparable.

**Adequacy rule, fixed before results.** The column **passes** only if every anchor's modal outcome
equals its expected class, and dispersion is bounded enough that grader noise alone could not
manufacture the separation a baseline needs. It **fails** if a selection-only anchor (`d4`, `d5`) or
the encapsulated-interpretation anchor (`d3`) is credited as detected in the modal case — that is the
previous failure reappearing — or if modal shares sit near a coin flip. On failure the milestone
stops; the grader is not tuned, and majority voting is not a repair.
