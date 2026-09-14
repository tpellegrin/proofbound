# `mlr-deepseek-v4-flash-high-paired-q1` — preregistration

Frozen before any semantic call. The first paired MLR experiment whose complete measurement path has
been field-qualified end to end.

**This is a new experiment.** `mlr-deepseek-v4-flash-high-paired-r4` remains permanently invalid and
`mlr-r5-deepseek-attribution-field-qualification` remains incomplete. Neither is resumed, repaired,
renumbered or pooled. This series starts at pair 1, slot 1. Every earlier series — Nemotron, C3, C3R,
the DeepSeek pilots, the first invalid paired run, R4-C3, r4, R5, R6 — is **methodology and history,
not samples**. They explain why this experiment exists. None of them is in its dataset.

## 1. The instrument is done

`mlr-context-6` now carries deterministic adversarial coverage, retrospective replay across 54
retained sessions, live sensitivity to genuine source ancestry, live component-scoped mixed-container
behaviour, and live specificity against source-shaped text delivered by a non-source activity — the
last established by the R6 known-answer calibration, where the same 169-byte span took three causal
routes and three origins with direct source above zero only where an activity opened the file.

No further instrument work happens absent a **concrete validity defect**. An unexpected scientific
result is not a defect. `contract` leaning heavily on disassembly, `full` ignoring source it could
read, arm differences smaller than hoped, wide variation between pairs — none of these is an
instrument problem, and none licenses a change mid-series.

## 2. One caveat settled before freezing

R6 recorded 170 bytes of quoted public documentation in `source_equivalent_reconstruction`. The
channel's mechanical definition, checked against the code and the corpus, is **model-authored text
that is source-equivalent** — r4 §8 puts it as *"source-form text the model reconstructed from
something else"*, with no clause requiring the text to have been unavailable elsewhere, and the
ledger already disclaims inference: *"no claim is made about what the model inferred, only about what
it had already been shown."*

So the measurement was correct and one interpretive gloss was too narrow. The instrument is unchanged
and the channel is preserved. What is tightened, here and in the code comment, is the reading:

> **A non-zero `source_equivalent_reconstruction` figure is not by itself evidence that hidden
> implementation interior was recovered.** It measures model-authored source-equivalent text. The
> same bytes may have been legitimately visible through the public surface and simply quoted back.
> Public-surface overlap must never be read as defeating encapsulation.

## 3. Question

> For a bounded implementation change conceptually outside module M, when correctness is preserved,
> does withholding direct readable implementation source for M — while preserving its public contract
> and its executable runtime — materially change the amount and the kind of implementation
> representation that enters the agent's reasoning?

Descriptive and causal within one tightly controlled setup. Not "does CONTRACT win", not "is
modularity good".

## 4. Treatment

**`full`** — the controlled readable implementation source for the hidden module is available.

**`contract`** — that direct readable source exposure is withheld. The public contract and the
executable compiled runtime remain.

`contract` is **not** tightened. It continues to permit Python, `help`, `pydoc`, `dir`, `inspect`
where the runtime allows, disassembly, tracebacks, runtime experimentation, `grep`/`find` over what is
present, temporary artefacts and model reconstruction. The experiment tests **source availability**,
not elimination of implementation knowledge.

## 5. Frozen stack — read from the repository

| | |
|---|---|
| source | `1f83c3b1f22ab756` |
| task | `eb24429a46ecad4c` — the MLR task |
| public contract | `af3d3e9be15b51ed` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| attribution | **`mlr-context-6`** |
| profile | `profile-1` |
| semantic boundary | `b88bd43109184459` — as constructed by the frozen launcher below; the policy exposes the interpreter that launches a slot, so the digest belongs to CPython 3.9.6 with the executor bound |
| hermeticity rule | `dcbf34fb63821980` — as computed on the execution host; the rule's identity includes its scan roots, which are host paths |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| credential | provider auth file staged into the constructed home, destroyed with the view |
| extraction | checkpoint-aware session copy plus workspace, after destruction |
| price identity | `deepseek-2026-09-09` |

