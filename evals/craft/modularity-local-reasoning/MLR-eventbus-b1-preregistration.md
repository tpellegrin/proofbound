# `mlr-deepseek-v4-flash-high-paired-eventbus-b1` — preregistration

Frozen before any semantic call. A cross-fixture replication: the software boundary changes, the
model and the measurement system do not.

**This is a new experiment.** `mlr-deepseek-v4-flash-high-paired-q1` keeps its own result and is not
amended, resumed or pooled. This series starts at pair 1, slot 1, and its dataset contains only its
own twelve trajectories.

## 1. What q1 found, and what is being replicated

Reconstructed from q1's record, not from a summary.

**Primary, uniform.** Six pairs, all `both correct`. `full` consumed 5,976 / 5,630 / 6,170 / 5,630 /
5,630 / 5,630 unique bytes of direct implementation source; `contract` **zero in all six**; six
positive pair values.

**Secondary, not uniform.** `contract` runtime-derived representation ran 19,654 · 36,072 · **109** ·
39,231 · 31,633 · **102**, and `full` was not uniform either — one trajectory used 18,142 bytes while
holding readable source. q1's family remains **E · Heterogeneous** and is not renamed here because
its primary half was consistent.

**What this replication targets is the first of those, not the second.** The core relation is that
withholding direct readable source changes direct implementation-source consumption while
correctness is preserved. Whether the procedural heterogeneity travels is a descriptive secondary
question, not the thing being replicated.

## 2. Question

> For a bounded implementation change conceptually outside module M, when correctness is preserved,
> does withholding direct readable implementation source — while retaining a sufficient public
> contract and an executable runtime — materially change the amount and kind of implementation
> representation entering the agent's reasoning, **when the software boundary is structurally
> different from the object-storage fixture**?

Bounded to this model, this fixture, this task and this harness. It is not a claim about modularity,
about software boundaries in general, about agents in general, or about repositories in general.

## 3. The one changed scientific dimension

**The fixture.** Everything else is held fixed: model, provider, variant, effort, role, permission
flag, executor, semantic boundary, hermeticity architecture, extraction, profile, attempt
accounting, attribution semantics, correctness-gating philosophy, primary measurand, secondary
channels, N, slot-order rule, retry rules and result-family structure.

### Verified structural contrast

Checked in code, not asserted. Seven of nine probed axes differ:

| | `objectstore` (fixture A) | `eventbus` (fixture B) |
|---|---|---|
| domain | persistence | messaging / fan-out |
| caller-supplied code across the public boundary | **none** | **`subscribe(handler)`** |
| shape | predominantly 1:1 | 1:N |
| failure | total, by exception (`NotFound`) | partial, captured and normalised into a receipt |
| registration lifecycle | none | subscribe before publish |
| re-entrancy | none | events published from inside a handler are deferred |
| retry loop inside M | yes | no |
| filesystem | yes | no |
| state | durable, on disk | in-process registry |

The dependency direction is the headline: `eventbus` calls back into application code, and
`objectstore` accepts no callable on its public surface at all.

## 4. Treatment — unchanged in concept

**`full`** — the readable implementation source of `eventbus` is available.
**`contract`** — that direct readable source exposure is withheld.

Both arms keep the identical compiled runtime, the public contract, the application source, the task
and the shipped tests. `contract` continues to permit Python, `help`, `pydoc`, `dir`, `inspect`,
disassembly, tracebacks, runtime experimentation, `grep`/`find`, temporary artefacts and model
reconstruction. **The treatment is not tightened because this module uses callbacks or re-entrancy.**

## 5. Frozen stack

| | |
|---|---|
| fixture | `evals/craft/modularity-local-reasoning/fixture-b`, package `eventbus` |
| source | `9999cc1365c98e23` |
| task | `d0eb34a91a7b0935` |
| public contract | `0be8e117bbb3050c` (`docs/eventbus-contract.md`) |
| oracle | `hidden/external_test.py`, `542d27df3fff8f52` |
| vendored path in `full` | `third_party/eventbus-2.1.0` |
| **attribution** | **`mlr-context-6`** |
| profile | `profile-1` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| price identity | `deepseek-2026-09-09` |
| credential | provider auth file staged into the constructed home, destroyed with the view |
| extraction | checkpoint-aware session copy plus workspace, after destruction |

