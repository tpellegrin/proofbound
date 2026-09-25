# BorrowDesk BD-MIGRATION-BACKUP-1: supervised run — 2026-09-25

**Delivered and verified on a fresh checkout, with a limitation more severe than the owner first
accepted.** Proofbound took BorrowDesk's second application change from the owner's goal to an
accepted, sealed patch: `migrate --backup <new-file>`, an explicit and verified pre-migration v0
backup. The run used 7 of 11 authorized launches and $0.408416 derived worker cost. It paused twice
for the owner. It is one more observation on a purpose-built application. It shows neither
reliability in general nor an advantage over direct coding.

## Identity

| | |
|---|---|
| Authorization | [borrowdesk-migration-backup-proposal-2026-09-24.md](borrowdesk-migration-backup-proposal-2026-09-24.md) at `8c433d2`, sha256 `6455bfd6…`; the owner's text and destination decision A recorded verbatim by `authorize-spending` |
| Execution code | scripts tree `b3dab12e…`, as at `b224c25`; checked before every step. Later Proofbound commits are documentation only |
| Target | BorrowDesk `4a0c622`, an isolated persistent clone, change `BD-MIGRATION-BACKUP-1`, goal sha256 `aa30a9e9…` |
| Worker | `deepseek-v4-flash-high` revision `2026-09-24`; OpenCode 1.18.29; Python 3.14.7; Node 24.19.0 and npm 11.17.0 declared with `--toolchain` (identity `b8fee4c5…`) |
| Coordinator | this interactive Claude Code session: requested `claude-code/opus`, self-reported Opus 5.5, none observed. No other coordinator session, subagent or cloud session |
| Project tooling | verified inside the boundary at authorization: `npm run check`, 67 of 67 |

## What happened

| Slot | Role | Result |
|---|---|---|
| 1 | requirements author | a strong proposal. It found and cited owner decision A |
| 2 | challenge | blocking F1: a repeated call on a migrated database, naming the old backup, would be refused, contradicting the goal. F2–F7 non-blocking. The coordinator added a missing refusal: the source's SQLite-owned names |
| 3 | author (repair) | the coordinator's settlements S1–S7 encoded, closing U1–U9 |
| 4 | challenge | no blocking findings. F-A and F-B, both witnessed on this host: a case-variant journal name, and the journal of a symlinked `--db`'s target, pass the destination guard |
| — | owner | accepted F-A and F-B as documented limitations, rather than a second requirements rework |
| 5 | consistency | no blocking findings. C-2: the absolute wording in the requirements against the owner's limitations, resolved by the owner's decision |
| 6 | implementer | a synchronous `serialize()` inside the migration's `BEGIN IMMEDIATE`, an exclusive `fsync`ed temporary file, verification through a fresh read-only connection, a no-clobber `link()`, a directory `fsync`. 82 tests |
| 7 | reviewer | no material defect. It independently built the seed `63da90e` and ran its commands on a backup. D1 (low): a `serialize()` failure would be classified `STORAGE_ERROR`, not `BACKUP_FAILED` |
| — | owner | accepted, knowing F-A and F-B were worse than described (below) |

**Recording decisions before requirements.** A requirements contract takes no instruction at its
first revision. The owner's destination decision therefore went into the authority directory beside
`goal.md` before the first launch, as well as the authorization receipt. The limitation decision
went in after the requirements were accepted and before consistency. Both travel in the delivery.

**The acceptance script** was frozen after the requirements and consistency were accepted, and
before implementation was bound (sha256 `6290627b…`). The binding record states each change from
the v1 scenarios with its reason:
- a deterministic concurrent-writer case was added;
- the random-writer case checks consistency, not exact equality, because the seed checks the
  schema when it opens and writes in a later transaction;
- the F-A and F-B cases are recorded as observations.

## F-A and F-B are worse than first accepted

The owner first accepted them as a *later* ordinary write deleting the backup. The coordinator
reproduced the real consequence against the candidate: **the same `migrate --backup` destroys the
backup and reports it `created: true, verified: true`**. The migration's own rollback journal is
that path. SQLite truncates the published backup when the schema change starts and deletes the
journal at commit. Witnessed: `DB.sqlite` → `db.sqlite-journal`, and `link.db` → `real.db` with
destination `real.db-journal`. The source and the migration are correct.

The owner, told this, chose to accept and to correct it after, as separate work. The delivered README
and behavior contract still say "a later ordinary write". A follow-up change is drafted, not
authorized, in the private evidence.

## Verification

`verify-delivery` ran on a fresh checkout of `4a0c622` with the sealed patch applied, under the
repaired verifier (`30be2fd`).

| Check | Result |
|---|---|
| Patch and manifest | applied; nothing altered or unlisted |
| Dependencies | `npm ci` exit 0; lockfile and dependency fields match the preparation; `node_modules` present |
| `npm run check` | 82 of 82 |
| Public acceptance (frozen script; fresh copies of seed-built v0 fixtures; not held out) | **293 of 293** |
| Accounting | $0.408416 recomputed from 1,115 retained rows; no anomalies |

What the acceptance run observed:
- **Restoration.** Every backup equals the pre-migration `STATE`: pragmas, schema, rows,
  `sqlite_sequence`. A real seed build lists, reports, adds, checks out at the next loan id, and
  returns on a copy. A plain `migrate` of a copy of the backup reproduces the migrated records.
- **Concurrency.**
  - **Competing migrations**, 5 rounds of 8 processes: one creator each time, and idempotent losers.
  - **A write pending under the lock** commits while `migrate --backup` waits. It is in the backup,
    3 of 3.
  - **With seed writers** (5 rounds), 4 v0 writes committed after the migration. They are correctly
    not in the backup, which is the seed's own check-then-write race.
  - **A lock held for 12 s** is refused as `DATABASE_BUSY` within the bound.
- **Migration failing after a backup** (a read-only source directory): the backup is kept, and the
  failure reports its location.
- **Interruption smoke check.** 30 `SIGKILL`s at random points: 20 left a migrated source with a
  completed backup, 10 an unchanged v0 source. No temporary file remained. This is process
  interruption only: power loss and write ordering are not tested.

## Costs and time

| | |
|---|---|
| Worker, derived | **$0.408416** of $0.55, complete; 228 calls. The executor's own cost estimate was $0.213245, a different computation. Provider billing was not observed |
| Launches | 7 of 11; one requirements repair; no implementation repair |
| This coordinator session | unavailable, not zero |
| Elapsed | 48 min 0 s from `start` to verified delivery, including two owner pauses; worker time 27 min 48 s |

## Friction and limits

- **Cost per launch.** It was about three times BD-HOLDS-1's. The consistency, implementer and
  reviewer launches took $0.237 together. After them, only about $0.09 remained before the $0.50 cutoff, so an
  implementation repair would not have fit. A proposal for a comparable change should set its limit
  from these rates.
- **In-progress spend.** No supported display yet; spend was read with the internal
  `_launch_budget.spend`, read-only.
- **Synchronous `decide --decision repair`.** It ran in the background to outlive the host's
  command limit. As recorded before, it uses the run's supervisor.
- **Linux.** An external review reported `tests.test_toolchain` at `8c433d2` on Linux with Python
  3.12.14: 13 passed, 4 macOS skips, no failures. That is an externally reported result, not
  observed here.
- **Nothing was merged, pushed or deployed.** The sealed delivery is in the run's `delivery/`. The
  retained copy, verification, acceptance, fixtures and decisions are in
  `~/proofbound-evidence/borrowdesk-migration-backup-1/` (private; no credentials).