**Three of these identities are properties of the execution host, not repository constants.** The
interpreter is whatever launches a slot; the semantic boundary exposes that interpreter; the
hermeticity rule's identity includes its scan roots, which are absolute host paths. The values above
are the ones this host produces, they are what every qualifying trajectory recorded, and each is
recorded again per measurement in the result. A run on another machine would legitimately carry
different digests for the same rule, and comparing the two would be comparing hosts rather than
experiments.

**The R6 calibration tasks are not part of this experiment.** `calibration-source-read.md` and
`calibration-runtime-doc.md` exist to move a known mass across a known boundary and are never used
here. This experiment uses the MLR task `eb24429a46ecad4c` and leaves the agent unsteered.

## 6. Admissible evidence for N

N must not be chosen from anything the qualifications observed. The barrier applied is the strict one:
**only evidence available before the first R4-C3 qualification trajectory (2026-09-13 16:02)**. That
excludes R4-C3, the invalid r4, R5 and R6 entirely — their arm differences, byte counts, correctness,
tokens, time, cost and tool behaviour alike.

## 7. Chronology of N, verified

| when | what |
|---|---|
| 2026-09-09 23:53 | `da3468a` freezes the N = 6 rationale, when **no `contract` slot had executed under any model** |
| 2026-09-10 | the first paired series runs and is invalidated; its outcomes are never used for sizing |
| 2026-09-13 16:02–16:09 | the R4-C3 qualification trajectories run |
| 2026-09-13 | `be1e23f` audits the rationale and corrects two statements, neither bearing on N |

The evidence base on 2026-09-09, verified directly from the records rather than from the prose: eight
`full` trajectories across C3D and C3D-R, **5,822 bytes of direct source in every one**, **8/8
correct**, and runtime-derived representation ranging **1,003 to 62,940 bytes**. Measured under
`mlr-context-2` and `mlr-context-3`; the figure is not claimed to agree with anything measured since,
and no comparison across instrument versions is made.

## 8. N = 6 pairs — fixed

Retained, on that evidence and for these reasons:

- The primary quantity has **no spread at all** in the arm that has it — 5,822 bytes, eight times out
  of eight — and the other arm is expected at zero by construction. A contrast between a constant and
  a structural zero needs few samples.
- What lacks resolution is **correctness**, where an 8/8 baseline shows nothing, and **runtime
  representation**, whose observed spread is sixty-fold.
- Six pairs give twelve executions and **an observational resolution of one in six** on correctness
  counts, and enough replication to show whether heavy runtime representation is typical or
  occasional.
- More would buy precision the result families do not use.

Two things this rationale does **not** say, both corrected in the audit and not reinstated here: that
the `full` figure is invariant across every run ever measured — it is bounded to those eight, under
those instrument versions — and that a single failure would be distinguishable **from noise**. Six
paired opportunities give a count, not a noise model. No result family uses a threshold, a power
calculation or a significance claim, and none is offered.

**Fixed N.** No adaptive extension, no sequential stopping, no sample added because a result looks
ambiguous, because an arm fails, because a pair is inconvenient, or because the pattern is nearly
there.

## 9. Pairs, order and unit

Twelve slots, generated mechanically by `pb_mlr.slots(["full", "contract"], 6)`, which rotates the
within-pair order every pair so temporal position is never identical to treatment:

| slot | pair | arm | | slot | pair | arm |
|---|---|---|---|---|---|---|
| 1 | 1 | `full` | | 7 | 4 | `contract` |
| 2 | 1 | `contract` | | 8 | 4 | `full` |
| 3 | 2 | `contract` | | 9 | 5 | `full` |
| 4 | 2 | `full` | | 10 | 5 | `contract` |
| 5 | 3 | `full` | | 11 | 6 | `contract` |
| 6 | 3 | `contract` | | 12 | 6 | `full` |

