# CSV strict-mode paired pilot — protocol v2

**Status: frozen, NOT authorized, NOT run. No provider request has been made.**

Supersedes [`protocol.md`](protocol.md), which was frozen against harness `a119583` and never ran.
The instrument changed on 2026-09-22 — host-controller deadline enforcement, a non-mutating and
bounded acceptance check, and three resume/completion repairs
([evidence](../../docs/architecture/proofbound/evidence/workflow-readiness-2026-09-22.md)) — so a
run under the old document would not have been a run of it.

## Instrument identity

| | |
|---|---|
| Harness commit | recorded at preparation; a dirty worktree refuses in live mode |
| Protocol | this file, sha256 recorded into the run's frozen identities before any launch |
| Worker | `deepseek/deepseek-v4-flash`, variant `high`, pinned OpenCode 1.18.29 darwin-arm64, sha256 `2f24593f…0190d669` |
| Coordinator | **Codex/GPT-6**, unchanged from v1 and held constant across both arms |
| Interpreter | recorded at preparation; a launch on a different minor version refuses |

**The coordinator is Codex/GPT-6 for this pilot.** Opus developed the harness; that does not make
Opus the pilot's coordinator, and running this under a different host would be a different
configuration needing its own recorded identity. A later pair may use Claude Code/Opus — as its own
pair, with both arms moved together.

## The pairing rule

Hold the frontier coordinator constant **within each pair**:

* **Direct arm** — Codex/GPT-6 works the same goal competently with ordinary repository access,
  planning, testing and self-review. No Proofbound.
* **Proofbound arm** — the *same* Codex/GPT-6 follows the coordinator protocol and delegates routine
  work to the declared DeepSeek workers.

Comparing direct-Codex against Opus-plus-DeepSeek and attributing the difference to Proofbound
would measure the model swap, not the workflow. That comparison is not this pilot.

## Launch ceiling, derived from the enumerated paths

The workflow's three stages are `requirements` (author + fresh challenge), `consistency` (challenge
only) and `implementation` (implementer + fresh review):

| Path | Launches |
|---|---|
| minimum: no repair, no revision | **5** |
| + one implementation repair (fixer, then a *fresh* reviewer) | 7 |
| + one requirements revision (re-author, then fresh challenge) | 9 |
| + one mechanical relaunch allowance for a pre-executor failure | **10** |

v1 set "at most 9", which is exactly the repair-plus-revision path with **zero** slack — one
transport failure before the executor would have exhausted the ceiling mid-run and ended the arm for
a reason unrelated to the work. The ceiling here is **10**, derived rather than chosen, and a
pre-executor failure consumes the allowance rather than being free.

**Repair allowance, stated exactly:** one *semantic* repair of the implementation, which costs two
launches because the repair must be re-reviewed by a fresh attempt. A second genuine finding after
that stops the arm. Requirements revision is a separate allowance of one, also costing two. Neither
renews.

## Resource policy — proposed, not authorized

| | |
|---|---|
| Aggregate derived worker spend | **$1.20** across both arms |
| Reserve | **$0.10** |
| Launch ceiling | **10**, across both arms |
| Per-attempt deadline | 900 s worker, plus the host bound and teardown grace |
| Elapsed | 45 minutes per arm |
| Coordinator tokens | 60,000 observed per arm where the host exposes them |

These are admission controls over **derived** spend — measured usage priced at a dated table. They
are not a provider billing cap, and provider-confirmed billing is not observed. Switching arms,
restarting a coordinator or resuming does not renew any allowance.

**Old experiment budgets do not carry forward.** `pb-handoff-2`'s authorization is exhausted and
does not apply here.

## Predeclared outcome checks

`check_outcome.py` is fixed and identical for both arms, and fails on the unchanged project. The
goal is fixed. Neither changes unless a demonstrated defect forces a documented new version — which
would be v3, not an edit.

## Measured, separately

Correctness against the outcome check; regressions in existing behaviour; observed false acceptance
and false rejection; handoff success; manual interventions; elapsed time; and **all** observable
usage — frontier coordinator tokens and worker tokens kept apart, input/output/cached separated per
the provider's actual semantics without double-counting overlapping fields.

Missing telemetry is **unavailable, not zero**.

## The economic question, and what would answer it

Whether Proofbound reduces **frontier** consumption or **total** cost at acceptable output quality.
More DeepSeek tokens can be worthwhile; fewer frontier tokens with worse software is not a win. The
result is reported as a tradeoff — frontier tokens, worker tokens, total cost, quality — and **not**
combined into a score.

One pair is one observation. No success rate, no savings percentage, and no comparison against an
unmeasured baseline.

## Stop conditions

Time or resource ceiling; unresolved authority; unknown spend; unavailable worker; a second failed
repair; a preservation failure. Every terminal outcome is retained; none is rerolled.

## Remaining dependency

Owner-authorized worker spend under these limits, naming this protocol. Nothing else is missing.
