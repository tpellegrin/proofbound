# MLR-C3D-R2 field qualification — pre-registered, not executed

Frozen before any call. **This is instrumentation validation, not effect estimation.** It is not a
paired experiment, it produces no MLR result, and no execution it collects may become a sample of one.

## 1. Question

> Under the frozen DeepSeek configuration, does the repaired attribution instrument preserve causal
> provenance and representation class across the direct-source, runtime-introspection,
> reconstruction, replay, metadata and public-contract routes that naturally occur in both arms?

Not *what does removing source do*. That question is unchanged, still unanswered, and stays that way
until a valid paired run under a new identity answers it.

## 2. Why a live run at all

The repair is already held to 1,193 items across twelve retained trajectories and to a synthetic
adversarial matrix, and both are green. Neither can produce a route nobody has thought of. The
previous instrument passed every test it had and was defeated in the field by a temporary file, so
what remains untested is exactly what testing cannot reach: an agent doing something new.

## 3. Sample — N = 3 pairs, 6 executions

Both arms, because R2 repairs `contract` behaviour specifically and a `full`-only qualification would
exercise none of it.

Three rather than two, on **route coverage**, which is an operational property of the corpus and not
a treatment outcome. Across the six `contract` runs of the invalid series, runtime introspection
appeared in five, `marshal` inspection in four, and `dir` in four; the temporary-file variant appeared
once and the verbatim reconstruction once. Two pairs would probably exercise introspection; three
make it near-certain and give the rarer routes a chance to appear. The invalid run's **outcome
distribution is not used** — not to choose N, not to set a threshold, not to shape an expectation.
Nothing here is sized to make a future result more or less likely.

**No adaptive extension.** An attempt invalid for setup or harness reasons is re-run into a fresh
attempt, bounded at three, and every record is retained. A valid failure is never re-rolled.

## 4. Frozen configuration

Everything is inherited unchanged from the invalid series except the attribution version, the runtime
identity, the oracle binding and the revision. No tuning: same model, same variant, same thinking
mode, same prompt, same role, same task, same fixture, same contract, same oracle.

| | |
|---|---|
| experiment | `mlr-deepseek-v4-flash-high-paired-r2-qualification` |
| model | `deepseek/deepseek-v4-flash`, thinking enabled, effort `high` |
| documented version | `DeepSeek-V4-Flash-0731` (docs read 2026-09-09; not re-read since) |
| observed identity | `deepseek-v4-flash` / provider `deepseek` / variant `high`, probed 2026-09-10 |
| role · permissions | implementer · `--auto` |
| oracle | `external_test_v2.py`, now bound by digest as the oracle in force |
| attribution | `mlr-context-4` — causal precedence, representation form, delivery route |
| profile | `profile-1`, unchanged |
| runtime identity | structural, over normalised code objects, with the interpreter bound |
| price identity | `deepseek-2026-09-09` |
| arms | `full`, `contract`, order generated before execution and rotating |

**If the observed or documented model identity has moved when execution begins, this
pre-registration does not apply.**

## 5. Cost ceiling — $0.45

Derived, not inherited. Six executions at the largest single run observed in the invalid series
($0.0596 derived) is $0.36; the median pair of arms would be about $0.19. The ceiling is **$0.45**,
checked before each slot with a reserve. The $1.50 of the paired series is not carried over: a
qualification that costs like an experiment is not a qualification.

Raw provider usage stays primary and money stays derived. The ~3× gap between derived and
executor-reported cost is unresolved and is **not** in scope here.

## 6. Pass criteria — all twelve, frozen before any call

1. No material attribution escape: no inbound item carrying material implementation representation
   outside an implementation origin.
2. No source over-attribution from a directory or path mention.
3. `contract` direct-source provenance is **0**, unless an actual source-boundary violation occurs —
   in which case it is a finding and the qualification still passes on this criterion.
4. Runtime representation materialised through a file and read back remains runtime-derived.
5. Source-equivalent text produced by the model remains distinct from direct source.
6. Metadata stays in its own unit and is never summed into source or runtime.
7. Public contract and docstring representation stays separate.
8. `unresolved` is 0 for treatment-relevant material representation, unless a genuinely new and
   ambiguous route appears — which is itself a finding and is reported as one.
9. Observer isolation stays symmetric: no oracle, instrument, prior-sample or partner-output marker
   reaches either arm, and control-plane paths appear in both or neither.
10. Model and configuration identity stay stable across all six executions.
11. The oracle judges every run and rejects nothing that is product-correct.
12. Runtime structural identity is a single value across all six materialisations.

Correctness is recorded and is **not** a pass criterion: this run is not measuring whether the task
gets done.

## 7. If a new route defeats the instrument

Stop. Do not patch and continue inside this identity. The verdict is
**`MLR R2 ATTRIBUTION REQUIRES FURTHER REVISION`**, every record is retained, and the repair happens
under a further identity. Silent repair after the first semantic call is the failure mode this
programme has already paid for twice.

## 8. What this cannot establish

That the instrument is correct — only that it was not defeated by six more trajectories. That the
treatment does anything. That DeepSeek generalises. That the boundary is why anything happened. The
internal control is still unbuilt, the second domain is still unbuilt, and cross-model replication is
still unbuilt.

A pass licenses exactly one thing: freezing a new paired experiment under a new identity.