Three pairs run `full → contract` and three run `contract → full`. Deterministic, not randomised, so
there is no seed to record. **No treatment-aware reordering once execution begins**, and no reordering
after a failure.

**Unit.** experiment → pair → semantic slot → infrastructure attempt. The paired comparison unit is
the frozen pair. A semantic trajectory that has begun is immutable. An infrastructure attempt that
fails before semantic execution begins is not a semantic sample.

## 10. Retry

Infrastructure attempts — construction, staging, preflight refusal, provider unreachability, launcher
failure — are bounded at **three per slot** and may retry the same slot; every attempt is recorded.

A completed semantic trajectory is **never** re-rolled. Not for being incorrect, not for being
expensive, not for an inconvenient tool strategy, not for a `contract` run heavy with representation,
not for a `full` run that never opens the source. A sample is never replaced because it weakens the
interpretation.

## 11. Missingness and invalidity — N counts scheduled pairs

**N = 6 refers to scheduled pairs.** The denominator never moves. The experiment does not run until
six valid pairs appear.

| case | rule |
|---|---|
| A · one infrastructure attempt fails before semantic execution | retry the slot, bounded at three; both records retained |
| B · all three infrastructure attempts for a slot fail | the series **stops**; outcome family **F**; completed pairs retained and reported, no treatment inference |
| C · a semantic trajectory begins and its lifecycle is interrupted | the attempt is accounted and preserved, contributes no measurement, and is **not** re-rolled; its pair is incomplete |
| D · extraction fails | instrument validity failure → **F**, series stops |
| E · material unresolved attribution, at item **or component** granularity | **F**, series stops |
| F · a contradiction or an uncovered material model-visible event | **F**, series stops |
| G · a boundary leak, uncontrolled source in `contract`, oracle/reference/prior-sample leakage, cross-slot contamination | **F**, series stops |
| H · provider, model, variant, boundary, runtime or attribution identity drift | **F**, series stops |
| I · the hidden oracle cannot grade an extracted workspace | **F**, series stops |
| J · the ceiling would be exceeded before a slot | that slot is not launched; the series ends short and reports how many pairs completed |

An instrument validity failure invalidates or stops the experiment. It never deletes a sample so that
collection can continue until six clean pairs have accumulated.

A pair contributes to the paired comparison only if **both** of its slots produced valid trajectories.
Incomplete pairs are reported, never silently dropped, and never replaced.

## 12. Correctness is a gate

Every slot is graded by the unchanged hidden oracle, control-side, on the extracted workspace. Pair
categories, fixed now:

**both correct** · **`full` only** · **`contract` only** · **neither**.

Representation is interpreted **only on pairs where both arms are correct**. `contract` consuming less
direct source while failing the oracle is not a better representation strategy; it is a failure with a
smaller number beside it. No category is invented afterwards.

## 13. Primary measurand

> **Unique bytes of direct implementation-source representation consumed on correct runs, per arm.**

Unchanged. *Direct* means bytes whose causal ancestry reaches readable implementation source made
available to the arm — not disassembly, not runtime names, not file names, not source-form text the
model produced from something else. *Consumed* keeps its operational definition: **text appearing in a
part OpenCode places in the message history before a later model call.**

Pair-level comparison, fixed: for each pair where both arms are correct, the pair's value is
`full` unique direct-source bytes minus `contract` unique direct-source bytes. Reported per pair and
as a count of pairs by sign. **Unique bytes** is the primary quantity and stays primary regardless of
which secondary channel turns out to be interesting.

## 14. Secondary dimensions — fixed now, never added later

Each is reported beside the primary and never summed into it. Source bytes, disassembly characters and
file-name references are different units.

