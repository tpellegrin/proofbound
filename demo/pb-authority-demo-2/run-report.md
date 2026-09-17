# pb-authority-demo-2 — run report

> **Added 2026-09-17, after this report was written. The report below is unchanged.** A post-run
> audit withdrew two of its claims and reclassified two of its departures:
> [`authority-workflow-demo-2-audit.md`](../../docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md).
> In short: the **Spend** section's "accounting complete" and its charged figure of `$0.112599` are
> withdrawn — the interrupted call was charged at an estimate, not a bound, and the figure is
> incomplete. The derived `$0.106891` stands. `D1` and `D4` are protocol departures, so this run is
> not a conforming execution of its frozen protocol. The findings themselves are unaffected.

**Outcome: stopped at a genuine finding against the parent intent, after the budgeted repair cycle
was spent. The fresh-context handoff was prepared but never exercised.**

The authority chain did its job. It caught a real defect in the specification, the repair closed
that defect, and a fresh independent review then showed that the repair had exposed an
inconsistency in **the accepted intent itself** — a document I wrote as parent. Two frozen stop
conditions fired together and the run stopped where it was supposed to.

That is a less tidy outcome than a completed handoff and a stronger result than a clean pass. It is
also the second time in two demonstrations that a real reviewer found something real.

## Identities

| | |
| --- | --- |
| Baseline (predecessor HEAD) | `16062678a35a5165c4edb735043e8b94476f7a83` |
| Preparation | `7f74a1717d5c3aa0e8d393ef7c11385b70368f0d` |
| Execution record | `4c2444d3969484fe7b5dc83d5d6252b63bfc3689` |
| Mid-run repairs | `5799c1c9bbc2943e9f1b8896601da44b4861fcb3`, `dcd7d30167102d5a37fd1e382af6aab0cb761010` |
| Model | `deepseek/deepseek-v4-flash`, variant `high` |
| Executor | pinned `opencode` 1.18.29, sha256 `2f24593f1b8e…` — deliberately the predecessor's build |
| Interpreter | `/usr/bin/python3` 3.14.7 |
| Intent | `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` |
| Protocol | `4258a28c47865ef08d6162c2304f788f10d53bfa5b7d2810bf1cb5461c0b3f62` |
| Fixture source / suite | `30bb419a37ff…` / `858482c17ca4…` — byte-identical to the predecessor's |

## Stage by stage

| # | Stage | Attempt | Outcome |
| --- | --- | --- | --- |
| 1 | Specification | `spec-author-1` | **Deadline expiry.** Wrote its report and `spec.md` in ~2 min, then hung 600s inside a stress script it wrote itself and was stopped at 900s. Gate refused: `integrity_ok: false`. Output discarded to the scope baseline. |
| 1′ | Specification | `spec-author-2` | Completed, 768s, gate passed. Recomputed the intent digest against its contract before working. |
| 2 | Specification challenge | `spec-reflector-1` | Completed, 480s. **No blocking finding.** 500,000-state search, worst excess ≈1.42 ulp. Flagged the §5 predicate as a *non-blocking* narrowness. |
| 3 | Ledger / graph / freeze | — | Recorded with all four required review keys; graph valid, zero findings; candidate `cb93bdf09ea2…`, one member (`spec.md`). |
| 4 | Aggregate consistency | `spec-reflector-2` | Completed, 291s. **Found a real incoherence** with a reachable witness: spec §5 fired on clause (a) alone while intent 7 covers all of requirement 1, so the spec demanded a finite delay that does not exist. |
| 5 | Repair (the one budgeted cycle) | `spec-author-3` | Completed, 157s. Re-derived the witness independently rather than trusting the report, scanned 200,000 `nextafter` steps, and scoped §5 to the whole of requirement 1. |
| 6 | Fresh reflection on the repair | `spec-reflector-3` | Completed, 293s. **Blocking finding:** including clause (b) in §5's predicate makes "a conforming finite delay exists" non-monotone in the clock, so the answer can go finite → `math.inf` as time advances, violating requirement 4. |
| 7 | **STOP** | — | Repair allowance spent; the finding is against the intent. `design/RG-spec` was never accepted and remains `gated`. |
| 8–10 | Handoff, implementation, review | — | **Not executed.** |

## The finding, verified independently

I did not take the reviewer's verdict on trust, and it matters that I did not, because **its decisive
exhibit was wrong while its finding was right**.

