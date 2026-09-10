# MLR-C3D — DeepSeek V4 Flash headroom qualification, pre-registered

Written and committed **before the first semantic call against the MLR fixture under this model**.
A new model is a new experimental condition, so this is a new series with its own identity — not a
repair of, resume of, or continuation from the Nemotron work.

## 1. Why this is a new experiment

The Nemotron paired run ended `MLR PAIRED EXPERIMENT INVALID`: three pairs completed and a provider
outage took the other five. The design did not fail; the run did. But the response is **not** to
re-run the same experiment under a different model, because model is part of the configuration. What
Nemotron established about *DeepSeek* is nothing at all.

In particular, **DeepSeek has not been shown to have MLR headroom.** Nemotron's `full` runs read the
implementation in 6 of 6 correct executions; whether DeepSeek does is the question this qualification
exists to answer, and it must be answered before any `contract` call is bought.

No Nemotron execution may become a sample here, and nothing here may be pooled with one.

## 2. Model configuration — frozen

| | |
|---|---|
| provider | `deepseek`, OpenCode's native integration |
| requested model | `deepseek/deepseek-v4-flash` |
| documented version | `DeepSeek-V4-Flash-0731` — docs read 2026-09-09 |
| provider-observed identity | `deepseek-v4-flash`, provider `deepseek` (verified in session telemetry) |
| thinking | **enabled** — the provider default, set deliberately rather than inherited |
| reasoning effort | **`high`** — passed as `--variant high`, and confirmed present in telemetry as `variant: high` |
| sampling | **not controllable**; see §3 |
| context | 1M documented |
| experiment id | `mlr-deepseek-v4-flash-high-full-headroom` |

**What can and cannot be frozen.** `deepseek-v4-flash` is a moving API alias, not an immutable
weights identifier, and this pre-registration does not pretend otherwise. What is bound is the
requested alias, the documented version at the time of writing, and the identity the provider
actually returns — recorded separately, so that if the alias moves later, evidence gathered before
the move is not silently reinterpreted. Every run records the observed identity, and a run whose
transcript shows more than one model is incomplete by construction.

**If the documented or observed identity changes between this qualification and any paired run,
that is a stop, not a detail.**

## 3. Sampling parameters cannot be frozen, and that is recorded rather than papered over

DeepSeek documents that thinking mode **does not support** `temperature`, `top_p`,
`presence_penalty` or `frequency_penalty` — setting them raises no error and has no effect. Thinking
is enabled here, so there are no sampling parameters to freeze. The honest statement is that
generation is not deterministic and cannot be made so through the API, which is why repeated fresh
executions remain necessary. Any claim of controlled sampling would be false.

## 4. Why `high` rather than `max`

DeepSeek documents `high` as the default effort and describes it as the setting for *daily agent
tasks*, with `max` for more complex scenarios. DeepSeek's own coding-agent benchmark configuration is
reported to use `max`.

Proofbound is not reproducing a vendor benchmark. The question here is how Proofbound's pipeline
behaves under a capable, representative, frozen configuration, and `high` is the configuration an
ordinary agent deployment would get. It is also cheaper, which matters when the alternative buys
nothing the question needs.

**This choice is made now, from model-level reasoning, and is frozen.** It will not be revisited
because a run failed to read the implementation — tuning effort until the desired headroom appears
would fit the configuration to the wanted result.

## 5. Compatibility, already qualified

A bounded synthetic task — not the MLR fixture — confirmed the mechanics before any fixture exposure:
the model resolved, tool calling worked across `read`, `edit` and `bash`, a real bug was fixed, the
test suite was run and passed, and telemetry recorded 4 model calls, 5 tool calls, usage, identity
and `variant: high`. Cost: **$0.0018** derived, **$0.0011** by OpenCode's own figure.

That check is infrastructure qualification. Its cost is accounted separately from the experiment's.

## 6. Pricing — verified, and derived rather than stored

Read from `https://api-docs.deepseek.com/quick_start/pricing` on **2026-09-09**, price identity
`deepseek-2026-09-09`, USD per 1M tokens:

| | cache hit | cache miss | output |
|---|---|---|---|
| off-peak | $0.007 | $0.22 | $0.66 |
| peak | $0.014 | $0.44 | $1.32 |

Peak is **01:00–04:00 and 06:00–10:00 UTC, Monday to Friday**; everything else is off-peak.

**Cache accounting, measured not assumed.** The smoke probe returned `total = 7380` with
`input = 5714`, `output = 2`, `cache.read = 1664` — which sum exactly. The reported input count
therefore **excludes** cached tokens on this provider, so input is billed at the miss rate and cache
on top at the hit rate.

