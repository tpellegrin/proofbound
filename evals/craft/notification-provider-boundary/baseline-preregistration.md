# Baseline headroom measurement — pre-registration

Frozen before any semantic call on the repaired case. Everything here is decided without having
seen a single reflection.

## What this measures, and what it does not

One arm only: the **untreated** craft context, on the repaired `r0002` case. No treatment exists and
none is designed in this milestone, deliberately — a treatment written after seeing baseline numbers
could be fitted to whatever room they happened to leave.

The question is narrow:

> Is untreated discovery of the pre-registered pressure far enough below saturation that a later
> treatment could show a measurable selective increase within a plausible budget?

The previous case died partly of the opposite: its pressure was already surfaced about four times in
five untreated, so no treatment could have raised it. That is what this run exists to find out
before spending on a treatment.

## The pressure

Carried verbatim from the repaired-case design and audited once more below:

> Adding the second provider required a part of the system that is not specific to any provider —
> the code owning the product's delivery outcomes and retry policy, or the application entry point —
> to acquire knowledge of how one provider reports its outcomes, or to restate the retry policy.

**Answer-blindness audit.** It names no state, no file, and no architecture. It names no mechanism:
no interface, adapter, registry, protocol, injection, package or layout. It describes a
*consequence* — knowledge arriving somewhere it does not belong — and not a location, so an
evaluator must read the change to decide whether it happened. It is equally applicable to all three
states, and in two of them the honest answer is no.

This statement is given to the **discovery grader**, never to the reflector. The reflector receives
the unchanged untreated craft context.

## Measurement

The frozen closed-world substrate, unmodified. Per `(instance, arm, pressure)` cell:

| | |
|---|---|
| Arms | one, `baseline` |
| Instances | the three states, each with the reference `r0002` implementation applied |
| Pressure | one, as above |
| Samples | **N = 10** per state — 30 fresh reflections, each graded once |
| Grading | the discovery grader, characterised at 5.6% pooled non-modal dispersion |
| Outcome per cell | `detected` / `not-detected` / missing, never a verdict |

**Why N = 10.** The paired treatment this baseline is deciding on would need two arms and the same
three instances, so N is chosen for what that experiment can afford rather than for this one: 10
per cell is 60 reflections there, comparable to the reliability run's cost, and it is the count the
grader characterisation was reasoned against. Ten is also enough to distinguish the shapes that
matter here — 0-2 of 10, around half, and 8-10 of 10 — which is all the baseline has to resolve.

**Why the reference implementations rather than fresh worker runs.** Every reflection sees the same
diff per state, so implementation variance is removed by construction, exactly as the V2 paired
design established. The cost is that the diffs are author-written rather than model-written, which
is recorded as a limit on what the baseline describes.

**Local resolution.** The discovery grader contributes roughly 0-1.7 counts of noise per cell of ten,
depending on how ambiguous the report is. Reflector-level variation on this pressure is unmeasured —
this run is its first measurement. So a difference of one or two counts means nothing here, and the
categories below are written in terms of shapes rather than thresholds. No p-values, no confidence
intervals, no assumption that ten same-model samples are ten independent draws.

## Interpretation categories, fixed in advance

- **Clear headroom.** `state-c` detected well below saturation — roughly half of samples or fewer —
  while `state-a` and `state-b` stay low. A treatment has room to move `state-c` and something to
  lose on `state-a`/`state-b`.
- **Limited headroom.** `state-c` detected often but not always, leaving a narrow band. A treatment
  could still be run, but the effect it could demonstrate may not be worth its cost.
- **No headroom.** `state-c` at or near ceiling. A treatment cannot demonstrate increased discovery,
  and the case needs a different probe or a different pressure.
- **Baseline non-specificity.** `state-a` or `state-b` frequently detected. The pressure or the
  fixture is ambiguous, and specificity would be lost before a treatment is even applied.
- **Measurement unstable.** Within-cell dispersion or missingness large enough that no treatment
  effect of a plausible size could be read against it.

These are research interpretations of one run, not enums, not state, and not a score.

## What may not happen after the first call

No change to the intent, the future contract, any state, the reference implementations, the pressure
wording, `N`, the grader, the reflector context, or the inclusion of any sample. If the baseline
reveals a defect, it is recorded and the next milestone redesigns. A benchmark repaired against its
own results is not a benchmark.

## Retained

Every sample: raw report, slot, outcome, report hash, grading result, missing status, configuration
identity, and runtime. No sample is dropped for being a minority, and nothing is collapsed into a
mode, a majority or a per-state classification.
