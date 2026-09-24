# BorrowDesk BD-HOLDS-1: supervised-alpha run — 2026-09-24

**Delivered and verified on a fresh checkout.** Proofbound took BorrowDesk from the owner's goal to
an accepted, sealed patch for maintenance holds and an explicit v0 migration. The run used 9 of 11
authorized launches and $0.179719 derived worker cost. One owner decision was needed, which the
coordinator requested before implementation. This is one exercise on a purpose-built application: it
shows usefulness on this task. It shows neither general reliability, nor independent production
adoption, nor any advantage over direct coding.

## Identity

| | |
|---|---|
| Authorization | [borrowdesk-proposal-2026-09-24.md](borrowdesk-proposal-2026-09-24.md) at `6ffe10c`, sha256 `a4f3addbca6aed7a3e3468ba3e6857df9e7da71f23ba179044cae10828cf95bf`; the owner's text recorded verbatim by `authorize-spending` |
| Frozen execution code | `8e71ff4`, scripts tree `8e0382ab…`, checked before every step |
| Target | BorrowDesk seed `63da90eb`, isolated checkout, change `BD-HOLDS-1`, goal sha256 `3dff6bc1…` |
| Worker | `deepseek-v4-flash-high` revision `2026-09-24`; OpenCode 1.18.29; Python 3.10.14; Node 24.19.0 and npm 11.17.0 declared with `--toolchain` |
| Coordinator | this interactive Claude Code session: requested `claude-code/opus`, self-reported Opus 5.5, none observed. No other coordinator session was started |
| Project tooling | verified inside the boundary at authorization: `npm run check`, 39 of 39 |

## What happened

| Slot | Role | Result |
|---|---|---|
| 1 | requirements author | a complete proposal that left seven choices open and put a new value in `status` |
| 2 | challenge | five findings: an unsatisfiable fixture requirement, an undefined hold payload, the corrupt-file code, untestable atomicity, and a widened compatibility exception |
| 3 | author (repair) | the coordinator settled every choice, kept `status` at its v0 meaning with additive `held`/`available` fields, and set the migration surface |
| 4 | challenge | no blocking findings; accepted |
| 5 | consistency | no blocking findings. N1: refusing ordinary commands on v0 databases is outside the goal's compatibility clause |
| — | owner | option A authorized, with constraints, recorded with `resolve-owner` |
| 6 | implementer | 65 of 65 tests pass |
| 7 | reviewer | pass; checked against a database from the real v0 release |
| 8 | fixer (repair) | prominent migration documentation; `--help` example restored; concurrent `migrate` made idempotent |
| 9 | reviewer | pass, 66 of 66; the new race test fails against the pre-fix code |

**The owner decision.** The coordinator had settled the refusal of ordinary commands on unmigrated
databases itself. Its own proposal sent any change of an existing exit status to the owner, so that
was wrong. The consistency review flagged it, and the coordinator referred it before implementation.
The owner authorized the exception, and the original goal is unchanged. The acceptance script was
then replaced before implementation. Version 1 (`f9e2ea85…`) is kept; version 2 (`45e49acb…`) adds
the decision's two expectations.

## Verification

`verify-delivery` ran on a fresh checkout of `63da90eb` with the sealed patch applied.

| Check | Result |
|---|---|
| Patch and manifest | applied; nothing altered or unlisted |
| `npm ci`, declared toolchain | exit 0; lockfile matches the preparation; no dependency change |
| `npm run check` | 66 of 66 |
| Public acceptance script v2 (outside the project; fresh copies of the untouched v0 fixture) | 17 of 17. It is public evidence, not held out: the worker authored the requirements it follows |
| Accounting | $0.179719 recomputed from 1,196 retained rows; no anomalies |

## Costs and time

| | |
|---|---|
| Worker, derived | $0.179719 of $0.55, complete. The launch threshold was never approached. Provider billing was not observed |
| Launches | 9 of 11, all reaching the executor. One requirements repair and one implementation repair, both allowances used |
| This coordinator session | unavailable, not zero |
| Elapsed | 42 min 52 s from `start` to verified delivery, including 6 min 50 s waiting for the owner; worker time 24 min |

## Friction and limits

- **Derived spend mid-run.** No supported command reports it while launches are proceeding. The
  coordinator read it with the internal `_launch_budget.spend`, read-only, as `finish` does.
- **Synchronous launches.** `decide --decision repair` launches synchronously, so it had to run in
  the background to outlive the host's command timeout.
- **`npm ci` output.** `verify-delivery` retains only its exit code, not its output. Whether it
  contacted the registry is not recorded.
- **What the delivery leaves the owner.**
  - A held, unborrowed item reads `status: "available"` beside `available: false`. This is
    documented, and follows the owner's instruction to keep `status`'s meaning.
  - A file with an unreadable header is classified by SQLite's own error.
  - `init` on a write-protected v0 file fails as a storage error.
  - No direct test races `hold` against `checkout`.
- **Nothing was merged, pushed or deployed.** The patch is in the run's `delivery/`.