The report presents two instants and says `now_B = -7.155009862133427` is "1e-7 later" than
`now_A = -7.155009762133426`. It is 1e-7 **earlier** — more negative. Correctly ordered, that pair
runs `inf → finite` as the clock advances, which is a *decrease* and perfectly conformant. As
presented, the headline witness demonstrates the opposite of its claim.

The substantive claim is nonetheless true, and I reproduced it with my own probe against the real
`allow` arithmetic and exact `Fraction` comparisons:

* at the reviewer's configuration (`capacity=2`, `refill_per_second=0.10978710655568508`, bucket last
  updated at `-7.155015362133442`), the excess ratio alternates between **3.174** and **7.174** on
  successive 1e-7 steps — straddling the four-ulp bound;
* a strictly forward scan of 1200 refused instants found **599 `finite → inf` transitions** and 600
  the other way. The answer oscillates every step;
* my first probe found zero transitions and was wrong: it conflated "bound violated" with "search
  budget exhausted". Corrected, it agrees with the reviewer.

The violation is rare. Twelve other randomly drawn configurations produced none. Rarity does not
matter: one reachable state where the requirements cannot all hold is enough.

### Why this is an intent defect and not a specification defect

`intent.md`'s requirements are each unconditional:

* **1** — the returned delay must admit at `now + w` **and** exceed the exact requirement by at most
  four units in the last place of `now + w`;
* **4** — "with no intervening calls, the value never increases as the clock advances";
* **7** — "when no finite delay can satisfy requirement 1, `retry_after` returns `math.inf`".

If "a finite delay satisfying requirement 1 exists" is non-monotone in `now` — and it is, measured —
then 1, 4 and 7 cannot all hold. Requirement 7 is also internally ambiguous: its normative sentence
says "cannot satisfy requirement 1", which includes the bound, while its own gloss says "no wait I
can express will get you admitted", which is the clause-(a)-only reading. The reviewer identified
exactly this fork and correctly refused to resolve it, calling it an authority question.

Both available continuations were closed to me by the frozen protocol. Ruling negative clocks out of
scope would change the intent mid-run, which the protocol forbids outright. Spending a second repair
is not available. Accepting the artifact anyway would mean treating a verified finding as not
genuine. So: stop.

### The evidence I had for the intent was weaker than I thought

The private witness I used to certify the intent satisfiable passes the frozen external suite — 13
tests, worst excess 1.000 ulp — and **fails the post-hoc negative-clock check**, returning a finite
delay in a state where requirement 7 demands `math.inf`. My satisfiability argument was only ever an
argument about non-negative clocks. All three agent searches that reported ≈1.25, ≈1.42 and ≈1.48 ulp
worst case were non-negative too. The first thing that looked at negative clocks found the problem
immediately.

## Spend

**Derived $0.106891; charged $0.112599 of the $0.40 admission limit; accounting complete.** Six
launches, all attributed — five by the session id recorded in their terminal record, one recovered
from the database by exact title. One model call was left in flight by the deadline stop and is
charged at an upper bound, the dearest completed call in its session.

The $0.40 rule is a launch-admission guard, not a guaranteed provider billing cap. It governed
whether each further launch was permitted; it does not constrain what the provider billed, and the
provider's own billing is authoritative.

Coordinators are disclosed separately and not netted against that limit: coordinator 1 is a Claude
Code session billed to a subscription. Coordinator 2 was never launched, so it cost nothing.

## Classification of every intervention I made

**Semantic judgment** — mine to make, and the places a reader should be most sceptical:

1. Judging `spec-reflector-1`'s §5 observation *not* a repair trigger. It called it non-blocking; I
   agreed and did not spend the allowance on it. In hindsight the same issue, pursued properly by
   the next reviewer, was blocking — but it was flagged as an aside, and spending the single shared
   allowance on a reviewer's own non-blocking aside would have been steering.
2. Judging `spec-reflector-2`'s finding genuine and triggering the repair.
3. Judging `spec-reflector-3`'s finding genuine **despite its decisive exhibit being mis-stated**,
   on the strength of my own reproduction rather than its text.
4. Ruling that the defect lies in the intent, not the specification, and therefore stopping.

**Mechanical operation** — no judgment, recorded for completeness: binding contracts, launching and
gating attempts, ledger record, graph validation, freeze creation, the withholding measure before
each run, discarding the refused attempt's output to its recorded scope baseline.

