# Authority-workflow demonstration 2 — post-run audit

**Dated 2026-09-17.** Corrections and classifications relating to `pb-authority-demo-2`, recorded
here rather than by editing that run's records.

`demo/pb-authority-demo-2/` is **unmodified** apart from additions: a dated correction inside
`scaffold.py`'s accounting, a new `negative_clock_adjudication.py` beside the post-hoc check it
adjudicates, a pointer row in that directory's README, and a dated notice at the top of
`run-report.md` pointing here — added because a reader lands on the run report, not on this file,
and the withdrawn figures are stated there. **No claim, figure or record in any of those documents
was edited**; the run report's body, the protocol, intent, contracts, departures, execution record,
attempt evidence, external suite, witness and `posthoc_negative_clock.py` are exactly as the run
committed them.

Nothing below withdraws the run's substantive findings. What it corrects is the strength of three
claims made *about* those findings, and it classifies two departures the run recorded as procedural
rather than as protocol compliance.

## The interrupted call was never bounded

`scaffold.interrupted_call_bound` called the dearest **completed** call in a session an upper bound
on a call that never finished, and `spend()` used that estimate to declare the figure complete and
to admit further launches. Nothing constrains an interrupted call to cost no more than a finished
one; a call stopped at a 900-second deadline is a plausible candidate for the largest the session
ever made.

**Reproduced** against the committed function, using its own pricing module: a session whose one
completed call used 100 output tokens yields an alleged bound of `$0.000066`, while the same price
table charges `$0.0066` for an unfinished call that reached 10,000 output tokens — two orders of
magnitude above the "ceiling". No executor or provider was invoked, and this says nothing about
what the run's actual interrupted call cost.

**What the session records about that call.** Its row carries `tokens.input = 0`,
`tokens.output = 0`, `cost = 0` and no completion time. There is no partial measurement to recover:
its consumption is unknown, not small.

**Repaired prospectively.** `interrupted_call_bound` is gone; `interrupted_call_reserve` takes its
place and reports an estimate labelled `is_upper_bound: false`, and `enforced_call_bound` is the
only thing that now produces a ceiling. `departures.md` names the old function, which is correct:
it is a record of what the run did, and it is not edited. A genuine ceiling requires an identified
enforced per-call limit
(`ENFORCED_MAX_OUTPUT_TOKENS`, which is unset because nothing in this configuration enforces one);
and an unfinished call with no such limit leaves the figure **incomplete**, which refuses further
launches under the protocol's own stop condition 1. Regressions in
`tests/test_authority_demo2_accounting.py` falsify the ceiling claim rather than restate the
formula, and the enforced-limit path is checked against priced calls at and below its limit.

**Effect on the run's claims.** Re-derived from the retained run tree under the corrected rule:

| | Run report | Corrected |
|---|---|---|
| Derived from measured usage | `$0.106891` | `$0.106891` — unchanged |
| Interrupted call | "charged at an upper bound" | heuristic reserve `$0.005708`, establishes nothing |
| Charged against the limit | `$0.112599` | `$0.106891`; the reserve is not charged as if measured |
| Accounting | "complete" | **incomplete** — `admit` now refuses |

So the run report's "accounting complete" and its `$0.112599` charged figure are withdrawn. The
derived figure stands as what measured usage prices to. Under the corrected rule the protocol's
stop condition 1 fires at the first deadline expiry, which means **the five launches after
`spec-author-1` were admitted on a basis that did not hold**. That is a procedural finding about
admission, not a claim that the limit was exceeded: `$0.106891` derived is well inside `$0.40`, and
what the provider actually billed is not established here.

**A third figure, not previously reported.** The same session's own cost field, as the executor
computed it, totals `$0.163198` — about 53% above the derived figure. `evals/_profile.py` already
keeps both because they are known to disagree. Neither is provider-confirmed billing. The five
categories the repository now keeps apart are: measured token usage; cost derived from a dated
price table; an estimated reservation; a bound justified by an enforced limit; and what the
provider actually charged, which nothing here observes.

## The negative-clock claim: right finding, unsound inference

`posthoc_negative_clock.a_conforming_delay_exists` searches at most 4,096 successive floats and
returns `None` on exhaustion; its caller reads that as *no finite delay can satisfy requirement 1*.
A finite search establishes nonexistence only if its completeness is argued, and no retained
artifact argued it. The final reflection's own scripts — retained outside the repository, under the
executor's scratch directory, and therefore not durable evidence — classify states the same way and
justify it with a slope argument that does not account for `ulp` doubling at a power of two.

**The inference is falsifiable and false in general.** With `capacity = 1`, a rate whose reciprocal
is not representable at that magnitude, and a clock at `1e9`, the committed search exhausts while a
conforming delay exists 0.248 units in the last place above the exact requirement. A correct
implementation would have been reported as defective.

