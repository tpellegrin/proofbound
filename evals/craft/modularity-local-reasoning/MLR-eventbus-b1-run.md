# `mlr-deepseek-v4-flash-high-paired-eventbus-b1` — the run

**2026-09-15/16.** Twelve slots, twelve valid trajectories, one attempt each, no retries, no stop
condition. $0.238762 of $0.50, and the figure is the whole of it. Preregistration
[`MLR-eventbus-b1-preregistration.md`](MLR-eventbus-b1-preregistration.md), sha256
`c2dd49a0864d02bb189aed01d84a2f80950605ece42659138bac0c7074c379a5`, frozen at `b158e8a`. Executed at
`0122b57`. Record:
[`craft-mlr-deepseek-v4-flash-high-paired-eventbus-b1.json`](../../results/craft-mlr-deepseek-v4-flash-high-paired-eventbus-b1.json).
How it was run: [`MLR-eventbus-b1-execution.md`](MLR-eventbus-b1-execution.md).

**Result family R1 · Core phenomenon replicates. Secondary procedural pattern: heterogeneous, and
it does not resemble q1's.**

## 1. What ran

Every frozen identity in §5 held on all twelve slots: source `9999cc1365c98e23`, task
`d0eb34a91a7b0935`, public contract `0be8e117bbb3050c`, executor `2f24593f1b8e578d`, package
`eventbus`, oracle `external_test.py`, `deepseek/deepseek-v4-flash` at `high`, implementer with
`--auto`, attribution `mlr-context-6`, profile `profile-1`, prices `deepseek-2026-09-09`. Frozen
identity `4219ca78cacefbc2fc11faa5bcccb4f4a4d64552825f640fd61b4b9f5c1d4bfc`.

Of the three host-derived identities §5 records per slot rather than freezing, two came out equal to
the frozen host's anyway — interpreter CPython 3.9.6 and boundary `b88bd43109184459` — and the
hermeticity rule resolved to `e86a9147867ceb7f` against the frozen host's `23a6e8001a46b70f`, which
is the positional difference §5 permits and the execution record explains. What the rule *checks* is
pinned directly and held.

Slot order was §9's table exactly: `full`/1, `contract`/1, `contract`/2, `full`/2, `full`/3,
`contract`/3, `contract`/4, `full`/4, `full`/5, `contract`/5, `contract`/6, `full`/6. Three pairs led
with each arm. No reordering, and no slot was offered twice.

## 2. Validity

Nothing in §11 fired. Twelve measurements, all `valid`, all `worker-executed`, all `attempt: 1`.

| check | result |
|---|---|
| hermeticity, per slot, inside the view | `clean` on all twelve, zero findings |
| declared exposure | `full` declares exactly 5, `contract` declares 0 |
| view destroyed | all twelve |
| evidence gate | `integrity_ok` and `ready_for_interpretation` on all twelve |
| unresolved attribution, item **and** component | 0 on all twelve |
| contradictions · uncovered model-visible events | 0 · 0 on all twelve |
| profile completeness | complete on all twelve, nothing missing |
| extraction | workspace and session recovered for all twelve; no retention failure |
| spend | `$0.238762` derived, `unpriced: []`, `complete: true` |

**Direct source under `contract` is structurally zero on all six pairs.** That is the treatment
working, and it is the one thing whose failure would have invalidated the comparison outright.

## 3. Correctness

Graded control-side by the unchanged fixture-B hidden oracle on the extracted workspace, gate and
regression both.

| pair category | count |
|---|---|
| **both correct** | **6** |
| `full` only | 0 |
| `contract` only | 0 |
| neither | 0 |

All six pairs are eligible for the representation comparison. §12's rule was not relaxed.

## 4. The primary measurand

§13: unique bytes of direct implementation-source representation consumed on correct runs, per arm;
pair value is `full` minus `contract` on both-correct pairs.

| pair | `full` unique | distinct representations | `full` delivered | `contract` unique | difference |
|---|---|---|---|---|---|
| 1 | 7,474 | 5 | 171,902 | 0 | +7,474 |
| 2 | 6,826 | 4 | 88,738 | 0 | +6,826 |
| 3 | 7,474 | 5 | 142,006 | 0 | +7,474 |
| 4 | 7,474 | 5 | 82,214 | 0 | +7,474 |
| 5 | 7,474 | 5 | 112,110 | 0 | +7,474 |
| 6 | 7,824 | 7 | 133,503 | 0 | +7,824 |

