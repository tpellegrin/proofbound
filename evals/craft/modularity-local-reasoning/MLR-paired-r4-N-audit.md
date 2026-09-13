# Pre-execution audit of the N = 6 decision in `mlr-deepseek-v4-flash-high-paired-r4`

One question: was N chosen from evidence available before the R4-C3 qualification, or did the
qualification's arm observations influence it?

**Answer: independently justified.** The experiment is unchanged and remains frozen as committed. Two
statements in its rationale are corrected here, neither of which bears on N.

This note changes no experiment semantics. N stays six pairs, the order stays, the measurand stays,
the result families stay. The preregistration is left byte-identical; nothing is rewritten.

## 1. Chronology

| when | what |
|---|---|
| 2026-09-09 23:53 | `da3468a` freezes `MLR-deepseek-paired-preregistration.md`, whose §7 is the N = 6 rationale. At this point **no `contract` slot had executed under any model** — the arm existed only as a design |
| 2026-09-10 | the first paired series runs and is invalidated by an attribution escape; its `contract` outcomes exist but are never used for sizing |
| 2026-09-13 16:02–16:09 | the four R4-C3 qualification trajectories run |
| 2026-09-13 16:15 | `4fd218e` freezes `MLR-paired-r4-preregistration.md`, restating the N = 6 rationale |

The restatement was written after the qualification. That is what makes the question worth asking
rather than assuming.

## 2. Clause-by-clause provenance

Every substantive clause of the argument is present in the 2026-09-09 freeze:

| clause in the r4 freeze | present on 2026-09-09 |
|---|---|
| a contrast against an arm that is zero by treatment needs few samples when the baseline does not move | yes |
| what needs samples is correctness | yes |
| six pairs make a single failure read as one-in-six | yes, verbatim |
| enough to see whether heavy reconstruction is typical or occasional | yes |
| more would buy precision the result families do not use | yes |

Nothing in the argument is new. The r4 document restates a rationale frozen four days and several
milestones earlier.

## 3. Which R4-C3 numbers appear at all

Two, and only two: `$0.0141` and `$0.0168`, the qualification's mean and maximum per-trajectory cost,
used in §7 to set the ceiling. Cost feasibility is a legitimate use of qualification evidence, and it
is downstream of an N that was already fixed — the ceiling was derived from twelve trajectories, not
the twelve from the ceiling.

**None of the qualification's arm observations appears anywhere in the document**: not `full`'s 5,630
bytes, not `contract`'s zero, not the 1,121 and 418 characters of runtime reconstruction, not 4/4
correctness. Checked by searching the committed text for each.

## 4. The independence test

*Could a competent researcher, using only pre-R4-C3 evidence, have chosen six for the same reasons?*

They did. On 2026-09-09 the available evidence was eight `full` runs across C3D and C3D-R at 5,822
bytes each with 8/8 correctness, and a runtime-reconstruction spread of 1,003 to 62,940 bytes — all of
it from the arm that was then the only one ever executed. The reasoning ran: the primary quantity has
no spread in the arm that has it, so the contrast needs few samples; correctness and reconstruction
are the quantities with the least resolution; six paired opportunities are what the descriptive result
families can use.

That argument stands on its own evidence and needs nothing from the qualification.

## 5. Two corrections to the prose

**The invariance claim is over-generalised, and false as written.** The 2026-09-09 text said *"5,822
bytes in all eight `full` runs across C3D and C3D-R"* — bounded, dated and checkable. The r4 text says
*"invariant across every run in which it was measured"*, which reaches forward into the qualification,
where the figure was **5,630**. The generalisation is therefore wrong, and wrong precisely because it
sweeps in runs the argument does not need. It is also a comparison across instrument versions: 5,822
was measured under `mlr-context-3` and 5,630 under `mlr-context-5`, a difference the R4-C3 outcome
already records.

> **Read instead:** DeepSeek's `full` direct-source figure was 5,822 bytes in all eight runs measured
> under `mlr-context-3` across C3D and C3D-R. That is the evidence the sample budget rests on. What
> the qualification measured is not part of it and is not claimed to agree with it.

**The appeal to "noise" is not defensible, and was not defensible in September either.** Both freezes
say a single `contract` failure would *"read as one-in-six rather than as noise"*. Six paired
opportunities give an **observational resolution of one in six**. They do not distinguish a failure
from chance variation, and no result family in either document uses a noise model, a threshold or a
significance claim — so nothing downstream depends on the sentence. It should not stand as written.

> **Read instead:** six pairs give twelve executions and an observational resolution of one in six on
> correctness counts, and enough replication to show whether heavy runtime reconstruction is typical
> or occasional. They support the descriptive result families and nothing finer.

Neither correction changes N. The first removes a claim the argument never required; the second
narrows what six pairs are said to provide, and six was already chosen for the descriptive resolution
that narrower statement describes.

## 6. Outcome

`mlr-deepseek-v4-flash-high-paired-r4` is unchanged, still frozen, and ready to execute. Its identity,
configuration, N, order, measurand, result families and stop conditions are exactly as committed at
`4fd218e`.
