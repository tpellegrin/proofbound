# BorrowDesk migration backup: preparation — 2026-09-24

**Prepared, unpaid; nothing launched.** This is the preparation for BorrowDesk's second supervised
change, `BD-MIGRATION-BACKUP-1`, an explicit and verified pre-migration backup. It includes one
portable-test repair in Proofbound. No provider request was made and no worker was launched. No
other coordinator session was started. The proposal is in
[borrowdesk-migration-backup-proposal-2026-09-24.md](borrowdesk-migration-backup-proposal-2026-09-24.md).
The private evidence is in `~/proofbound-evidence/borrowdesk-migration-backup-1/`.

## Identities

| | |
|---|---|
| Proofbound | `origin/main` = `6fa5882` at the start. GitHub CI passed on it (Ubuntu 24.04; CPython 3.10.21 and 3.14.7; 1,461 tests, 132 skips each), so `0981e2d`'s `/private/tmp` repair holds on Linux |
| BorrowDesk | `origin/main` = `4a0c622`, the merge of PR #2 (the BD-HOLDS-1 review follow-up), tree `8a0e4bf9…`. It is identical to the reviewed `d248a7d` tree, so the owner review was not repeated. CI passed |
| Host | macOS 27.0, arm64. Python 3.14.7 (Homebrew). Node 24.19.0 and npm 11.17.0, from the official tarball (sha256 `8294b7aa…`), in `~/.local/toolchains/` |

## The portable-test defect

**Observed by the owner.** Linux, Python 3.12, `tests.test_toolchain` at `6fa5882`: 11 passes,
4 macOS-boundary skips, 1 failure and 1 error, in
`Preparation.test_acceptance_checks_use_the_prepared_bytes_and_refuse_changed_dependencies` and
`VerifyDelivery.test_the_checkout_is_prepared_like_the_run_and_checked_with_the_same_bytes`. The
error was `ModuleNotFoundError: No module named 'encodings'`.

**Cause.** The fixture's native dependency is a copy of the test interpreter, placed in
`node_modules`. A *relocatable* interpreter build cannot find its standard library from the copy's
location. Its compiled-in prefix is also missing: python-build-standalone's is `/install`.

**Why CI passed.** `setup-python`'s interpreters fall back to a compiled prefix that exists on the
runner. So CI could not show the defect, before or after the repair.

**Reproduced here.** `tests.test_toolchain` ran at `6fa5882` with python-build-standalone 3.12.14
(`20260924`, aarch64-apple-darwin, checksum verified; libpython linked statically). There were 3
failures and 1 error:
- the owner's two tests: the acceptance-check error and the `verify-delivery` failure;
- on macOS the two `Boundary` tests also run, and they failed the same way, in the log: "Could not
  find platform independent libraries", `sys.prefix = '/install'`.

That is the same mechanism on another platform. **It is not Linux validation.**

**Repair, `b224c25`.** The fixture's `npm ci` writes a `pyvenv.cfg` beside the copied interpreter,
naming the interpreter's home. That is the layout `venv --copies` produces (PEP 405).

| Module run after the repair | Result |
|---|---|
| python-build-standalone 3.12.14 | 17 of 17, no skips; `Boundary` executes the copy inside the real sandbox |
| Homebrew 3.14.7 | 17 of 17, no skips |
| The native copy removed, with `pyvenv.cfg` kept (a mutation) | 4 failures and 1 error, with each interpreter: native execution is still what the tests need |

**Linux validation of the repair is still owed.** No Linux host or container runtime is available
here. CI's interpreters cannot discriminate. The owner's command is the check:
`python -m unittest tests.test_toolchain -v` on the Linux 3.12 environment. The expected result
is 13 passes and 4 macOS skips. The canonical suite at the final code is recorded in the proposal.

## The application baseline

At `4a0c622`, `npm run check` gave 67 of 67. It ran with the pinned toolchain; the lockfile is
`e3a5d1e5…`, and better-sqlite3 13.0.3 bundles SQLite 3.53.4. The log is retained. The migration
code and the behavior contract are those reviewed for BD-HOLDS-1. The contract's "`migrate` never
creates a file" is one sentence the new option must extend explicitly.

## Feasibility

The primary documentation read was SQLite's pages on `VACUUM`, the online backup API and
`sqlite3_serialize`, and better-sqlite3's `docs/api.md` at `v13.0.3`. The disposable probes ran
on fresh copies of seed-built fixtures, with the installed versions.