Count by sign: **six positive, zero zero, zero negative.** `full` median 7,474 (range 6,826–7,824);
`contract` 0 in every pair, by every route, with zero distinct representations.

Every byte of it arrived by route `source-file`, and **`replays` is 0 on all twelve slots** — no
representation was delivered twice identically in either arm.

Two things about the unit, because the numbers invite a wrong reading. First, the implementation the
`full` arm exposes is **5,980 bytes** across five files (`__init__` 511, `_dispatch` 3,262, `_errors`
436, `_receipt` 958, `_registry` 813), so 7,474 is *larger than the module itself*. That is not
double counting: §13 measures representation — "text appearing in a part OpenCode places in the
message history" — and the delivering tool's per-file framing is part of that text. Second, the
distinct-representation count says how much of the module each slot actually took in: four slots took
all five files, pair 2 took four of the five, and pair 6 took seven representations covering re-read
spans under different framing. So `full` saw substantially the whole implementation in five of six
pairs and most of it in the sixth.

The delivered column is §14's "delivered direct-source bytes", and it is a different quantity again:
the same 6,826–7,824 unique bytes were re-delivered to between 15 and 29 model calls, 82,214 to
171,902 bytes in total. Unique and delivered are not summed and not traded off against each other.

## 5. Where the arms differ, and where they do not

Separate units, never summed (§14). Medians on correct runs, with ranges.

| dimension | `full` | `contract` |
|---|---|---|
| direct source | 7,474 (6,826–7,824) | **0 (0–0)** |
| implementation runtime representation | 0 (0–32,607) | 141.5 (0–13,078) |
| implementation metadata / disclosure | 15,654 (11,240–44,765) | 1,882 (0–20,411) |
| public contract document | 0 (0–73) | 0 (0–1,038) |
| application | 13,088 (13,046–13,968) | 13,332 (13,059–13,992) |
| behaviour | 614 (104–3,261) | 542.5 (104–614) |

`source_equivalent_reconstruction` is **zero in all twelve slots, both arms**. Nothing here shows
model-authored source-equivalent text, and §14's corrected reading of that channel is not exercised
either way.

**The secondary procedural pattern is heterogeneous.** Runtime-derived representation appears in
three of six `full` slots (32,607 · 4,745 · and otherwise 0) and in four of six `contract` slots
(13,078 · 2,374 · 149 · 134, with two at 0). Neither arm compensates consistently, and the variation
inside each arm is larger than any difference between the arms' medians. Per §17 this is reported
inside the family and does not change which family is reached.

`application` is the one dimension where the two arms are close, which is what a task both arms
completed correctly ought to look like.

## 6. Why R1, and not R3, R2 or R4

§17 is evaluated in order and the first family that applies is the result.

- **F · Invalid or stopped** does not apply: §2 above. No §11 condition fired, no validity defect,
  no uncontrolled source in `contract`, spend complete.
- **R3 · No informational pressure** does not apply: `full` did materially consume the hidden
  source — 6,826 to 7,824 bytes, on every pair, never zero. The contrast is informative for this
  fixture.
- **R2 · Partial replication** does not apply: `contract` correctness was not harmed on any portion
  of the pairs. It was correct on six of six.
- **R1 · Core phenomenon replicates** applies: correctness preserved on all eligible pairs, `full`
  materially consuming direct source, `contract` consuming none.
- **R4 · Little meaningful difference** is not reached, and would not fit: the representation
  profiles are not close on the primary channel, they are 7,474 against 0.

## 7. Resources — descriptive only, and never compared between arms

§15. Ten of twelve slots ran 54.7–144.7 s wall clock. Input 17,271–34,945 tokens, output
5,577–9,470, reasoning 2,309–8,272, cache reads up to 708,224. Tool calls 36–52 per slot. Executor
cost and derived cost are both retained and still disagree; that remains out of scope.

**Two slots are conspicuous and both are `contract`.** Slot 6 (`contract`/3) ran 5,439.9 s and slot 7
(`contract`/4) ran 4,778.5 s — 40 to 50 times the median. Both are the only slots with failed tool
calls (2 each) and the only slots where the session records model calls that started and never
finished: 26 started against 21 finished, and 29 against 25. Slot 6's retained session shows four
individual assistant messages stalling 15, 15, 25 and 34 minutes, with the workspace last written 91
minutes before the session closed. This is the outbound-firewall provider stall this repository has
documented before, not slow work: `elapsed`, `session_span` and `model_seconds_derived` agree to
within a few seconds on both slots, so the time was spent waiting inside the attempt.

