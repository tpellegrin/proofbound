# MLR paired calibration — `full` against `contract`, pre-registered

Frozen before any `contract` call. **No paired call has been made.** Written after MLR-C3R
established that the instrument is valid and that fresh `full` runs consume implementation source in
every correct execution.

## 1. The question

> On correct executions of the external task, does removing direct implementation-source visibility
> reduce the implementation-source representation entering reasoning, without reducing correctness,
> and without merely causing comparable reconstruction of implementation detail through runtime
> introspection?

The third clause is the one MLR-C3 taught. Without it the question is answerable by an arm that
rebuilt the interior through `help()` and read as a success. It is narrower than *does modularity
help* and weaker than *is implementation knowledge unnecessary*, and both deliberately: the treatment
manipulates source **visibility**, because that is what the mechanics isolate. The interior remains
reachable through the live object in both arms.

## 2. Experimental unit

`fixture revision × external task × repeat × arm`, `full` and `contract` paired on the repeat, one
fresh execution per slot. Pairing controls task and fixture variance; it does not create statistical
independence, and no test assuming independence is applied.

## 3. Treatment

**Identical:** application, public contract, public docstrings and signatures, compiled runtime and
its digest, interpreter pin, task text, oracle v2, role protocol, permissions, tooling, executor,
model, telemetry and profile versions.

**Different, in exactly one way:** `full` carries a readable copy of the module's source at
`third_party/objectstore-1.4.0/`; `contract` does not. No instruction differs, and `contract` is
never told it should not need internals.

## 4. Correctness — the guardrail

Deterministic, no grader: hidden gate `external_test_v2.py` passes **and** the service's own suite
passes. Recorded beside it as evidence, never as pass conditions: whether the contract document, the
vendored copy and the runtime are unchanged, and which oracle version judged the run.

## 5. Primary comparison

> Unique bytes of direct implementation-source representation consumed on **correct** runs, `full`
> against `contract`.

`contract` will normally be zero here by treatment. That alone establishes only that source
representation was removed. What makes the comparison worth making is what is reported with it:
whether correctness held, and whether `contract` rebuilt the interior another way.

## 6. Resource vector — reported, never collapsed

Product correctness · regression correctness · unique and delivered implementation-source bytes ·
unique implementation-runtime bytes by route (documentation, introspection, disassembly) · disclosure
bytes and names · public contract and docstring bytes · application bytes · harness bytes · model
calls started and finished · input, output, reasoning and cache tokens · provider cost · tool calls
by name and failed calls · measured tool seconds · session span · derived model seconds ·
verification seconds · harness wall time · truncation and summarisation flags.

## 7. Result families, declared in advance

| family | shape |
|---|---|
| **Local substitution supported** | correctness preserved; `full` consumed implementation source materially; `contract` did **not** replace it with comparable implementation-derived reconstruction; total module-internal representation is lower |
| **Representation shifted, not removed** | correctness preserved, but `contract` rebuilt the interior through documentation or introspection. Source hiding changed the retrieval form, not the dependence. **A falsification of the stronger reading, not a success** |
| **No treatment headroom** | `full`'s source use is negligible in this series; nothing was available to remove |
| **Implementation access materially useful** | `contract` correctness regresses and the evidence indicates implementation information mattered |
| **Public contract insufficient** | `contract` fails for want of a legitimate external fact the contract omits — a contract defect or a leaky boundary, diagnosed from what successful `full` runs read |
| **Measurement unstable** | run-to-run variance overwhelms interpretation |
| **Experiment invalid** | telemetry incomplete, configuration drift, or an oracle failure |

No architectural verdict, no majority vote, no score. A `contract` arm that is cheaper *and* less
correct is a tradeoff for a person, not an improvement.

## 8. Budget — N = 8 pairs, fixed

Derived from C3R's measured variation, not convention. Correct-run source consumption across six
`full` runs was 2,761 / 4,797 / 4,797 / 6,543 / 7,204 / 7,204 bytes — a median of 5,670 with a spread
of roughly 4.4 kB, and `full` correctness was 6/6 across C3R and 5/6 across C3 under a stricter
oracle. The primary comparison is against a `contract` arm expected at or near zero by treatment, so
the source contrast does not need many samples; **correctness is the quantity that needs them**,
because that is where a regression would appear and where a 6/6 baseline leaves little resolution.

Eight pairs give sixteen executions, about two hours at C3R's observed pace and no monetary cost on
this model. It is enough that a single `contract` failure is visible as one-in-eight rather than
dismissible, and small enough not to over-sample a calibration fixture. **No adaptive extension, no
outcome-based reruns.** An attempt invalid for setup or harness reasons is re-run into a fresh
attempt and both records are retained.

## 9. Configuration identity

fixture revision · arm identities · runtime digest · public contract identity · public API surface ·
task identity · oracle v2 identity · executor · source-visibility treatment · model and provider ·
role prompt · permission flag · tool set · consumed-context definition · attribution version
(`mlr-context-2`) · profile version (`profile-1`) · ordering · paired N. Changing any of these
creates a new experiment identity, and resume refuses across any of them.

## 10. Pairing, order, resume, non-splicing

All slots and the arm order are generated before execution, rotating per repeat so neither arm
systematically leads. No adaptive slot addition, no outcome-based reruns. Resume refuses across a
changed fixture, runtime, contract, task, oracle, model, telemetry version, arm set or budget.
**No MLR-C3 or MLR-C3R execution may become a paired sample**; both pilots are development evidence
with their own identities, and the paired run collects fresh evidence in both arms.

## 11. The strongest claim this could support

> For this task, domain, fixture, executor and model configuration, direct source access to the
> module provided no material correctness benefit, and successful `contract` runs used a smaller
> module-internal representation without reconstructing it by another route.

It could **not** support: that the boundary *caused* it — one architecture cannot separate boundary
quality from documentation quality; that implementation knowledge is never required; that modularity
is better; that less context helps agents; or anything about a second domain.

## 12. What stays deferred, and what that costs

**Internal control** — a task whose responsibility lies inside the module — remains unbuilt, because
with a compiled runtime the module is a closed-source dependency in both arms. Consequence, recorded
prominently: **a successful paired result demonstrates source substitution for this external task,
not that the boundary correctly separates external from internal responsibilities.**
**Architecture controls** (alternative-good, over-fragmented) remain MLR-C4; **holdout confirmation**
in an uninspected domain remains MLR-C5. A successful first paired run validates the measurement and
the phenomenon, never modularity as a cause.