**An adequate argument does exist for the state actually reported**, and is now retained in
`demo/pb-authority-demo-2/negative_clock_adjudication.py` as a three-valued decision — `exists`,
`none`, `unknown` — where `none` requires covering every larger delay: admission is monotone in the
instant, so the least admitting delay is found by bisection rather than by stepping upward from the
exact deficit (which never looked *below* it, where a delay conforms trivially); excess grows while
the allowance cannot within one binary exponent; and reaching the next exponent costs more excess
than the wider allowance grants, wherever an exact check confirms it. Where it does not, the answer
is `unknown`. `tests/test_authority_demo2_negative_clock.py` exhibits a concrete monotone predicate
in exactly that regime, where the least admitting delay breaks the bound and a larger one conforms.

**What this establishes, kept separate:**

| Claim | Status |
|---|---|
| The private witness is defective at the reported state | **Verified counterexample.** It returns a finite delay whose excess is 61.796 units in the last place of the instant it reaches. If a conforming delay exists this breaks requirement 1; if none does, requirement 7 demands `math.inf`. Either way, independently of the completeness question |
| No conforming delay exists at that state | **Established** under the argument above, not by the search that reported it |
| The run's post-hoc output | Re-adjudicated: 209 refused states, 208 with a conforming delay found, and its single exhausted search is the one the argument covers. Agreement about these seeded cases, not about the inference |
| Requirements 1, 4 and 7 cannot all hold | **Established under two stated readings**, with a strictly forward exhibit: 99 `exists → none` transitions in 200 instants at the reflection's own configuration |
| The reflection's decisive exhibit | **Wrong as presented.** Its `now_B` is 1e-7 *earlier* than its `now_A`, so as printed it shows a conformant decrease. The run report caught this and reproduced the claim independently |

**The two readings are semantic, not mechanical.** "The mathematically exact requirement" is read
as the real-arithmetic deficit, as the intent's own worked examples use it. Requirement 1 is read as
requiring a *finite* delay wherever a conforming one exists — under a literal extended-real reading
`math.inf` satisfies its text, which would make "always infinity" conforming and defeat the
requirement's stated purpose. That loophole is itself an intent defect. Neither reading is something
Python decides, and the intent-defect finding depends on them.

## D1 and D4 were protocol departures

Both are recorded in `departures.md` with their reasoning, which is the behaviour the protocol asked
for. The classification is what needs correcting: the run report presents them under "missing
procedure", and a reader could take the run as having conformed to its frozen protocol. It did not.

**D1 — resolving contradictory frozen rules in favour of continuation.** The accounting clause and
the deadline clause could not both be satisfied, which the run states plainly. Choosing continuation
was a choice, and the departure note says so. But the mechanism that made continuation defensible —
charging the interrupted call at a "ceiling" — is the defect described above. With that removed, the
frozen rules resolve the other way: the figure is incomplete and stop condition 1 fires.

**D4 — raising a frozen launch ceiling mid-run.** Recomputing `5 + 1 + 3 = 9` from clauses already
in the frozen document is a defensible reading, and the run flags it as the departure most at risk
of being self-serving. It remains a mid-run change to a frozen allowance, decided by the party it
benefited. That the dollar guard was left untouched is a real mitigation and is not evidence of
conformance — an unchanged constraint that never bound cannot demonstrate discipline.

**What survives, and what does not.** The observations survive: a real reviewer found a real
specification defect; a repair closed it; a fresh reviewer then found a defect in the parent intent;
the chain stopped rather than proceeding. Those are facts about attempts that ran, and the evidence
for them is retained. What does not survive is any claim that this run is a **conforming execution
of its frozen protocol**, and therefore any use of it as a controlled observation whose conditions
were held fixed. Where an evaluation needs conformance, a departure of this kind requires a new
protocol version and a new run identity rather than an amendment — which is the separation
[evaluation.md §E24](../evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement) draws
between ordinary engineering adaptation and an experiment whose rules moved.

## Smaller identity corrections

**The interpreter identity does not resolve.** `protocol.md`, `execution-record.json` and the run
report record the interpreter as `/usr/bin/python3` at version 3.14.7. On this host
`/usr/bin/python3` is 3.9.6; the 3.14.7 interpreter is Homebrew's, first on `PATH` as `python3`.
The recorded version is almost certainly what ran, and the recorded path is wrong. Which
interpreter executed a given attempt is not recoverable from the run tree.

**The fresh-context handoff remains untested.** The run report states this already. It is repeated
here because it is the single most load-bearing limitation of both demonstrations, and because the
evaluation slice added alongside this audit
(`evals/authority_slice/`) exists to make that question answerable without another
provider-funded series.