**Two cost figures are retained, and neither replaces token counts.** OpenCode reports a cost of its
own; on the smoke probe it disagreed with the published rates ($0.0011 against $0.0018 derived). Raw
usage is the primary historical evidence; both cost figures are interpretations of it, each labelled
with where it came from. Each attempt is priced by the window its own start timestamp falls in, so a
series crossing 04:00 UTC is not costed at one rate.

## 7. Cost forecast, before spending

From the 14 valid MLR executions already recorded (Nemotron), used only as a **token envelope** for
planning — never as evidence about DeepSeek:

| | per run |
|---|---|
| median, off-peak | $0.051 |
| largest observed, off-peak | $0.080 |
| median, peak | $0.102 |
| largest observed, peak | $0.160 |

At N = 5, the conservative total is **$0.40 off-peak** or **$0.80 peak**, using the largest observed
run for every sample. DeepSeek at `high` effort may consume more than Nemotron did — thinking tokens
are billed as output — so the ceiling below carries margin beyond that.

## 8. Hard spend ceiling — $2.00

Fixed before the first call. It is a safety bound, not a target.

Enforcement is **before launching each slot**: if the derived spend so far plus a $0.20 reserve would
exceed the ceiling, the slot is not started and the refusal is recorded. A trajectory is never cut
short for money, because truncating difficult runs selectively would change the correctness
distribution — the quantity everything else is gated on.

**Is the spend worth it?** It buys the answer to *does DeepSeek naturally read the implementation*,
which decides whether a paired experiment costing roughly ten times as much should be bought at all.
At two dollars, for a decision that gates the entire remaining programme, yes.

## 9. Budget — N = 5, fixed

The decision is coarse — is there source-access headroom under this model — and cost is not the
binding constraint at these amounts. Two things set the number. A null result needs to mean
something: at N = 5 the rule of three bounds an unobserved read rate below roughly 60%, which is weak
but honest, and more samples buy precision the proceed/stop decision does not need. And the
attribution audit needs **trajectory diversity**, because a new model may reach for routes Nemotron
never used — under Nemotron the `help()` route that disqualified an earlier instrument appeared in
exactly one run of six. Five independent trajectories is a reasonable floor for that.

**No adaptive extension. No outcome-based reruns.** An attempt invalid for setup or harness reasons
is re-run into a fresh attempt, bounded at three, and every record is retained.

## 10. What is run, and what is not

`full` only. **No `contract` call is made under this model until headroom is established**, because a
`contract` sample costs money and cannot answer whether `full` naturally uses the representation the
treatment would remove.

The frozen external task, oracle v2, attribution `mlr-context-2`, profile `profile-1`, implementer
role, `--auto`. The task, contract, module, application and gate are unchanged from the Nemotron
series — the fixture is not adjusted to encourage headroom under a new model.

## 11. Provider precondition

A health probe runs before the series: one trivial call, outside the fixture, in a throwaway
database. If the provider is unavailable, no semantic slot is spent discovering it. This does not
promise availability for the next slot — an outage beginning mid-series still costs the slot it
interrupts — it only stops the series from opening into a dead endpoint, which is what consumed
twenty-five launches last time.

## 12. Interpretation categories — declared before any call

Over **correct** runs only; failed runs are reported as cost and process evidence.

| category | operational rule |
|---|---|
| **Strong headroom** | at least 3 of the correct runs consume implementation source, and the median unique source bytes over correct runs is ≥ 1,000 |
| **Limited headroom** | some correct runs consume source, but fewer than 3 do, or the median is between 200 and 1,000 bytes |
| **No demonstrated headroom** | at most one correct run consumes any source, or the median is below 200 bytes |
| **Correctness inadequate** | fewer than 3 of 5 runs correct |
| **Attribution requires revision** | any material implementation representation reached model history through a route attribution v2 did not classify |
| **Oracle invalid** | oracle v2 rejected a product-correct implementation arrangement |
| **Pilot invalid** | model identity changed mid-series, telemetry incomplete on a completed attempt, or provider failure prevented the budget being spent as declared |

200 bytes is below the smallest file in the module (395); 1,000 is a substantial fraction of
`_store.py` (2,200). Both are local to this qualification, carried over from the Nemotron pilots so
the two are readable against each other — which is not the same as pooling them.

**Only "strong headroom", with a clean attribution audit and adequate correctness, authorises
designing a paired experiment. Nothing here authorises running one.**

## 13. Contamination rule

Once the first call is made, the fixture, task, contract, module, application, oracle, role prompt,
attribution rules, metric definitions, model, thinking mode and reasoning effort are frozen for this
series. A defect found afterwards creates a new identity; it is never repaired in place while the
series continues.
