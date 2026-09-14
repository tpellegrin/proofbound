# `mlr-deepseek-v4-flash-high-paired-q1` — the run

Twelve slots, twelve valid trajectories, one attempt each, no retries, no deviations.
$0.2079 of $0.50. Preregistration
[`MLR-paired-q1-preregistration.md`](MLR-paired-q1-preregistration.md), sha256
`7a6c197ed19aded9cdafd6cf64f779a77d6b92238520c872bf8c8eca19e5901e`, frozen at `9408edc`. Record:
[`craft-mlr-deepseek-v4-flash-high-paired-q1.json`](../../results/craft-mlr-deepseek-v4-flash-high-paired-q1.json).

**Result family E · Heterogeneous.**

## 1. What ran

Every frozen identity held on all twelve slots: boundary `b88bd43109184459`, hermeticity
`dcbf34fb63821980`, executor `2f24593f1b8e578d`, source `1f83c3b1f22ab756`, task `eb24429a46ecad4c`,
contract `af3d3e9be15b51ed`, runtime structure `28ba66e1cd49b157`, CPython 3.9.6,
`deepseek/deepseek-v4-flash` at effort `high`, implementer, `--auto`, attribution `mlr-context-6`.
Zero distinct values for any of them. Three neutral readiness probes at 2.77 s, 2.98 s and 2.80 s
before slot 1.

The agent was not steered. It received the frozen task and the arm's environment, and nothing else.

## 2. Validity

Preflight clean on all twelve — `full` declaring its four files and finding nothing else, `contract`
declaring and finding nothing. Unresolved items **0**, unresolved components **0**, contradictions
**0**, uncovered model-visible events **0**, in every session. Every view destroyed, every extracted
database readable afterwards, every profile complete, zero failed tool calls, zero truncated items.
Workspace digests `9053040a` for `full` and `c93d39f6` for `contract`, identical within arm and
different between — the historical values.

No stop condition fired. No slot was retried, replaced or re-rolled.

## 3. Correctness

**Six of six pairs both correct.** Twelve of twelve trajectories satisfied the unchanged hidden
oracle, run control-side on the extracted workspace. Every pair is therefore eligible for
representation interpretation under the frozen gate.

## 4. The primary measurand

> Unique bytes of direct implementation-source representation consumed on correct runs, per arm.

| pair | `full` | `contract` | pair value |
|---|---|---|---|
| 1 | 5,976 | **0** | 5,976 |
| 2 | 5,630 | **0** | 5,630 |
| 3 | 6,170 | **0** | 6,170 |
| 4 | 5,630 | **0** | 5,630 |
| 5 | 5,630 | **0** | 5,630 |
| 6 | 5,630 | **0** | 5,630 |

**Six positive, zero negative, zero tied.** Per the preregistration, per-pair values and sign counts
are the result; no mean, percentage, interval or significance test is computed, and none was
preregistered.

`contract`'s zero is not an absence of measurement. `mlr-context-6` was qualified against exactly the
failure that would have produced a false zero or a false non-zero here, and in the one `contract`
slot that reached the documentation route the 210 bytes it produced were attributed to the model, not
to the source.

## 5. Where the pairs disagree

The channel that decides between families A and B does not agree with itself.

| pair | `contract` runtime representation | `full` runtime representation |
|---|---|---|
| 1 | 19,654 | 0 |
| 2 | 36,072 | 18,142 |
| 3 | **109** | 0 |
| 4 | 39,231 | 0 |
| 5 | 31,633 | 102 |
| 6 | **102** | 0 |

Four `contract` trajectories rebuilt a great deal of the interior through disassembly and
introspection. Two solved the task correctly having reached the interior essentially not at all — 109
and 102 bytes, against 39,231 in the same arm. A 385-fold spread on the exact quantity the
interpretation turns on.

And the behaviour is not arm-determined. One `full` trajectory used **18,142 bytes** of runtime
representation while holding readable source; another used 102; four used none. Having the source did
not reliably stop the model from disassembling, and lacking it did not reliably make it start.

## 6. Why family E, and not A or B

- **C** is excluded: correctness did not regress; every pair was both-correct.
- **D** is excluded: the profiles are not close. `full` consumed 5,630–6,170 bytes of direct source
  in every pair and `contract` consumed zero in every pair.
- **A** requires that `contract` *did not* replace the source with comparable implementation-derived
  representation. False in four of six pairs.
- **B** requires that `contract` *did* rebuild the interior at comparable or greater volume. False in
  two of six pairs.
- **F** is excluded: no instrument or execution validity defect occurred.

Neither single story fits, which is the state family **E** was frozen to describe. The result stays
descriptive and per-pair, and the six pairs are reported rather than averaged into a cleaner claim.

Source bytes and disassembly characters remain different units and are never summed; the comparison
above is between pairs within the same channel, not across channels.

## 7. Resources — descriptive only

Model calls 115–178, tool calls 38–56, zero failures anywhere. Input 17,806–46,778 tokens, output
7,228–9,706, reasoning 6,014–15,135, cache reads 377,600–1,350,400. Elapsed 83–186 s. Derived cost
**$0.2079**, executor-reported **$0.1425** — a ratio of 1.46, the same unresolved discrepancy carried
through every milestone; both are retained and neither is preferred.

No resource dimension is compared between arms, and none of these figures bears on the result family.

## 8. What this supports

For **this model, this task, this fixture and this qualified harness**: withholding direct readable
implementation source while preserving the public contract and the executable runtime did not cost
correctness in any of six pairs, and removed direct implementation-source consumption entirely in all
six. What replaced it varied enormously between trajectories, in both arms, and no single
compensating pattern describes the series.

## 9. What it does not support

It does not establish that modularity is good, that information hiding reduces context, that public
contracts can replace implementations, that fewer tokens mean better engineering, that source hiding
improves agents, that DeepSeek V4 Flash represents any other model, that this fixture represents other
repositories, that the measurand is a general architecture metric, or that correctness parity on six
pairs proves the two arms' work semantically equivalent. Six pairs are six observations. No
significance claim is made because none was preregistered, and the heterogeneity in §5 is a result
rather than noise to be averaged away.