The q1 fixture and the R6 calibration tasks are **not** used here.

### Host-derived identities

Carried forward from q1's corrected doctrine. The interpreter, the semantic boundary digest and the
hermeticity rule digest all depend on the execution host — the boundary exposes the launching
interpreter, and the hermeticity rule's identity includes its absolute scan roots. On this host they
are CPython 3.9.6, boundary `b88bd43109184459`, hermeticity `23a6e8001a46b70f` (fixture B's own rule,
necessarily different from fixture A's because it protects a different module). **These are recorded
per slot as execution facts, not frozen as universal constants.** What is frozen is the rule and the
machinery that derives them; a slot that produces a different digest for the same rule on a different
host is a host difference, while a change in policy, exposure, enforcement or scan-root meaning is
stack drift and stops the series.

## 6. Why no live fixture qualification

Applying the Field Test: which untested mechanism would a semantic trajectory exercise?

Unchanged and already field-qualified: attribution semantics, causal lineage, representation forms,
the semantic execution boundary, extraction, profiling, the executor, the model configuration and
attempt accounting. New: the fixture, its module, task, contract, oracle and hermeticity payload —
and every one of those risks has been closed **deterministically**:

- `contract` contains no private module file and **no file in it carries a single line of the
  implementation**, checked by fingerprint over every readable file;
- the runtime ships only bytecode, and in **both** arms the module that executes is the compiled one;
- the only workspace difference between arms is the vendored tree, and nothing appears only in
  `contract`;
- the oracle fails the unfixed fixture, accepts two structurally distinct correct solutions and
  rejects four wrong ones, with the shipped suite green throughout;
- a source read in `full` attributes to `implementation-source` on `artifact-path`, a disassembly in
  `contract` to `implementation-runtime` with zero direct source, and the R6 docstring property
  reproduces on the new module;
- the fixture-B hermeticity preflight runs **clean in a real constructed semantic view in both arms**
  — `full` declaring its five source files, `contract` declaring nothing, zero findings either way.

Nothing is left that a model call would test and a deterministic check could not. And there is a
positive reason not to spend one: **the first eventbus trajectory should be data, not design
feedback.** Running one as a qualification and then adjusting anything would leak replication
evidence into the design.

## 7. N contamination barrier

No value q1 observed may justify N. Not its 6/6 correctness, not its six positive contrasts, not its
byte values, not its runtime spread, not its reconstruction, tokens, time, cost or tool strategies.
"q1 was stable at six, so six is enough" and "q1 was heterogeneous, so we need more" are both
forbidden: each conditions the replication's design on the discovery's outcome.

## 8. N = 6 pairs — fixed

### Audit of the pre-q1 rationale

N = 6 was frozen on **2026-09-09** (`da3468a`), when no `contract` slot had executed under any model.
Its clauses divide into two kinds, and only one kind is usable here:

| clause | fixture-independent? |
|---|---|
| the primary quantity has no spread in the arm that has it | **no** — that was an `objectstore` observation and nothing establishes it for `eventbus` |
| what needs samples is correctness | yes |
| six paired opportunities give an observational resolution of one in six on correctness counts | yes |
| enough replication to show whether a compensating pattern is typical or occasional | yes |
| more would buy precision the result families do not use | yes |
| bounded cost | yes |

The first clause is dropped. It is not assumed for fixture B, and no substitute for it is invented.

### The rationale actually used

1. **Replication design.** Holding N constant keeps the fixture the main changed scientific
   dimension. This uses q1's *design*, which was fixed before q1 ran, and not q1's *outcome*.
2. Six paired opportunities give twelve semantic trajectories and an observational resolution of
   **one in six** on correctness counts.
3. Enough repeated exposure to show whether a compensating representation pattern is typical or
   occasional, for whichever pattern this fixture produces.
4. More would buy precision the result families below do not use.

**What six does not provide:** any means of distinguishing an outcome from chance variation. There is
no noise model, no threshold, no significance test and no power calculation, and none is added
because the word "replication" appears — this programme has no parametric effect model that would
make one meaningful.

**Fixed N.** No adaptive extension, no sequential stopping. Not because a pair failed, not because
dispersion is high, not because the pattern looks nearly there, not because a result is ambiguous.

## 9. Pairs, order and unit

Twelve slots from `pb_mlr.slots(["full", "contract"], 6)`, the same generator q1 used, which rotates
the within-pair order each pair so temporal position is never identical to treatment:

| slot | pair | arm | | slot | pair | arm |
|---|---|---|---|---|---|---|
| 1 | 1 | `full` | | 7 | 4 | `contract` |
| 2 | 1 | `contract` | | 8 | 4 | `full` |
| 3 | 2 | `contract` | | 9 | 5 | `full` |
| 4 | 2 | `full` | | 10 | 5 | `contract` |
| 5 | 3 | `full` | | 11 | 6 | `contract` |
| 6 | 3 | `contract` | | 12 | 6 | `full` |

Three pairs lead with each arm. Deterministic, so there is no seed. No treatment-aware reordering
once execution begins, and no reordering after a failure.

**Unit.** experiment → pair → semantic slot → infrastructure attempt. The paired unit is the frozen
pair. A semantic trajectory that has begun is immutable. An infrastructure failure before semantic
execution begins is not a semantic sample.

## 10. Retry — q1 semantics, unchanged

Infrastructure attempts are bounded at **three per slot** and may retry the same slot; every attempt
is recorded. A completed semantic trajectory is **never** re-rolled — not for being incorrect,
expensive, representation-heavy, representation-light, or for a `full` run that never opens the
source. No eventbus-specific retry semantics are invented.

## 11. Missingness — N counts scheduled pairs

**N = 6 refers to scheduled pairs.** The denominator never moves, and the series does not run until
six valid pairs appear.

| case | rule |
|---|---|
| A · an infrastructure attempt fails before semantic execution | retry the slot, bounded at three; both records retained |
| B · all three infrastructure attempts for a slot fail | series **stops**; family **F**; completed pairs retained, no treatment inference |
| C · a semantic trajectory begins and is interrupted | accounted and preserved, contributes no measurement, **not** re-rolled; its pair is incomplete |
| D · extraction fails | **F**, series stops |
| E · material unresolved attribution, at item **or component** granularity | **F**, series stops |
| F · a contradiction or an uncovered material model-visible event | **F**, series stops |
| G · a boundary leak, uncontrolled source in `contract`, oracle/reference/prior-sample leakage, cross-slot contamination | **F**, series stops |
| H · provider, model, variant, boundary, runtime or attribution drift beyond a host-identity difference | **F**, series stops |
| I · the hidden oracle cannot grade an extracted workspace | **F**, series stops |
| J · the ceiling would be exceeded before a slot | that slot is not launched; the series ends short and reports how many pairs completed |

A validity failure invalidates or stops the experiment. It never deletes a sample so collection can
continue until six clean pairs accumulate. A pair contributes to the paired comparison only if both
its slots produced valid trajectories; incomplete pairs are reported, never replaced.

## 12. Correctness gate

Every slot is graded by the unchanged fixture-B hidden oracle, control-side, on the extracted
workspace. Pair categories, fixed now: **both correct** · **`full` only** · **`contract` only** ·
**neither**. Representation is interpreted only on pairs where both arms are correct. The rule is not
relaxed because this fixture's domain involves partial failure.

## 13. Primary measurand

> **Unique bytes of direct implementation-source representation consumed on correct runs, per arm.**

Unchanged, with "consumed" unchanged: text appearing in a part OpenCode places in the message history
before a later model call. Pair value, on both-correct pairs: `full` unique direct-source bytes minus
`contract` unique direct-source bytes, reported per pair and as a count by sign. It stays primary
whichever secondary channel looks more interesting afterwards.

## 14. Secondary dimensions — the q1 set, unchanged

Delivered direct-source bytes · implementation-runtime representation · `source_equivalent_
reconstruction` · implementation metadata · public contract · application · unresolved,
contradictions and uncovered events. **No eventbus-specific channel is added.** Source bytes,
disassembly characters and file-name references remain different units and are never summed.

`source_equivalent_reconstruction` keeps q1's corrected reading: it measures model-authored
source-equivalent text, and a non-zero value is **not** by itself evidence that hidden implementation
interior was recovered.

## 15. Resource dimensions — descriptive only

Model calls · tool calls by name and failures · input, output, reasoning and cache tokens · elapsed
and session time · tool seconds · derived model seconds · verification seconds · **executor-reported
and derived cost, both retained**. The discrepancy between the two cost figures remains unresolved
and out of scope; neither is selected because it favours an arm. No resource dimension is compared
between arms.

## 16. What counts as replication

Defined before execution, and deliberately **not** "fixture B must also be family E".

**Core phenomenon (the primary target).** On eligible pairs, withholding direct readable source
materially changes direct implementation-source consumption while correctness is preserved.

**Secondary procedural pattern (descriptive).** Whether agents compensate through variable
runtime-derived or model-authored representation, and whether that variability resembles q1's.

**Numerical equality is not required and is not expected.** `eventbus` has a different module, a
different contract and a different task, so its byte magnitudes have no reason to match q1's. The
replicable claim is a relation, not a number.

## 17. Result families — complete, mutually exclusive, fixed

Evaluated in order; the first that applies is the result.

| family | shape |
|---|---|
| **F · Invalid or stopped** | any instrument or execution validity defect under §11, including uncontrolled source reaching `contract`. No treatment inference of any kind |
| **R3 · No informational pressure** | correctness broadly preserved, but `full` itself does not materially consume the hidden source, so the treatment contrast is uninformative for this fixture |
| **R2 · Partial replication** | the direct-source treatment behaves as expected, but `contract` correctness is harmed on a meaningful portion of pairs — evidence that the phenomenon is boundary- or task-dependent |
| **R1 · Core phenomenon replicates** | correctness broadly preserved on eligible pairs, `full` materially consuming direct source and `contract` consuming none |
| **R4 · Little meaningful difference** | correctness preserved and the representation profiles of the two arms are close |

The secondary procedural pattern is reported inside whichever family applies, as **homogeneous** or
**heterogeneous**, and never changes which family is reached. No architectural verdict. **No scalar** —
no architecture score, modularity score, context-efficiency score, quality-per-token,
correctness-weighted cost or composite rank.

## 18. Cross-fixture comparison plan

Frozen now, and performed **only after** the within-fixture-B result is recorded. The two questions
stay separate: first what happened on eventbus under its own frozen experiment, then what q1 and
eventbus jointly suggest.

Compared dimensions: correctness pair categories · sign of the primary contrast per pair · presence
or absence of direct source under `contract` · whether `full` actually consumed source · the
distribution of runtime-derived representation, descriptively · source-equivalent model-authored
representation · broad trajectory strategies.

**Raw byte magnitudes are not compared across fixtures as though they were the same quantity**, and
no normalised cross-fixture scalar is invented afterwards.

## 19. Budget — $0.50 ceiling

Checked before each slot with a $0.10 reserve; a trajectory under way is never cut short for money.
Feasibility only, and downstream of an N already fixed by §8: at the published
`deepseek-2026-09-09` rates, twelve trajectories of this shape sit inside this ceiling. Cost does not
determine N and enters no treatment interpretation.

## 20. What this experiment cannot establish

Written before execution so a striking result cannot widen it. It cannot establish that two fixtures
make a phenomenon universal; that `objectstore` and `eventbus` represent software generally; that
correctness parity proves the two arms' work semantically equivalent; that zero direct source means
lower total context; that runtime bytes and source bytes are comparable quantities; that a public
contract is universally sufficient; that DeepSeek V4 Flash represents other models; that the
measurand is a general modularity metric; that a successful replication proves causality beyond this
frozen treatment; or that a failed replication falsifies information hiding.

Two deliberately different fixtures, if they agree, show that the phenomenon is not specific to
object storage. That is all they show.

## 21. Immutability

Frozen at the commit that adds this file. Once the first semantic call is made it is not edited. Any
later clarification is a separate record that cannot alter this plan.
