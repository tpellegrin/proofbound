# MLR paired calibration under DeepSeek V4 Flash — pre-registered, not executed

Frozen after MLR-C3D-R requalified the instrument. **No `contract` call has been made under any
model.** Paired N is therefore chosen with no treatment outcome in view, which is the point.

## 1. Question

> On correct executions of the external task, does removing direct implementation-source visibility
> reduce the implementation-source representation entering reasoning, without reducing correctness,
> and without merely causing comparable reconstruction of implementation detail through runtime
> introspection?

Unchanged in substance from the Nemotron freeze. The model changes; the scientific property does not.

## 2. Treatment

**Identical in both arms:** application, task, public contract, public docstrings, compiled runtime
and digest, interpreter pin, oracle v2, role protocol, permissions, tooling, executor, model,
thinking mode, reasoning effort, attribution and profile versions, and every observer-isolation
property — the isolation must not itself become a treatment.

**Different in exactly one way:** `full` carries a readable copy of the module's source at
`third_party/objectstore-1.4.0/`; `contract` does not. No instruction differs, and `contract` is
never told it should not need internals.

**Repository topology is not equalised.** `full` contains the source files and `contract` does not,
so traversal reveals a structural difference. That is part of source availability as the design
intends it, and it is reported as `implementation-metadata` rather than folded into source. Making
the topologies identical with opaque placeholders would be a different treatment and is not adopted.

## 3. Correctness

Oracle v2 unchanged: the hidden gate passes **and** the service's own suite passes. Recorded beside
it as evidence, never as pass conditions: whether the contract document, the vendored copy and the
runtime are unchanged, and which oracle judged the run.

## 4. Primary comparison

> Unique bytes of direct implementation-source representation consumed on **correct** runs, per arm.

Unchanged, and now measurable across replay and copy routes. `contract` will normally be zero here by
treatment; what makes the comparison worth making is whether correctness held and whether `contract`
rebuilt the interior another way.

## 5. Representation vector — reported, never summed

Source unique and delivered, by delivery route · runtime-derived unique · metadata references and
names · public contract and docstrings · application · behaviour · harness · **unresolved** · items
attributed by lineage · disclosure items and names · model calls · input, output, reasoning and cache
tokens · derived and executor-reported cost · tool calls by name and failures · measured tool
seconds · session span · derived model seconds · verification seconds · wall time · truncation and
summarisation flags.

Source bytes, disassembly characters and file-name references are different units and are never added
together.

## 6. Result families

| family | shape |
|---|---|
| **Local substitution supported** | correctness preserved; `full` consumed source materially; `contract` did not replace it with comparable implementation-derived reconstruction; total module-internal representation lower |
| **Representation shifted, not removed** | correctness preserved, but `contract` rebuilt the interior through documentation or introspection. A falsification of the stronger reading, not a success |
| **Partial reconstruction** | correctness preserved; `contract` uses some runtime representation but materially less than the source it replaced |
| **No treatment headroom** | `full`'s source use negligible in this series |
| **Implementation access materially useful** | `contract` correctness regresses and the evidence indicates implementation information mattered |
| **Public contract insufficient** | `contract` fails for want of a legitimate external fact the contract omits |
| **Measurement unstable** | run-to-run variance overwhelms interpretation |
| **Experiment invalid** | telemetry incomplete, configuration drift, oracle failure, or a material unresolved attribution affecting the question |

No architectural verdict, no scalar score. A `contract` arm cheaper *and* less correct is a tradeoff
for a person, not an improvement.

## 7. Budget — N = 6 pairs

Derived from what has been measured, with no treatment outcome in view.

DeepSeek is markedly more consistent than Nemotron on the quantity that matters: source unique was
**5,822 bytes in all eight `full` runs across C3D and C3D-R**, and correctness was **8/8**. A contrast
against an arm expected at zero by treatment needs few samples when the baseline has no spread at
all. What needs samples is **correctness**, where an 8/8 baseline leaves little resolution, and
**runtime reconstruction**, whose spread is wide — 1,003 to 62,940 bytes.

Six pairs give twelve executions: enough that a single `contract` correctness failure reads as
one-in-six rather than as noise, and enough to see whether heavy reconstruction is typical or
occasional. More would buy precision the interpretation categories do not use.

**Cost.** At the observed $0.027–$0.035 per run: expected **≈ $0.37 peak**, **≈ $0.19 off-peak**;
conservative at the observed maximum **≈ $0.42 peak**. **Hard ceiling $1.50**, enforced before each
slot with a reserve; a trajectory is never cut short for money. Running off-peak is legitimate cost
control provided the model version has not moved and both arms stay inside one pricing regime where
feasible — cheaper pricing never outranks experiment identity.

**No adaptive extension, no outcome-based reruns.** An attempt invalid for setup or harness reasons is
re-run into a fresh attempt, bounded at three, and every record retained.

## 8. Identity

fixture revision · arm identities · runtime digest · public contract · public API surface · task ·
oracle v2 · executor · source-visibility treatment · provider and requested model
(`deepseek/deepseek-v4-flash`) · documented version `DeepSeek-V4-Flash-0731` · observed identity ·
thinking enabled · effort `high` · attribution `mlr-context-3` · profile `profile-1` · price identity
· ordering · paired N. Changing any of these creates a new experiment; resume refuses across any.

**If the documented or observed model identity changes before execution, this pre-registration does
not apply.** A moving alias is not the same model because the price is convenient.

## 9. Order and non-splicing

All slots and arm order generated before execution, rotating per repeat so neither arm leads. **No
C3D, C3D-R or Nemotron execution may become a paired sample** — all are development evidence with
their own identities, and the paired run collects fresh evidence in both arms.

## 10. Strongest supportable claim, and its limits

> For this task, domain, fixture, executor and DeepSeek configuration, direct source access provided
> no material correctness benefit, and successful `contract` runs used a smaller module-internal
> representation without reconstructing it comparably by another route.

It could **not** support that the boundary *caused* it — one architecture cannot separate boundary
quality from documentation quality; that implementation knowledge is never required; that modularity
is better; that less context helps agents; or anything about another model or domain. The internal
control remains unbuilt, so even a clean result shows source substitution for this external task, not
that the boundary separates external from internal responsibilities.