| # | Question | Observed |
|---|---|---|
| P1 | `VACUUM INTO` while the migrating connection holds `BEGIN IMMEDIATE` | refused: "cannot VACUUM from within a transaction". SQLite documents this |
| P2 | What a `VACUUM INTO` copy preserves | `STATE` equal (pragmas, schema, rows, `sqlite_sequence`), bytes not equal; the seed operates on it and its next loan id is 5 |
| P3 | `VACUUM INTO` onto existing files | a non-empty file is refused and unchanged. **An existing empty file is silently written.** The source path itself is refused |
| P4 | `serialize()` inside `BEGIN IMMEDIATE` | synchronous; bytes equal to the file; `STATE` equal; the seed operates on it |
| P5 | The asynchronous `backup()` | fails ("unable to open database file") while the same connection holds the write lock; works outside it and in a read transaction. The library also advises against spanning event-loop turns inside a transaction |
| P6 | A copy taken without the write lock, then a concurrent v0 write, then `migrate` | **the copy lacks the loan**: a consistent snapshot, but not the state migrated |
| P7 | While `BEGIN IMMEDIATE` is held | a v0 writer waits about 5.5 s and fails with `DATABASE_BUSY`; a v0 reader proceeds |
| P8 | Destination aliases | a symlink or hard link shares the source's inode. A **dangling** symlink looks absent to `existsSync` and present to `lstat`. `VACUUM INTO` follows it and **creates the file at the link's target**; an exclusive create (`wx`) refuses it |
| P9 | Publishing without overwriting | `link()` refuses an existing name; `rename()` replaces it |
| P10 | A truncated copy (5 of 14 pages) | the seed fails with `STORAGE_ERROR`, and `integrity_check` reports "malformed". This case is detectable, but not every partial copy is shown to be |
| P11 | `migrate` with the source directory read-only | `STORAGE_ERROR` (`SQLITE_READONLY_DIRECTORY`); the file unchanged; the seed still reads it. This is a CLI route to "migration fails after a backup" |
| P12 | `sqlite_sequence` against `max(loans.id)` | equal: public v0 commands cannot make them differ. Loan-id allocation is checked directly, and through the seed's next checkout |
| J | A complete copy written at `<source>-journal` | **deleted by the next ordinary v0 read of the source**. SQLite owns that name, and `-wal` and `-shm` too |

**Material constraints for the requirements:**
1. **The exact pre-migration state needs the write lock across the copy and the schema change**,
   or proof at lock time that nothing changed after the copy. A snapshot alone is not enough (P6).
   `serialize()` works under the lock; `VACUUM INTO` and `backup()` do not (P1, P5). The mechanism
   is left to the worker's requirements and the challenge.
2. **The destination check must use `lstat` and exclusive creation.** It must also refuse the
   source's SQLite sibling names, even when absent (P3, P8, J).
3. **Interruption.** Anything written directly at the requested path can be left partial. Telling
   a completed backup apart needs a rule, such as publishing only a completed, verified file under
   the requested name (P9). A partial copy is not reliably recognized by opening it (P10).
4. **Verification** means comparing the copy's application records with the source's under the
   lock, not `integrity_check` alone.

**Not observed.** Power-loss and file-system write-ordering behavior; any guarantee after `fsync`
is taken from documentation, not observed.

## The production-path rehearsal

This was a throwaway run in a clone of the baseline, with the pinned executor (OpenCode 1.18.29,
`2f24593f…`), a dummy credential in a fake home, and ordinary `start --toolchain` followed by a
test-only `authorize-spending`. There was no launch and no launch ledger.
- **`project_tooling.verified: true`.** The in-boundary `npm run check` gave 67 of 67 in 6.4 s.
- **Inside the boundary:**
  - Node 24.19.0, npm 11.17.0 and TypeScript 7.0.2 run;
  - better-sqlite3 loads SQLite 3.53.4;
  - `VACUUM INTO`, a `serialize()` write, hard links and symlinks all work in the worker's
    temporary directory;
  - a read-only directory refuses writes (`EACCES`);
  - an offline `npm install` fails and changes nothing.
- **Toolchain identity:** `b8fee4c5…`. It differs from BD-HOLDS-1's `734835bf…` because this host
  has the official tarball rather than nvm's install.
- **Scripts tree:** `b3dab12e…`.

## Evidence availability

The retention plan and the split between what retained files can verify and what needs this host
are in the private directory's `README.md`. The earlier BD-HOLDS-1 delivery was unavailable on
this host. It is recorded as a limitation, not reconstructed.