| dimension | what it mechanically measures | what it does not license |
|---|---|---|
| delivered direct-source bytes | unique bytes multiplied by the model calls that began afterwards | a claim about attention or influence |
| implementation-runtime representation | disassembly and live-object renderings of the module | that the interior was "recovered"; it is representation, not comprehension |
| `source_equivalent_reconstruction` | **model-authored text that is source-equivalent** | **not** evidence that hidden interior was recovered — the bytes may have been public surface quoted back (§2) |
| implementation metadata | references to the module's files carrying no contents | that structure disclosure equals implementation disclosure |
| public-contract representation | the contract document and public surface | that reading the contract is equivalent to reading source |
| application representation | the service's own code | anything about module M |
| unresolved, contradictions, uncovered events | audit counts at item and component granularity | anything scientific; they are validity gates |

## 15. Resource dimensions — descriptive only

Model calls · tool calls by name and failures · input, output, reasoning, cache-read and cache-write
tokens · elapsed and session time · tool seconds · derived model seconds · verification seconds ·
**executor-reported cost and independently derived cost, both retained**.

The executor-versus-derived cost discrepancy remains unresolved and out of scope. Both figures are
reported; neither is selected because it favours an arm. None of these is collapsed into the others.

## 16. Budget — $0.50 ceiling

Checked before each slot with a $0.10 reserve; a trajectory under way is never cut short for money.

Feasibility only, and downstream of an N already fixed: at the published `deepseek-2026-09-09` rates
and the operational cost of comparable trajectories, twelve executions sit well inside this ceiling.
Cost does not determine N and does not enter any treatment interpretation.

## 17. Result families — complete, fixed before execution

| family | shape |
|---|---|
| **A · Local source substitution supported** | correctness preserved; `full` consumed source materially; `contract` did not replace it with comparable implementation-derived representation |
| **B · Representation shifted, not removed** | correctness preserved, but `contract` rebuilt the interior through another route at comparable or greater volume |
| **C · Implementation access materially useful** | `contract` correctness regresses and the evidence indicates implementation information mattered |
| **D · Little meaningful representation difference** | correctness preserved and the representation profiles are close; no support for the proposed reduction under this task |
| **E · Heterogeneous** | pairs disagree in direction or magnitude enough that no single story fits; the result stays descriptive and per-pair |
| **F · Experiment invalid or stopped** | an instrument or execution validity defect under §11; no treatment inference of any kind |

No architectural verdict. **No scalar.** Explicitly prohibited: architecture score, modularity score,
context-efficiency score, quality-per-token, correctness-weighted cost, bytes-per-correctness, or any
composite rank. Multiple dimensions stay multiple dimensions. An arm that is cheaper *and* less correct
is a tradeoff for a person, not an improvement.

## 18. What this experiment cannot establish

Written before execution, so that a striking result cannot quietly widen it. It cannot establish that:

- modularity is universally good, or good at all outside this setup;
- information hiding reduces context in general;
- public contracts can replace implementations in general;
- fewer tokens mean better engineering;
- source hiding improves agents;
- DeepSeek V4 Flash represents any other model, or agents in general;
- this fixture represents other repositories, languages or module boundaries;
- the measurand is a general architecture metric;
- correctness parity on six pairs proves semantic equivalence of the two arms' work;
- repetition or consensus establishes truth.

It is a bounded, descriptive, causal observation about one model, one task, one module boundary and
one measurement path.

## 19. Analysis timing

Each slot is validated for integrity as it completes, because the harness has to decide whether to
continue — that is a validity check, not a treatment reading. **No aggregate paired summary is
computed until all twelve slots have terminated.**

Blinding is impossible here and is not claimed: the operator sees per-slot values as they land. What
prevents adaptation is that N, the slot order, the retry rules, the stopping rules and the result
families are all immutable from this commit onward, and a completed trajectory can never be re-rolled.

## 20. Immutability

This document is frozen at the commit that adds it. Once the first semantic call is made it is not
edited. Any later clarification is a separate record that cannot alter this plan, exactly as the
N audit was a separate record that left r4's preregistration byte-identical.
