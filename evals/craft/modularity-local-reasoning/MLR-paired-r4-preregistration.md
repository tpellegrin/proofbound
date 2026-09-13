# MLR DeepSeek FULL/CONTRACT paired experiment — frozen, not executed

The measurement stack is field-qualified and frozen. This asks the modularity question itself, for
the first time on a stack that has survived real model-driven execution end to end.

**Not executed.** Freezing it is the last act of the qualification milestone; running it is the whole
of the next one.

## 1. Question

> On correct executions of an engineering task outside module M, does removing direct visibility of
> M's implementation source reduce the implementation-source representation entering reasoning,
> without reducing correctness, and without merely causing comparable reconstruction of
> implementation detail through other routes?

Unchanged in substance since the first paired freeze. What has changed is that the instrument that
would answer it is now qualified rather than assumed.

## 2. Identity — `mlr-deepseek-v4-flash-high-paired-r4`

New. Never a resumption of the invalid Nemotron series, the invalid DeepSeek paired series, or any
qualification identity.

| | |
|---|---|
| source | `1f83c3b1f22ab756` |
| task | `eb24429a46ecad4c` |
| public contract | `af3d3e9be15b51ed` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| attribution | `mlr-context-5` |
| profile | `profile-1` |
| semantic boundary | `b88bd43109184459` |
| hermeticity rule | `dcbf34fb63821980` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| price identity | `deepseek-2026-09-09` |
| attempt path | `run_bounded_attempt` — construct, stage, preflight, launch inside the view, extract, destroy, grade outside |

## 3. Treatment

Identical in both arms: application, task, public contract, docstrings, compiled runtime and its
structural identity, interpreter, oracle, role, permissions, tooling, executor, model, thinking mode,
effort, attribution, profile, boundary policy, hermeticity rule, credential mechanism, home, scratch
and session policy.

Different in exactly one way: `full` carries a readable copy of the module's source at
`third_party/objectstore-1.4.0/`, declared as its exposure and validated as such by every slot's
preflight; `contract` carries none, and its preflight asserts zero source anywhere in the view. No
instruction differs and `contract` is never told anything is missing.

**Repository topology is not equalised** — `full` contains the files and `contract` does not, so
traversal reveals a structural difference. That is part of source availability as the design intends
it, and it is reported as metadata rather than folded into source.

## 4. N = 6 pairs — twelve executions

Re-derived rather than inherited, and independent of anything the qualification observed.

The original rationale was formed before any `contract` outcome existed and still holds. The quantity
the primary comparison turns on has no spread in the arm that has it: DeepSeek's `full` direct-source
figure was invariant across every run in which it was measured. A contrast against an arm that is
zero by treatment needs few samples when the baseline does not move.

What needs samples is the two quantities with the least resolution. **Correctness**, where a run of
successes leaves almost none — six pairs make a single `contract` failure read as one-in-six rather
than as noise. And **runtime reconstruction**, whose spread has been wide wherever it has been
measured — six pairs are enough to see whether heavy reconstruction is typical or occasional.

More would buy precision the result families do not use. Fewer would leave a single correctness
failure uninterpretable.

**The qualification's arm differences are not used.** Not for N, not for a threshold, not for an
expectation. It observed four trajectories to check an instrument, and four trajectories cannot size
anything.

## 5. Order

Generated before execution by the established rotating generator, so neither arm leads every pair:

```
pair 1: full · contract      pair 4: contract · full
pair 2: contract · full      pair 5: full · contract
pair 3: full · contract      pair 6: contract · full
```

Taken from the established generator rather than written by hand, so the order in this document is
the order the runner will produce.

No adaptive ordering. No arm chosen from what the previous one did.

## 6. Lifecycle and failure

Per slot: fresh view · stage · hermeticity preflight · launch only if clean · execute · checkpoint and
extract · destroy · grade control-side · attribute · profile.

Infrastructure attempts — construction, staging, preflight refusal, provider unreachability, launcher
failure — retry the same slot, bounded at three, and every attempt is retained. A semantic trajectory
that began is never re-rolled: not for correctness, not for cost, not for how much it read, not for
how it read it. If the provider route degrades, a neutral health probe decides whether to retry, and
an unhealthy route stops the series rather than spending slots against it.

## 7. Budget — $0.50

Twelve trajectories at the qualification's mean of $0.0141 is $0.17; at its maximum of $0.0168, $0.20.
The ceiling is **$0.50**, checked before each slot with a $0.05 reserve — generous enough that no
trajectory is ever truncated for money. Raw usage stays primary and money stays derived; the
executor-reported figure is retained beside it and the discrepancy between them remains unresolved
and out of scope.

## 8. Primary measurand

> Unique bytes of direct implementation-source representation consumed on **correct** runs, per arm.

Unchanged. "Direct" means bytes whose causal ancestry includes readable implementation source made
available to the arm — not disassembly, not runtime names, not file names, not source-form text the
model reconstructed from something else.

## 9. Reported beside it, never summed

Source unique and delivered, by route · runtime-derived representation · source-equivalent
reconstruction · implementation metadata · public contract · application · behaviour · harness ·
model-derived · unresolved · contradictions · uncovered events · by form · by basis · model calls ·
input, output, reasoning and cache tokens · tool calls by name and failures · tool seconds · session
span · verification seconds · executor-reported and derived cost · truncation and summarisation flags.

Source bytes, disassembly characters and file-name references are different units and are never added
together.

## 10. Result families

| family | shape |
|---|---|
| **Local source substitution supported** | correctness preserved; `full` consumed source materially; `contract` did not replace it with comparable implementation-derived reconstruction |
| **Representation shifted, not removed** | correctness preserved, but `contract` rebuilt the interior through another route at comparable or greater volume |
| **Partial reconstruction** | correctness preserved; `contract` reconstructs materially less than the source it replaced |
| **No treatment headroom** | `full`'s source consumption negligible across the series |
| **Implementation access materially useful** | `contract` correctness regresses and the evidence indicates implementation information mattered |
| **Public contract insufficient** | `contract` fails for want of a legitimate external fact the contract omits |
| **Measurement unstable** | run-to-run variance overwhelms interpretation |
| **Experiment invalid** | telemetry incomplete, configuration drift, oracle failure, boundary failure, or a material unresolved attribution affecting the question |

No architectural verdict and no scalar score. An arm that is cheaper *and* less correct is a tradeoff
for a person, not an improvement.

## 11. Stop conditions

Uncontrolled source availability · oracle, reference or prior-sample leakage · a boundary bypass · a
material attribution escape · an uncovered model-visible event · material unresolved attribution · a
contradiction indicating an instrument defect · cross-slot contamination · model identity
inconsistency · session extraction failure. Preserve the evidence and repair under a new identity; do
not patch and continue.

Do not stop for ordinary model behaviour, and do not stop because a result is emerging.

## 12. What it will not be able to claim

That the boundary is *why* anything happened — one architecture cannot separate boundary quality from
documentation quality, and the internal control remains unbuilt. That implementation knowledge is
never required. That modularity is better. That less context helps agents. Anything about another
model, another task, another domain, or production scale.

## 13. The stack is frozen

Fixture, task, contract, runtime, oracle, attribution, profile, semantic boundary, hermeticity rule,
executor, provider and model configuration, credential mechanism, extraction and attempt accounting
are held. Absent a concrete defect found by the experiment itself, none of them moves again. That is
what makes the result mean something.
