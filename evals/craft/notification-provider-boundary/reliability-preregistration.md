# Reliability baseline — pre-registration

Frozen before any repeated measurement. Everything here is a decision made without having seen a
single repeated outcome.

## What is being measured

Not whether the craft instrument is right. Whether it says the same thing twice.

Three layers, reported separately and never combined:

| Layer | Held fixed | Repeated | Answers |
|---|---|---|---|
| **G** | report bytes | grader | Given identical semantic evidence, how stable is the grader? |
| **R** | architectural evidence | reflector | Given identical architecture, how stable is the reflector's reading? |
| **E** | architectural evidence | reflector, then one fresh grade | What a user of the instrument actually experiences |

Layer E is Layer R's reports graded once each. Layer G is what makes E interpretable: without it,
E's dispersion cannot be attributed.

## Operational term

**Test-retest under frozen Proofbound configuration.** VIM's *repeatability condition* requires the
same procedure, operators, measuring system, operating conditions and location, replicated over a
short period. This run satisfies all of those it can: identical prompt bytes, identical model
identifiers, one machine, one harness version, one short window. It fails one, and the failure
cannot be repaired here — **the provider serves a model behind an alias and exposes neither
temperature nor seed** (`opencode run` has no such flag). What is served under
`opencode/big-pickle` on this day is not pinnable, so the claim is repeatability *under the
configuration Proofbound can actually freeze*, not laboratory repeatability. The V1↔V2 historical
comparison spans days and is weaker still: that is **intermediate precision**, and it is reported
separately for exactly that reason.

## Layer G — grader repeatability

**Anchors:** the six frozen reports in `anchors/`, selected by the rule recorded in
`anchors/manifest.json` — one per outcome class, plus both sides of the two instances whose
judgement changed between V1 and the byte-identical V2 untreated rerun. Selected before any
repeated grading existed, so none could have been chosen for looking unstable.

**N = 15 independent grades per anchor. 90 grader calls.**

Fifteen rather than the three that repeated-judging studies commonly use, because those studies
average over hundreds of items and this one deliberately has six. With six non-representative
anchors, the per-anchor distribution *is* the result, and fifteen repeats distinguish 15/15 from
11/15 from 8/15 well enough to act on. A 20% per-call flip rate has a 96% chance of showing at
least one flip in fifteen draws, and a 5% rate has a 54% chance — so a clean 15/15 is meaningful
evidence of stability and not merely a small sample.

**Held identical across repeats:** report bytes, property text, grader prompt, grader model,
provider, harness version, timeout, machine. Each call is a separate `opencode run` process with
no session continuation, so no repeat can see another.

## Layer R and E — reflector repeatability

**Anchors:** six retained V1 implementation instances, two per state — for each state, the
instance whose judgement changed between V1 and the V2 untreated rerun, and one whose judgement
did not.

| Instance | State | V1 | V2 untreated | Why |
|---|---|---|---|---|
| `state-a-1788834064346` | a | upheld | upheld | historically stable sound |
| `state-a-1788835442112` | a | upheld | false-degradation | reversed |
| `state-b-1788834477264` | b | upheld | upheld | stable alternative-good |
| `state-b-1788836383405` | b | false-degradation | upheld | reversed |
| `state-c-1788834970624` | c | missed | missed | stable, and stably wrong |
| `state-c-1788835274286` | c | recognised | missed | reversed |

**N = 10 fresh reflections per instance. 60 reflector calls, each graded once — 60 grader calls.**

Ten rather than fifteen because a reflector call costs roughly five times a grader call, and
because breadth was already spent: six instances at ten repeats is a better reliability
measurement than twelve instances at five. Repetition of the same measurand is the point;
architectural variety is not.

**Held identical across repeats:** before-tree, diff bytes, accepted intent, future-change
contract, the untreated V1 craft prompt verbatim, model, provider, harness, timeout, machine.
**No question routing.** No prompt change. Fresh process per call.

## Separating reflector variance from grader variance

Layer E confounds them by construction. The decomposition is:

- Layer G gives the grader's flip rate on fixed text.
- Layer R gives the reflector's conclusion stability, established **without** a second stochastic
  judge — by human coding against the rubric below, performed after the raw run is frozen.
- Layer E is what the two produce together.

Adding a second model to compare reports would create a third measurement problem rather than
solve one. Human coding is bounded, auditable, and explicitly analysis-only: it never overrides a
grader output, never becomes ground truth, and never enters the benchmark.

## Human coding rubric — declared before reading any repeated report

Each reflector report is coded on three axes, from the report text alone, blind to its grade:

1. **Conclusion on the property.** Does the report assert that provider-specific concerns reach
   outside the delivery boundary, or that adding a provider forces unrelated parts to change?
   → `asserts-breach` / `asserts-sound` / `observes-without-concluding`.
2. **Concentration observation.** Does the report state where provider knowledge sits after the
   change? → `names-location` / `absent`.
3. **Endorsement.** Where the report names a concentration, does it treat it as appropriate?
   → `endorses` / `criticises` / `neither`.

Axis 1 is the reflector's conclusion; axes 2 and 3 exist because V2 showed a report can name the
concentration precisely and still endorse it. Prose quality, length, file citations and style are
**not** coded. A report that genuinely does not resolve on an axis is coded `ambiguous` and
reported as ambiguous, never forced.

## Interpretation categories — declared before any outcome is seen

No threshold like "90% is reliable". These are descriptions, chosen to be falsifiable against the
size of effect Proofbound wants to interpret:

- **High observed repeatability.** Nearly every repeat of an identical measurement yields the same
  conclusion, and per-anchor disagreement is rare relative to the effects the instrument is used
  to detect.
- **Material variance.** Repeats of an identical measurement change conclusion often enough that a
  treatment effect of the size V2 tried to detect could not be distinguished from measurement
  noise.
- **Severe instability.** No dominant conclusion on important anchors, or substantial bidirectional
  flipping.

The category is chosen by comparing observed per-anchor dispersion against the treatment effects
Proofbound has actually attempted, not against an imported threshold.

## Analysis plan

Per anchor: exact outcome counts, modal outcome, modal share, number of distinct outcomes, parse
failures, call failures, and order of results. Across anchors: per-anchor figures first,
aggregates second and only as description. Missing measurements are reported as missing and never
counted as a semantic outcome. No composite score, no ranking, no reliability state, no
confidence interval that would imply a population these six anchors do not represent.

## Pre-registered consequences

The location of the variance chooses the next milestone, and the mapping is fixed now so the data
cannot choose it after the fact:

- Grader stable, reflector unstable → the semantic evaluator is the reliability problem.
- Reflector stable, grader unstable → measurement of reflector output is the problem; calibrate or
  decompose the grader before touching craft reasoning.
- Both unstable → the semantic evaluation stack needs reliability design before any V3.
- Both individually stable, end-to-end unstable → interaction, context or harness effects.
- Both sufficiently stable → return to validity with a pre-registered criterion.

## Explicitly not done here

No missing criterion added. No question routing. No property decomposition. No prompt change to
reflector or grader. No temperature or sampling change. No ensembling or majority voting. No model
comparison. No production routing. No reliability state persisted anywhere.