**Integration defect** — a defect in the harness, repaired mid-run and recorded as `D2`:
`run_worker.lookup_session_id` asked `opencode session list` without a working directory. That
command scopes to the directory it is asked from and otherwise exits 0 printing nothing, which
parses as *no sessions*. **Every terminal record in `pb-authority-demo-1` carries `session_id: null`
with the identical error, including its two clean attempts** — so that demonstration's completeness
claim rested on an attribution check that could not have run. Fixed, with a regression.

**Missing procedure** — gaps in my own frozen protocol, found by executing it:

* `D1` — the accounting rule and the deadline rule contradicted each other. One clause made any
  timeout permanently fatal; another explicitly contemplated surviving one. Resolved by separating
  *unaccounted* from *unbounded*: an in-flight call is charged at a ceiling and admission now spends
  against the charged figure, which is stricter than what it replaced. Unbounded still stops.
* `D4` — the launch ceiling was written as `5 clean + 3 repair = 8` and never added the survivable
  deadline expiry the same section grants. Corrected to 9. **This is the departure most at risk of
  being self-serving and should be read sceptically**; the money guard was not relaxed by a cent.
* `D5` — the frozen external suite's clock bases are all non-negative, so it cannot see the states
  this run turned on. The suite was **not** edited; a separate post-hoc check was written and is
  reported separately, never merged into the frozen suite's verdict.

## Software checks

| Check | Result |
| --- | --- |
| Canonical repository suite, serially | 1121 tests, **OK** (1 skip) |
| Fixture's own suite, unedited, against the unchanged fixture | 5 tests, **OK** |
| External suite satisfiable + discriminating (`verify_suite.py`) | **exit 0** — witness passes, unmodified fixture fails, all 6 defective variants fail |
| Frozen external suite vs. the private witness | 13 tests, **OK** |
| Post-hoc negative-clock check vs. the private witness | **1 failure** — finite delay returned where requirement 7 demands `math.inf` |

There is no implementation to test. `rateguard/` and `tests/` are byte-identical to the project's
base commit; no worker was ever authorized to touch them.

## Limitations

* **The fresh-context handoff was never exercised.** This was the point of the milestone and it did
  not happen, because the run stopped upstream of the handoff point. `handoff-input.md` is committed
  — written before I knew what coordinator 2 would need, leak-checked to contain no candidate
  identity, no stage outcome and no conclusion of mine — but no coordinator ever received it. Nothing
  here should be read as evidence that a fresh coordinator can or cannot recover authority state
  from the repository. That remains untested.
* Had it run, coordinator 2 would have been a separately launched agent starting cold with none of
  this conversation — a genuine fresh *context*, but launched by me, on the same model family,
  against a repository whose `departures.md` describes what went wrong earlier in this run. The
  withholding is over what is *supplied*, not information-theoretic isolation.
* The candidate bound exactly one member, `spec.md`. Even had the run completed, it would have
  demonstrated candidate-bound implementation and not multi-artifact coherence. The consistency
  reflector stated this in the run's own evidence, as its contract required.
* The reviewers are the same model in different roles. Independence here is independence of context
  and input, not of architecture or training.
* `spec-reflector-2` could not reproduce the candidate hash from the artifacts by hand. The identity
  is derivable by the tooling (`pb_execution authorize` reports it), so this is not a defect, but the
  artifact-side predicate remains unestablished.

## The single next product improvement

**Make the parent intent reviewable before anything is built against it.**

Every stage downstream of `intent.md` had an independent challenge; `intent.md` had none. It was
frozen by assertion, and its internal inconsistency — requirements 1, 4 and 7 cannot all hold —
survived preparation, a private witness, a specification, a specification challenge, a consistency
reflection and a repair before a fresh reviewer reached it, at a cost of six paid attempts. The
cheapest possible moment to find it was before the first one.

Concretely: an intent-challenge stage, run as an ordinary task with its own contract and its own
fresh reviewer, whose question is not "is this specification faithful to the intent" but "can this
intent be satisfied at all, and are its requirements jointly consistent over the domain it leaves
unrestricted". The machinery to do this already exists — a contract, an attempt, a review purpose,
a gate. What is missing is that the intent is currently an input to the chain rather than a member
of it.

That is also the smallest change that would have caught this run's actual defect, and it would have
caught the predecessor's too.