It does not touch the result. Both slots graded correct, hermeticity clean, attribution complete with
nothing unresolved, profile complete. **And it must not be read as a treatment effect**: §15 forbids
comparing any resource dimension between arms, which is exactly the trap two slow `contract` slots
out of six would set. Two observations of a network stall are two observations of a network stall.

What it does expose is an instrument defect, recorded in §9 below.

## 8. What this supports

On a second fixture — a different module, a different public contract, a different task, and a
structurally different boundary from `objectstore` — withholding direct readable implementation
source removed direct implementation-source representation completely while correctness was
preserved on every pair. §16's core phenomenon replicates, and §16 asked for a relation rather than a
number: q1's per-pair differences were +5,976 · +5,630 · +6,170 · +5,630 · +5,630 · +5,630 and
b1's are +7,474 · +6,826 · +7,474 · +7,474 · +7,474 · +7,824. The magnitudes differ, as §16 said they
had no reason not to. The sign and the structural zero are identical.

### §18, the cross-fixture comparison, performed after the above was recorded

Compared on the frozen dimensions only, by hand, comparing values rather than key names — q1's record
uses `arm`/`pair` where this one uses `item`/`repeat`.

| dimension | q1 · `objectstore` | b1 · `eventbus` |
|---|---|---|
| correctness pair categories | 6 both-correct | 6 both-correct |
| sign of the primary contrast | 6/6 positive | 6/6 positive |
| direct source under `contract` | zero on all six | zero on all six |
| did `full` actually consume source | yes, 5,630–6,170 | yes, 6,826–7,824 |
| runtime-derived representation, descriptively | `contract` 19,654 · 36,072 · 109 · 39,231 · 31,633 · 102; `full` mostly 0 | `contract` 0 · 149 · 2,374 · 134 · 0 · 13,078; `full` mostly 0 |
| source-equivalent model-authored representation | one slot at 210 bytes, rest 0 | 0 everywhere |
| broad trajectory strategies | heterogeneous | heterogeneous, differently |

The two fixtures agree on the core phenomenon and **disagree on the compensation**. In q1 the
`contract` arm rebuilt the interior through runtime-derived representation in most pairs, at tens of
thousands of bytes; in `eventbus` it mostly did not, and where it did the magnitudes are an order of
magnitude smaller. Raw byte magnitudes are not compared across fixtures as though they were the same
quantity, and no normalised cross-fixture scalar is invented here. What the pair of experiments
shows is that the phenomenon is not specific to object storage. Per §20, that is all it shows.

## 9. Two instrument findings, neither affecting this result

**The declared attempt ceiling does not bound an attempt.** `_mlr_run.ATTEMPT_TIMEOUT_SECONDS` is
1,800 s and its comment says it "exists so one stuck worker cannot hold a series open". Slots 6 and 7
ran 5,439.9 s and 4,778.5 s and came back with `launch_returncode: 0` and full valid trajectories, so
the bound did not fire. The path: `_mlr_boundary.launch` passes `timeout=1800` to the launcher, but
`scripts/dsd_attempt.py launch` always appends `--detach` to the low-level monitor, so the worker
stops being its child, and then implements foreground behaviour by calling `scripts/wait_worker.py`
— whose own `--timeout` defaults to **3,600 s**, is never overridden, and whose docstring states that
"a timeout is intentionally a non-event". Neither bound terminates the attempt; the detached worker
runs to completion holding the inherited pipes. Two stuck workers held this series open for 2.8
hours. Nothing was changed to accommodate it: §21 freezes the instrument once the first semantic call
is made, and it is recorded here for a later milestone.

**`paired_analysis` cannot read q1's record.** It reads `item`/`repeat`; q1 wrote `arm`/`pair`. The
execution record disclosed this in advance and §18 is performed by a person, so the comparison above
was done by hand — but the asymmetry means the committed analysis command answers for one of the two
fixtures only.

## 10. What it does not support

It does not establish that two fixtures make a phenomenon universal; that `objectstore` and
`eventbus` represent software generally; that correctness parity proves the two arms' work
semantically equivalent; that zero direct source means lower total context; that runtime bytes and
source bytes are comparable quantities; that a public contract is universally sufficient; that
DeepSeek V4 Flash represents any other model; that the measurand is a general modularity metric;
that a successful replication proves causality beyond this frozen treatment; or that this would have
falsified information hiding had it come out the other way. Six pairs are six observations. No
significance claim is made because none was preregistered, and the heterogeneity in §5 is a result
rather than noise to be averaged away. No architectural verdict, and no scalar.
