# BorrowDesk BD-HOLDS-1: owner-acceptance review and verifier repair — 2026-09-24

**A review after the run, and one repaired verifier defect. Nothing spent.** This is an independent
review of the delivered change, done for the owner's acceptance. It also repairs a
`verify-delivery` defect that the review reproduced. It adds to
[borrowdesk-bd-holds-1-2026-09-24.md](borrowdesk-bd-holds-1-2026-09-24.md) and leaves that record
unchanged (`P9`). No provider request was made, no worker was launched, and no other coordinator
session was started. This session's own usage is unavailable, not zero.

## What was reviewed

| | |
|---|---|
| PR #1 | head `e61d65e`, one commit on the seed `63da90eb`. It was already **squash-merged** as `fbe58c2` (2026-09-24 23:30 UTC), before this review. The merged tree, `ae00df44…`, is the head's tree, so one review covers both |
| Toolchain | Node 24.19.0 and npm 11.17.0, the official darwin-arm64 build (checksum matched `SHASUMS256.txt`). The lockfile is `e3a5d1e5…`, as the run recorded it. Python 3.14.7; no 3.10 interpreter on this host |
| Retained run | **not on this host.** The run's recorded paths do not exist here, and a search found no copy. The sealed delivery, the acceptance scripts and the owner decision's verbatim text could not be inspected, and the delivery could not be verified again |

## Application findings

**No correctness defect was demonstrated.** In order of weight:

1. **Missing coverage, now closed.** No test raced `hold` against `checkout`; the run record says so.
   A follow-up test races one hold against three checkouts across processes, released together at a
   stdin barrier, and accepts either order. Final state cannot tell a legitimate checkout-first
   order from a checkout that slipped past a committed hold, so the witness is the item the hold
   read inside its own write transaction. A mutant that reads the hold before its write transaction
   failed this test in 3 of 3 runs, and failed no other test. The real code passed 25 of 25 runs:
   150 rounds, 70 hold-first and 80 checkout-first.
2. **Documentation gaps, now addressed.** The owner's migration exception was recorded nowhere in
   the application repository. `requirements.md` still opens "Proposed requirements — not
   accepted", and it is digest-pinned. `AGENTS.md` and the behavior contract still said v0
   databases must stay readable. The README did not say that migration is one-way: the seed refuses
   a migrated file with `UNSUPPORTED_SCHEMA_VERSION`.
3. **Accepted tradeoffs, as documented.** A held item with no loan reads `status: "available"`
   beside `available: false`. Read-only commands refuse v0 files, by the owner's decision.
4. **Stated limitations not reproduced here.** `init` on a `chmod 444` v0 file succeeded, in the
   seed and the candidate alike. Only `migrate` fails there: `STORAGE_ERROR`, file unchanged.

What held, against a populated v0 database built with **the seed's own commands** (5 items, 4 loans,
2 active), with an untouched read-only copy:
- all nine ordinary commands exit 2 with `MIGRATION_REQUIRED`, and leave the file byte-identical
  with no report written;
- `init` reports `migrationRequired: true` and changes nothing;
- after `migrate`, items equal the seed's own `list-items` plus `held: false` and `available`, and
  loans are identical;
- a repeated `migrate` changes nothing;
- the v0 loan is returnable;
- 5 rounds of 8 concurrent CLI `migrate`s: each had exactly one `migrated: true`, no error, and
  records intact.

The in-process v0 fixtures in the application's tests match the seed's file (pragmas and normalized
DDL). A migrated file matches a fresh version 2 file. The existing tests were updated additively; no
assertion was weakened.

**Checks.** `npm run check`: seed 39 of 39; `e61d65e` 66 of 66; the follow-up candidate 67 of 67,
from a clean `git archive`. The owner walkthrough passes against both. GitHub CI passed on
`e61d65e` and `fbe58c2`.

**The follow-up is review work, not the worker's delivery.** It is three local commits on
`review/bd-holds-1-followup` in the BorrowDesk clone, `83b9bbf`, `3a96bf5` and `d248a7d` (tree
`8a0e4bf9…`), with no product code changed. It is not pushed. This candidate is not byte-identical
to the delivery.

## The verifier defect

**Reproduced at `a5d0ac2`** with the synthetic toolchain delivery in `tests/test_toolchain.py` and a
passing stand-in check. The matching delivery gave `verified: true`. Changing only the recorded
prepared lockfile digest, and resealing that fixture's manifest, gave
`lockfile_matches_prepared: false` beside `verified: true`. `verified` tested only the preparation's
exit code. This is inconsistent verification semantics. It is not tampering with the BorrowDesk
delivery, and it does not show that delivery's lockfile differed: the run recorded a match.

**Repaired in `30be2fd`.**
- A candidate whose lockfile, or `package.json` dependency fields, differ from the prepared ones is
  refused before `npm ci` runs.
- After `npm ci`, verification requires three things: the command succeeded, the declarations still
  match, and `node_modules` exists. Otherwise the project check is not run and `verified` is false,
  with the reason.
- `npm ci`'s stdout and stderr are kept, with the existing 4,000-character bound. They do not show
  whether a registry was contacted.
- A command that cannot start is reported, not raised.

Deliveries without a toolchain are unchanged. Regressions cover:
- a matching preparation;
- a mismatched recorded lockfile;
- a preparation that rewrites the lockfile;
- a failed preparation that installed nothing, or part;
- a preparation command that cannot start;
- a delivery without a toolchain.

At `a5d0ac2`, both mismatch cases verify. A failed `npm ci` already failed verification there, but
its output was not kept. A command that cannot start produced an error instead of a verification
result. The delivery without a toolchain passes before and after.

**CI had been red since `8e71ff4`.** GitHub CI failed on `6ffe10c` and `a5d0ac2`, on 3.10 and
3.14, with 10 errors of 1,456 tests. The toolchain test harness created its directory under
`/private/tmp`, which exists only on macOS, and CI runs on Ubuntu. So the frozen execution code of
BD-HOLDS-1 was green on macOS only. It is repaired in `0981e2d`: macOS keeps `/private/tmp`, and
other platforms use the default. That branch was exercised on macOS with a non-darwin platform, and
it has not run on Linux. The synthetic native dependency is a copy of the test interpreter, which
may not start from a copied location on Linux. That is unverified.

**Historical verification is not re-derived.** The BD-HOLDS-1 `verification.json` keeps its bytes,
and it is not on this host. Verifying that delivery again under the corrected code would be a new
observation, with its own verifier identity. It was not possible here.

## Friction, in proportion

- **Synchronous repair is not a lifecycle defect.** `decide --decision repair` launches through
  `_supervised_launch.launch`, which is the run-owned supervisor `continue` uses. If the caller
  exits, the launch still finishes, and a later `continue` waits for it. Only the caller blocks.
- **In-progress spend.** A supported, read-only display of derived spend while launches proceed is
  still needed. It is recorded under `CAP-progression` and not implemented.
